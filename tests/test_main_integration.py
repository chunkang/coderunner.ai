# ==============================================================================
#  CodeRunner.AI  ::  main.py — stream_llm and agentic_turn with a fake client
# ------------------------------------------------------------------------------
#  Project : SPEC-MEMORY-001, tasks T7-T10
#  Covers  : AC-1 (cold start), AC-2 (injection position and ephemerality),
#            AC-6/AC-6b (miss still captures), and the M2 non-capture rules.
#
#  main.py is NOT under the coverage gate (acceptance.md scopes that to
#  memory.py and recall.py). These tests exist because main.py has had zero
#  tests of any kind, so the T7 signature change and the T9/T10 wiring would
#  otherwise be verifiable only by a human running the product.
#
#  Skipped rather than failed when rich/ollama/httpx are absent, so the
#  stdlib-only memory.py suite still runs clean on a bare interpreter.
# ==============================================================================

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, Sequence

import pytest

pytest.importorskip("rich", reason="main.py needs rich; run in-container")
pytest.importorskip("ollama", reason="main.py needs ollama; run in-container")
pytest.importorskip("httpx", reason="main.py needs httpx; run in-container")

import main  # noqa: E402
import memory  # noqa: E402
from vectorstore import VectorStore  # noqa: E402

from conftest import make_record  # noqa: E402


class FakeClient:
    """Stands in for ollama.Client, exposing the two methods main.py uses."""

    def __init__(
        self,
        responses: Sequence[str],
        embedding: Sequence[float] | None = None,
        embed_raises: BaseException | None = None,
    ) -> None:
        self.responses = list(responses)
        self.embedding = list(embedding) if embedding is not None else [1.0, 0.0]
        self.embed_raises = embed_raises
        self.chat_calls: list[list[dict]] = []
        self.embed_calls: list[dict] = []

    def chat(
        self, model: str = "", messages: Any = None, stream: bool = False
    ) -> Iterator[dict]:
        # Snapshot the list AND its dicts: agentic_turn appends to
        # conv.messages after this call, and a shallow alias would let those
        # later mutations rewrite what we recorded.
        self.chat_calls.append([dict(message) for message in (messages or [])])
        text = self.responses.pop(0) if self.responses else "Answer: done"
        return iter([{"message": {"content": text}}])

    def embed(self, model: str = "", input: Any = "", keep_alive: Any = None) -> dict:  # noqa: A002
        self.embed_calls.append({"model": model, "input": input, "keep_alive": keep_alive})
        if self.embed_raises is not None:
            raise self.embed_raises
        return {"embeddings": [list(self.embedding)]}

    @property
    def embed_count(self) -> int:
        return len(self.embed_calls)


CODE_REPLY = "Thought: print it.\n\n```python\nprint(42)\n```"
ANSWER_REPLY = "Answer: the value is 42."
DIRECT_REPLY = "Answer: a list is mutable, a tuple is not."


@pytest.fixture()
def conv() -> "main.Conversation":
    conversation = main.Conversation()
    conversation.system(main.SYSTEM_PROMPT)
    return conversation


@pytest.fixture(autouse=True)
def fast_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep turns short and thresholds predictable."""
    monkeypatch.setattr(main, "MAX_RETRIES", 2)


@pytest.fixture()
def status_lines(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Record every status() call so degradation reporting can be asserted."""
    recorded: list[dict] = []

    def recorder(icon: str, tag: str, message: str, style: str = "cyan") -> None:
        recorded.append({"icon": icon, "tag": tag, "message": message, "style": style})

    monkeypatch.setattr(main, "status", recorder)
    return recorded


def memory_lines(recorded: list[dict]) -> list[dict]:
    return [line for line in recorded if line["tag"] == "Memory"]


def warnings_of(recorded: list[dict]) -> list[dict]:
    return [line for line in memory_lines(recorded) if line["style"] == "yellow"]


# ------------------------------------------------------------------------------
# T7 — stream_llm now takes an explicit message list
# ------------------------------------------------------------------------------


def test_stream_llm_accepts_a_message_list_and_yields_content() -> None:
    client = FakeClient(["hello world"])
    messages = [{"role": "user", "content": "hi"}]

    assert "".join(main.stream_llm(client, messages)) == "hello world"
    assert client.chat_calls[0] == messages


