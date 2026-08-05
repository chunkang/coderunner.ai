# ==============================================================================
#  CodeRunner.AI  ::  vectorstore.py — the Milvus Lite storage seam
# ------------------------------------------------------------------------------
#  Project : SPEC-MEMORY-001 v1.1.0, tasks T-VS1..T-VS6, T-VS11
#  Covers  : AC-3d/e/f/i (storage degradation), AC-4 (meta survives a reopen),
#            AC-7a (survivor identity), AC-7b (seq/created_at carried forward),
#            AC-7c (C11 truncation), AC-7d (convergence with gaps),
#            AC-10 (COSINE is a similarity, cross-checked against dot()),
#            AC-11 (FLAT/COSINE pinned), AC-12 (eligibility filter by search).
#
#  Runs against a REAL embedded Milvus Lite on tmp_path — it is embedded, so
#  this needs no service (acceptance.md "Testability constraints").
# ==============================================================================

from __future__ import annotations

import math
from pathlib import Path

import pytest

pytest.importorskip("milvus_lite", reason="vectorstore.py needs pymilvus[milvus_lite]")

import memory  # noqa: E402
import vectorstore  # noqa: E402
from conftest import CHAT_MODEL, EMBED_MODEL, FLOAT32_TOL, make_record  # noqa: E402
from vectorstore import VectorStore  # noqa: E402


def unit(*values: float) -> list[float]:
    return memory.l2_normalise(list(values))


def tasks_of(records) -> list[str]:
    return [record.task for record in records]


# ------------------------------------------------------------------------------
# open() / schema / meta  — M1
# ------------------------------------------------------------------------------


def test_open_creates_the_store_and_its_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "deeper" / "memory.milvus.db"
    store = VectorStore.open(path)
    assert store is not None
    try:
        assert path.exists()
    finally:
        store.close()


def test_open_creates_the_meta_side_collection_with_the_schema_version(
    tmp_store: VectorStore,
) -> None:
    # AC-1: the meta side-collection exists from the moment the store opens.
    assert tmp_store.meta_get("schema_version") == memory.SCHEMA_VERSION


def test_open_is_idempotent_and_does_not_wipe_existing_records(db_path: Path) -> None:
    first = VectorStore.open(db_path)
    assert first is not None
    assert first.insert(make_record(), max_records=500) is True
    first.close()

    second = VectorStore.open(db_path)
    assert second is not None
    try:
        assert second.count() == 1
    finally:
        second.close()


def test_a_reopened_store_can_actually_SERVE_A_SEARCH(db_path: Path) -> None:
    """V5c: a persisted collection comes back `released` and must be LOADED.

    A collection created in-process is implicitly loaded, so session one works
    perfectly. Every later session — a fresh container opening the volume —
    gets `MilvusException (code=101) ... call load() before search` from the
    first search, which lands in recall.py's broad except, is reported once as
    a fault, and leaves memory dead from session two onward. Measured on a real
    100k collection: count() works pre-load, search() does not.

    This is trap-A-shaped, and NO test that creates and searches a collection
    in one process can catch it. Asserting a reopened store SERVES a search —
    not merely that it opened and reported a count — is what makes it catchable.
    """
    first = VectorStore.open(db_path)
    assert first is not None
    assert first.insert(
        make_record(task="weather in Seoul", embedding=unit(1.0, 0.0, 0.0)), max_records=500
    )
    # Releasing is what makes this test HONEST. A close-and-reopen inside one
    # process reuses the cached milvus-lite server with the collection still
    # loaded, so it passes with or without the load call — verified by mutation.
    # (A subprocess cannot substitute: milvus_lite holds a data-dir lock for the
    # life of the process, so a second interpreter gets DataDirLockedError
    # rather than a released collection. That is V5d, not V5c.) Releasing
    # reproduces the fresh-container state precisely:
    #   MilvusException (code=101) Collection 'solutions' is in state
    #   'released'; call load() before search/get/query
    first._client.release_collection(vectorstore.SOLUTIONS_COLLECTION)
    first._client.release_collection(vectorstore.META_COLLECTION)
    first.close()

    second = VectorStore.open(db_path)
    assert second is not None
    try:
        assert second.count() == 1  # get_collection_stats() needs no load
        hits = second.search(unit(1.0, 0.0, 0.0), 1, 0.0, EMBED_MODEL, 3)
        assert [hit.record.task for hit in hits] == ["weather in Seoul"]
        assert second.recent(1)[0].task == "weather in Seoul"
    finally:
        second.close()


def test_next_seq_and_min_seq_survive_a_reopen(db_path: Path) -> None:
    """AC-4: they CANNOT be recovered from the main collection (trap D).

    A process that failed to persist them would restart sequence allocation at
    zero and begin colliding with existing records.
    """
    first = VectorStore.open(db_path)
    assert first is not None
    for index in range(3):
        first.insert(make_record(task=f"task {index}"), max_records=500)
    assert first.meta_get("next_seq") == "3"
    first.close()

    second = VectorStore.open(db_path)
    assert second is not None
    try:
        assert second.meta_get("next_seq") == "3"
        assert second.meta_get("min_seq") == "0"
        second.insert(make_record(task="task after reopen"), max_records=500)
        (newest,) = second.recent(1)
        assert newest.id == 3  # NOT 0: allocation continued from persisted state
    finally:
        second.close()


def test_open_records_the_first_observed_embed_model_and_dim(tmp_store: VectorStore) -> None:
    # plan.md 2: `dim` is DERIVED from len(vector) at runtime and persisted, so
    # a model swap is detectable rather than silently corrupting comparisons.
    tmp_store.insert(make_record(embedding=[0.0] * 768), max_records=500)
    assert tmp_store.meta_get("embed_model") == EMBED_MODEL
    assert tmp_store.meta_get("dim") == "768"


