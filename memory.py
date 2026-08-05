# ==============================================================================
#  CodeRunner.AI  ::  Solution Memory — record model, vector maths, formatting
# ------------------------------------------------------------------------------
#  Author  : kurapa <kurapa@kurapa.com>
#  Project : SPEC-MEMORY-001
#  Purpose : Persist successful agentic turns and retrieve them semantically for
#            reuse as few-shot prompt context. This module is the STDLIB-ONLY
#            CORE: the record model, truncation policy (M1), dedupe hashing,
#            config parsing (M5), the pure-Python cosine oracle and the
#            adapt-or-ignore block formatting (M4).
#
#  IMPORTS : stdlib ONLY — no rich, no ollama, no httpx, no pymilvus, NO NUMPY.
#            This is load bearing, not stylistic: it is what lets this module's
#            entire test suite run on bare `pytest` with nothing else installed
#            (plan.md 1.1, acceptance.md "Testability constraints", AC-14).
#            Two seams keep it that way — recall.py is the only module that
#            touches the embedding backend, and vectorstore.py is the only
#            module that touches Milvus. Once pymilvus leaks in here, every
#            primitive test acquires a 352 MB dependency tree and the guarantee
#            is gone for good.
# ==============================================================================

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------

SCHEMA_VERSION = "2"

#: Per-field truncation limits (M1, tightened by C11/D4 at v1.1.0 from
#: thought 4000 / code 8000 / stdout 4000). The old limits were sized for a
#: 500-record cap where the worst case was 8.5 MB; at the 100,000-record cap of
#: C9 they were unbudgeted at ~2.4 GB. These bound a record to ~8 KB and the
#: worst-case volume to ~1.4 GB (V4 5).
#:
#: RECALL QUALITY IS UNAFFECTED: only the TASK text is embedded, and
#: MAX_TASK_CHARS is unchanged, so not one stored vector differs by a bit
#: because of this (AC-7c asserts exactly that).
MAX_TASK_CHARS = 2000
MAX_THOUGHT_CHARS = 1000
MAX_CODE_CHARS = 4000
MAX_STDOUT_CHARS = 1000

#: Defaults for the memory configuration block (plan.md 3).
DEFAULT_EMBED_MODEL = "nomic-embed-text:latest"
#: BOTH HALVES OF THIS NAME ARE LOAD-BEARING, and they pull in opposite
#: directions:
#:
#: * It MUST still end in `.db`. Milvus Lite validates the URI and rejects
#:   anything else outright — "uri: ... is illegal, needs start with
#:   [unix, http, https, tcp] or a local file endswith [.db]" — even though what
#:   it then creates at that path is a DIRECTORY holding a collection file set,
#:   not a file.
#: * It MUST NOT be `memory.db`. Pointed at a v1.0.x SQLite store, Milvus Lite's
#:   data_dir mkdir hits FileExistsError and every launch raises
#:   ConnectionConfigException, forever: memory would degrade on every turn of
#:   every session with the fault looking exactly like well-behaved graceful
#:   degradation. Out-of-scope item 14 says any pre-existing store is left
#:   untouched and ignored, and not colliding with its name is how.
#:
#: CODERUNNER_MEMORY_DB in docker-compose.yml must move with this.
DEFAULT_DB_PATH = Path.home() / ".coderunner" / "memory.milvus.db"
DEFAULT_TOP_K = 1
DEFAULT_MIN_SIMILARITY = 0.65
DEFAULT_MAX_RECORDS = 100000

#: Clamp ranges, mirroring the table in plan.md 3.
#:
#: MAX_RECORDS_RANGE MUST NOT DROP BELOW DEFAULT_MAX_RECORDS. `env_int()` clamps
#: AFTER falling back to the default, so the v1.0.x ceiling of 50,000 would
#: silently halve the new 100,000 cap: the SPEC, the compose file and the
#: documentation would all say 100,000 while the running system enforced 50,000,
#: with no error and no warning. AC-8 asserts the RELATIONSHIP between the two
#: constants, not merely the resulting value, so they cannot drift apart again.
#: The ceiling is 200,000 rather than exactly 100,000 so an operator can raise
#: the cap without editing source — V4 3 measured 200k as viable (260 ms
#: median, 291 ms p90 with FLAT), just disk-expensive at 1,233 MB.
TOP_K_RANGE = (1, 5)
MIN_SIMILARITY_RANGE = (0.0, 1.0)
MAX_RECORDS_RANGE = (10, 200000)

