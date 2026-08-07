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

import io
import re
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("rich", reason="main.py needs rich; run in-container")
pytest.importorskip("ollama", reason="main.py needs ollama; run in-container")
pytest.importorskip("httpx", reason="main.py needs httpx; run in-container")

from rich.cells import cell_len
from rich.console import Console

import main
import memory
from conftest import make_record
from vectorstore import VectorStore


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

    # `input` mirrors ollama's embed() signature; renaming it here would stop
    # this fake standing in for the real client.
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
def conv() -> main.Conversation:
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
    tmp_store: VectorStore, conv: main.Conversation
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
    tmp_store: VectorStore, conv: main.Conversation
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
    tmp_store: VectorStore, conv: main.Conversation
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
    store_with_prior: VectorStore, conv: main.Conversation
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
    store_with_prior: VectorStore, conv: main.Conversation
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
    store_with_prior: VectorStore, conv: main.Conversation
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[1.0, 0.0])
    main.agentic_turn(client, conv, "Tell me the temperature in Busan", store_with_prior)

    assert len(client.chat_calls) == 2
    grounded = client.chat_calls[1]
    assert all("PRIOR SUCCESSFUL SOLUTION" not in m["content"] for m in grounded)


def test_retry_attempts_receive_no_recall_block(
    store_with_prior: VectorStore, conv: main.Conversation
) -> None:
    """Constraint C8: attempt 1 only."""
    failing = "Thought: oops.\n\n```python\nraise SystemExit(3)\n```"
    client = FakeClient([failing, failing], embedding=[1.0, 0.0])

    main.agentic_turn(client, conv, "Tell me the temperature in Busan", store_with_prior)

    assert len(client.chat_calls) == 2
    assert any("PRIOR SUCCESSFUL SOLUTION" in m["content"] for m in client.chat_calls[0])
    assert all("PRIOR SUCCESSFUL SOLUTION" not in m["content"] for m in client.chat_calls[1])


def test_the_executed_code_comes_from_this_turn_not_from_the_store(
    store_with_prior: VectorStore, conv: main.Conversation
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
    store_with_prior: VectorStore, conv: main.Conversation
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
    tmp_store: VectorStore, conv: main.Conversation
) -> None:
    """AC-6: the no-code-block early return stores nothing."""
    client = FakeClient([DIRECT_REPLY])
    main.agentic_turn(client, conv, "Explain list versus tuple", tmp_store)
    assert tmp_store.count() == 0


def test_a_failed_execution_is_not_captured(
    tmp_store: VectorStore, conv: main.Conversation
) -> None:
    failing = "Thought: oops.\n\n```python\nraise SystemExit(3)\n```"
    client = FakeClient([failing, failing])
    main.agentic_turn(client, conv, "do the impossible", tmp_store)
    assert tmp_store.count() == 0


def test_retry_exhaustion_is_not_captured(
    tmp_store: VectorStore, conv: main.Conversation
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
    conv: main.Conversation,
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY])
    main.agentic_turn(client, conv, "compute the answer", None)

    assert len(client.chat_calls) == 2
    assert client.embed_count == 0
    assert len(conv.messages) == 5


def test_a_turn_completes_when_the_embedding_backend_is_down(
    store_with_prior: VectorStore, conv: main.Conversation
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
    conv: main.Conversation, monkeypatch: pytest.MonkeyPatch
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
    store_with_prior: VectorStore, conv: main.Conversation, status_lines: list[dict]
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
    tmp_store: VectorStore, conv: main.Conversation, status_lines: list[dict]
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
    store_with_prior: VectorStore, conv: main.Conversation, status_lines: list[dict]
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
    store_with_prior: VectorStore, conv: main.Conversation, status_lines: list[dict]
) -> None:
    """remember_success() returning False was silent too."""
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[0.0, 1.0])
    store_with_prior.close()  # every write now fails

    main.agentic_turn(client, conv, "some task", store_with_prior)

    warnings = warnings_of(status_lines)
    assert len(warnings) == 1
    assert "continuing without memory" in warnings[0]["message"].lower()


