# ==============================================================================
#  CodeRunner.AI  ::  recall.py — embedding seam and turn-level orchestration
# ------------------------------------------------------------------------------
#  Project : SPEC-MEMORY-001, task T5
#  Covers  : AC-1 (cold start costs zero embed calls), AC-3a/b/c/h (embedding
#            backend degradation), AC-6 (below threshold is a miss), and M2's
#            "at most one embedding call per turn".
#
#  Runs without a live Ollama: the client is a fake exposing only .embed().
# ==============================================================================

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import ollama
import pytest

import memory
import recall
from conftest import FLOAT32_TOL, FakeEmbedClient
from memory import MemoryConfig

from conftest import CHAT_MODEL, EMBED_MODEL, make_record

if TYPE_CHECKING:
    from vectorstore import VectorStore


@pytest.fixture()
def cfg(tmp_path: Path) -> MemoryConfig:
    return MemoryConfig(
        enabled=True,
        embed_model=EMBED_MODEL,
        chat_model=CHAT_MODEL,
        db_path=tmp_path / "memory.milvus.db",
        top_k=1,
        min_sim=0.65,
        max_records=500,
    )


class SubscriptOnlyResponse:
    """A response supporting ONLY subscript access — no ``.embeddings``.

    Verification V2: ollama 0.3.0 returns a TypedDict (a plain dict at runtime)
    on which ``resp.embeddings`` raises AttributeError, while 0.6.2 returns a
    pydantic model on which both forms work. Subscript is the only portable
    access pattern across the >=0.3.0 range that requirements.txt:2 permits.
    This class is what makes that constraint enforced rather than aspirational:
    a reviewer who "tidies" the subscript to attribute access fails here.
    """

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __getitem__(self, key: str) -> object:
        return self._payload[key]


# ------------------------------------------------------------------------------
# embed_text()  — happy path and the response-shape contract
# ------------------------------------------------------------------------------


def test_embed_text_returns_an_l2_normalised_vector(fake_embedder: FakeEmbedClient) -> None:
    fake_embedder.default = [3.0, 4.0]
    vector = recall.embed_text(fake_embedder, EMBED_MODEL, "a task")

    assert vector == pytest.approx([0.6, 0.8], abs=FLOAT32_TOL)
    assert math.sqrt(sum(v * v for v in vector)) == pytest.approx(1.0, abs=FLOAT32_TOL)


def test_embed_text_reads_a_plain_dict_response(fake_embedder: FakeEmbedClient) -> None:
    # The fake already returns a plain dict, i.e. the ollama 0.3.0 shape.
    fake_embedder.response = {"embeddings": [[1.0, 0.0]]}
    assert recall.embed_text(fake_embedder, EMBED_MODEL, "task") == pytest.approx(
        [1.0, 0.0], abs=FLOAT32_TOL
    )


def test_embed_text_uses_subscript_access_not_attribute_access(
    fake_embedder: FakeEmbedClient,
) -> None:
    fake_embedder.response = SubscriptOnlyResponse({"embeddings": [[0.0, 2.0]]})
    assert recall.embed_text(fake_embedder, EMBED_MODEL, "task") == pytest.approx(
        [0.0, 1.0], abs=FLOAT32_TOL
    )


def test_embed_text_passes_keep_alive_10m(fake_embedder: FakeEmbedClient) -> None:
    # V3 confirmed keep_alive="10m" is accepted and keeps the embedder resident
    # between turns, holding a warm call at ~40 ms against a 906 ms cold load.
    recall.embed_text(fake_embedder, EMBED_MODEL, "task")
    assert fake_embedder.calls[-1]["keep_alive"] == "10m"
    assert recall.EMBED_KEEP_ALIVE == "10m"


def test_embed_text_passes_the_model_and_input(fake_embedder: FakeEmbedClient) -> None:
    recall.embed_text(fake_embedder, EMBED_MODEL, "the exact task text")
    assert fake_embedder.calls[-1]["model"] == EMBED_MODEL
    assert fake_embedder.calls[-1]["input"] == "the exact task text"


def test_embed_text_of_blank_text_does_not_call_the_backend(
    fake_embedder: FakeEmbedClient,
) -> None:
    assert recall.embed_text(fake_embedder, EMBED_MODEL, "   ") is None
    assert fake_embedder.call_count == 0


# ------------------------------------------------------------------------------
# embed_text()  — degradation  (AC-3a, AC-3b, AC-3c, AC-3h)
# ------------------------------------------------------------------------------


