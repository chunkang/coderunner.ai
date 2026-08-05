# ==============================================================================
#  CodeRunner.AI  ::  pytest fixtures and the per-file coverage gate
# ------------------------------------------------------------------------------
#  Author  : kurapa <kurapa@kurapa.com>
#  Project : SPEC-MEMORY-001, tasks T1 / T-VS10
#  Purpose : Shared fixtures (`tmp_store`, `fake_embedder`), the record factory
#            every store-dependent suite builds on, plus enforcement of the
#            *per-file* coverage floor that `--cov-fail-under` cannot express.
# ==============================================================================

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Sequence

import pytest

# The modules under test live at the repository root, next to this file. pytest
# puts rootdir on sys.path only when a tests/__init__.py is absent; we ship one
# (so the suite is a package), so make the path insertion explicit.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if TYPE_CHECKING:  # import lazily inside the fixture, so a collection-time
    from vectorstore import VectorStore  # import error surfaces as a test failure


# ------------------------------------------------------------------------------
# Tolerances
# ------------------------------------------------------------------------------

# FLOAT_VECTOR is IEEE-754 *single* precision (~7 significant decimal digits), so
# a float64-normalised vector does not round-trip exactly: self-similarity comes
# back as ~0.9999997 and can land marginally above 1.0, and 0.3 comes back as
# 0.30000001192092896. Every comparison of a vector component or a similarity
# must therefore use pytest.approx with this tolerance. Never `==`.
FLOAT32_TOL = 1e-6


# ------------------------------------------------------------------------------
# The record factory
# ------------------------------------------------------------------------------
# Lives here rather than in a test module so that every suite touching the store
# shares one definition. It used to live in tests/test_memory_store.py, which
# T-VS7 deletes.

EMBED_MODEL = "nomic-embed-text:latest"
CHAT_MODEL = "llama3.1:8b"


def make_record(
    task: str = "sum the first 10 primes",
    *,
    thought: str = "iterate and test primality",
    code: str = "print(129)",
    stdout: str = "129",
    embedding: Sequence[float] | None = None,
    embed_model: str = EMBED_MODEL,
    created_at: str = "2026-08-02T00:00:00+00:00",
) -> "Any":
    from memory import SolutionRecord

    vector = [1.0, 0.0, 0.0] if embedding is None else [float(v) for v in embedding]
    return SolutionRecord(
        id=None,
        created_at=created_at,
        task=task,
        thought=thought,
        code=code,
        stdout=stdout,
        chat_model=CHAT_MODEL,
        embed_model=embed_model,
        dim=len(vector),
        embedding=vector,
    )


# ------------------------------------------------------------------------------
# Fake embedding client
# ------------------------------------------------------------------------------


class FakeEmbedClient:
    """Minimal stand-in for ``ollama.Client``, exposing only ``.embed()``.

    Returns a **plain dict** on purpose. Verification V2 established that
    ``ollama==0.3.0`` returns a ``TypedDict`` (a plain ``dict`` at runtime)
    while ``0.6.2`` returns a pydantic ``SubscriptableBaseModel``. Subscript
    access works on both; attribute access raises ``AttributeError`` on 0.3.0.
    Making the fake the harsher of the two shapes is what turns that constraint
    from aspirational into enforced.
    """

    def __init__(
        self,
        vectors: dict[str, Sequence[float]] | None = None,
        default: Sequence[float] | None = None,
        raises: BaseException | None = None,
    ) -> None:
        self.vectors: dict[str, list[float]] = {
            key: list(val) for key, val in (vectors or {}).items()
        }
        self.default: list[float] = list(default) if default is not None else [1.0, 0.0, 0.0]
        self.raises: BaseException | None = raises
        self.response: Any = None  # set to override the whole payload
        self.calls: list[dict[str, Any]] = []

    def embed(
        self,
        model: str = "",
        input: str | Sequence[str] = "",  # noqa: A002 - mirrors the real signature
        keep_alive: Any = None,
        **kwargs: Any,
    ) -> Any:
        self.calls.append({"model": model, "input": input, "keep_alive": keep_alive})
        if self.raises is not None:
            raise self.raises
        if self.response is not None:
            return self.response
        vector = self.vectors.get(input if isinstance(input, str) else "", self.default)
        return {"embeddings": [list(vector)]}

    @property
    def call_count(self) -> int:
        return len(self.calls)


# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    # Mirrors memory.DEFAULT_DB_PATH, and both halves of the name matter: the
    # URI must still end in `.db` (Milvus Lite rejects any other local path),
    # while the name must NOT be `memory.db`, which would collide with a v1.0.x
    # SQLite store and make every open raise forever. What is created at this
    # path is a DIRECTORY holding a collection file set, not a single file.
    return tmp_path / "memory.milvus.db"


@pytest.fixture()
def tmp_store(db_path: Path) -> Iterator["VectorStore"]:
    # T-VS10: repointing this single fixture repoints every store-dependent
    # test. The importorskip is a safety net for a platform with no milvus_lite
    # wheel; it is NOT a licence to skip the vectorstore.py coverage gate, which
    # requirements-dev.txt makes unconditional.
    pytest.importorskip("milvus_lite", reason="vectorstore.py needs pymilvus[milvus_lite]")
    from vectorstore import VectorStore

    store = VectorStore.open(db_path)
    assert store is not None, "fixture precondition: the store must open cleanly"
    try:
        yield store
    finally:
        store.close()


@pytest.fixture()
def fake_embedder() -> FakeEmbedClient:
    return FakeEmbedClient()


# ------------------------------------------------------------------------------
# Per-file coverage gate
# ------------------------------------------------------------------------------
#
# acceptance.md requires a floor on memory.py, recall.py AND vectorstore.py
# *separately*. pytest-cov's `--cov-fail-under` compares the COMBINED total
# only, so 100% on a large memory.py would mask 40% on a small recall.py. This
# hook re-reports the same coverage data once per file and fails the session if
# any falls short.
#
# The floors differ by design (plan.md 6.3): memory.py and recall.py are at 100%
# today and the migration must not regress them, while vectorstore.py — the new
# module, whose degradation branches are exercised through a real engine — is
# gated at 85%.
#
# `trylast=True` matters: pytest-cov stops its controller and flushes the data
# file in its own `pytest_sessionfinish`, so this must run after it.

PER_FILE_COVERAGE_FLOOR = 85.0
PER_FILE_COVERAGE_TARGETS = {
    "memory.py": 100.0,
    "recall.py": 100.0,
    "vectorstore.py": PER_FILE_COVERAGE_FLOOR,
}


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    cov_plugin = session.config.pluginmanager.get_plugin("_cov")
    controller = getattr(cov_plugin, "cov_controller", None)
    cov = getattr(controller, "cov", None)
    if cov is None:
        return  # running with --no-cov; nothing to enforce

    failures: list[str] = []
    for target, floor in PER_FILE_COVERAGE_TARGETS.items():
        try:
            percent = cov.report(include=[target], file=io.StringIO(), show_missing=False)
        except Exception as err:  # no data for this file at all
            failures.append(f"{target}: coverage unavailable ({err.__class__.__name__}: {err})")
            continue
        if percent < floor:
            failures.append(f"{target}: {percent:.2f}% < {floor:.0f}%")

    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if failures:
        if reporter is not None:
            reporter.write_line("")
            reporter.write_line("FAIL Required per-file coverage not met:", red=True, bold=True)
            for line in failures:
                reporter.write_line(f"  - {line}", red=True)
        session.exitstatus = 1
    elif reporter is not None:
        joined = ", ".join(f"{name} >= {floor:.0f}%" for name, floor in PER_FILE_COVERAGE_TARGETS.items())
        reporter.write_line(f"Per-file coverage gate passed ({joined})", green=True)