def test_open_with_an_explicit_dim_creates_the_collection_eagerly(db_path: Path) -> None:
    store = VectorStore.open(db_path, dim=4)
    assert store is not None
    try:
        assert store.count() == 0
        assert store.index_info()["index_type"] == vectorstore.INDEX_TYPE
    finally:
        store.close()


# ------------------------------------------------------------------------------
# The cold start must not reach the engine, or be heard from it  (AC-1, M5)
# ------------------------------------------------------------------------------


def test_a_cold_start_never_touches_the_engine(
    tmp_store: VectorStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-1: the first turn of a fresh install must cost nothing and say nothing.

    Until the first capture there is no solutions collection, and ASKING Milvus
    about a collection that does not exist raises — which pymilvus then LOGS,
    with a full traceback, through its own handler on the real stderr.
    recall.py calls `count()` up to three times per turn, so a store that
    answered the cold start by provoking an exception would print some sixty
    lines of library traceback into a Rich-rendered turn, on the very first task
    of every fresh install, while AC-1 requires that turn to be
    indistinguishable from the pre-feature product.

    Asserting the engine is never called is what keeps that true. `count()`
    returning 0 is necessary but nowhere near sufficient — it is exactly what
    the noisy implementation also does.

    THE SENTINEL DERIVES FROM BaseException DELIBERATELY. Every method here is
    wrapped in `except Exception` by M5's degrade-never-raise contract, so an
    AssertionError sentinel would be swallowed by the very code under test and
    this would pass whatever the implementation did. Mutation testing caught
    exactly that: the first version of this test could not fail.
    """

    class ReachedTheEngine(BaseException):
        pass

    def unreachable(*args: object, **kwargs: object) -> object:
        raise ReachedTheEngine("the cold-start path must not reach the engine")

    for method in ("get_collection_stats", "search", "query", "delete"):
        monkeypatch.setattr(tmp_store._client, method, unreachable)

    assert tmp_store.count() == 0
    assert tmp_store.search([1.0, 0.0, 0.0], 1, 0.0, EMBED_MODEL, 3) == []
    assert tmp_store.recent(10) == []
    assert tmp_store.delete(1) is False


def test_the_backend_cannot_print_over_the_user_interface() -> None:
    """M5: exactly ONE status line per turn, and it is ours.

    pymilvus logs every failed RPC at ERROR with a traceback. Every fault it
    can report, this module already reports in one line — so the library's copy
    is pure noise arriving in the middle of a turn, and it would arrive on the
    degradation path M5 exists to make quiet.
    """
    import logging

    for name in ("pymilvus", "milvus_lite"):
        assert logging.getLogger(name).level >= logging.CRITICAL


# ------------------------------------------------------------------------------
# AC-11 — index and metric are PINNED, not defaulted
# ------------------------------------------------------------------------------


def test_the_index_is_flat_and_the_metric_is_cosine_read_back_from_the_collection(
    tmp_store: VectorStore,
) -> None:
    """AC-11: relying on a library default fails this criterion.

    V4 3 measured HNSW as SLOWER than FLAT at 100k (190 ms vs 133 ms median)
    and far worse at the tail at 200k (1,742 ms vs 291 ms p90), so the correct
    choice here is counter-intuitive and a future library default is as likely
    to move away from it as toward it.
    """
    tmp_store.insert(make_record(), max_records=500)

    info = tmp_store.index_info()
    assert info["index_type"] == "FLAT"
    assert info["metric_type"] == "COSINE"
    assert vectorstore.INDEX_TYPE == "FLAT"
    assert vectorstore.METRIC_TYPE == "COSINE"


# ------------------------------------------------------------------------------
# open() degradation  — AC-3d, AC-3e, AC-3f, AC-3i
# ------------------------------------------------------------------------------


def test_open_returns_none_when_the_parent_path_is_a_regular_file(tmp_path: Path) -> None:
    """AC-3d/AC-3f: the store directory cannot be created.

    Deliberately NOT tested with os.chmod(dir, 0o500): chmod is a no-op for
    uid 0, so a permission-based test passes vacuously in-container and in any
    root CI. Pointing the path at a location whose parent is an existing
    regular file fails regardless of uid.
    """
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("this is a regular file", encoding="utf-8")

    assert VectorStore.open(blocker / "memory.milvus.db") is None
    assert VectorStore.open(blocker / "deeper" / "memory.milvus.db") is None


def test_open_returns_none_when_the_path_is_an_existing_regular_file(
    tmp_path: Path,
) -> None:
    """AC-3e: Milvus Lite needs a DIRECTORY at this path.

    This is also what protects out-of-scope item 14: a v1.0.x SQLite
    `memory.db` left on the volume is not read, not converted and not
    corrupted — the store simply declines to open on that path.
    """
    legacy = tmp_path / "memory.db"
    legacy.write_bytes(b"SQLite format 3\x00" + b"legacy data" * 64)

    assert VectorStore.open(legacy) is None
    assert legacy.read_bytes().startswith(b"SQLite format 3")  # untouched


def test_open_returns_none_when_the_client_cannot_be_constructed(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-3i, and AC-3g with it: the backend refuses the connection.

    Two causes, one exception and one outcome. `pymilvus` installed without the
    `milvus_lite` extra raises ConnectionConfigException at
    `MilvusClient("<path>")` (V4 1) — a one-word omission in requirements.txt
    that produces total failure. And V5d measured Milvus Lite refusing
    CONCURRENT access the same way: the second client of two loses AT OPEN,
    with no equivalent of the WAL + busy_timeout the SQLite design relied on.

    Simulated rather than raced: a real concurrency test in the unit suite would
    be timing-dependent, and what matters is that `open()` returns None instead
    of letting the exception crash the REPL before the banner.
    """
    from pymilvus.exceptions import ConnectionConfigException

    def refuse(*args: object, **kwargs: object) -> object:
        raise ConnectionConfigException(message="Open local milvus failed")

    monkeypatch.setattr(vectorstore, "MilvusClient", refuse)
    assert VectorStore.open(db_path) is None


def test_open_returns_none_when_schema_setup_fails(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-3d: the client connects but the meta collection cannot be created."""
    real_open = VectorStore.open

    def broken_init(self: VectorStore) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(VectorStore, "_init_meta", broken_init)
    assert real_open(db_path) is None


# ------------------------------------------------------------------------------
# insert()  — happy path
# ------------------------------------------------------------------------------


def test_insert_stores_a_retrievable_record(tmp_store: VectorStore) -> None:
    assert tmp_store.insert(make_record(), max_records=500) is True
    assert tmp_store.count() == 1

    (stored,) = tmp_store.recent(10)
    assert stored.id == 0  # the first value allocated from next_seq
    assert stored.task == "sum the first 10 primes"
    assert stored.thought == "iterate and test primality"
    assert stored.code == "print(129)"
    assert stored.stdout == "129"
    assert stored.chat_model == CHAT_MODEL
    assert stored.embed_model == EMBED_MODEL
    assert stored.dim == 3
    assert stored.embedding == pytest.approx([1.0, 0.0, 0.0], abs=FLOAT32_TOL)


def test_insert_rejects_a_record_with_an_empty_embedding(tmp_store: VectorStore) -> None:
    assert tmp_store.insert(make_record(embedding=[]), max_records=500) is False
    assert tmp_store.count() == 0


def test_insert_of_a_mismatched_dim_degrades_rather_than_raising(
    tmp_store: VectorStore,
) -> None:
    """A collection carries ONE vector dimension; a 2-dim record cannot join a
    3-dim collection. M5 forbids raising, so this returns False and leaves the
    existing records intact.
    """
    assert tmp_store.insert(make_record(embedding=[1.0, 0.0, 0.0]), max_records=500)
    assert tmp_store.insert(make_record(task="other", embedding=[1.0, 0.0]), max_records=500) is False
    assert tmp_store.count() == 1


def test_an_empty_store_adopts_a_new_dimension(tmp_store: VectorStore) -> None:
    """The recovery path after `/memory clear --yes` and a model swap.

    Without this, changing CODERUNNER_EMBED_MODEL to a model of a different
    dimension would leave the store permanently unwritable — silent degradation
    on every turn, which is exactly risk R7.
    """
    assert tmp_store.insert(make_record(embedding=[1.0, 0.0, 0.0]), max_records=500)
    tmp_store.clear()

    assert tmp_store.insert(
        make_record(task="new model", embedding=[0.0] * 5, embed_model="other-model"),
        max_records=500,
    )
    assert tmp_store.count() == 1


def test_a_store_emptied_by_pruning_also_adopts_a_new_dimension(
    tmp_store: VectorStore,
) -> None:
    # The same recovery, reached without `/memory clear`: a cap of 0 empties the
    # collection but leaves it in place, so the rebuild has to drop it first.
    assert tmp_store.insert(make_record(embedding=[1.0, 0.0, 0.0]), max_records=0)
    assert tmp_store.count() == 0

    assert tmp_store.insert(
        make_record(task="new model", embedding=[0.0] * 7, embed_model="other-model"),
        max_records=500,
    )
    assert tmp_store.count() == 1
    (stored,) = tmp_store.recent(1)
    assert stored.dim == 7


# ------------------------------------------------------------------------------
# AC-7c — truncation at the tightened C11 limits
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field_name", "limit"),
    [
        ("task", 2000),
        ("thought", 1000),
        ("code", 4000),
        ("stdout", 1000),
    ],
)
def test_insert_truncates_each_field_at_its_C11_limit(
    tmp_store: VectorStore, field_name: str, limit: int
) -> None:
    # Exact boundary assertions: at the limit nothing is lost; one character
    # over is cut to exactly the limit; grossly over is cut to exactly the limit.
    for length, expected in ((limit, limit), (limit + 1, limit), (50_000, limit)):
        tmp_store.clear()
        record = make_record(task=f"task-{field_name}-{length}")
        setattr(record, field_name, "x" * length)
        assert tmp_store.insert(record, max_records=500) is True

        (stored,) = tmp_store.recent(1)
        assert len(getattr(stored, field_name)) == expected


def test_insert_truncates_a_50000_character_stdout_to_exactly_1000(
    tmp_store: VectorStore,
) -> None:
    # AC-7c verbatim.
    tmp_store.insert(make_record(stdout="y" * 50_000), max_records=500)
    (stored,) = tmp_store.recent(1)
    assert len(stored.stdout) == 1000


def test_the_C11_constants_hold_their_decided_values() -> None:
    assert memory.MAX_TASK_CHARS == 2000  # unchanged
    assert memory.MAX_THOUGHT_CHARS == 1000  # was 4000
    assert memory.MAX_CODE_CHARS == 4000  # was 8000
    assert memory.MAX_STDOUT_CHARS == 1000  # was 4000


def test_truncation_does_not_change_one_bit_of_the_stored_embedding(
    tmp_store: VectorStore,
) -> None:
    """AC-7c: C11 claims recall quality is unaffected. This is that claim.

    Only the TASK text is embedded and MAX_TASK_CHARS did not change, so no
    stored vector may differ because thought/code/stdout got shorter.
    """
    vector = unit(0.3, -0.7, 0.65)
    short = make_record(task="the same task", embedding=vector)
    tmp_store.insert(short, max_records=500)
    (before,) = tmp_store.recent(1)

    fat = make_record(
        task="the same task",
        thought="t" * 50_000,
        code="c" * 50_000,
        stdout="s" * 50_000,
        embedding=vector,
    )
    tmp_store.insert(fat, max_records=500)
    (after,) = tmp_store.recent(1)

    assert after.embedding == before.embedding
    assert after.embedding == pytest.approx(vector, abs=FLOAT32_TOL)
    assert (len(after.thought), len(after.code), len(after.stdout)) == (1000, 4000, 1000)


def test_a_task_longer_than_the_varchar_capacity_is_still_stored(
    tmp_store: VectorStore,
) -> None:
    # Milvus Lite counts VARCHAR max_length in CHARACTERS, but a Milvus server
    # counts BYTES. The schema therefore carries UTF-8 headroom, and a task of
    # multi-byte characters at the C11 limit must still be storable.
    assert tmp_store.insert(make_record(task="한" * 5000), max_records=500) is True
    (stored,) = tmp_store.recent(1)
    assert len(stored.task) == 2000


# ------------------------------------------------------------------------------
# AC-7b — dedupe preserves the user-facing id and the creation time  (R14)
# ------------------------------------------------------------------------------


def test_dedupe_replaces_in_place_and_carries_seq_and_created_at_forward(
    tmp_store: VectorStore,
) -> None:
    """AC-7b / R14: `upsert()` overwrites EVERY non-key field, `seq` included.

    V5a's trace returned `seq: 99` on the replaced row. An implementation that
    does not point-query the existing row before upserting silently reallocates
    the display id, and `/memory forget 4` starts addressing a different record
    after a re-ask. No count-based assertion detects this.
    """
    for index in range(5):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=500)

    target = [record for record in tmp_store.recent(5) if record.task == "task 4"][0]
    assert target.id == 4
    assert target.created_at == "2026-08-02T00:00:00+00:00"

    tmp_store.insert(
        make_record(
            task="task 4",
            thought="a better approach",
            code="print(2)",
            stdout="second",
            created_at="2026-12-31T23:59:59+00:00",
            embedding=unit(0.0, 1.0, 0.0),
        ),
        max_records=500,
    )

    assert tmp_store.count() == 5  # replaced in place (V5a)
    (updated,) = [record for record in tmp_store.recent(5) if record.task == "task 4"]
    assert updated.id == 4  # /memory forget 4 still addresses this record
    assert updated.created_at == "2026-08-02T00:00:00+00:00"  # first learned, not last seen
    assert updated.thought == "a better approach"
    assert updated.code == "print(2)"
    assert updated.stdout == "second"
    assert updated.embedding == pytest.approx(unit(0.0, 1.0, 0.0), abs=FLOAT32_TOL)


def test_dedupe_does_not_consume_a_sequence_number(tmp_store: VectorStore) -> None:
    tmp_store.insert(make_record(task="only task"), max_records=500)
    assert tmp_store.meta_get("next_seq") == "1"
    tmp_store.insert(make_record(task="only task", stdout="again"), max_records=500)
    assert tmp_store.meta_get("next_seq") == "1"


def test_dedupe_is_insensitive_to_case_and_whitespace(tmp_store: VectorStore) -> None:
    tmp_store.insert(make_record(task="Sum the primes"), max_records=500)
    tmp_store.insert(make_record(task="  SUM   THE\tPRIMES  "), max_records=500)
    assert tmp_store.count() == 1


def test_dedupe_does_not_trigger_pruning(tmp_store: VectorStore) -> None:
    for index in range(10):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=10)
    tmp_store.insert(make_record(task="task 0", stdout="updated"), max_records=10)
    assert tmp_store.count() == 10


# ------------------------------------------------------------------------------
# AC-7a — pruning, asserted by SURVIVOR IDENTITY  (trap C, R13)
# ------------------------------------------------------------------------------

#: Deliberately shuffled so insertion order coincides with neither the lexical
#: nor the hash ordering of the task texts. A wrong implementation therefore
#: cannot pass by coincidence.
SHUFFLED = (5, 2, 9, 0, 7, 3, 8, 1, 6, 4)


def test_pruning_evicts_the_oldest_by_seq_and_keeps_the_ten_most_recent(
    tmp_store: VectorStore,
) -> None:
    """AC-7a: asserting only `row_count == 10` DOES NOT satisfy this criterion.

    V5 proved `order_by="seq"` is accepted and silently ignored, returning
    insertion order unsorted; an implementation that queries "the oldest N" and
    deletes them passes a count-only assertion while evicting arbitrary records.

    Every record carries an IDENTICAL created_at on purpose: AC-7 inserts in a
    tight loop, so second-granularity timestamps tie and "the oldest record"
    would be non-deterministic under a created_at ordering. `seq` is the only
    stable definition of insertion order.
    """
    frozen = "2026-08-02T12:00:00+00:00"
    for label in SHUFFLED:
        assert tmp_store.insert(
            make_record(task=f"task number {label}", created_at=frozen), max_records=10
        )
    assert tmp_store.count() == 10

    survivors = {record.task: record.id for record in tmp_store.recent(50)}
    assert survivors == {f"task number {label}": seq for seq, label in enumerate(SHUFFLED)}

    assert tmp_store.insert(
        make_record(task="the eleventh task", created_at=frozen), max_records=10
    )

    assert tmp_store.count() == 10
    survivors = {record.task: record.id for record in tmp_store.recent(50)}

    # The FIRST-INSERTED record, and only that one, is gone.
    assert "task number 5" not in survivors
    assert survivors == {
        **{f"task number {label}": seq for seq, label in enumerate(SHUFFLED) if seq > 0},
        "the eleventh task": 10,
    }


def test_pruning_survives_a_query_that_cannot_see_the_whole_collection(
    tmp_store: VectorStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-7a/AC-7d: pruning must not depend on READING the collection (trap D).

    `query()` is hard-capped at 16,384 rows and `query_iterator` is broken, so
    "read the seq values and delete the oldest N" cannot see a large store — and
    that is the whole danger, because below the cap it works perfectly. It
    ships green, and it fails only once a user's store has grown past 16,384
    records, long after anyone is looking.

    Mutation testing found this gap: a prune that deletes the first N rows
    `query()` returns passes the survivor-identity test above, because `seq` is
    allocated monotonically and so physical order and `seq` order coincide at
    small scale. Capping the query in the same shape the engine caps it is what
    makes the two implementations distinguishable HERE rather than in
    production. The correct implementation never calls `query()` while pruning
    at all, so the cap cannot touch it.
    """
    for index in range(20):
        assert tmp_store.insert(make_record(task=f"task {index}"), max_records=500)

    real_query = tmp_store._client.query

    def truncating_query(*args: object, **kwargs: object) -> list:
        # The 16,384-row ceiling, in miniature.
        return list(real_query(*args, **kwargs))[:2]

    monkeypatch.setattr(tmp_store._client, "query", truncating_query)
    assert tmp_store.insert(make_record(task="task 20"), max_records=5)
    monkeypatch.undo()

    assert tmp_store.count() == 5
    assert tasks_of(tmp_store.recent(50)) == [
        "task 20",
        "task 19",
        "task 18",
        "task 17",
        "task 16",
    ]


def test_pruning_removes_as_many_records_as_needed_in_one_pass(
    tmp_store: VectorStore,
) -> None:
    for index in range(12):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=500)
    assert tmp_store.count() == 12

    tmp_store.insert(make_record(task="one more"), max_records=5)

    assert tmp_store.count() == 5
    assert tasks_of(tmp_store.recent(50)) == [
        "one more",
        "task 11",
        "task 10",
        "task 9",
        "task 8",
    ]


def test_pruning_to_a_cap_of_zero_empties_the_store(tmp_store: VectorStore) -> None:
    for index in range(3):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=500)
    tmp_store.insert(make_record(task="last"), max_records=0)
    assert tmp_store.count() == 0