def test_embed_text_returns_none_on_ollama_response_error(
    fake_embedder: FakeEmbedClient,
) -> None:
    """AC-3a: the embedding model was never pulled (trap B, spec.md 3.2)."""
    fake_embedder.raises = ollama.ResponseError("model 'nomic-embed-text' not found")
    assert recall.embed_text(fake_embedder, EMBED_MODEL, "task") is None


def test_embed_text_returns_none_on_httpx_connect_error(
    fake_embedder: FakeEmbedClient,
) -> None:
    """AC-3b: the Ollama sidecar became unreachable mid-turn."""
    fake_embedder.raises = httpx.ConnectError("connection refused")
    assert recall.embed_text(fake_embedder, EMBED_MODEL, "task") is None


def test_embed_text_returns_none_on_httpx_read_timeout(
    fake_embedder: FakeEmbedClient,
) -> None:
    """AC-3c: the embedding call stalled."""
    fake_embedder.raises = httpx.ReadTimeout("timed out")
    assert recall.embed_text(fake_embedder, EMBED_MODEL, "task") is None


@pytest.mark.parametrize(
    "payload",
    [
        {},  # KeyError  — no 'embeddings' key at all
        {"embeddings": []},  # IndexError — present but empty
        {"embeddings": [[]]},  # empty vector
        {"embeddings": [None]},  # TypeError on iteration
        {"embeddings": [["not", "numbers"]]},  # ValueError on float()
        {"embeddings": [[0.0, 0.0, 0.0]]},  # degenerate zero vector
    ],
    ids=["missing-key", "empty-list", "empty-vector", "none", "non-numeric", "all-zero"],
)
def test_embed_text_returns_none_on_a_malformed_response(
    fake_embedder: FakeEmbedClient, payload: dict
) -> None:
    """AC-3h: a malformed response must not escape as KeyError/IndexError."""
    fake_embedder.response = payload
    assert recall.embed_text(fake_embedder, EMBED_MODEL, "task") is None


def test_embed_text_returns_none_on_an_unexpected_exception(
    fake_embedder: FakeEmbedClient,
) -> None:
    # M5: no memory-subsystem fault may raise, abort a turn, or exit non-zero.
    fake_embedder.raises = RuntimeError("something nobody predicted")
    assert recall.embed_text(fake_embedder, EMBED_MODEL, "task") is None


# ------------------------------------------------------------------------------
# recall_for_task()  — cold start  (AC-1)
# ------------------------------------------------------------------------------


def test_empty_store_returns_none_without_embedding_at_all(
    tmp_store: "VectorStore", fake_embedder: FakeEmbedClient, cfg: MemoryConfig
) -> None:
    """AC-1: a cold start costs ZERO additional latency.

    The call counter must be exactly 0, not merely small. This is the guarantee
    M3 makes and it is trivially regressible — any future refactor that embeds
    before checking the store would still pass a "returns None" assertion.
    """
    assert recall.recall_for_task(fake_embedder, tmp_store, "a task", cfg) is None
    assert fake_embedder.call_count == 0


def test_absent_store_returns_none_without_embedding(
    fake_embedder: FakeEmbedClient, cfg: MemoryConfig
) -> None:
    assert recall.recall_for_task(fake_embedder, None, "a task", cfg) is None
    assert fake_embedder.call_count == 0


def test_blank_task_returns_none_without_embedding(
    tmp_store: "VectorStore", fake_embedder: FakeEmbedClient, cfg: MemoryConfig
) -> None:
    tmp_store.insert(make_record(), max_records=500)
    assert recall.recall_for_task(fake_embedder, tmp_store, "  ", cfg) is None
    assert fake_embedder.call_count == 0


# ------------------------------------------------------------------------------
# recall_for_task()  — hit and miss
# ------------------------------------------------------------------------------