_TRUE_TOKENS = frozenset({"1", "true", "yes", "on", "y", "t"})
_FALSE_TOKENS = frozenset({"0", "false", "no", "off", "n", "f"})


# ==============================================================================
# Environment parsing helpers
# ------------------------------------------------------------------------------
# Accepted compromise (plan.md 1.1): these are not really "memory" concerns, but
# they live here rather than in a third module, because memory.py is the only
# stdlib-only module and both consumers need them.
#
# Every helper catches ValueError, clamps to a documented range, and falls back
# to the default (M5). This is a deliberate contrast with main.py:67-68, where
# a bare int(os.environ.get(...)) raises at import time — before the banner and
# before any Rich rendering — showing the user a raw traceback from a container
# that exits immediately. Retrofitting those two is out of scope (spec.md 6.8).
# ==============================================================================


def env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable, falling back to ``default``."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    token = raw.strip().casefold()
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    return default


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    """Read an int environment variable, clamped to ``[minimum, maximum]``."""
    raw = os.environ.get(name)
    if raw is None:
        return _clamp_int(default, minimum, maximum)
    try:
        value = int(raw.strip())
    except (ValueError, TypeError):
        return _clamp_int(default, minimum, maximum)
    return _clamp_int(value, minimum, maximum)


def env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    """Read a float environment variable, clamped to ``[minimum, maximum]``."""
    raw = os.environ.get(name)
    if raw is None:
        return _clamp_float(default, minimum, maximum)
    try:
        value = float(raw.strip())
    except (ValueError, TypeError):
        return _clamp_float(default, minimum, maximum)
    # NaN parses cleanly but poisons every downstream comparison (NaN >= x is
    # always False), which would silently disable retrieval. Treat as garbage.
    if math.isnan(value):
        return _clamp_float(default, minimum, maximum)
    return _clamp_float(value, minimum, maximum)


def env_str(name: str, default: str) -> str:
    """Read a non-empty string environment variable, else ``default``.

    AC-8 turns on this: ``CODERUNNER_EMBED_MODEL=""`` must yield
    ``nomic-embed-text:latest`` *including* the ``:latest`` suffix, without
    which ``grep -qx`` at coderunner:176 never matches and 274 MB is re-pulled
    on every single launch (spec.md 3.2).
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    stripped = raw.strip()
    return stripped if stripped else default


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


# ==============================================================================
# Vector maths — the pure-Python oracle
# ------------------------------------------------------------------------------
# THE IN-PROCESS COSINE SCAN IS GONE (C6 superseded at v1.1.0: Milvus Lite
# measured faster at every scale, including the original 500-record cap —
# 0.78 ms vs 13 ms). These two functions are RETAINED anyway, and not as dead
# code: they are the pure-Python oracle AC-10 uses to prove that the score
# Milvus returns for COSINE really is a cosine similarity, and higher-is-better.
#
# That matters because every threshold comparison in the system is written as a
# lower bound. A metric returning a DISTANCE would invert all of them and
# silently turn the product into one that recalls the LEAST similar record —
# while still recalling something on every turn, and so still looking alive.
#
# `l2_normalise` also still runs on the live path: recall.py normalises every
# embedding before it is stored or searched.
#
# FLOAT_VECTOR is IEEE-754 *single* precision. A float64-normalised vector does
# NOT round-trip exactly: self-similarity comes back at ~0.9999997 and can land
# marginally above 1.0. Callers must never compare these with `==`.
# ==============================================================================


def l2_normalise(vec: Sequence[float]) -> list[float]:
    """Return ``vec`` scaled to unit length; a zero vector is returned as-is."""
    values = [float(value) for value in vec]
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0.0:
        return values
    return [value / norm for value in values]


def dot(left: Sequence[float], right: Sequence[float]) -> float:
    """Dot product — cosine similarity, given L2-normalised inputs.

    A length mismatch means the two vectors are not comparable at all. Returning
    0.0 makes such a pair a guaranteed miss; raising would put an exception in
    the middle of a turn, which M5 forbids. The store's own search applies the
    `(embed_model, dim)` eligibility filter, so this is a backstop.
    """
    if len(left) != len(right):
        return 0.0
    return math.fsum(a * b for a, b in zip(left, right))


# ==============================================================================
# Task normalisation and hashing
# ==============================================================================


def normalise_task(task: str) -> str:
    """Strip, casefold, then collapse all internal whitespace to single spaces."""
    return " ".join(task.strip().casefold().split())


def task_hash(task: str) -> str:
    """SHA-256 of the normalised task — the dedupe key (M1).

    Hashed from the FULL task, before truncation, so two long tasks that differ
    only past ``MAX_TASK_CHARS`` stay distinct records rather than colliding.
    """
    return hashlib.sha256(normalise_task(task).encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string, for the ``created_at`` column."""
    return datetime.now(timezone.utc).isoformat()