def test_pruning_converges_across_sequence_gaps(tmp_store: VectorStore) -> None:
    """AC-7d: the loop converges on row_count, tolerating gaps.

    Gaps left by `/memory forget` and by earlier pruning are permanent
    (out-of-scope item 16). A loop that assumed `seq` was dense — "delete the
    lowest `excess` sequence numbers and stop" — would terminate below the cap
    or not at all.
    """
    for index in range(20):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=500)
    for seq in range(0, 16):  # a 16-wide hole at the bottom of the seq range
        tmp_store.delete(seq)
    assert tmp_store.count() == 4
    assert tmp_store.meta_get("min_seq") == "0"

    tmp_store.insert(make_record(task="task 20"), max_records=3)

    assert tmp_store.count() == 3
    assert tasks_of(tmp_store.recent(50)) == ["task 20", "task 19", "task 18"]
    # min_seq advanced past the hole rather than looping over it one at a time.
    assert int(tmp_store.meta_get("min_seq")) >= 18


def test_pruning_advances_and_persists_min_seq(tmp_store: VectorStore) -> None:
    for index in range(6):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=3)
    assert tmp_store.count() == 3
    assert tmp_store.meta_get("min_seq") == "3"
    assert tmp_store.meta_get("next_seq") == "6"


def test_the_default_cap_is_100000_and_fits_inside_its_clamp_range() -> None:
    # AC-8: env_int() clamps AFTER falling back, so a ceiling below the default
    # would silently halve the cap with no error and no warning.
    assert memory.DEFAULT_MAX_RECORDS == 100_000
    assert memory.MAX_RECORDS_RANGE == (10, 200_000)
    assert memory.DEFAULT_MAX_RECORDS <= memory.MAX_RECORDS_RANGE[1]


