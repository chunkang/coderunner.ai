# ==============================================================================
#  CodeRunner.AI  ::  Solution Memory — the Milvus Lite storage seam
# ------------------------------------------------------------------------------
#  Author  : kurapa <kurapa@kurapa.com>
#  Project : SPEC-MEMORY-001 v1.1.0
#  Purpose : Every `pymilvus` call in the product lives here and nowhere else
#            (C12/D5). memory.py keeps the record model, truncation, dedupe
#            hashing, config parsing and recall formatting, and stays STDLIB
#            ONLY so its whole suite still runs on a bare interpreter; this
#            module mirrors what recall.py already does for `ollama`.
#
#  IMPORTS : `pymilvus` — and no other first-party module may import it.
#            numpy arrives transitively with pymilvus[milvus_lite] and is
#            ACCEPTED, NOT ADOPTED: no first-party module may import it
#            (spec.md 6 item 7, AC-14).
#
#  INSTALL : `pip install "pymilvus[milvus_lite]"`. The extra is NOT optional —
#            bare `pymilvus` raises ConnectionConfigException at
#            MilvusClient("<path>") (V4 1).
#
#  CONTRACT: every public method DEGRADES rather than raising. `open()` returns
#            None on any failure, mutators return False/0, readers return empty
#            results. That is M5, and it is why a memory-subsystem fault can
#            never abort a turn.
# ==============================================================================

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pymilvus import DataType, MilvusClient

from memory import (
    MAX_CODE_CHARS,
    MAX_STDOUT_CHARS,
    MAX_TASK_CHARS,
    MAX_THOUGHT_CHARS,
    SCHEMA_VERSION,
    Hit,
    SolutionRecord,
    task_hash,
    truncate,
)

# ------------------------------------------------------------------------------
# Keep the backend off the user's terminal
# ------------------------------------------------------------------------------
# pymilvus logs every failed RPC at ERROR with a full traceback, through its own
# handler bound to the real stderr — it is not captured by redirect_stderr, and
# it lands in the middle of a Rich-rendered turn.
#
# That is not cosmetic. M5 requires EXACTLY ONE status line for a memory fault
# and behaviour otherwise identical to the pre-feature product, and AC-1
# requires a cold start to be indistinguishable from it. Left alone, a single
# degraded turn prints ~20 lines of library traceback per failed call, and this
# module makes up to three such calls per turn — so the product would look
# catastrophically broken at precisely the moment M5 says it must look normal.
#
# We already report every one of these faults ourselves, in one line, with the
# store's own vocabulary. CRITICAL rather than NOTSET so that a genuine
# emergency can still speak.
for _backend_logger in ("pymilvus", "milvus_lite"):
    logging.getLogger(_backend_logger).setLevel(logging.CRITICAL)

# ------------------------------------------------------------------------------
# Collection design (plan.md 2, settled by V5a/V5b)
# ------------------------------------------------------------------------------

SOLUTIONS_COLLECTION = "solutions"
META_COLLECTION = "meta"

#: PINNED EXPLICITLY, never left to a library default (C10, AC-11). FLAT
#: measured FASTER than HNSW at 100k (133 ms vs 190 ms median) and far better at
#: the tail at 200k (291 ms vs 1,742 ms p90) — V4 3. The choice is
#: counter-intuitive, so a future library default is as likely to move away from
#: it as toward it. AC-11 reads both values back off the collection.
INDEX_TYPE = "FLAT"
METRIC_TYPE = "COSINE"

#: meta keys. `next_seq` and `min_seq` CANNOT be recovered from the main
#: collection — it cannot be enumerated (trap D) — so they are persisted here.
META_SCHEMA_VERSION = "schema_version"
META_NEXT_SEQ = "next_seq"
META_MIN_SEQ = "min_seq"
META_EMBED_MODEL = "embed_model"
META_DIM = "dim"

#: Milvus requires at least one vector field in every collection, so the meta
#: side-collection carries a one-dimensional placeholder that is never searched.
_META_VECTOR = [0.0]
_META_DIM = 1