def test_stream_llm_skips_empty_chunks() -> None:
    class Chunky(FakeClient):
        def chat(self, model: str = "", messages: Any = None, stream: bool = False):
            return iter(
                [
                    {"message": {"content": "a"}},
                    {"message": {"content": ""}},
                    {},  # no message key at all
                    {"message": {"content": "b"}},
                ]
            )

    assert "".join(main.stream_llm(Chunky([]), [])) == "ab"


# ------------------------------------------------------------------------------
# AC-1 — cold start
# ------------------------------------------------------------------------------


def test_cold_start_injects_nothing_and_sends_the_pre_feature_message_list(
    tmp_store: VectorStore, conv: "main.Conversation"
) -> None:
    """AC-1: the attempt-1 request is byte-for-byte the pre-feature list."""
    client = FakeClient([CODE_REPLY, ANSWER_REPLY])
    expected_first_request = [dict(message) for message in conv.messages] + [
        {"role": "user", "content": "compute the answer"}
    ]

    main.agentic_turn(client, conv, "compute the answer", tmp_store)

    assert client.chat_calls[0] == expected_first_request
    assert all(
        message["role"] != "system" or message["content"] == main.SYSTEM_PROMPT
        for message in client.chat_calls[0]
    )


def test_cold_start_captures_the_first_record_with_exactly_one_embed(
    tmp_store: VectorStore, conv: "main.Conversation"
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY])
    main.agentic_turn(client, conv, "compute the answer", tmp_store)

    assert tmp_store.count() == 1
    (stored,) = tmp_store.recent(1)
    assert stored.task == "compute the answer"
    assert stored.code == "print(42)"
    assert "42" in stored.stdout
    assert stored.chat_model == main.MODEL_NAME
    assert stored.embed_model == main.EMBED_MODEL
    assert client.embed_count == 1


def test_cold_start_pays_no_embed_for_retrieval(
    tmp_store: VectorStore, conv: "main.Conversation"
) -> None:
    # The single embed above must be the CAPTURE one. Retrieval on an empty
    # store must not call the backend at all (M3).
    client = FakeClient([DIRECT_REPLY])
    main.agentic_turn(client, conv, "explain lists", tmp_store)
    assert client.embed_count == 0  # DIRECT return: no capture either


# ------------------------------------------------------------------------------
# AC-2 — injection
# ------------------------------------------------------------------------------


@pytest.fixture()
def store_with_prior(tmp_store: VectorStore) -> VectorStore:
    tmp_store.insert(
        make_record(
            task="What is the current weather in Seoul in Celsius?",
            thought="Fetch wttr.in and read temp_C.",
            code="print('29C')",
            stdout="29C",
            embedding=memory.l2_normalise([1.0, 0.0]),
        ),
        max_records=500,
    )
    return tmp_store


def test_a_hit_injects_exactly_one_system_message_before_the_user_message(
    store_with_prior: VectorStore, conv: "main.Conversation"
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[1.0, 0.0])
    main.agentic_turn(client, conv, "Tell me the temperature in Busan right now", store_with_prior)

    first_request = client.chat_calls[0]
    injected = first_request[-2]
    assert injected["role"] == "system"
    assert "PRIOR SUCCESSFUL SOLUTION" in injected["content"]
    assert memory.ADAPT_OR_IGNORE_SENTENCE in injected["content"]
    assert first_request[-1]["role"] == "user"
    assert first_request[-1]["content"] == "Tell me the temperature in Busan right now"

    system_messages = [m for m in first_request if m["role"] == "system"]
    assert len(system_messages) == 2  # the base prompt plus exactly one block