def truncate(text: str, limit: int) -> str:
    """Cut ``text`` to ``limit`` characters (M1, C11).

    Public, and called from vectorstore.py: the truncation POLICY stays in the
    stdlib-only core with the constants it enforces, so C11 cannot drift apart
    from the storage layer that applies it.
    """
    return text[:limit]


# ==============================================================================
# Configuration
# ==============================================================================


@dataclass
class MemoryConfig:
    """Effective memory settings for one process (plan.md 3).

    Built once at import time by main.py and passed down, so `/memory` can
    report the EFFECTIVE values rather than the raw environment strings (AC-8).
    ``chat_model`` is supplied by the caller rather than read here, so this does
    not duplicate the MODEL_NAME constant at main.py:52.
    """

    enabled: bool
    embed_model: str
    chat_model: str
    db_path: Path
    top_k: int
    min_sim: float
    max_records: int

    @classmethod
    def from_env(cls, chat_model: str) -> "MemoryConfig":
        raw_path = os.environ.get("CODERUNNER_MEMORY_DB", "").strip()
        return cls(
            enabled=env_bool("CODERUNNER_MEMORY", True),  # constraint C4: ON
            embed_model=env_str("CODERUNNER_EMBED_MODEL", DEFAULT_EMBED_MODEL),
            chat_model=chat_model,
            db_path=Path(raw_path) if raw_path else DEFAULT_DB_PATH,
            top_k=env_int("CODERUNNER_MEMORY_TOP_K", DEFAULT_TOP_K, *TOP_K_RANGE),
            min_sim=env_float(
                "CODERUNNER_MEMORY_MIN_SIMILARITY",
                DEFAULT_MIN_SIMILARITY,
                *MIN_SIMILARITY_RANGE,
            ),
            max_records=env_int(
                "CODERUNNER_MEMORY_MAX_RECORDS", DEFAULT_MAX_RECORDS, *MAX_RECORDS_RANGE
            ),
        )


# ==============================================================================
# Records
# ==============================================================================


@dataclass
class SolutionRecord:
    """One captured successful turn (M2).

    ``id`` is ``None`` before insertion. On the way out it carries the store's
    monotonic ``seq``: the USER-FACING id shown by ``/memory list`` and taken by
    ``/memory forget <id>`` (V5a). The record's own primary key in the store is
    the hash of its task, which is what makes dedupe structural.

    ``embedding`` is held as plain floats and L2-normalised by the caller. The
    store persists it as a FLOAT_VECTOR — single precision, so it does not
    round-trip exactly.
    """

    id: int | None
    created_at: str
    task: str
    thought: str
    code: str
    stdout: str
    chat_model: str
    embed_model: str
    dim: int
    embedding: list[float] = field(default_factory=list)