#: VARCHAR capacity, in the units the ENGINE counts. Milvus Lite counts
#: CHARACTERS ("value length 11 exceeds max_length=10" for 11 ASCII characters,
#: while 5 CJK characters — 15 bytes — fit in 10), but a Milvus server counts
#: BYTES. The C11 limits are character limits, so the declared capacity carries
#: UTF-8 headroom: without it a 2,000-character CJK task would be a valid
#: truncation and an invalid row, and capture would fail for non-Latin users
#: only. Headroom is free — Milvus permits up to 65,535.
_UTF8_HEADROOM = 4

#: `query()` is hard-capped at 16,384 rows and `query_iterator` is broken
#: (trap D), so nothing here may depend on enumerating the collection.
_QUERY_CEILING = 16384

#: How far `recent()` widens its range filter before giving up. `order_by` is a
#: silent no-op, so the newest N records are found by walking back from
#: `next_seq`; a store riddled with pruning and dedupe gaps needs a few passes.
_RECENT_WINDOW_GROWTH = 8
_RECENT_MAX_PASSES = 6

#: A prune pass either deletes rows or widens by _RECENT_WINDOW_GROWTH, so the
#: boundary reaches next_seq geometrically. The bound exists only so that a
#: store whose meta has been corrupted cannot spin.
_PRUNE_MAX_PASSES = 64

_RECORD_FIELDS = (
    "task_hash",
    "seq",
    "created_at",
    "task",
    "thought",
    "code",
    "stdout",
    "chat_model",
    "embed_model",
    "dim",
    "embedding",
)


def _quote(value: str) -> str:
    """Render ``value`` as a Milvus expression string literal.

    Filters are expression STRINGS, so an embedding-model tag carrying a quote
    or a backslash has to be escaped rather than interpolated. This version of
    pymilvus rejects `filter_params` placeholders, so JSON quoting — which
    produces exactly the escapes the expression parser accepts — is the
    portable form.
    """
    return json.dumps(str(value))


# ==============================================================================
# The store
# ==============================================================================