# ------------------------------------------------------------------------------
# search()  — ranking
# ------------------------------------------------------------------------------


def store_vector(store: VectorStore, task: str, vector: list[float]) -> None:
    assert store.insert(make_record(task=task, embedding=vector), max_records=500)


def test_search_on_an_empty_store_returns_nothing(tmp_store: VectorStore) -> None:
    assert tmp_store.search([1.0, 0.0, 0.0], 1, 0.65, EMBED_MODEL, 3) == []


def test_search_returns_the_most_similar_record_first(tmp_store: VectorStore) -> None:
    query = unit(1.0, 0.0, 0.0)
    store_vector(tmp_store, "near", unit(0.95, 0.30, 0.0))
    store_vector(tmp_store, "nearest", unit(1.0, 0.02, 0.0))
    store_vector(tmp_store, "far-ish", unit(0.70, 0.70, 0.0))

    hits = tmp_store.search(query, 3, 0.0, EMBED_MODEL, 3)
    assert [hit.record.task for hit in hits] == ["nearest", "near", "far-ish"]
    assert isinstance(hits[0], memory.Hit)
    assert hits[0].similarity > hits[1].similarity > hits[2].similarity


def test_search_honours_top_k(tmp_store: VectorStore) -> None:
    query = unit(1.0, 0.0, 0.0)
    for index in range(5):
        store_vector(tmp_store, f"task {index}", unit(1.0, 0.01 * index, 0.0))

    assert len(tmp_store.search(query, 1, 0.0, EMBED_MODEL, 3)) == 1
    assert len(tmp_store.search(query, 3, 0.0, EMBED_MODEL, 3)) == 3
    assert memory.DEFAULT_TOP_K == 1  # constraint C7