def test_recall_returns_the_best_hit_above_threshold(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    stored = memory.l2_normalise([1.0, 0.0])
    tmp_store.insert(
        make_record(task="weather in Seoul", embedding=stored), max_records=500
    )
    client = FakeEmbedClient(default=[1.0, 0.02])

    result = recall.recall_for_task(client, tmp_store, "temperature in Busan", cfg)

    assert result is not None
    assert result.record.task == "weather in Seoul"
    assert result.similarity >= cfg.min_sim
    assert result.query_vector == pytest.approx(
        memory.l2_normalise([1.0, 0.02]), abs=FLOAT32_TOL
    )
    assert client.call_count == 1


def test_recall_below_threshold_is_a_miss_but_keeps_the_vector(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    """AC-6 / M3: below threshold injects nothing, but still surfaces the vector.

    Returning None here would discard the embedding, and the capture path would
    then have to either skip the record or embed a second time — breaking M2's
    one-embed-per-turn limit. A miss is exactly what a NEW task looks like, so
    discarding it would cap the store at its first record forever.
    """
    tmp_store.insert(
        make_record(task="weather in Seoul", embedding=memory.l2_normalise([1.0, 0.0])),
        max_records=500,
    )
    # cos ~= 0.35 — squarely in the V3 "unrelated" band of 0.297-0.395.
    query = [0.35, math.sqrt(1 - 0.35**2)]
    client = FakeEmbedClient(default=query)

    result = recall.recall_for_task(client, tmp_store, "list vs tuple", cfg)

    assert result is not None
    assert result.record is None  # the miss
    assert result.query_vector == pytest.approx(
        memory.l2_normalise(query), abs=FLOAT32_TOL
    )
    assert result.similarity == pytest.approx(0.35, abs=1e-4)
    assert result.similarity < cfg.min_sim
    assert client.call_count == 1


def test_a_miss_reports_the_actual_best_similarity_not_zero(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    # The best candidate's real score, so a human can see how close it came.
    # Three dimensions, so the query can be near one record and orthogonal to
    # the other. In two dimensions any vector that is 0.64 from [1,0] is
    # necessarily 0.768 from [0,1] — i.e. a hit — which is the trap this
    # arrangement avoids.
    tmp_store.insert(
        make_record(task="near miss", embedding=memory.l2_normalise([1.0, 0.0, 0.0])),
        max_records=500,
    )
    tmp_store.insert(
        make_record(task="far miss", embedding=memory.l2_normalise([0.0, 0.0, 1.0])),
        max_records=500,
    )
    client = FakeEmbedClient(default=[0.64, math.sqrt(1 - 0.64**2), 0.0])

    result = recall.recall_for_task(client, tmp_store, "a task", cfg)
    assert result is not None and result.record is None
    assert result.similarity == pytest.approx(0.64, abs=1e-4)


def test_hit_and_miss_are_distinguished_by_record_not_by_truthiness(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    """Callers must branch on `recall.record is not None`, never on the Recall.

    A dataclass instance is always truthy, so `if recall:` cannot tell a hit
    from a miss. Asserting that here stops a caller from being written against
    a distinction that does not exist.
    """
    tmp_store.insert(
        make_record(task="weather in Seoul", embedding=memory.l2_normalise([1.0, 0.0])),
        max_records=500,
    )

    hit = recall.recall_for_task(
        FakeEmbedClient(default=[1.0, 0.0]), tmp_store, "a task", cfg
    )
    miss = recall.recall_for_task(
        FakeEmbedClient(default=[0.0, 1.0]), tmp_store, "a task", cfg
    )

    assert hit is not None and miss is not None
    assert bool(hit) is bool(miss) is True  # truthiness cannot discriminate
    assert hit.record is not None
    assert miss.record is None


def test_recall_returns_none_only_for_the_four_unavailable_conditions(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    """None means "no retrieval happened", never "retrieval found nothing"."""
    # 1. store unavailable
    assert recall.recall_for_task(FakeEmbedClient(), None, "t", cfg) is None
    # 2. empty store (cold-start short-circuit)
    assert recall.recall_for_task(FakeEmbedClient(), tmp_store, "t", cfg) is None
    # 3. memory disabled
    tmp_store.insert(make_record(embedding=[1.0, 0.0]), max_records=500)
    cfg.enabled = False
    assert recall.recall_for_task(FakeEmbedClient(), tmp_store, "t", cfg) is None
    # 4. embedding failure
    cfg.enabled = True
    failing = FakeEmbedClient(raises=ollama.ResponseError("nope"))
    assert recall.recall_for_task(failing, tmp_store, "t", cfg) is None


def test_recall_returns_none_when_embedding_fails(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    tmp_store.insert(make_record(), max_records=500)
    client = FakeEmbedClient(raises=ollama.ResponseError("not found"))
    assert recall.recall_for_task(client, tmp_store, "a task", cfg) is None


def test_recall_ignores_records_from_a_different_embedding_model(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    tmp_store.insert(
        make_record(
            task="stale", embedding=memory.l2_normalise([1.0, 0.0]), embed_model="old-model"
        ),
        max_records=500,
    )
    client = FakeEmbedClient(default=[1.0, 0.0])

    # A store of nothing but stale vectors is a miss, not an absence of
    # retrieval: the vector still comes back so the turn can be captured under
    # the CURRENT model, which is how the store recovers after a model swap.
    result = recall.recall_for_task(client, tmp_store, "a task", cfg)
    assert result is not None
    assert result.record is None
    assert result.query_vector


def test_recall_derives_the_dimension_from_the_returned_vector(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    # AC-1: `dim` is never hardcoded. A 5-dim store must be matched by a 5-dim
    # query and ignored by a 2-dim one.
    stored = memory.l2_normalise([1.0, 0.0, 0.0, 0.0, 0.0])
    tmp_store.insert(make_record(task="five dims", embedding=stored), max_records=500)

    matched = recall.recall_for_task(FakeEmbedClient(default=stored), tmp_store, "t", cfg)
    assert matched is not None and matched.record is not None

    mismatched = recall.recall_for_task(
        FakeEmbedClient(default=[1.0, 0.0]), tmp_store, "t", cfg
    )
    assert mismatched is not None and mismatched.record is None


# ------------------------------------------------------------------------------
# remember_success()
# ------------------------------------------------------------------------------


def test_remember_success_persists_the_record(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    vector = memory.l2_normalise([1.0, 2.0, 2.0])
    assert (
        recall.remember_success(
            tmp_store, "a task", "a thought", "print(1)", "1", vector, cfg
        )
        is True
    )

    (stored,) = tmp_store.recent(1)
    assert stored.task == "a task"
    assert stored.thought == "a thought"
    assert stored.code == "print(1)"
    assert stored.stdout == "1"
    assert stored.chat_model == CHAT_MODEL
    assert stored.embed_model == EMBED_MODEL
    assert stored.dim == 3
    assert stored.created_at  # ISO-8601 stamp, generated at capture time


def test_remember_success_derives_dim_from_the_vector(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    recall.remember_success(
        tmp_store, "a task", "t", "c", "o", memory.l2_normalise([1.0] * 768), cfg
    )
    (stored,) = tmp_store.recent(1)
    assert stored.dim == 768
    assert tmp_store.meta_get("dim") == "768"


def test_remember_success_honours_the_record_cap(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    cfg.max_records = 3
    for index in range(6):
        recall.remember_success(
            tmp_store, f"task {index}", "t", "c", "o", [1.0, 0.0], cfg
        )
    assert tmp_store.count() == 3


@pytest.mark.parametrize("vector", [None, []], ids=["none", "empty"])
def test_remember_success_without_a_vector_is_a_no_op(
    tmp_store: "VectorStore", cfg: MemoryConfig, vector: list[float] | None
) -> None:
    assert recall.remember_success(tmp_store, "t", "t", "c", "o", vector, cfg) is False
    assert tmp_store.count() == 0


def test_remember_success_without_a_store_is_a_no_op(cfg: MemoryConfig) -> None:
    assert recall.remember_success(None, "t", "t", "c", "o", [1.0, 0.0], cfg) is False


def test_remember_success_degrades_when_the_store_write_fails(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    tmp_store.close()
    assert recall.remember_success(tmp_store, "t", "t", "c", "o", [1.0, 0.0], cfg) is False


def test_remember_success_cannot_embed_because_it_has_no_client() -> None:
    # Structural guarantee for M2's "at most one embedding call per turn":
    # remember_success takes no client, so it CANNOT issue a second call.
    import inspect

    assert "client" not in inspect.signature(recall.remember_success).parameters


# ------------------------------------------------------------------------------
# One embedding call per turn  (M2)
# ------------------------------------------------------------------------------


def test_a_full_retrieve_then_capture_turn_embeds_exactly_once(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    """M2: the retrieval vector is reused for capture — one embed, not two."""
    tmp_store.insert(
        make_record(task="weather in Seoul", embedding=memory.l2_normalise([1.0, 0.0])),
        max_records=500,
    )
    client = FakeEmbedClient(default=[1.0, 0.02])

    result = recall.recall_for_task(client, tmp_store, "temperature in Busan", cfg)
    assert result is not None

    assert recall.remember_success(
        tmp_store,
        "temperature in Busan",
        "a thought",
        "print(29)",
        "29",
        result.query_vector,
        cfg,
    )

    assert client.call_count == 1
    assert tmp_store.count() == 2


def test_a_missed_turn_still_captures_and_still_embeds_only_once(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    """AC-6b at unit level: a miss must still learn.

    M3: "a miss is exactly what a NEW task looks like". If a missed turn did
    not capture, the store would keep its first record and never grow — the
    feature would silently cap itself at one entry while appearing to work.
    """
    tmp_store.insert(
        make_record(task="weather in Seoul", embedding=memory.l2_normalise([1.0, 0.0])),
        max_records=500,
    )
    client = FakeEmbedClient(default=[0.0, 1.0])  # orthogonal: similarity 0.0

    result = recall.recall_for_task(client, tmp_store, "an unrelated new task", cfg)
    assert result is not None and result.record is None

    assert recall.remember_success(
        tmp_store,
        "an unrelated new task",
        "a thought",
        "print(1)",
        "1",
        result.query_vector,
        cfg,
    )

    assert tmp_store.count() == 2  # the store learned from the miss
    assert client.call_count == 1  # and still paid for exactly one embed


# ------------------------------------------------------------------------------
# retrieval_degraded()  — telling a fault apart from a deliberate quiet path
# ------------------------------------------------------------------------------


def test_degraded_is_true_only_when_an_embed_was_attempted_and_failed(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    tmp_store.insert(make_record(embedding=[1.0, 0.0]), max_records=500)
    client = FakeEmbedClient(raises=ollama.ResponseError("not pulled"))

    result = recall.recall_for_task(client, tmp_store, "a task", cfg)
    assert result is None
    assert recall.retrieval_degraded(tmp_store, "a task", cfg, result) is True


def test_a_completed_retrieval_is_never_degraded(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    tmp_store.insert(
        make_record(embedding=memory.l2_normalise([1.0, 0.0])), max_records=500
    )
    hit = recall.recall_for_task(FakeEmbedClient(default=[1.0, 0.0]), tmp_store, "t", cfg)
    miss = recall.recall_for_task(FakeEmbedClient(default=[0.0, 1.0]), tmp_store, "t", cfg)

    assert recall.retrieval_degraded(tmp_store, "t", cfg, hit) is False
    assert recall.retrieval_degraded(tmp_store, "t", cfg, miss) is False


def test_the_cold_start_short_circuit_is_not_degradation(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    # Skipping the embed on an empty store is the M3 optimisation. Reporting it
    # would put a warning on the first turn of every fresh install.
    client = FakeEmbedClient()
    result = recall.recall_for_task(client, tmp_store, "the first task", cfg)
    assert result is None and client.call_count == 0
    assert recall.retrieval_degraded(tmp_store, "the first task", cfg, result) is False


def test_deliberately_disabled_memory_is_not_degradation(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    tmp_store.insert(make_record(embedding=[1.0, 0.0]), max_records=500)
    cfg.enabled = False
    assert recall.retrieval_degraded(tmp_store, "a task", cfg, None) is False


def test_an_absent_store_is_not_degradation(cfg: MemoryConfig) -> None:
    # Reported once at startup instead, not on every turn.
    assert recall.retrieval_degraded(None, "a task", cfg, None) is False


@pytest.mark.parametrize("task", ["", "   ", "\n\t "])
def test_a_blank_task_is_not_degradation(
    tmp_store: "VectorStore", cfg: MemoryConfig, task: str
) -> None:
    # No embed is attempted for a blank task, so there is nothing to report.
    tmp_store.insert(make_record(embedding=[1.0, 0.0]), max_records=500)
    assert recall.retrieval_degraded(tmp_store, task, cfg, None) is False


# ------------------------------------------------------------------------------
# vector_for_capture()  — the cold-start seam
# ------------------------------------------------------------------------------


def test_capture_vector_is_reused_from_a_hit(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    tmp_store.insert(
        make_record(task="prior", embedding=memory.l2_normalise([1.0, 0.0])),
        max_records=500,
    )
    client = FakeEmbedClient(default=[1.0, 0.0])
    result = recall.recall_for_task(client, tmp_store, "a task", cfg)

    vector = recall.vector_for_capture(client, tmp_store, "a task", cfg, result)
    assert vector == result.query_vector
    assert client.call_count == 1  # no second embed


def test_capture_vector_is_reused_from_a_miss(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    tmp_store.insert(
        make_record(task="prior", embedding=memory.l2_normalise([1.0, 0.0])),
        max_records=500,
    )
    client = FakeEmbedClient(default=[0.0, 1.0])
    result = recall.recall_for_task(client, tmp_store, "a task", cfg)
    assert result is not None and result.record is None

    vector = recall.vector_for_capture(client, tmp_store, "a task", cfg, result)
    assert vector == result.query_vector
    assert client.call_count == 1


def test_capture_vector_is_embedded_once_on_a_cold_start(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    """The first record would otherwise never be written.

    Retrieval short-circuits an empty store WITHOUT embedding (AC-1), so a
    cold-start turn has no cached vector. If capture were gated on the
    retrieval result, the store would stay empty forever and every later turn
    would keep short-circuiting — a feature that never starts working while
    looking perfectly healthy.
    """
    client = FakeEmbedClient(default=[1.0, 0.0])
    result = recall.recall_for_task(client, tmp_store, "the very first task", cfg)
    assert result is None
    assert client.call_count == 0

    vector = recall.vector_for_capture(client, tmp_store, "the very first task", cfg, result)
    assert vector == pytest.approx([1.0, 0.0], abs=FLOAT32_TOL)
    assert client.call_count == 1  # still exactly one for the whole turn


def test_capture_vector_does_not_retry_a_failed_embedding(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    """A degraded backend must cost one failed call per turn, not two.

    Retrieval already tried and failed on this non-empty store. Trying again at
    capture time would double the cost of every turn while Ollama is down.
    """
    tmp_store.insert(make_record(embedding=[1.0, 0.0]), max_records=500)
    client = FakeEmbedClient(raises=ollama.ResponseError("model not found"))

    result = recall.recall_for_task(client, tmp_store, "a task", cfg)
    assert result is None
    assert client.call_count == 1

    assert recall.vector_for_capture(client, tmp_store, "a task", cfg, result) is None
    assert client.call_count == 1


def test_capture_vector_is_none_when_memory_is_off_or_absent(
    tmp_store: "VectorStore", cfg: MemoryConfig
) -> None:
    client = FakeEmbedClient()
    assert recall.vector_for_capture(client, None, "t", cfg, None) is None

    cfg.enabled = False
    assert recall.vector_for_capture(client, tmp_store, "t", cfg, None) is None
    assert client.call_count == 0


# ------------------------------------------------------------------------------
# MemoryConfig
# ------------------------------------------------------------------------------


def test_memory_config_from_env_uses_documented_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "CODERUNNER_MEMORY",
        "CODERUNNER_EMBED_MODEL",
        "CODERUNNER_MEMORY_DB",
        "CODERUNNER_MEMORY_TOP_K",
        "CODERUNNER_MEMORY_MIN_SIMILARITY",
        "CODERUNNER_MEMORY_MAX_RECORDS",
    ):
        monkeypatch.delenv(name, raising=False)

    config = MemoryConfig.from_env(CHAT_MODEL)
    assert config.enabled is True  # constraint C4: memory defaults ON
    assert config.embed_model == "nomic-embed-text:latest"
    assert config.top_k == 1
    assert config.min_sim == 0.65
    assert config.max_records == 100_000  # C9, raised from 500 at v1.1.0
    assert config.chat_model == CHAT_MODEL


def test_memory_config_from_env_survives_hostile_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-8: no ValueError escapes; every value clamps or falls back."""
    monkeypatch.setenv("CODERUNNER_MEMORY_TOP_K", "abc")
    monkeypatch.setenv("CODERUNNER_MEMORY_MIN_SIMILARITY", "")
    monkeypatch.setenv("CODERUNNER_MEMORY_MAX_RECORDS", "0")
    monkeypatch.setenv("CODERUNNER_EMBED_MODEL", "")

    config = MemoryConfig.from_env(CHAT_MODEL)
    assert config.top_k == 1
    assert config.min_sim == 0.65
    assert config.max_records == 10
    # The :latest suffix matters: coderunner:186 matches with `grep -qx`
    # against fully-qualified tags, so a bare name re-pulls 274 MB every launch.
    assert config.embed_model == "nomic-embed-text:latest"


def test_memory_config_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODERUNNER_MEMORY", "0")
    assert MemoryConfig.from_env(CHAT_MODEL).enabled is False


def test_memory_config_reads_a_custom_database_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CODERUNNER_MEMORY_DB", str(tmp_path / "custom.milvus.db"))
    assert MemoryConfig.from_env(CHAT_MODEL).db_path == tmp_path / "custom.milvus.db"