# ==============================================================================
# Search results
# ------------------------------------------------------------------------------
# The ranking itself moved to vectorstore.py at v1.1.0 — it is now a Milvus
# vector search with the `(embed_model, dim)` eligibility filter riding on the
# search call (M3, AC-12) rather than an in-process scan. `Hit` stays here with
# the record model, so nothing outside the seam changed shape.
# ==============================================================================


@dataclass
class Hit:
    """A candidate record and its cosine similarity to the query vector."""

    record: SolutionRecord
    similarity: float


# ==============================================================================
# Recall block formatting and injection
# ==============================================================================

#: The adapt-or-ignore framing M4 makes non-negotiable. Kept as a named constant
#: so a test can assert it verbatim: without this sentence the block reads as an
#: instruction to reproduce, which is the R3 false-positive failure mode.
ADAPT_OR_IGNORE_SENTENCE = (
    "If it does not apply, ignore it entirely and solve the current task from\n"
    "scratch."
)

_RECALL_TEMPLATE = """\
PRIOR SUCCESSFUL SOLUTION — reference only.

A previous task was solved successfully. It may or may not apply to the current
task. {sentence} Do not copy it blindly; adapt it.

Previous task: {task}

Approach that worked:
{thought}

Script that ran successfully:
```python
{code}
```

Its actual output was:
```
{stdout}
```"""


def format_recall_block(record: SolutionRecord) -> str:
    """Render a stored solution as the few-shot system message body (M4)."""
    return _RECALL_TEMPLATE.format(
        sentence=ADAPT_OR_IGNORE_SENTENCE,
        task=record.task,
        thought=record.thought,
        code=record.code,
        stdout=record.stdout,
    )


def inject_recall(messages: list[dict], block: str) -> list[dict]:
    """Return a NEW message list with ``block`` inserted before the last message.

    This is the whole of M4's injection mechanic, kept out of main.py so it can
    be tested without a client, a console, or a conversation (AC-2).

    The input list is never mutated and its elements are carried by reference,
    so `Conversation.messages` (main.py:161) is untouched and the block stays
    ephemeral to a single request — it cannot accumulate across turns and so
    cannot worsen the unbounded-context problem in product.md 6.6.
    """
    recall_message = {"role": "system", "content": block}
    if not messages:
        return [recall_message]
    return messages[:-1] + [recall_message] + messages[-1:]


# ==============================================================================
# The /memory REPL command
# ------------------------------------------------------------------------------
# Lives here rather than in main.py, and takes an `emit` callable rather than a
# rich Console, so that the whole of AC-9 is unit-testable on bare pytest and
# memory.py stays free of third-party imports. main.py supplies
# `lambda line: console.print(line)`.
# ==============================================================================

MEMORY_COMMAND = "/memory"
LIST_DEFAULT = 10
LIST_RANGE = (1, 100)

_USAGE_LINES = (
    "Usage:",
    "  /memory                 show store status",
    "  /memory list [n]        list the n most recent records",
    "  /memory forget <id>     delete one record by id",
    "  /memory clear --yes     delete every record",
)


def _human_bytes(size: int) -> str:
    """Render an on-disk size (AC-9).

    MB and GB tiers are not cosmetic at v1.1.0. The 100,000-record cap of C9
    puts a healthy store at ~0.9 GB and a worst case at ~1.4 GB, which the KB
    tier alone would render as "943718.4 KB" — technically honest and
    practically unreadable, on the single figure spec.md 4.1 obliges this
    product to state plainly.
    """
    if size < 1024:
        return f"{size} bytes"
    for unit in ("KB", "MB"):
        size /= 1024.0  # type: ignore[assignment]
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size / 1024.0:.2f} GB"