def test_search_with_a_non_positive_top_k_or_no_query_returns_nothing(
    tmp_store: VectorStore,
) -> None:
    store_vector(tmp_store, "anything", [1.0, 0.0, 0.0])
    assert tmp_store.search([1.0, 0.0, 0.0], 0, 0.0, EMBED_MODEL, 3) == []
    assert tmp_store.search([], 1, 0.0, EMBED_MODEL, 3) == []


def test_search_returns_the_full_record_including_its_vector(
    tmp_store: VectorStore,
) -> None:
    vector = unit(0.37, -0.91, 0.15)
    store_vector(tmp_store, "identical", vector)

    (hit,) = tmp_store.search(vector, 1, 0.0, EMBED_MODEL, 3)
    assert hit.record.task == "identical"
    assert hit.record.id == 0
    assert hit.record.created_at == "2026-08-02T00:00:00+00:00"
    assert hit.record.chat_model == CHAT_MODEL
    assert hit.record.embedding == pytest.approx(vector, abs=FLOAT32_TOL)
    # Self-similarity is ~0.9999997, not 1.0, and may sit a hair above 1.0.
    assert hit.similarity == pytest.approx(1.0, abs=FLOAT32_TOL)


def test_search_with_a_query_of_the_wrong_dimension_degrades_to_a_miss(
    tmp_store: VectorStore,
) -> None:
    # Milvus raises on a dimension mismatch. M5 forbids letting that escape into
    # the middle of a turn, and a mismatched pair is not comparable anyway, so
    # the correct outcome is a guaranteed miss — the same contract dot() has.
    store_vector(tmp_store, "three dims", unit(1.0, 0.0, 0.0))
    assert tmp_store.search([1.0, 0.0], 1, 0.0, EMBED_MODEL, 2) == []