def test_injection_does_not_mutate_the_conversation(
    store_with_prior: VectorStore, conv: "main.Conversation"
) -> None:
    """AC-2: conv.messages must be what the pre-feature product would hold.

    One successful attempt appends: user(task), assistant(thought),
    user(stdout feedback), assistant(answer) — four, on top of the system
    prompt. A recall block that leaked into the conversation would make five.
    """
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[1.0, 0.0])
    main.agentic_turn(client, conv, "Tell me the temperature in Busan", store_with_prior)

    assert len(conv.messages) == 5
    assert [m["role"] for m in conv.messages] == [
        "system",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert all("PRIOR SUCCESSFUL SOLUTION" not in m["content"] for m in conv.messages)


def test_the_grounded_answer_pass_receives_no_recall_block(
    store_with_prior: VectorStore, conv: "main.Conversation"
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[1.0, 0.0])
    main.agentic_turn(client, conv, "Tell me the temperature in Busan", store_with_prior)

    assert len(client.chat_calls) == 2
    grounded = client.chat_calls[1]
    assert all("PRIOR SUCCESSFUL SOLUTION" not in m["content"] for m in grounded)


def test_retry_attempts_receive_no_recall_block(
    store_with_prior: VectorStore, conv: "main.Conversation"
) -> None:
    """Constraint C8: attempt 1 only."""
    failing = "Thought: oops.\n\n```python\nraise SystemExit(3)\n```"
    client = FakeClient([failing, failing], embedding=[1.0, 0.0])

    main.agentic_turn(client, conv, "Tell me the temperature in Busan", store_with_prior)

    assert len(client.chat_calls) == 2
    assert any("PRIOR SUCCESSFUL SOLUTION" in m["content"] for m in client.chat_calls[0])
    assert all("PRIOR SUCCESSFUL SOLUTION" not in m["content"] for m in client.chat_calls[1])


def test_the_executed_code_comes_from_this_turn_not_from_the_store(
    store_with_prior: VectorStore, conv: "main.Conversation"
) -> None:
    """Constraint C2: stored code is context, never replayed."""
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[1.0, 0.0])
    main.agentic_turn(client, conv, "Tell me the temperature in Busan", store_with_prior)

    fresh = [record for record in store_with_prior.recent(10) if record.task.startswith("Tell me")]
    assert len(fresh) == 1
    assert fresh[0].code == "print(42)"  # this turn's script
    assert fresh[0].code != "print('29C')"  # not the stored one


# ------------------------------------------------------------------------------
# AC-6b — a miss still captures, still one embed
# ------------------------------------------------------------------------------


def test_a_missed_retrieval_still_captures_and_embeds_once(
    store_with_prior: VectorStore, conv: "main.Conversation"
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[0.0, 1.0])  # orthogonal
    main.agentic_turn(client, conv, "a completely unrelated new task", store_with_prior)

    assert all(
        "PRIOR SUCCESSFUL SOLUTION" not in m["content"] for m in client.chat_calls[0]
    )
    assert store_with_prior.count() == 2  # the store learned
    assert client.embed_count == 1


# ------------------------------------------------------------------------------
# M2 — the non-capture rules
# ------------------------------------------------------------------------------


def test_a_direct_protocol_turn_is_not_captured(
    tmp_store: VectorStore, conv: "main.Conversation"
) -> None:
    """AC-6: the no-code-block early return stores nothing."""
    client = FakeClient([DIRECT_REPLY])
    main.agentic_turn(client, conv, "Explain list versus tuple", tmp_store)
    assert tmp_store.count() == 0


def test_a_failed_execution_is_not_captured(
    tmp_store: VectorStore, conv: "main.Conversation"
) -> None:
    failing = "Thought: oops.\n\n```python\nraise SystemExit(3)\n```"
    client = FakeClient([failing, failing])
    main.agentic_turn(client, conv, "do the impossible", tmp_store)
    assert tmp_store.count() == 0


def test_retry_exhaustion_is_not_captured(
    tmp_store: VectorStore, conv: "main.Conversation"
) -> None:
    failing = "Thought: oops.\n\n```python\nraise SystemExit(3)\n```"
    client = FakeClient([failing, failing])
    main.agentic_turn(client, conv, "do the impossible", tmp_store)
    assert tmp_store.count() == 0
    assert len(client.chat_calls) == main.MAX_RETRIES


# ------------------------------------------------------------------------------
# AC-3 — degradation inside a real turn
# ------------------------------------------------------------------------------


def test_a_turn_completes_normally_with_no_store_at_all(
    conv: "main.Conversation",
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY])
    main.agentic_turn(client, conv, "compute the answer", None)

    assert len(client.chat_calls) == 2
    assert client.embed_count == 0
    assert len(conv.messages) == 5


def test_a_turn_completes_when_the_embedding_backend_is_down(
    store_with_prior: VectorStore, conv: "main.Conversation"
) -> None:
    """AC-3a inside a full turn: no exception, no capture, turn still works."""
    import ollama

    client = FakeClient(
        [CODE_REPLY, ANSWER_REPLY], embed_raises=ollama.ResponseError("not pulled")
    )
    main.agentic_turn(client, conv, "some task", store_with_prior)

    assert len(client.chat_calls) == 2
    assert len(conv.messages) == 5
    assert store_with_prior.count() == 1  # unchanged; nothing captured
    # One failed retrieval attempt, NOT retried at capture time.
    assert client.embed_count == 1