class VectorStore:
    """Embedded Milvus Lite solution store (M1).

    The public surface is deliberately the shape the callers already used, so
    `recall.py` and `handle_memory_command()` needed no restructuring:
    ``open``, ``close``, ``count``, ``insert``, ``search``, ``recent``,
    ``delete``, ``clear``, ``stats``, ``meta_get``.
    """

    def __init__(self, client: Any, path: Path) -> None:
        self._client = client
        self.path = path
        self._dim: int | None = None
        self._next_seq = 0
        self._min_seq = 0

    # -- lifecycle ------------------------------------------------------------

    @classmethod
    def open(cls, path: Path | str, dim: int | None = None) -> VectorStore | None:
        """Open (creating if needed) the store at ``path``; ``None`` on any failure.

        Covers AC-3d (unwritable path), AC-3e (the path is a file rather than a
        Milvus directory), AC-3f (absent parent that cannot be created) and
        AC-3i (the `milvus_lite` extra missing, so MilvusClient raises
        ConnectionConfigException) with a single return contract.

        THE `except` AROUND THE CONSTRUCTOR ALSO CARRIES AC-3g. V5d measured
        Milvus Lite as refusing concurrent access outright: with two clients on
        one database the loser raises ConnectionConfigException AT OPEN, not on
        a later operation. There is no equivalent of the WAL + busy_timeout=3000
        the SQLite design used to let sessions coexist. Uncaught, a second
        concurrent session would crash the REPL at startup rather than
        degrading; caught, it runs with memory off and one startup warning,
        which is M5 working as specified. `coderunner:263` launches with
        `--name coderunner` so a second launcher collides on the container name
        first, but `docker compose run --rm -T coderunner` sets no name and can
        genuinely overlap.

        ``dim`` is optional because it is DERIVED from the first embedding at
        runtime, never hardcoded: the nomic-embed-text model page does not
        publish a dimension, and deriving it is also what survives a model swap.
        Until a dimension is known the solutions collection does not exist,
        which reads as an empty store — exactly the cold start AC-1 describes.
        """
        resolved = Path(path)
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            client = MilvusClient(uri=str(resolved))
        except Exception:
            return None

        store = cls(client, resolved)
        try:
            store._init_meta()
            store._restore_state(dim)
        except Exception:
            store.close()
            return None
        return store

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    # -- schema ---------------------------------------------------------------

    def _init_meta(self) -> None:
        """Create the meta side-collection idempotently and stamp the version."""
        if not self._client.has_collection(META_COLLECTION):
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
            schema.add_field("key", DataType.VARCHAR, is_primary=True, max_length=64)
            schema.add_field("value", DataType.VARCHAR, max_length=1024)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=_META_DIM)
            self._create(META_COLLECTION, schema, "vector")
        else:
            self._load(META_COLLECTION)
        # AC-1: the meta side-collection exists with schema_version, next_seq
        # AND min_seq persisted from the moment the store is created. Leaving
        # the watermarks unwritten until the first prune would read, on a
        # reopen, as "no value recorded" — indistinguishable from a store whose
        # meta had been lost, which is the one thing trap D makes unrecoverable.
        self._meta_set_once(META_SCHEMA_VERSION, SCHEMA_VERSION)
        self._meta_set_once(META_NEXT_SEQ, "0")
        self._meta_set_once(META_MIN_SEQ, "0")

    def _create(self, name: str, schema: Any, vector_field: str) -> None:
        """Create a collection with the index and metric PINNED (C10).

        The index is built out of line and the collection loaded explicitly
        rather than letting `create_collection(index_params=...)` do both: that
        convenience path blocks for a flat 0.5 s per collection waiting on an
        index that FLAT does not have to build.
        """
        self._client.create_collection(name, schema=schema)
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name=vector_field, index_type=INDEX_TYPE, metric_type=METRIC_TYPE
        )
        self._client.create_index(name, index_params, sync=False)
        self._load(name)

    def _load(self, name: str) -> None:
        """Load ``name`` into memory. MANDATORY on every open (V5c).

        A collection created in this process is implicitly loaded, so the first
        session works perfectly. A PERSISTED collection comes back in state
        `released`, and every `search`/`query` against it then raises
        `MilvusException (code=101) ... call load() before search`. That
        exception lands in recall.py's broad except, is reported once as a
        fault, and leaves solution memory dead from session two onward while
        session one looked flawless — trap A's shape exactly.

        `get_collection_stats()` does NOT require this, which is why `count()`
        stays usable pre-load and the cold-start short-circuit is unaffected.

        Idempotent, and measured at 0.17 s on a real 100,000-record collection.
        """
        self._client.load_collection(name)

    def _solutions_schema(self, dim: int) -> Any:
        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
        # task_hash is the PRIMARY KEY, which makes dedupe STRUCTURAL: upsert()
        # replaces in place, and there is no surrogate key left for the engine
        # to reallocate (V5a). The hazard that removes did not vanish, it moved
        # into insert() — see the point query there.
        schema.add_field("task_hash", DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field("seq", DataType.INT64)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=dim)
        schema.add_field("created_at", DataType.VARCHAR, max_length=64)
        schema.add_field("task", DataType.VARCHAR, max_length=MAX_TASK_CHARS * _UTF8_HEADROOM)
        schema.add_field("thought", DataType.VARCHAR, max_length=MAX_THOUGHT_CHARS * _UTF8_HEADROOM)
        schema.add_field("code", DataType.VARCHAR, max_length=MAX_CODE_CHARS * _UTF8_HEADROOM)
        schema.add_field("stdout", DataType.VARCHAR, max_length=MAX_STDOUT_CHARS * _UTF8_HEADROOM)
        schema.add_field("chat_model", DataType.VARCHAR, max_length=256)
        schema.add_field("embed_model", DataType.VARCHAR, max_length=256)
        schema.add_field("dim", DataType.INT64)
        return schema

    def _restore_state(self, dim: int | None) -> None:
        """Read the persisted watermarks back, and load an existing collection."""
        self._next_seq = _as_int(self.meta_get(META_NEXT_SEQ), 0)
        self._min_seq = _as_int(self.meta_get(META_MIN_SEQ), 0)

        if self._client.has_collection(SOLUTIONS_COLLECTION):
            self._dim = self._collection_dim()
            self._load(SOLUTIONS_COLLECTION)  # V5c — see _load()
        elif dim:
            self._ensure_collection(int(dim))

    def _collection_dim(self) -> int | None:
        for field in self._client.describe_collection(SOLUTIONS_COLLECTION)["fields"]:
            if field["name"] == "embedding":
                return int(field["params"]["dim"])
        return None  # pragma: no cover - a collection we created always has one

    def _ensure_collection(self, dim: int) -> bool:
        """Make the solutions collection exist at ``dim``; False if it cannot.

        A collection carries exactly ONE vector dimension, so a model swap that
        changes the dimension cannot simply be absorbed. Existing records are
        kept and the write declines; once the store is empty — after
        `/memory clear --yes`, or after pruning — the collection is rebuilt at
        the new dimension, so there is a way back that does not require the
        operator to delete a Docker volume.
        """
        if self._dim == dim:
            return True
        if self._dim is not None:
            if self.count() > 0:
                return False
            self._drop_solutions()
        self._create(SOLUTIONS_COLLECTION, self._solutions_schema(dim), "embedding")
        self._dim = dim
        return True

    def _drop_solutions(self) -> None:
        self._client.drop_collection(SOLUTIONS_COLLECTION)
        self._dim = None

    # -- meta -----------------------------------------------------------------

    def meta_get(self, key: str) -> str | None:
        try:
            rows = self._client.query(
                META_COLLECTION,
                filter=f"key == {_quote(key)}",
                output_fields=["value"],
                limit=1,
            )
        except Exception:
            return None
        return str(rows[0]["value"]) if rows else None

    def _meta_set(self, key: str, value: str) -> None:
        self._client.upsert(
            META_COLLECTION, [{"key": key, "value": str(value), "vector": _META_VECTOR}]
        )

    def _meta_set_once(self, key: str, value: str) -> None:
        if self.meta_get(key) is None:
            self._meta_set(key, value)

    def _meta_clear(self, key: str) -> None:
        self._client.delete(META_COLLECTION, ids=[key])

    # -- writes ---------------------------------------------------------------

    def insert(self, record: SolutionRecord, max_records: int) -> bool:
        """Truncate, upsert (dedupe by task hash), then prune to ``max_records``.

        THE READ BEFORE THE WRITE IS LOAD-BEARING (R14). `upsert()` overwrites
        every non-key field, `seq` included — V5a's own trace shows the replaced
        row coming back with whatever `seq` the caller supplied. Point-querying
        the existing row by primary key and carrying `seq` and `created_at`
        forward is what keeps `/memory forget <id>` addressing the same record
        after a re-ask, and keeps `created_at` a fact about when the task was
        first learned rather than last seen. A point query by primary key is not
        affected by the 16,384-row `query()` cap.

        Omitting a non-key field from the upsert instead of carrying it forward
        does NOT silently null it — Milvus raises DataNotMatchException (V5e) —
        so this particular mistake fails loudly. Reallocating `seq` from a fresh
        counter would not.
        """
        if not record.embedding:
            return False
        try:
            vector = [float(value) for value in record.embedding]
            if not self._ensure_collection(len(vector)):
                return False

            digest = task_hash(record.task)
            existing = self._point_query(digest)
            if existing is None:
                seq = self._next_seq
                created_at = record.created_at
            else:
                seq = int(existing["seq"])
                created_at = str(existing["created_at"])

            self._client.upsert(
                SOLUTIONS_COLLECTION,
                [
                    {
                        "task_hash": digest,
                        "seq": seq,
                        "embedding": vector,
                        "created_at": created_at,
                        "task": truncate(record.task, MAX_TASK_CHARS),
                        "thought": truncate(record.thought, MAX_THOUGHT_CHARS),
                        "code": truncate(record.code, MAX_CODE_CHARS),
                        "stdout": truncate(record.stdout, MAX_STDOUT_CHARS),
                        "chat_model": record.chat_model,
                        "embed_model": record.embed_model,
                        "dim": int(record.dim),
                    }
                ],
            )

            if existing is None:
                self._next_seq = seq + 1
                self._meta_set(META_NEXT_SEQ, str(self._next_seq))
            self._meta_set_once(META_EMBED_MODEL, record.embed_model)
            self._meta_set_once(META_DIM, str(int(record.dim)))
            self._prune(max_records)
        except Exception:
            return False
        return True

    def _point_query(self, digest: str) -> dict[str, Any] | None:
        rows = self._client.query(
            SOLUTIONS_COLLECTION,
            filter=f"task_hash == {_quote(digest)}",
            output_fields=["seq", "created_at"],
            limit=1,
        )
        return dict(rows[0]) if rows else None

    def _prune(self, max_records: int) -> None:
        """Delete oldest-first until the row count is at or below the cap (M1).

        A CONVERGING DELETE-BY-FILTER LOOP, AND IT MUST STAY ONE.
        `order_by` is ACCEPTED AND SILENTLY IGNORED by Milvus Lite: V5 inserted
        [50, 10, 90, 30, 70, ...] and `query(order_by="seq")` returned insertion
        order, unsorted, with no exception. `query()` is also hard-capped at
        16,384 rows and `query_iterator` is broken, so the collection cannot be
        enumerated at all. "Query the oldest N and delete them" therefore
        deletes ARBITRARY records, passes a `count == cap` assertion, and evicts
        the user's most valuable memories while `/memory` reports exactly the
        expected number of entries.

        DO NOT "simplify" this into a sorted query. AC-7a asserts which records
        survived, from a shuffled insertion order, precisely so that a wrong
        implementation cannot pass by coincidence, and AC-13 asserts the
        parameter appears nowhere in the source.

        Ordering is by `seq`, never by `created_at`: timestamps have second
        granularity and AC-7a inserts in a tight loop, so they tie and "the
        oldest record" becomes non-deterministic. Sequence gaps left by dedupe
        and by earlier pruning are permanent and harmless — the loop converges
        on `row_count`, not on arithmetic.
        """
        cap = max(0, int(max_records))
        total = self.count()
        batch = max(1, total - cap)
        for _ in range(_PRUNE_MAX_PASSES):
            if total <= cap or self._min_seq >= self._next_seq:
                return
            boundary = min(self._min_seq + batch, self._next_seq)
            self._client.delete(SOLUTIONS_COLLECTION, filter=f"seq < {boundary}")
            self._min_seq = boundary
            self._meta_set(META_MIN_SEQ, str(boundary))

            remaining = self.count()
            # A pass that deleted nothing walked over a gap: widen rather than
            # crawl, so a store whose low sequence numbers are all holes still
            # converges in a bounded number of passes.
            batch = batch * _RECENT_WINDOW_GROWTH if remaining == total else max(1, remaining - cap)
            total = remaining

    def delete(self, seq: int) -> bool:
        """Resolve ``seq`` to its primary key and delete that record (AC-9, V5a).

        The resolution is not ceremony. Milvus reports success for a delete by
        an id that never existed, so `/memory forget 99999` would claim to have
        deleted something; and `seq` is not the primary key, so it cannot be
        deleted by directly.
        """
        if self._dim is None:
            return False
        try:
            rows = self._client.query(
                SOLUTIONS_COLLECTION,
                filter=f"seq == {int(seq)}",
                output_fields=["task_hash"],
                limit=1,
            )
            if not rows:
                return False
            self._client.delete(SOLUTIONS_COLLECTION, ids=[rows[0]["task_hash"]])
        except Exception:
            return False
        return True

    def clear(self) -> int:
        """Drop every record, and with them the collection's fixed dimension.

        Dropping rather than deleting row by row is what makes the store
        recoverable after an embedding-model change: the next capture rebuilds
        the collection at whatever dimension the new model produces. It also
        actually returns the disk, which at the 100,000 cap is ~0.9 GB.

        `next_seq` is deliberately NOT reset. Reusing sequence numbers would
        make `/memory forget 0` mean two different records over one session.
        """
        try:
            total = self.count()
            if self._dim is not None:
                self._drop_solutions()
            self._min_seq = self._next_seq
            self._meta_set(META_MIN_SEQ, str(self._min_seq))
            self._meta_clear(META_EMBED_MODEL)
            self._meta_clear(META_DIM)
        except Exception:
            return 0
        return total

    # -- reads ----------------------------------------------------------------

    def count(self) -> int:
        """Total stored records. 0 on any failure, so callers can branch safely.

        `get_collection_stats()["row_count"]` is the ONLY trustworthy count
        signal: it is accurate, cheap, uncapped, needs no `load()`, and V5e
        measured it as immediately consistent after insert, upsert and delete
        with no `flush()`. `query()` is not — it is hard-capped at 16,384 rows
        (trap D), so a count derived from it ships green and understates on any
        large store.

        The cold-start guard is not an optimisation. Asking Milvus about a
        collection that does not exist yet RAISES, and a raised RPC is LOGGED
        with a full traceback; recall.py calls this up to three times per turn,
        so without the guard the first turn of every fresh install would print
        some sixty lines of library traceback while AC-1 requires that turn to
        be indistinguishable from the pre-feature product.
        """
        if self._dim is None:
            return 0  # no collection yet — a cold start, not a fault
        try:
            return int(self._client.get_collection_stats(SOLUTIONS_COLLECTION)["row_count"])
        except Exception:
            return 0

    def search(
        self,
        query_vec: Sequence[float],
        top_k: int,
        min_sim: float,
        embed_model: str,
        dim: int,
    ) -> list[Hit]:
        """Top-``top_k`` eligible records at or above ``min_sim``, best first.

        The comparison is `>=`: M3 defines a miss as similarity *below* the
        threshold, so the boundary value itself is a hit.

        ELIGIBILITY RIDES ON THE SEARCH CALL as a Milvus scalar filter, never as
        a post-filter (AC-12). Milvus ranks before we can inspect, so with
        top_k=1 a stale vector that is a perfect raw match would occupy the only
        result slot and be discarded afterwards — yielding a miss where a hit
        was available, and looking like bad luck rather than a bug (R8).

        The score is COSINE, higher-is-better, directly comparable to the
        threshold (AC-10). A metric returning a distance would invert every
        comparison in the system.
        """
        if not query_vec or top_k <= 0 or self._dim is None:
            return []
        try:
            results = self._client.search(
                SOLUTIONS_COLLECTION,
                data=[[float(value) for value in query_vec]],
                limit=int(top_k),
                filter=self._eligibility_filter(embed_model, dim),
                search_params={"metric_type": METRIC_TYPE},
                output_fields=list(_RECORD_FIELDS),
            )
        except Exception:
            # No collection yet, a dimension mismatch, or a store that has gone
            # away: all of them are a miss, none of them may reach the turn (M5).
            return []

        hits = [
            Hit(record=_entity_to_record(match["entity"]), similarity=float(match["distance"]))
            for match in results[0]
            if float(match["distance"]) >= min_sim
        ]
        # Descending similarity; ties broken toward the more recent record. This
        # is a Python sort of at most `top_k` already-ranked rows, NOT a sorted
        # query — see _prune() for why that distinction matters.
        hits.sort(key=lambda hit: (hit.similarity, hit.record.id or 0), reverse=True)
        return hits

    @staticmethod
    def _eligibility_filter(embed_model: str, dim: int) -> str:
        return f"embed_model == {_quote(embed_model)} and dim == {int(dim)}"

    def recent(self, limit: int) -> list[SolutionRecord]:
        """The ``limit`` most recently inserted records, newest first (AC-9).

        `ORDER BY id DESC LIMIT ?` has no Milvus equivalent — `order_by` is a
        silent no-op — so the window is derived from `next_seq` by RANGE FILTER
        and sorted IN PYTHON. Dedupe and pruning leave permanent gaps, so a
        window sized exactly `limit` can come back short; it widens until it has
        enough or reaches `min_seq`.
        """
        if limit <= 0 or self._dim is None:
            return []
        window = max(int(limit), 16)
        rows: list[dict[str, Any]] = []
        try:
            for _ in range(_RECENT_MAX_PASSES):
                low = max(self._min_seq, self._next_seq - window)
                rows = list(
                    self._client.query(
                        SOLUTIONS_COLLECTION,
                        filter=f"seq >= {low}",
                        output_fields=list(_RECORD_FIELDS),
                        limit=min(max(window, 1), _QUERY_CEILING),
                    )
                )
                if len(rows) >= limit or low <= self._min_seq:
                    break
                window *= _RECENT_WINDOW_GROWTH
        except Exception:
            return []

        rows.sort(key=lambda row: int(row["seq"]), reverse=True)
        return [_entity_to_record(row) for row in rows[:limit]]

    def stats(self, embed_model: str | None = None, dim: int | None = None) -> dict[str, Any]:
        """Everything ``/memory`` needs to report (AC-9).

        Falls back to the first-observed values in ``meta`` when the caller does
        not supply the current configuration.
        """
        result: dict[str, Any] = {
            "path": str(self.path),
            "count": 0,
            "eligible": 0,
            "embed_model": embed_model,
            "dim": dim,
            "bytes": 0,
            "error": None,
        }
        try:
            if self.meta_get(META_SCHEMA_VERSION) is None:
                raise RuntimeError("meta side-collection unreadable")
            result["count"] = self.count()
            if result["embed_model"] is None:
                result["embed_model"] = self.meta_get(META_EMBED_MODEL)
            if result["dim"] is None:
                result["dim"] = _as_int(self.meta_get(META_DIM), None)
            if result["embed_model"] is not None and result["dim"] is not None:
                result["eligible"] = self._eligible_count(result["embed_model"], result["dim"])
        except Exception as err:
            result["error"] = f"{err.__class__.__name__}: {err}"

        result["bytes"] = self._disk_bytes()
        return result

    def _eligible_count(self, embed_model: str, dim: int) -> int:
        """Count matching rows WITHOUT enumerating them (trap D).

        `count(*)` is answered by the engine; reading the rows back and taking
        `len()` would silently stop at 16,384.
        """
        if self._dim is None:
            return 0
        rows = self._client.query(
            SOLUTIONS_COLLECTION,
            filter=self._eligibility_filter(embed_model, dim),
            output_fields=["count(*)"],
        )
        return int(rows[0]["count(*)"]) if rows else 0

    def _disk_bytes(self) -> int:
        """The RECURSIVE size of the Milvus file set.

        Milvus Lite writes a directory tree — `collections/<name>/wal/*.arrow`
        and friends — not the single file SQLite used. `path.stat().st_size` on
        the top-level directory reports a few hundred bytes regardless of
        content, understating by orders of magnitude the very footprint
        spec.md 4.1 obliges the documentation to state honestly.
        """
        try:
            return sum(item.stat().st_size for item in self.path.rglob("*") if item.is_file())
        except OSError:
            return 0

    def index_info(self) -> dict[str, Any]:
        """The index as the collection actually holds it (AC-11)."""
        try:
            return dict(self._client.describe_index(SOLUTIONS_COLLECTION, "embedding"))
        except Exception:
            return {}


# ==============================================================================
# Row decoding
# ==============================================================================


def _as_int(raw: Any, default: int | None) -> Any:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _entity_to_record(entity: dict[str, Any]) -> SolutionRecord:
    """Build a record from a Milvus row.

    `seq` becomes `SolutionRecord.id` — the user-facing id in `/memory list`
    and the argument to `/memory forget <id>` (V5a). The record model itself did
    not move; only the engine underneath it did.
    """
    return SolutionRecord(
        id=int(entity["seq"]),
        created_at=str(entity["created_at"]),
        task=str(entity["task"]),
        thought=str(entity["thought"]),
        code=str(entity["code"]),
        stdout=str(entity["stdout"]),
        chat_model=str(entity["chat_model"]),
        embed_model=str(entity["embed_model"]),
        dim=int(entity["dim"]),
        embedding=[float(value) for value in entity["embedding"]],
    )