def test_the_healthy_hit_path_warns_about_nothing(
    store_with_prior: VectorStore, conv: main.Conversation, status_lines: list[dict]
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY], embedding=[1.0, 0.0])
    main.agentic_turn(client, conv, "Tell me the temperature in Busan", store_with_prior)

    assert warnings_of(status_lines) == []
    recalled = [line for line in memory_lines(status_lines) if "Recalled" in line["message"]]
    assert len(recalled) == 1
    assert recalled[0]["style"] == "green"


def test_the_healthy_cold_start_path_warns_about_nothing(
    tmp_store: VectorStore, conv: main.Conversation, status_lines: list[dict]
) -> None:
    client = FakeClient([CODE_REPLY, ANSWER_REPLY])
    main.agentic_turn(client, conv, "the first task", tmp_store)

    assert warnings_of(status_lines) == []
    captured = [line for line in memory_lines(status_lines) if "Captured" in line["message"]]
    assert len(captured) == 1
    assert captured[0]["style"] == "green"
    assert tmp_store.count() == 1


def test_the_empty_store_short_circuit_is_not_a_failure(
    tmp_store: VectorStore, conv: main.Conversation, status_lines: list[dict]
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
    conv: main.Conversation,
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
    conv: main.Conversation, status_lines: list[dict]
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
    store_with_prior: VectorStore, conv: main.Conversation, status_lines: list[dict]
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


# ------------------------------------------------------------------------------
# Processing pulse — the icon animates only while a phase is running
# ------------------------------------------------------------------------------


# `icon_style()` used to live here, reading the style of a status line's first
# span. It is deliberately gone: every assertion it served was an assertion that
# a STYLE alternated, which is exactly the thing that turned out to prove
# nothing against a colour emoji. Reintroducing it would make the same class of
# test easy to write again.


# Every production call site passes a colour emoji, so every test here must
# too. The original suite passed "*" — a TEXT glyph, for which bold and dim
# work perfectly — and so asserted a mechanism that was inert in the only
# context that ships. Using a real emoji is what makes these tests mean
# anything; do not "simplify" it back to an ASCII placeholder.
PULSE_ICON = "🔄"


def test_pulsing_line_blinks_the_icon_on_and_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pulse is derived from the clock, so __rich__ alone proves the beat.

    The assertion is on the GLYPH, not on a style. A colour emoji ignores SGR 1
    and SGR 2 entirely, so an assertion that the icon's style alternates
    bold/dim passes while the terminal shows a motionless line — which is
    precisely what happened.
    """
    clock = {"now": 0.0}
    monkeypatch.setattr(main.time, "monotonic", lambda: clock["now"])
    pulse = main._PulsingLine(PULSE_ICON, "LLaMA", "thinking", "cyan")

    clock["now"] = 0.0
    assert PULSE_ICON in pulse.__rich__().plain
    clock["now"] = main.PULSE_HALF_PERIOD_SEC
    assert PULSE_ICON not in pulse.__rich__().plain
    clock["now"] = main.PULSE_HALF_PERIOD_SEC * 2
    assert PULSE_ICON in pulse.__rich__().plain


def test_pulsing_line_never_animates_through_a_style_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The two frames must differ in TEXT, not merely in styling.

    This is the regression guard. Any future implementation that goes back to
    varying an attribute on the icon — bold, dim, colour, blink — will render
    identically on a colour emoji and must fail here rather than ship.
    """
    clock = {"now": 0.0}
    monkeypatch.setattr(main.time, "monotonic", lambda: clock["now"])
    pulse = main._PulsingLine(PULSE_ICON, "LLaMA", "thinking", "cyan")

    clock["now"] = 0.0
    lit = pulse.__rich__()
    clock["now"] = main.PULSE_HALF_PERIOD_SEC
    dark = pulse.__rich__()

    assert lit.plain != dark.plain


def test_pulsing_line_holds_its_width_so_the_text_does_not_shift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A double-width emoji blanked to ONE space would jitter the line leftwards.

    The blank is cell_len(icon) spaces for that reason, and cell_len is what
    the terminal actually measures — `len("🔄")` is 1 while it occupies 2
    columns, so a naive len() would still jitter.
    """
    clock = {"now": 0.0}
    monkeypatch.setattr(main.time, "monotonic", lambda: clock["now"])
    pulse = main._PulsingLine(PULSE_ICON, "LLaMA", "thinking", "cyan")

    clock["now"] = 0.0
    lit = pulse.__rich__()
    clock["now"] = main.PULSE_HALF_PERIOD_SEC
    dark = pulse.__rich__()

    assert cell_len(lit.plain) == cell_len(dark.plain)
    # And the guard is only meaningful because the two differ in code points:
    assert len(lit.plain) != len(dark.plain) or cell_len(PULSE_ICON) == 1


def test_pulsing_line_carries_the_same_text_as_a_settled_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lit frame and the settled line must be identical; wording cannot shift."""
    monkeypatch.setattr(main.time, "monotonic", lambda: 0.0)
    pulsing = main._PulsingLine(PULSE_ICON, "LLaMA", "thinking", "cyan").__rich__()
    settled = main._status_line(PULSE_ICON, "LLaMA", "thinking", "cyan")
    assert pulsing.plain == settled.plain


def test_every_pulsed_icon_in_main_is_wider_than_zero_cells() -> None:
    """Guards the blanking arithmetic against an icon cell_len cannot measure.

    If an icon ever measures 0 columns the dark frame would be a zero-length
    blank and the line would jitter, silently, exactly as before.
    """
    for icon in ("🔄", "🧠", "⚙️", "💬", "📊"):
        assert cell_len(icon) > 0


def test_processing_settles_into_one_permanent_line(status_lines: list[dict]) -> None:
    with main.processing("*", "System", "working", "yellow"):
        pass
    assert status_lines == [
        {"icon": "*", "tag": "System", "message": "working", "style": "yellow"}
    ]


def test_processing_reports_even_when_the_phase_raises(status_lines: list[dict]) -> None:
    """A failed phase still leaves a record of what was attempted."""
    with pytest.raises(RuntimeError), main.processing("*", "System", "working", "yellow"):
        raise RuntimeError("boom")
    assert [line["message"] for line in status_lines] == ["working"]


def test_processing_with_settle_false_leaves_the_wording_to_the_caller(
    status_lines: list[dict],
) -> None:
    with main.processing("*", "Memory", "searching", "green", settle=False):
        pass
    assert status_lines == []


def test_prime_stream_yields_every_token_in_order() -> None:
    assert list(main.prime_stream(iter(["a", "b", "c"]))) == ["a", "b", "c"]


def test_prime_stream_tolerates_an_empty_stream() -> None:
    assert list(main.prime_stream(iter([]))) == []


def test_prime_stream_draws_exactly_one_token_eagerly() -> None:
    """This is what puts the pulse over the model's warm-up rather than after it.

    Ollama yields nothing until the prompt has been evaluated. Pulling one token
    inside the processing block means the animation covers that wait; pulling
    none would leave it running over an already-streaming response, and pulling
    all of them would defeat the streaming panel entirely.
    """
    drawn: list[str] = []

    def source() -> Iterator[str]:
        for token in ("a", "b", "c"):
            drawn.append(token)
            yield token

    primed = main.prime_stream(source())
    assert drawn == ["a"]
    assert list(primed) == ["a", "b", "c"]


# ------------------------------------------------------------------------------
# Streaming render — completed lines are printed once and never repainted
# ------------------------------------------------------------------------------
#
# render_stream() had NO tests before 2026-08-07, which is how it shipped an
# implementation that re-rendered a growing Panel(Markdown(...)) on every token
# at 24 fps. Nothing asserted how much it wrote, so nothing noticed that the
# answer was "the whole document, once per token".


def _captured_console(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    """Point main.console at a buffer that still believes it is a terminal.

    force_terminal matters: without it Rich disables Live entirely and the test
    would pass against an implementation that never animates at all.
    """
    buf = io.StringIO()
    monkeypatch.setattr(main, "console", Console(file=buf, force_terminal=True, width=80))
    return buf


def _chunks(text: str, size: int = 3) -> Iterator[str]:
    """Split into small pieces, the way a real token stream arrives."""
    return iter([text[i : i + size] for i in range(0, len(text), size)])


def test_render_stream_returns_the_stream_verbatim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured_console(monkeypatch)
    reply = "Thought: plan it.\n```python\nprint(1)\n```\n"
    assert main.render_stream("Thought", "cyan", _chunks(reply)) == reply


def test_render_stream_writes_each_completed_line_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The regression guard. This is the flicker, expressed as an assertion.

    A line that is written more than once has been REPAINTED, which is what the
    Panel/Markdown implementation did to every line on every token. Counting
    occurrences in the byte stream is the only way to catch that: the rendered
    result looks correct either way, and only the terminal sees the difference.
    """
    buf = _captured_console(monkeypatch)
    reply = "first line here\nsecond line here\nthird line here\n"
    main.render_stream("Thought", "cyan", _chunks(reply))
    raw = buf.getvalue()

    # Every line but the last-in-flight one must appear exactly once.
    assert raw.count("first line here") == 1
    assert raw.count("second line here") == 1
    assert raw.count("third line here") == 1


def test_render_stream_prints_a_trailing_line_that_never_ended(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Live region is transient, so an unterminated tail is erased on exit.

    Without the explicit reprint the last line of any reply not ending in a
    newline would vanish from the transcript entirely.
    """
    buf = _captured_console(monkeypatch)
    result = main.render_stream("Thought", "cyan", _chunks("done\nno trailing newline"))
    assert result == "done\nno trailing newline"
    assert "no trailing newline" in buf.getvalue()


def test_render_stream_handles_several_newlines_in_one_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ollama chunks on token boundaries, not line boundaries.

    A single chunk can carry two newlines, so the split has to loop rather than
    handle one per token.
    """
    buf = _captured_console(monkeypatch)
    main.render_stream("Thought", "cyan", iter(["alpha\nbeta\ngamma\n"]))
    raw = buf.getvalue()
    for word in ("alpha", "beta", "gamma"):
        assert raw.count(word) == 1


def test_render_stream_tolerates_an_empty_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured_console(monkeypatch)
    assert main.render_stream("Thought", "cyan", iter([])) == ""


# ------------------------------------------------------------------------------
# Prompt — readline must be told which prompt bytes are invisible
# ------------------------------------------------------------------------------


def test_prompt_brackets_every_escape_sequence_for_readline() -> None:
    """The prompt renders identically whether or not this holds. Only history breaks.

    readline counts every unbracketed byte as a visible column, so the colour
    escapes must sit inside \\001...\\002 (RL_PROMPT_START_IGNORE /
    RL_PROMPT_END_IGNORE). Without them readline's idea of the cursor column is
    eleven too far right, every redraw starts from the wrong origin, and
    recalling an entry with Up appends to the current line instead of replacing
    it.

    Asserting on the rendered prompt would catch none of this — it looks correct
    either way. The assertion has to be on what readline *counts*.
    """
    counted = re.sub("\001[^\002]*\002", "", main.PROMPT)

    assert "\033" not in counted, (
        "an escape sequence is outside \\001...\\002, so readline will count it "
        "as visible columns and history navigation will corrupt the line"
    )
    assert counted == "you ➜ "