def handle_memory_command(
    store: Any,
    text: str,
    emit: Callable[[str], None],
    cfg: "MemoryConfig | None" = None,
) -> bool:
    """Handle a ``/memory`` REPL command. ``True`` if it was ours to handle.

    Returning ``True`` tells the REPL the input was consumed locally and
    ``agentic_turn()` must not run (AC-9), mirroring the exit-word check at
    main.py:483.

    Dispatch is on the FIRST WHITESPACE TOKEN, not on a prefix: `/memoryfoo` is
    a different word and belongs to the model, not to us. A prefix match would
    silently swallow input the user did not address to this command.

    ``store`` is typed ``Any`` rather than ``VectorStore`` deliberately: naming
    the class — even under ``TYPE_CHECKING`` — would put a `vectorstore` import
    in this module's AST and break the stdlib-only assertion that keeps this
    whole suite runnable on a bare interpreter (AC-14). What is actually
    required is the eight-method interface ``count``, ``insert``, ``search``,
    ``recent``, ``delete``, ``clear``, ``stats``, ``meta_get`` — which is why
    substituting the backend needed no change here at all.
    """
    parts = text.strip().split()
    if not parts or parts[0].casefold() != MEMORY_COMMAND:
        return False

    if store is None:
        emit("Solution memory is disabled or unavailable for this session.")
        return True

    subcommand = parts[1].casefold() if len(parts) > 1 else ""
    arguments = parts[2:]

    if subcommand == "":
        _emit_status(store, emit, cfg)
    elif subcommand == "list":
        _emit_list(store, emit, arguments)
    elif subcommand == "forget":
        _emit_forget(store, emit, arguments)
    elif subcommand == "clear":
        _emit_clear(store, emit, arguments)
    else:
        emit(f"Unknown subcommand: {parts[1]}")
        for line in _USAGE_LINES:
            emit(line)
    return True


def _emit_status(
    store: Any, emit: Callable[[str], None], cfg: "MemoryConfig | None"
) -> None:
    embed_model = cfg.embed_model if cfg is not None else None
    stats = store.stats(embed_model, None)

    emit("Solution memory")
    emit(f"  path        : {stats['path']}")
    emit(f"  records     : {stats['count']}")
    emit(f"  eligible    : {stats['eligible']}")
    emit(f"  embed model : {stats['embed_model'] or 'n/a'}")
    emit(f"  dimension   : {stats['dim'] if stats['dim'] is not None else 'n/a'}")
    emit(f"  on disk     : {_human_bytes(stats['bytes'])}")
    if cfg is not None:
        # AC-8: the EFFECTIVE values, after clamping and fallback, never the
        # raw environment strings.
        emit(f"  threshold   : {cfg.min_sim}")
        emit(f"  top k       : {cfg.top_k}")
        emit(f"  record cap  : {cfg.max_records}")
    if stats["error"]:
        emit(f"  status      : degraded ({stats['error']})")


def _emit_list(
    store: Any, emit: Callable[[str], None], arguments: Sequence[str]
) -> None:
    limit = LIST_DEFAULT
    if arguments:
        try:
            limit = _clamp_int(int(arguments[0]), *LIST_RANGE)
        except (ValueError, TypeError):
            limit = LIST_DEFAULT

    records = store.recent(limit)
    if not records:
        emit("No records stored yet.")
        return
    for record in records:
        task = record.task.replace("\n", " ")
        if len(task) > 68:
            task = task[:67] + "…"
        emit(f"  [{record.id}] {record.created_at[:19]}  {task}")


def _emit_forget(
    store: Any, emit: Callable[[str], None], arguments: Sequence[str]
) -> None:
    if len(arguments) != 1:
        emit("Usage: /memory forget <id>")
        return
    try:
        record_id = int(arguments[0])
    except (ValueError, TypeError):
        emit(f"Not a record id: {arguments[0]}")
        return

    if store.delete(record_id):
        emit(f"Deleted record {record_id}.")
    else:
        emit(f"Record {record_id} not found — nothing deleted.")


def _emit_clear(
    store: Any, emit: Callable[[str], None], arguments: Sequence[str]
) -> None:
    if "--yes" not in arguments:
        # AC-9: no confirmation flag means delete nothing and print the form.
        emit("Refusing to clear without confirmation.")
        emit("Required form: /memory clear --yes")
        return
    emit(f"Cleared {store.clear()} record(s).")