# ------------------------------------------------------------------------------
# search()  — the threshold boundary  (AC-6, constraint C5)
# ------------------------------------------------------------------------------
#
# M3 says a similarity "below" the threshold is a miss, so the comparison must
# be `>=` and the boundary value itself must be a HIT.
#
# The boundary is taken from the score the engine actually returns rather than
# from an arithmetically contrived pair: COSINE normalises both operands, and
# the float32 storage means no round decimal is exactly representable. Asserting
# against `nextafter` of the observed score tests the operator itself, which is
# the whole point, and cannot go stale if the engine's rounding changes.


def test_a_similarity_exactly_at_the_threshold_is_a_hit(tmp_store: VectorStore) -> None:
    store_vector(tmp_store, "boundary", unit(1.0, 0.5, 0.0))
    query = unit(1.0, 0.0, 0.0)

    (ranked,) = tmp_store.search(query, 1, -1.0, EMBED_MODEL, 3)
    observed = ranked.similarity
    assert 0.0 < observed < 1.0  # a genuine partial match, not a degenerate one

    assert len(tmp_store.search(query, 1, observed, EMBED_MODEL, 3)) == 1
    assert tmp_store.search(query, 1, math.nextafter(observed, 2.0), EMBED_MODEL, 3) == []


def test_the_default_threshold_is_0_65_not_0_75() -> None:
    # Constraint C5, revised on V3 evidence: 0.75 sat 0.004 below AC-2's own
    # worked example (measured 0.7540), making that criterion flaky by
    # construction. Unrelated pairs measured 0.297-0.395. The live smoke run
    # scored the same pair at 0.76.
    assert memory.DEFAULT_MIN_SIMILARITY == 0.65


def test_the_default_threshold_separates_the_measured_populations(
    tmp_store: VectorStore,
) -> None:
    # A realistic unit-vector check with margin on both sides, standing in for
    # the V3 distribution: a true positive at ~0.75, noise at ~0.35.
    query = unit(1.0, 0.0)
    store_vector(tmp_store, "related", unit(0.754, math.sqrt(1 - 0.754**2)))
    store_vector(tmp_store, "unrelated", unit(0.35, math.sqrt(1 - 0.35**2)))

    hits = tmp_store.search(query, 5, memory.DEFAULT_MIN_SIMILARITY, EMBED_MODEL, 2)
    assert [hit.record.task for hit in hits] == ["related"]


# ------------------------------------------------------------------------------
# AC-10 — the Milvus score IS a cosine similarity, checked against dot()
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stored",
    [(1.0, 0.0, 0.0), (0.9, 0.4, 0.2), (0.3, 0.9, 0.3), (-0.5, 0.5, 0.7), (0.0, 0.0, 1.0)],
    ids=["identical", "close", "middling", "opposed", "orthogonal"],
)
def test_the_milvus_score_equals_the_pure_python_dot_product(
    tmp_store: VectorStore, stored: tuple[float, float, float]
) -> None:
    """AC-10: Milvus's COSINE score, cross-checked against the retained oracle.

    `dot()` and `l2_normalise()` stay in memory.py after the scan is gone for
    exactly this test. Every threshold comparison in the system is written as a
    lower bound; a metric returning a DISTANCE would invert all of them and
    silently turn the system into one that recalls the LEAST similar record —
    while still recalling something every turn, and so still looking alive.
    """
    query = unit(1.0, 0.0, 0.0)
    stored_unit = unit(*stored)
    store_vector(tmp_store, "the record", stored_unit)

    (hit,) = tmp_store.search(query, 1, -1.0, EMBED_MODEL, 3)
    assert hit.similarity == pytest.approx(memory.dot(query, stored_unit), abs=1e-6)