def test_memory_disabled_means_no_store_and_no_embedding(
    conv: "main.Conversation", monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main, "MEMORY_ENABLED", False)
    assert main._open_memory_store() is None


def test_open_memory_store_degrades_on_an_unwritable_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("regular file", encoding="utf-8")

    monkeypatch.setattr(main, "MEMORY_ENABLED", True)
    monkeypatch.setattr(main, "MEMORY_DB", blocker / "memory.db")
    assert main._open_memory_store() is None  # no exception escapes


# ------------------------------------------------------------------------------
# M5 — degradation must be VISIBLE, and exactly once per turn
# ------------------------------------------------------------------------------
#
# The smoke run found this silent: with the embedding model removed, turns
# completed correctly but emitted nothing at all, so a user had no way to learn
# that memory had stopped working. That is risk R7 — silent degradation —
# reached from a different direction than trap A.
#
# The invariant is one WARNING per turn. A turn where retrieval fails and
# capture then also fails must warn once, not twice: on a degraded session the
# second line is pure noise on every single turn.


def test_a_failed_retrieval_emits_exactly_one_warning(
    store_with_prior: VectorStore, conv: "main.Conversation", status_lines: list[dict]
) -> None:
    import ollama

    client = FakeClient(
        [CODE_REPLY, ANSWER_REPLY], embed_raises=ollama.ResponseError("not pulled")
    )
    main.agentic_turn(client, conv, "some task", store_with_prior)

    warnings = warnings_of(status_lines)
    assert len(warnings) == 1
    assert warnings[0]["icon"] == "🧠"
    assert warnings[0]["tag"] == "Memory"
    assert "continuing without memory" in warnings[0]["message"].lower()
    assert len(client.chat_calls) == 2  # the turn itself is unaffected


def test_a_failed_cold_start_capture_emits_exactly_one_warning(
    tmp_store: VectorStore, conv: "main.Conversation", status_lines: list[dict]
) -> None:
    """Retrieval never embedded (empty store); the CAPTURE embed is what failed."""
    import ollama

    client = FakeClient(
        [CODE_REPLY, ANSWER_REPLY], embed_raises=ollama.ResponseError("not pulled")
    )
    main.agentic_turn(client, conv, "the first task", tmp_store)

    assert len(warnings_of(status_lines)) == 1
    assert tmp_store.count() == 0


def test_retrieval_and_capture_both_failing_still_warns_only_once(
    store_with_prior: VectorStore, conv: "main.Conversation", status_lines: list[dict]
) -> None:
    """The assertion that stops a well-meaning fix from double-reporting.

    Retrieval attempts an embed and fails; capture then finds no cached vector
    and cannot produce one either. Both paths are broken in the same turn, and
    the user must still be told exactly once.
    """
    import ollama

    client = FakeClient(
        [CODE_REPLY, ANSWER_REPLY], embed_raises=ollama.ResponseError("not pulled")
    )
    main.agentic_turn(client, conv, "some task", store_with_prior)

    assert client.embed_count == 1  # retrieval tried; capture did not retry
    assert store_with_prior.count() == 1  # nothing captured
    assert len(warnings_of(status_lines)) == 1


def test_an_unwritable_store_warns_once_on_capture(
    store_with_prior: VectorStore, conv: "main.Conversation", status_lines: list[dict]
) -> None:
    """remember_success() returning False was silent too."""
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[0.0, 1.0])
    store_with_prior.close()  # every write now fails

    main.agentic_turn(client, conv, "some task", store_with_prior)

    warnings = warnings_of(status_lines)
    assert len(warnings) == 1
    assert "continuing without memory" in warnings[0]["message"].lower()


def test_the_healthy_hit_path_warns_about_nothing(
    store_with_prior: VectorStore, conv: "main.Conversation", status_lines: list[dict]
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[1.0, 0.0])
    main.agentic_turn(client, conv, "Tell me the temperature in Busan", store_with_prior)

    assert warnings_of(status_lines) == []
    recalled = [line for line in memory_lines(status_lines) if "Recalled" in line["message"]]
    assert len(recalled) == 1
    assert recalled[0]["style"] == "green"