def test_a_similar_pair_scores_higher_than_a_dissimilar_pair(
    tmp_store: VectorStore,
) -> None:
    """AC-10: the DIRECTION of the metric, not merely its magnitude."""
    query = unit(1.0, 0.0)
    store_vector(tmp_store, "near 0.9", unit(0.9, math.sqrt(1 - 0.9**2)))
    store_vector(tmp_store, "far 0.3", unit(0.3, math.sqrt(1 - 0.3**2)))

    hits = tmp_store.search(query, 2, -1.0, EMBED_MODEL, 2)
    scores = {hit.record.task: hit.similarity for hit in hits}
    assert scores["near 0.9"] == pytest.approx(0.9, abs=1e-6)
    assert scores["far 0.3"] == pytest.approx(0.3, abs=1e-6)
    assert scores["near 0.9"] > scores["far 0.3"]  # higher-is-better


# ------------------------------------------------------------------------------
# AC-12 — the eligibility filter is applied BY the search  (M3, R8)
# ------------------------------------------------------------------------------


def test_a_stale_perfect_match_loses_to_an_adequate_current_one_at_top_k_1(
    tmp_store: VectorStore,
) -> None:
    """AC-12: post-filtering fails this criterion.

    With top_k=1 (C7) a stale PERFECT match would occupy the only result slot
    and be discarded afterwards, yielding a miss where a hit was available — and
    the system would look merely unlucky rather than wrong. Milvus ranks before
    we can inspect, so the restriction must ride on the search call.
    """
    query = unit(1.0, 0.0, 0.0)
    tmp_store.insert(
        make_record(task="stale but identical", embedding=query, embed_model="old-model"),
        max_records=500,
    )
    store_vector(tmp_store, "current but weaker", unit(0.8, 0.6, 0.0))

    hits = tmp_store.search(query, 1, 0.0, EMBED_MODEL, 3)
    assert [hit.record.task for hit in hits] == ["current but weaker"]


def test_search_never_returns_a_record_with_a_mismatched_embed_model(
    tmp_store: VectorStore,
) -> None:
    query = unit(1.0, 0.0, 0.0)
    tmp_store.insert(
        make_record(task="stale but identical", embedding=query, embed_model="old-model"),
        max_records=500,
    )
    store_vector(tmp_store, "current but weaker", unit(0.8, 0.6, 0.0))

    hits = tmp_store.search(query, 5, 0.0, EMBED_MODEL, 3)
    assert [hit.record.task for hit in hits] == ["current but weaker"]


def test_search_never_returns_a_record_stamped_with_a_mismatched_dim(
    tmp_store: VectorStore,
) -> None:
    # The `dim` half of the filter is not redundant: a record whose stored `dim`
    # disagrees with the current configuration is not comparable, however the
    # collection came to hold it.
    store_vector(tmp_store, "right dim", unit(0.8, 0.6, 0.0))
    assert tmp_store.search(unit(1.0, 0.0, 0.0), 5, 0.0, EMBED_MODEL, 999) == []


def test_a_store_of_nothing_but_stale_vectors_is_a_miss_not_an_error(
    tmp_store: VectorStore,
) -> None:
    # R8: mismatched rows become INERT, not wrong.
    tmp_store.insert(
        make_record(embedding=unit(1.0, 0.0, 0.0), embed_model="old-model"), max_records=500
    )
    assert tmp_store.search(unit(1.0, 0.0, 0.0), 1, 0.0, EMBED_MODEL, 3) == []


def test_an_embed_model_containing_quotes_does_not_break_the_filter(
    tmp_store: VectorStore,
) -> None:
    # The filter is an expression string, so the model tag has to be escaped
    # rather than interpolated. A tag is operator-supplied via
    # CODERUNNER_EMBED_MODEL and is not trusted input.
    hostile = 'we"ird\\model'
    tmp_store.insert(
        make_record(embedding=unit(1.0, 0.0, 0.0), embed_model=hostile), max_records=500
    )

    assert tmp_store.search(unit(1.0, 0.0, 0.0), 1, 0.0, hostile, 3)
    assert tmp_store.search(unit(1.0, 0.0, 0.0), 1, 0.0, EMBED_MODEL, 3) == []


# ------------------------------------------------------------------------------
# recent() / delete() / clear() / stats()
# ------------------------------------------------------------------------------


def test_recent_returns_newest_first_and_honours_the_limit(tmp_store: VectorStore) -> None:
    for index in range(5):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=500)

    assert tasks_of(tmp_store.recent(2)) == ["task 4", "task 3"]
    assert tasks_of(tmp_store.recent(50)) == [f"task {i}" for i in reversed(range(5))]


def test_recent_widens_its_window_until_it_has_enough_records(
    tmp_store: VectorStore,
) -> None:
    """The `order_by`-free replacement for `ORDER BY id DESC LIMIT ?`.

    `recent()` derives its window from `next_seq` and range-filters, so a store
    riddled with gaps must widen the window rather than silently under-report.
    """
    for index in range(30):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=500)
    for seq in range(2, 28):  # leaves seq 0, 1, 28, 29
        tmp_store.delete(seq)
    assert tmp_store.count() == 4

    assert tasks_of(tmp_store.recent(3)) == ["task 29", "task 28", "task 1"]
    assert tasks_of(tmp_store.recent(10)) == ["task 29", "task 28", "task 1", "task 0"]


def test_recent_with_a_non_positive_limit_returns_nothing(tmp_store: VectorStore) -> None:
    tmp_store.insert(make_record(), max_records=500)
    assert tmp_store.recent(0) == []
    assert tmp_store.recent(-3) == []


def test_recent_on_an_empty_store_returns_nothing(tmp_store: VectorStore) -> None:
    assert tmp_store.recent(10) == []


def test_delete_resolves_seq_to_the_primary_key_and_removes_that_record(
    tmp_store: VectorStore,
) -> None:
    # AC-9 / V5a: `forget N` resolves seq == N to a task_hash and deletes by
    # primary key, removing exactly the record the user saw in `/memory list`.
    for index in range(3):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=500)

    assert tmp_store.delete(1) is True
    assert tmp_store.count() == 2
    assert tasks_of(tmp_store.recent(10)) == ["task 2", "task 0"]


def test_delete_of_a_missing_seq_reports_failure_without_raising(
    tmp_store: VectorStore,
) -> None:
    # AC-9: `/memory forget 99999` prints not-found, deletes nothing, raises
    # nothing. Milvus's delete-by-id reports success for ids that never existed,
    # so this MUST be resolved by a point query first.
    tmp_store.insert(make_record(), max_records=500)
    assert tmp_store.delete(99999) is False
    assert tmp_store.count() == 1


def test_delete_on_an_empty_store_is_harmless(tmp_store: VectorStore) -> None:
    assert tmp_store.delete(1) is False


def test_clear_removes_everything_and_returns_the_count(tmp_store: VectorStore) -> None:
    for index in range(3):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=500)

    assert tmp_store.clear() == 3
    assert tmp_store.count() == 0
    assert tmp_store.clear() == 0


def test_clear_keeps_sequence_allocation_monotonic(tmp_store: VectorStore) -> None:
    # Reusing sequence numbers after a clear would make `/memory forget 0` mean
    # two different records over one session's lifetime.
    for index in range(3):
        tmp_store.insert(make_record(task=f"task {index}"), max_records=500)
    tmp_store.clear()

    tmp_store.insert(make_record(task="after the clear"), max_records=500)
    (record,) = tmp_store.recent(10)
    assert record.id == 3


def test_stats_reports_the_fields_the_memory_command_needs(tmp_store: VectorStore) -> None:
    # AC-9: path, total count, eligible count, embedding model, dimension, size.
    store_vector(tmp_store, "current", unit(1.0, 0.0, 0.0))
    tmp_store.insert(
        make_record(task="stale", embedding=unit(1.0, 0.0, 0.0), embed_model="old-model"),
        max_records=500,
    )

    stats = tmp_store.stats(EMBED_MODEL, 3)
    assert stats["count"] == 2
    assert stats["eligible"] == 1
    assert stats["embed_model"] == EMBED_MODEL
    assert stats["dim"] == 3
    assert stats["path"].endswith("memory.milvus.db")
    assert stats["bytes"] > 0
    assert stats["error"] is None


def test_stats_sums_the_milvus_file_set_recursively(tmp_store: VectorStore) -> None:
    """AC-9: Milvus Lite writes a DIRECTORY tree, not one file.

    `Path.stat().st_size` on the top-level directory reports a few hundred
    bytes regardless of content, which would understate by orders of magnitude
    precisely the footprint spec.md 4.1 obliges the documentation to be honest
    about.
    """
    for index in range(20):
        tmp_store.insert(
            make_record(task=f"task {index}", stdout="x" * 900, embedding=[0.5] * 64),
            max_records=500,
        )

    reported = tmp_store.stats()["bytes"]
    on_disk = sum(f.stat().st_size for f in tmp_store.path.rglob("*") if f.is_file())
    assert reported == on_disk
    assert reported > tmp_store.path.stat().st_size


def test_stats_falls_back_to_the_meta_recorded_model_and_dim(
    tmp_store: VectorStore,
) -> None:
    tmp_store.insert(make_record(embedding=[0.0] * 4), max_records=500)
    stats = tmp_store.stats()
    assert stats["embed_model"] == EMBED_MODEL
    assert stats["dim"] == 4
    assert stats["eligible"] == 1


def test_stats_on_an_empty_store_reports_zeroes(tmp_store: VectorStore) -> None:
    stats = tmp_store.stats()
    assert stats["count"] == 0
    assert stats["eligible"] == 0
    assert stats["embed_model"] is None
    assert stats["dim"] is None
    assert stats["error"] is None


def test_stats_with_an_explicit_config_on_a_cold_store_reports_zero_eligible(
    tmp_store: VectorStore,
) -> None:
    # `/memory` on the very first launch: the configuration names a model and a
    # dimension, but no collection exists yet to count anything in. Zero
    # eligible is the answer; an exception is not.
    stats = tmp_store.stats(EMBED_MODEL, 768)
    assert stats["count"] == 0
    assert stats["eligible"] == 0
    assert stats["error"] is None


def test_stats_reports_zero_bytes_when_the_store_has_vanished(
    tmp_store: VectorStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    # AC-3f in miniature: the volume disappeared under a live handle.
    def gone(*args: object, **kwargs: object) -> object:
        raise OSError("no such file or directory")

    monkeypatch.setattr(vectorstore.Path, "rglob", gone)
    assert tmp_store.stats()["bytes"] == 0


# ------------------------------------------------------------------------------
# Degradation after close  — M5
# ------------------------------------------------------------------------------


def test_every_operation_degrades_rather_than_raises_after_close(
    tmp_store: VectorStore,
) -> None:
    tmp_store.insert(make_record(), max_records=500)
    tmp_store.close()

    assert tmp_store.insert(make_record(task="later"), max_records=500) is False
    assert tmp_store.count() == 0
    assert tmp_store.recent(5) == []
    assert tmp_store.delete(0) is False
    assert tmp_store.clear() == 0
    assert tmp_store.search([1.0, 0.0, 0.0], 1, 0.0, EMBED_MODEL, 3) == []
    assert tmp_store.meta_get("schema_version") is None
    assert tmp_store.index_info() == {}

    stats = tmp_store.stats()
    assert stats["error"] is not None


def test_close_is_idempotent(tmp_store: VectorStore) -> None:
    tmp_store.close()
    tmp_store.close()  # must not raise


def test_close_swallows_a_failing_client_close(
    tmp_store: VectorStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom() -> None:
        raise RuntimeError("cannot close")

    monkeypatch.setattr(tmp_store._client, "close", boom)
    tmp_store.close()  # must not raise