def test_the_healthy_cold_start_path_warns_about_nothing(
    tmp_store: VectorStore, conv: "main.Conversation", status_lines: list[dict]
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY])
    main.agentic_turn(client, conv, "the first task", tmp_store)

    assert warnings_of(status_lines) == []
    captured = [line for line in memory_lines(status_lines) if "Captured" in line["message"]]
    assert len(captured) == 1
    assert captured[0]["style"] == "green"
    assert tmp_store.count() == 1


def test_the_empty_store_short_circuit_is_not_a_failure(
    tmp_store: VectorStore, conv: "main.Conversation", status_lines: list[dict]
) -> None:
    """A cold start skipping the embed is a deliberate optimisation (M3), not a fault.

    Warning here would fire on the very first turn of every fresh install.
    """
    client = FakeClient([DIRECT_REPLY])  # DIRECT: no capture either
    main.agentic_turn(client, conv, "explain lists", tmp_store)

    assert client.embed_count == 0
    assert warnings_of(status_lines) == []
    assert memory_lines(status_lines) == []


def test_memory_disabled_emits_nothing_at_all(
    tmp_store: VectorStore,
    conv: "main.Conversation",
    status_lines: list[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CODERUNNER_MEMORY=0 is a choice, not a fault. Never report it per turn."""
    monkeypatch.setattr(main, "MEMORY_ENABLED", False)
    disabled = memory.MemoryConfig(
        enabled=False,
        embed_model=main.EMBED_MODEL,
        chat_model=main.MODEL_NAME,
        db_path=tmp_store.path,
        top_k=1,
        min_sim=0.65,
        max_records=500,
    )
    monkeypatch.setattr(main, "MEMORY_CFG", disabled)

    client = FakeClient([CODE_REPLY, ANSWER_REPLY])
    main.agentic_turn(client, conv, "some task", tmp_store)

    assert memory_lines(status_lines) == []
    assert client.embed_count == 0


def test_no_store_at_all_emits_nothing_per_turn(
    conv: "main.Conversation", status_lines: list[dict]
) -> None:
    # The unavailable store is reported ONCE at startup by _open_memory_store,
    # not on every turn thereafter.
    client = FakeClient([CODE_REPLY, ANSWER_REPLY])
    main.agentic_turn(client, conv, "some task", None)
    assert memory_lines(status_lines) == []


def test_startup_reports_an_unavailable_store_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status_lines: list[dict]
) -> None:
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("regular file", encoding="utf-8")
    monkeypatch.setattr(main, "MEMORY_ENABLED", True)
    monkeypatch.setattr(main, "MEMORY_DB", blocker / "memory.db")

    assert main._open_memory_store() is None
    assert len(warnings_of(status_lines)) == 1


def test_startup_says_nothing_when_memory_is_disabled(
    monkeypatch: pytest.MonkeyPatch, status_lines: list[dict]
) -> None:
    monkeypatch.setattr(main, "MEMORY_ENABLED", False)
    assert main._open_memory_store() is None
    assert status_lines == []


def test_a_degraded_turn_never_raises_and_still_answers(
    store_with_prior: VectorStore, conv: "main.Conversation", status_lines: list[dict]
) -> None:
    """The M5 backstop: nothing from this subsystem may escape."""
    import httpx

    client = FakeClient(
        [CODE_REPLY, ANSWER_REPLY], embed_raises=httpx.ConnectError("refused")
    )
    main.agentic_turn(client, conv, "some task", store_with_prior)

    assert len(conv.messages) == 5  # full thought -> code -> answer sequence
    assert len(warnings_of(status_lines)) == 1


# ------------------------------------------------------------------------------
# Config block  — T5
# ------------------------------------------------------------------------------


def test_main_exposes_the_six_memory_constants() -> None:
    assert isinstance(main.MEMORY_ENABLED, bool)
    assert main.EMBED_MODEL.endswith(":latest")
    assert isinstance(main.MEMORY_DB, Path)
    assert main.MEMORY_TOP_K == 1
    assert main.MEMORY_MIN_SIM == 0.65
    assert main.MEMORY_MAX_RECORDS == 100_000  # C9, raised from 500 at v1.1.0


def test_the_memory_config_is_shared_not_re_read_per_turn() -> None:
    assert main.MEMORY_CFG.embed_model == main.EMBED_MODEL
    assert main.MEMORY_CFG.top_k == main.MEMORY_TOP_K
    assert main.MEMORY_CFG.chat_model == main.MODEL_NAME
