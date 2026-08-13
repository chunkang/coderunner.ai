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
import readline
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
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
import params
import settings
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


# Which ESCAPE CODE carries a colour is decided by the environment, and not by
# anything a test can pin after the fact. main._PY_HIGHLIGHTER is a module-level
# Syntax built at IMPORT time, so its theme is baked against whatever colour
# system the console resolved to then: truecolor (\x1b[38;2;R;G;B) on a
# developer machine with COLORTERM set, plain 16-colour (\x1b[91;49m) on a
# GitHub runner with TERM unset. Re-pinning the console afterwards does not
# change it — the Text already holds downgraded colours.
#
# So assertions here match ANY foreground colour: truecolor, 256, bright, or
# standard. The claim under test is "this text is coloured", never "coloured
# this particular way". The first version of this suite asserted \x1b[38;2;
# and failed on its first ever CI run for exactly this reason.
_ANY_FG_COLOUR = re.compile(r"\x1b\[(?:38;[25];|9[0-7]|3[0-7])")
# A dim that has leaked onto coloured text: SGR 2 combined with a colour in one
# sequence, in whatever encoding that colour happens to use.
_DIM_ON_COLOUR = re.compile(r"\x1b\[2;\d")


def _visible(raw: str) -> str:
    """The text a human sees, with every ANSI sequence removed.

    Syntax highlighting puts an escape sequence BETWEEN every pygments token,
    so `import requests` never appears as a contiguous substring of the raw
    stream even though it is exactly what the terminal draws. Assertions about
    content belong here; assertions about styling belong on the raw bytes.
    """
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", raw)


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


# ------------------------------------------------------------------------------
# Streaming render — inline markdown, and the fenced-block placeholder
# ------------------------------------------------------------------------------
#
# The first line-by-line renderer printed lines verbatim, on the stated
# reasoning that "little is lost in practice". The model's own replies
# disproved that within one turn: they open with **CODE protocol** and close
# with **Stop here.**, both of which reached the user as literal asterisks.


def test_render_stream_renders_inline_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Asterisks must not survive to the terminal as text."""
    buf = _captured_console(monkeypatch)
    main.render_stream("T", "cyan", _chunks("**CODE protocol** and *soft* and `x = 1`\n"))
    raw = buf.getvalue()

    assert "**" not in raw
    assert "CODE protocol" in raw
    assert "\x1b[1m" in raw  # bold was actually emitted


def test_render_stream_highlights_code_lines_as_they_arrive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The code must appear WHILE it is written, numbered and highlighted.

    Its predecessor suppressed the block behind a placeholder to remove the
    duplication with show_code(). That removed the duplication and the live
    view with it: writing the script is the longest stretch of a turn, so it
    became the one stretch with nothing on screen.
    """
    buf = _captured_console(monkeypatch)
    reply = "before\n```python\nimport requests\nprint(1)\n```\nafter\n"
    result = main.render_stream("T", "cyan", _chunks(reply), highlight_code=True)
    raw = buf.getvalue()

    seen = _visible(raw)
    assert result == reply  # the RETURN value must stay complete; extraction needs it
    assert "import requests" in seen
    assert _ANY_FG_COLOUR.search(raw)  # pygments colour was actually emitted
    assert "   1 " in seen and "   2 " in seen  # gutter numbering, restarting per block
    assert "```" not in seen  # the fence markers themselves are not shown
    assert "before" in seen and "after" in seen


def test_render_stream_does_not_dim_the_highlighted_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the gutter is dim. Text(..., style=) sets a BASE style that leaks.

    Building the line as Text(f"{n} ", style="dim") applies dim to everything
    appended afterwards, washing out every pygments colour on the line. The
    rendered result still looks like code, just uniformly faded, so nothing but
    an assertion on the emitted attributes catches it.
    """
    buf = _captured_console(monkeypatch)
    main.render_stream("T", "cyan", _chunks("```python\nimport requests\n```\n"),
                       highlight_code=True)
    raw = buf.getvalue()

    assert "\x1b[2m" in raw  # the gutter IS dim
    assert not _DIM_ON_COLOUR.search(raw)  # ...and the code is NOT, in any encoding


def test_render_stream_leaves_code_plain_when_highlighting_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The final Answer streams without highlighting, but must still show code."""
    buf = _captured_console(monkeypatch)
    main.render_stream("Answer", "magenta", _chunks("see:\n```python\nprint(1)\n```\n"))
    seen = _visible(buf.getvalue())
    assert "print(1)" in seen
    assert "   1 " not in seen  # no gutter outside the reasoning stream


def test_render_stream_does_not_mistake_bold_for_italic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`**x**` must not be read as an emphasised `*x*` with stray asterisks."""
    buf = _captured_console(monkeypatch)
    main.render_stream("T", "cyan", _chunks("**bold**\n"))
    raw = buf.getvalue()
    assert "*" not in raw


def test_in_flight_line_renders_exactly_as_it_will_settle() -> None:
    """A line must not change costume when its newline arrives.

    This is the "not natural" complaint, expressed as an assertion. When the
    tail was rendered plain-and-dim while the settled line was numbered and
    highlighted, every line visibly restyled at the instant it completed:
    characters flowed in, then the finished line blinked into a different
    appearance. That reads as lines being posted one at a time rather than as a
    stream.

    Asserting on the RENDERED output is the only way to catch it — both
    versions display the correct text, and they differ only in styling.
    """
    for fence_depth, highlight in ((1, True), (1, False), (0, False)):
        in_flight = main._style_line("import req", fence_depth, 1, highlight)
        settled = main._style_line("import requests", fence_depth, 1, highlight)

        # Same prefix, same spans over it: the tail is the settled line, shorter.
        assert settled.plain.startswith(in_flight.plain)
        assert [(s.start, s.style) for s in in_flight.spans if s.start == 0] == [
            (s.start, s.style) for s in settled.spans if s.start == 0
        ]


def test_a_fence_marker_is_never_shown_even_half_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``` must not flash into view while the opening fence is being typed."""
    buf = _captured_console(monkeypatch)
    main.render_stream("T", "cyan", _chunks("x\n```python\nprint(1)\n```\n"),
                       highlight_code=True)
    assert "```" not in _visible(buf.getvalue())


# ==============================================================================
#  SPEC-INPUT-001 — declared parameters
# ------------------------------------------------------------------------------
#  Covers  : AC-INJ (execution), AC-SYN, AC-CAP, AC-ONCE, AC-MASK, AC-FUTURE.
#            The pure halves are in tests/test_params.py and
#            tests/test_settings.py, which run on a bare interpreter.
#
#  Three of these exist because a plausible implementation is GREEN while doing
#  the wrong thing, and they are the ones to read first:
#
#    * AC-INJ  — the difference between safe and unsafe is one character inside
#                an f-string, and BOTH versions run the script successfully.
#    * AC-CAP  — the tidy refactor that breaks it (`code = prelude + code`)
#                passes every other test in this repository.
#    * AC-ONCE — prompting per attempt passes a single-attempt test and asks the
#                user for their API key three times before the turn gives up.
# ==============================================================================

@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Never read or write the developer's real ~/.coderunner/settings.json.

    Autouse rather than opt-in: `_resolve_param_policy()` reaches for
    settings.SETTINGS_PATH by default, and a test that forgot this would read a
    file whose contents decide whether capture happens — passing or failing
    depending on a machine's history.
    """
    target = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", target)
    monkeypatch.delenv(settings.ENV_OVERRIDE, raising=False)
    return target


def session_with(policy: str) -> settings.PolicySession:
    """A session whose policy is already resolved, so no file is consulted."""
    return settings.PolicySession(policy=settings.Policy(policy, settings.PROV_FILE))


def reply_with(code: str, thought: str = "Thought: I need a value.") -> str:
    return f"{thought}\n\n```python\n{code}\n```"


CITY_CODE = '# @param city: str = "Which city?"\nprint(city)'
SECRET_CODE = '# @param api_key: secret = "API key"\nprint("token " + api_key)'


@pytest.fixture()
def answers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Script the user's replies by parameter name, recording every prompt."""
    scripted: dict[str, str] = {}
    scripted["_asked"] = []  # type: ignore[assignment]

    def ask(declaration: params.Declaration, retry: bool) -> str:
        scripted["_asked"].append(declaration.name)  # type: ignore[attr-defined]
        return scripted.get(declaration.name, "")

    monkeypatch.setattr(main, "_ask_param", ask)
    return scripted


def asked(scripted: dict[str, str]) -> list[str]:
    return scripted["_asked"]  # type: ignore[return-value]


# ------------------------------------------------------------------------------
# AC-INJ — a hostile value arrives as DATA, through the real execution path
# ------------------------------------------------------------------------------

#: Measured 2026-08-06. Naively interpolated, this executes `id` and prints
#: `uid=501(kurapa) gid=20(staff) …`. Through repr() it arrives as a
#: 39-character string. BOTH EXIT 0.
HOSTILE = 'Seoul"; import os; os.system("id"); x="'

#: The same attack needing no quote character at all: naively interpolated it
#: yields four statements where the author wrote one.
HOSTILE_NEWLINES = 'a\nimport os\nos.system("id")\nb = "'

_PROBE = '\nprint(len(city))\nprint(repr(city))'


@pytest.mark.parametrize("value", [HOSTILE, HOSTILE_NEWLINES])
def test_a_hostile_value_round_trips_as_data_through_run_python(value: str) -> None:
    """The assertion is on the ROUND-TRIPPED VALUE, never on the exit status.

    `f'city = "{value}"'` also exits 0, also produces output, and also leaves a
    cleaned-up temp directory. In the REPL it shows a green `Execution OK (rc=0)`
    panel, the model receives its stdout as success feedback and the turn is
    captured as a solved task. The only thing separating the two constructions is
    WHAT THE OUTPUT SAYS.
    """
    declarations = params.parse_declarations(CITY_CODE)
    prelude = params.render_prelude(declarations, {"city": value})

    result = main.run_python("print(city)" + _PROBE, prelude=prelude)

    assert result.ok
    assert f"\n{len(value)}\n" in "\n" + result.stdout
    assert repr(value) in result.stdout
    assert "uid=" not in result.stdout  # `id` did not run
    assert "uid=" not in result.stderr


def test_the_unsafe_construction_really_does_execute_the_value() -> None:
    """AC-INJ observed FAILING, permanently, against the construction it forbids.

    A gate never observed failing is not known to be a gate. This drives the
    exact f-string interpolation `params.render_prelude()` refuses to contain,
    through the same `run_python()`, with the same value acceptance.md measured
    on 2026-08-06 — and watches the injected statement run.

    The discriminator is `uid=`, which appears in the OUTPUT of `id` and nowhere
    in the value itself. That distinction is the point: an assertion on the value
    text would match both halves, since the safe half prints the attack back as
    data. Only what `id` PRINTS separates them.

    Both halves exit 0. That is the whole reason AC-INJ asserts the value.
    """
    probe = "print(city)" + _PROBE

    unsafe = main.run_python(probe, prelude=f'city = "{HOSTILE}"')
    safe = main.run_python(probe, prelude=params.render_prelude(
        params.parse_declarations(CITY_CODE), {"city": HOSTILE}
    ))

    assert unsafe.returncode == 0 and safe.returncode == 0
    assert "uid=" in unsafe.stdout  # the attack lands: `id` ran
    assert "uid=" not in safe.stdout  # and repr() stops it
    assert repr(HOSTILE) in safe.stdout  # intact, not mangled
    assert "39" in safe.stdout  # all 39 characters of it


def test_a_hostile_value_survives_a_whole_turn_as_data(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str]
) -> None:
    answers["city"] = HOSTILE
    client = FakeClient([reply_with(CITY_CODE + _PROBE), ANSWER_REPLY])

    main.agentic_turn(client, conv, "weather please", tmp_store, session_with(
        settings.POLICY_ALWAYS
    ))

    stdout = "".join(
        message["content"] for message in conv.messages if message["role"] == "user"
    )
    assert repr(HOSTILE) in stdout
    assert "uid=" not in stdout


# ------------------------------------------------------------------------------
# AC-SYN — the declaration syntax cannot disarm code extraction
# ------------------------------------------------------------------------------


def test_a_declaration_inside_the_fence_leaves_the_block_intact() -> None:
    extracted = main.extract_last_python_block(reply_with(CITY_CODE))
    assert extracted == CITY_CODE
    assert extracted  # non-empty, so main.py:826 does not short-circuit


def test_a_separate_params_fence_would_silently_disarm_the_turn() -> None:
    """The measurement that disqualified the alternative (N5), asserted so the
    reason survives as a fact rather than as a paragraph.

    The regex's optional `(?:python|py)?` does not match `params`, so the OPENING
    fence of a params block is not a match — but its CLOSING fence pairs with the
    opening fence of the following python block, and `(.*?)` captures the empty
    string between them. `extract_last_python_block()` takes `matches[-1]`, which
    is that empty string, and the empty string is FALSY at main.py:826.

    The consequence is the worst available: the script is never executed and
    nothing reports an error. Reverse the two blocks and it works — which is why
    the form is forbidden outright rather than an order being mandated.
    """
    response = (
        "Here you go.\n\n```params\ncity: str\n```\n\n```python\nprint(city)\n```\n"
    )
    assert main.CODE_BLOCK_RE.findall(response) == [""]
    assert main.extract_last_python_block(response) == ""
    assert not main.extract_last_python_block(response)  # the falsy branch


def test_a_direct_answer_turn_asks_for_nothing(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    isolated_settings: Path,
) -> None:
    """A session that never declares a parameter never asks and never creates
    the file. That is the whole of what makes the settings.json reversal cheap."""
    main.agentic_turn(FakeClient([DIRECT_REPLY]), conv, "explain lists", tmp_store)

    assert asked(answers) == []
    assert not isolated_settings.exists()


# ------------------------------------------------------------------------------
# AC-FUTURE — a `from __future__` import survives the prelude
# ------------------------------------------------------------------------------


def test_a_future_import_in_generated_code_still_runs_with_a_prelude() -> None:
    code = "from __future__ import annotations\nprint(city)"
    result = main.run_python(code, prelude="city = 'Seoul'")

    assert result.ok, result.stderr
    assert result.stdout.strip() == "Seoul"


def test_without_the_guard_the_same_script_is_a_syntax_error() -> None:
    """The measured failure the guard exists for, driven end to end.

    Impact is total: the script does not run at all and the model is handed a
    SyntaxError for code it wrote correctly, then burns its remaining attempts
    at main.py:792 "fixing" it.
    """
    result = main.run_python(
        "city = 'Seoul'\nfrom __future__ import annotations\nprint(city)"
    )
    assert not result.ok
    assert "__future__" in result.stderr


# ------------------------------------------------------------------------------
# AC-CAP — the injected value is absent from the store BY CONSTRUCTION
# ------------------------------------------------------------------------------


def test_capture_receives_the_very_object_extraction_returned(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Asserted by IDENTITY, not by comparing strings.

    The refactor that destroys this is one line — `code = prelude + code` — and
    it is the TIDY version: it reads better, it removes an argument from
    `run_python()`, and a reviewer would plausibly suggest it. Every other test
    in this suite still passes under it: the script runs, the output is right,
    the answer streams, the turn is captured. The only visible difference is that
    coderunner_app_data now holds the user's API key in plaintext, in a store
    tech.md 7.2 states any later generated script can read.

    A string comparison would pass under that refactor whenever the prelude
    happened to be empty — which is every test that does not declare a
    parameter, i.e. almost all of them. IDENTITY IS THE ASSERTION THAT CANNOT BE
    SATISFIED BY ACCIDENT.
    """
    extracted: list[str] = []
    real_extract = main.extract_last_python_block

    def recording_extract(text: str):
        block = real_extract(text)
        extracted.append(block)
        return block

    captured: list[str] = []
    real_capture = main._capture_turn

    def recording_capture(client, store, task, thought, code, stdout, recall, warned):
        captured.append(code)
        return real_capture(client, store, task, thought, code, stdout, recall, warned)

    monkeypatch.setattr(main, "extract_last_python_block", recording_extract)
    monkeypatch.setattr(main, "_capture_turn", recording_capture)

    answers["api_key"] = "sk-live-DEADBEEF"
    client = FakeClient([reply_with(SECRET_CODE), ANSWER_REPLY])
    main.agentic_turn(client, conv, "call the API", tmp_store, session_with(
        settings.POLICY_ALWAYS
    ))

    assert len(captured) == 1
    assert captured[0] is extracted[-1], (
        "the prelude was merged into `code` before capture; the user's value is "
        "now persisted in plaintext"
    )


def test_a_secret_reaches_none_of_remember_successs_arguments(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Not task, not thought, not code, not stdout."""
    recorded: list[tuple] = []
    real = main.remember_success

    def recording(store, task, thought, code, stdout, vector, cfg):
        recorded.append((task, thought, code, stdout))
        return real(store, task, thought, code, stdout, vector, cfg)

    monkeypatch.setattr(main, "remember_success", recording)

    secret = "sk-live-DEADBEEF"
    answers["api_key"] = secret
    client = FakeClient([reply_with(SECRET_CODE), ANSWER_REPLY])
    main.agentic_turn(client, conv, "call the API", tmp_store, session_with(
        settings.POLICY_SENSITIVE
    ))

    assert len(recorded) == 1
    assert secret not in "\n".join(recorded[0])


def test_under_sensitive_excluded_the_secret_is_redacted_at_all_three_sinks(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E6 names three sinks and this asserts each separately: the screen, the
    model's conversation, and the persistent store.

    A script that echoes a secret is not contrived — an HTTP error carrying the
    full URL with the key in its query string does it without the model trying.
    """
    buf = _captured_console(monkeypatch)
    secret = "sk-live-DEADBEEF"
    answers["api_key"] = secret
    client = FakeClient([reply_with(SECRET_CODE), ANSWER_REPLY])

    main.agentic_turn(client, conv, "call the API", tmp_store, session_with(
        settings.POLICY_SENSITIVE
    ))

    screen = _visible(buf.getvalue())
    conversation = "\n".join(message["content"] for message in conv.messages)
    (stored,) = tmp_store.recent(1)

    assert secret not in screen
    assert secret not in conversation
    assert secret not in stored.stdout
    # ...and the surrounding output still arrived, so this is redaction rather
    # than suppression.
    assert params.REDACTION_MARKER in stored.stdout
    assert "token" in stored.stdout


def test_under_never_the_turn_is_not_captured_and_one_line_says_so(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    status_lines: list[dict],
) -> None:
    """S1. Silence here is indistinguishable from a successful capture."""
    answers["city"] = "Seoul"
    client = FakeClient([reply_with(CITY_CODE), ANSWER_REPLY])

    main.agentic_turn(client, conv, "weather please", tmp_store, session_with(
        settings.POLICY_NEVER
    ))

    assert tmp_store.count() == 0
    said = [line for line in status_lines if main.PARAMS_NOT_STORED_MSG in line["message"]]
    assert len(said) == 1


def test_under_always_nothing_is_redacted_and_the_turn_is_captured_in_full(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
) -> None:
    """Asserted so the policy is known to be DOING something rather than being a
    no-op that happens to look safe."""
    secret = "sk-live-DEADBEEF"
    answers["api_key"] = secret
    client = FakeClient([reply_with(SECRET_CODE), ANSWER_REPLY])

    main.agentic_turn(client, conv, "call the API", tmp_store, session_with(
        settings.POLICY_ALWAYS
    ))

    assert tmp_store.count() == 1
    (stored,) = tmp_store.recent(1)
    assert secret in stored.stdout


def test_a_non_parameterised_turn_is_captured_under_every_policy(
    tmp_store: VectorStore, conv: main.Conversation,
) -> None:
    """`never` applies to turns that USED parameters, not to the whole store."""
    client = FakeClient([CODE_REPLY, ANSWER_REPLY])
    main.agentic_turn(client, conv, "compute the answer", tmp_store, session_with(
        settings.POLICY_NEVER
    ))
    assert tmp_store.count() == 1


# ------------------------------------------------------------------------------
# AC-ONCE — collected once per turn, and before the Live region opens
# ------------------------------------------------------------------------------

FAILING_CITY = '# @param city: str = "Which city?"\nprint(city)\nraise SystemExit(3)'


def test_the_user_is_prompted_exactly_once_across_a_failing_retry(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
) -> None:
    """E4. The obvious implementation — parse and prompt at the top of each loop
    iteration — is simpler, passes a single-attempt test, and asks the user for
    their API key three times before the turn gives up."""
    answers["city"] = "Seoul"
    failing = reply_with(FAILING_CITY)
    client = FakeClient([failing, failing])

    main.agentic_turn(client, conv, "weather please", tmp_store, session_with(
        settings.POLICY_ALWAYS
    ))

    assert len(client.chat_calls) == main.MAX_RETRIES  # the loop really ran twice
    assert asked(answers) == ["city"]


def test_attempt_two_carries_the_same_value_as_attempt_one(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preludes: list[str] = []
    real_run = main.run_python

    def recording(code: str, timeout: int = main.EXEC_TIMEOUT_SEC, prelude: str = ""):
        preludes.append(prelude)
        return real_run(code, timeout, prelude)

    monkeypatch.setattr(main, "run_python", recording)
    answers["city"] = "Seoul"
    failing = reply_with(FAILING_CITY)

    main.agentic_turn(
        FakeClient([failing, failing]), conv, "weather please", tmp_store,
        session_with(settings.POLICY_ALWAYS),
    )

    assert len(preludes) == 2
    assert preludes[0] == preludes[1] == "city = 'Seoul'"


def test_a_name_first_declared_on_attempt_two_prompts_only_for_itself(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
) -> None:
    answers["city"] = "Seoul"
    answers["days"] = "3"
    first = reply_with(FAILING_CITY)
    second = reply_with(
        '# @param city: str = "Which city?"\n'
        '# @param days: int = "How many days?"\n'
        "print(city, days)"
    )

    main.agentic_turn(
        FakeClient([first, second, ANSWER_REPLY]), conv, "forecast", tmp_store,
        session_with(settings.POLICY_ALWAYS),
    )

    assert asked(answers) == ["city", "days"]


def test_collection_completes_before_the_live_region_opens(
    tmp_store: VectorStore, conv: main.Conversation, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S5, asserted on ORDER rather than on count.

    `processing()` opens a transient Rich `Live` region (main.py:562-596) and an
    `input()` inside one contends with the renderer for the terminal. There is
    exactly one point in the turn that satisfies this — between main.py:828 and
    main.py:830 — and asserting the count alone would not catch a
    correct-but-misplaced prompt.
    """
    events: list[str] = []
    real_processing = main.processing

    @contextmanager
    def recording(icon, tag, message, style="cyan", *, settle=True):
        events.append(f"processing:{message}")
        with real_processing(icon, tag, message, style, settle=settle):
            yield

    def ask(declaration: params.Declaration, retry: bool) -> str:
        events.append(f"ask:{declaration.name}")
        return "Seoul"

    monkeypatch.setattr(main, "processing", recording)
    monkeypatch.setattr(main, "_ask_param", ask)

    main.agentic_turn(
        FakeClient([reply_with(CITY_CODE), ANSWER_REPLY]), conv, "weather", tmp_store,
        session_with(settings.POLICY_ALWAYS),
    )

    running = next(i for i, e in enumerate(events) if e.startswith("processing:Running"))
    assert events.index("ask:city") < running


# ------------------------------------------------------------------------------
# AC-MASK — a secret is never echoed, printed, or persisted to history
# ------------------------------------------------------------------------------


def test_a_secret_is_read_through_getpass_and_never_through_input(
    tmp_store: VectorStore, conv: main.Conversation, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N3, asserted on the READLINE HISTORY BUFFER rather than on the function
    call, because the function call is the implementation and the buffer is the
    property.

    `_install_history()` (main.py:930-957) wires readline and registers an
    `atexit` writer, so any line read through `input()` while readline is loaded
    enters the history buffer and is written to CODERUNNER_HISTORY — pinned by
    compose to /home/runner/.coderunner/history on the volume that survives
    `--rm`. A secret typed at an `input()` prompt would therefore be persisted in
    plaintext by a mechanism NO capture policy in this SPEC inspects: every
    policy, INCLUDING `never`, would report that nothing was stored and would be
    telling the truth about the only store it knows about.

    `input()` is stubbed to do what readline does on a real TTY — append the line
    to the history buffer — so the assertion is a live reproduction rather than a
    vacuous one under pytest's non-tty stdin.
    """
    secret = "sk-live-DEADBEEF"
    plain = "Seoul"

    def fake_input(prompt: str = "") -> str:
        readline.add_history(plain)  # what readline itself does on a TTY
        return plain

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(main.getpass, "getpass", lambda prompt="": secret)

    before = readline.get_current_history_length()
    code = (
        '# @param city: str = "Which city?"\n'
        '# @param api_key: secret = "API key"\n'
        'print(city + " " + api_key)'
    )
    main.agentic_turn(
        FakeClient([reply_with(code), ANSWER_REPLY]), conv, "call it", tmp_store,
        session_with(settings.POLICY_ALWAYS),
    )
    after = [
        readline.get_history_item(i)
        for i in range(before + 1, readline.get_current_history_length() + 1)
    ]

    assert plain in after, "the stubbed input() did not reach readline; test is vacuous"
    assert secret not in after


def test_the_prelude_is_never_printed_streamed_or_panelled(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N2, and the reason it is a rule with no exceptions.

    The moment display depends on a per-value flag, the display path acquires a
    branch that a later reclassification can get wrong — and a masked value
    printed in a prelude defeats the masking completely and irreversibly: it is
    on the user's scrollback and, in a recorded session, in the recording.

    Asserted on a secret, because a non-secret value is legitimately echoed in
    the per-parameter confirmation line (O2) and so cannot distinguish the two.
    """
    buf = _captured_console(monkeypatch)
    secret = "sk-live-DEADBEEF"
    answers["api_key"] = secret

    main.agentic_turn(
        FakeClient([reply_with('# @param api_key: secret = "API key"\nprint("ok")'),
                    ANSWER_REPLY]),
        conv, "call it", tmp_store, session_with(settings.POLICY_ALWAYS),
    )

    screen = _visible(buf.getvalue())
    assert secret not in screen
    assert f"api_key = {params.SECRET_MASK}" in screen  # the mask, not the value


def test_the_two_prompt_paths_are_wired_to_different_readers() -> None:
    """The asymmetry is what invites a "unify these" cleanup. Do not."""
    plain = main.params.plain_prompt(params.Declaration("city", "str", "Which city?"))
    secret = main.params.secret_prompt(params.Declaration("k", "secret", "API key"))

    assert "\001" in plain and "\002" in plain
    assert "\001" not in secret and "\002" not in secret


# ------------------------------------------------------------------------------
# The lazy first-run question
# ------------------------------------------------------------------------------


def test_a_non_interactive_session_falls_back_to_never_and_writes_nothing(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    status_lines: list[dict], isolated_settings: Path,
) -> None:
    """Under pytest stdin is not a TTY, so `_resolve_param_policy()` passes
    `ask=None` and the question cannot be asked. One line says so, nothing is
    written, and the turn otherwise proceeds normally."""
    answers["city"] = "Seoul"

    main.agentic_turn(
        FakeClient([reply_with(CITY_CODE), ANSWER_REPLY]), conv, "weather", tmp_store
    )

    assert not isolated_settings.exists()
    assert tmp_store.count() == 0  # `never`
    params_lines = [line for line in status_lines if line["tag"] == "Params"]
    assert [line for line in params_lines if line["style"] == "yellow"]


# ------------------------------------------------------------------------------
# /params dispatch in the REPL
# ------------------------------------------------------------------------------
# main.py is not under a coverage gate and its share of this SPEC is wiring, so
# these two exist for the one failure wiring can still have: a command that never
# reaches its handler, or one that reaches the model instead. Both are invisible
# to every test above, and both are shipped bugs.


def _headless_repl(
    monkeypatch: pytest.MonkeyPatch, typed: list[str]
) -> tuple[io.StringIO, list[str]]:
    """Run repl() over a scripted transcript with no Ollama and no store."""
    buf = _captured_console(monkeypatch)
    reached_model: list[str] = []
    lines = iter([*typed, "/exit"])

    monkeypatch.setattr(main, "show_banner", lambda: None)
    monkeypatch.setattr(main, "_install_history", lambda: None)
    monkeypatch.setattr(main, "build_client", lambda: FakeClient([]))
    monkeypatch.setattr(main, "preflight", lambda client: True)
    monkeypatch.setattr(main, "_open_memory_store", lambda: None)
    monkeypatch.setattr(main, "_prompt_user", lambda: next(lines))
    monkeypatch.setattr(
        main, "agentic_turn", lambda *a, **k: reached_model.append(a[2])
    )

    main.repl()
    return buf, reached_model


def test_params_is_handled_locally_and_never_reaches_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buf, reached_model = _headless_repl(monkeypatch, ["/params"])

    assert reached_model == []
    assert "Parameter capture policy" in _visible(buf.getvalue())


def test_params_capture_sets_the_policy_for_the_rest_of_the_session(
    monkeypatch: pytest.MonkeyPatch, isolated_settings: Path
) -> None:
    """The replacement policy has to be installed on the session, or the choice
    is written to disk and then ignored until the next launch."""
    buf, reached_model = _headless_repl(monkeypatch, ["/params capture 2", "/params"])
    screen = _visible(buf.getvalue())

    assert reached_model == []
    assert isolated_settings.exists()
    assert settings.POLICY_NEVER in screen
    assert settings.PROVENANCE_LABELS[settings.PROV_FILE] in screen


# ==============================================================================
#  SPEC-KEYCHAIN-001 — host-keychain secrets for declared parameters
# ------------------------------------------------------------------------------
#  Covers  : AC-SOURCE (the value takes the same path as a typed one) and
#            AC-POLICY (the capture policy is resolved even when nothing is
#            prompted). The pure half is in tests/test_keychain.py; the launcher
#            half is source-asserted in tests/test_source_seam.py, because the
#            launcher has no harness of any kind.
#
#  AC-POLICY is the AC-CAP-shaped criterion of this SPEC. Before it, there was no
#  such thing as a turn that DECLARES a parameter and SUPPLIES it without asking
#  — the combination did not exist, so nothing tested it. The wrong
#  implementation is one line different from the right one and every other test
#  in this repository passes under it.
# ==============================================================================


@pytest.fixture()
def keychain_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Stand in for what the launcher exported and `keychain.load()` popped.

    Patched on `main.SECRETS` rather than on `os.environ`, because the real thing
    is read ONCE at import (E3) and re-reading it here would test a mechanism the
    product does not have.
    """
    loaded: dict[str, str] = {}
    monkeypatch.setattr(main, "SECRETS", loaded)
    return loaded


def spy_on_ensure_policy(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Record every call to `settings.ensure_policy()`, then do the real thing."""
    calls: list[tuple] = []
    real = settings.ensure_policy

    def recording(session, ask, emit, warn, **kwargs):
        calls.append((session, ask))
        return real(session, ask, emit, warn, **kwargs)

    monkeypatch.setattr(settings, "ensure_policy", recording)
    return calls


SOURCED_SECRET = "sk-live-FROM-THE-KEYCHAIN"

#: AC-TRANSPORT's fixture, and it is SPECIFIED rather than chosen. A `$`-free
#: value round-trips identically under `--env-from-file` too, which was measured
#: on 2026-08-07 to expand `$bc` away and deliver a credential three characters
#: shorter than the one the user stored — with no error, no warning and rc 0.
#: The `$` is the entire discriminating power of the criterion.
TRANSPORT_VALUE = 'sk-a$bc de#f "g" \\h'

ECHO_SECRET_CODE = (
    '# @param api_key: secret = "API key"\n'
    'print("using " + api_key)'
)


# ------------------------------------------------------------------------------
# AC-POLICY — the policy is resolved on a turn where NOTHING was prompted
# ------------------------------------------------------------------------------


def test_the_capture_policy_is_resolved_even_when_nothing_is_prompted(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-POLICY, asserted ON THE CALL and not on its effect.

    The wrong implementation resolves the policy inside the block that prompts
    rather than the block that has pending declarations. Then, for a turn whose
    values all came from the keychain:

        _resolve_param_policy() not called
          -> param_session.policy is None
          -> main.py:981   policy == ""
          -> main.py:988   policy == POLICY_SENSITIVE  -> False -> no redaction
          -> main.py:1026  policy == POLICY_NEVER      -> False -> capture proceeds
          -> _capture_turn() persists stdout containing the secret, in plaintext,
             to coderunner_app_data, which tech.md 7.2 states any later generated
             script can read.

    Nothing in that chain raises, warns or prints. The script runs, the panel is
    green, the answer streams, the turn is captured as solved.

    An assertion on the redacted output would pass whenever the fixture's script
    happens not to print the secret — which is what a fixture written to test
    "the value arrives correctly" naturally does. The call is the property; the
    redaction is one of its consequences.
    """
    calls = spy_on_ensure_policy(monkeypatch)
    keychain_env["API_KEY"] = SOURCED_SECRET
    session = session_with(settings.POLICY_SENSITIVE)

    main.agentic_turn(
        FakeClient([reply_with(ECHO_SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session,
    )

    assert asked(answers) == [], "the fixture is vacuous: something was prompted"
    assert len(calls) == 1, "settings.ensure_policy() was never called on a zero-prompt turn"
    assert session.policy is not None


def test_a_keychain_sourced_secret_is_redacted_at_every_sink(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The consequence of the call, asserted separately from the call itself.

    Both are asserted because only one of them can be satisfied by a well-behaved
    fixture, and this is the one that can.
    """
    buf = _captured_console(monkeypatch)
    keychain_env["API_KEY"] = SOURCED_SECRET

    main.agentic_turn(
        FakeClient([reply_with(ECHO_SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session_with(settings.POLICY_SENSITIVE),
    )

    screen = _visible(buf.getvalue())
    conversation = "\n".join(message["content"] for message in conv.messages)
    (stored,) = tmp_store.recent(1)

    assert SOURCED_SECRET not in screen
    assert SOURCED_SECRET not in conversation
    assert SOURCED_SECRET not in stored.stdout
    # ...and the rest of the output still arrived, so this is redaction rather
    # than a turn that quietly failed.
    assert params.REDACTION_MARKER in stored.stdout
    assert "using" in stored.stdout


def test_a_keychain_sourced_secret_reaches_none_of_remember_successs_arguments(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[tuple] = []
    real = main.remember_success

    def recording(store, task, thought, code, stdout, vector, cfg):
        recorded.append((task, thought, code, stdout))
        return real(store, task, thought, code, stdout, vector, cfg)

    monkeypatch.setattr(main, "remember_success", recording)
    keychain_env["API_KEY"] = SOURCED_SECRET

    main.agentic_turn(
        FakeClient([reply_with(ECHO_SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session_with(settings.POLICY_SENSITIVE),
    )

    assert len(recorded) == 1
    assert SOURCED_SECRET not in "\n".join(recorded[0])


def test_under_never_a_zero_prompt_turn_is_not_captured_and_one_line_says_so(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str], status_lines: list[dict],
) -> None:
    """The `never` half of AC-POLICY. Silence here is indistinguishable from a
    successful capture, which is why the line is part of the criterion."""
    keychain_env["API_KEY"] = SOURCED_SECRET

    main.agentic_turn(
        FakeClient([reply_with(ECHO_SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session_with(settings.POLICY_NEVER),
    )

    assert asked(answers) == []
    assert tmp_store.count() == 0
    said = [line for line in status_lines if main.PARAMS_NOT_STORED_MSG in line["message"]]
    assert len(said) == 1


def test_the_first_run_question_fires_on_a_turn_the_user_typed_nothing_into(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str], status_lines: list[dict],
    isolated_settings: Path,
) -> None:
    """R8, asserted rather than avoided.

    A user whose values all came from the keychain, on a machine with no
    settings.json, is asked how solution memory should treat parameterised turns
    — in the middle of a turn they thought was ordinary. That is CORRECT: the
    policy governs capture, not prompting. It is asserted so that nobody "fixes"
    the surprise by making resolution conditional again, which is exactly the
    change AC-POLICY exists to catch.

    Under pytest stdin is not a TTY, so `_resolve_param_policy()` passes
    `ask=None`, the question cannot be asked, and the fallback is `never` with
    one line. The observable half of "the question fired" is therefore that line
    plus the non-capture.
    """
    keychain_env["API_KEY"] = SOURCED_SECRET

    main.agentic_turn(
        FakeClient([reply_with(ECHO_SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store,
    )

    assert asked(answers) == []
    assert not isolated_settings.exists()
    assert tmp_store.count() == 0  # resolved, and resolved to `never`
    yellow = [
        line for line in status_lines
        if line["tag"] == "Params" and line["style"] == "yellow"
    ]
    assert yellow, "the policy was never resolved on a turn that prompted nothing"


# ------------------------------------------------------------------------------
# AC-SOURCE — a keychain value takes the same path as a typed one
# ------------------------------------------------------------------------------


def test_ask_is_never_invoked_for_a_keychain_sourced_name(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str],
) -> None:
    """Asserted by spying on the callable handed to `params.collect_values()`,
    not by observing an absence of output.

    The mechanism is that `values` is filled BEFORE collection, so the existing
    skip at params.py:201-203 does the work: `ask` is not suppressed, it is
    simply never reached. The absence of a call is easier to verify than the
    presence of a guard.
    """
    keychain_env["API_KEY"] = SOURCED_SECRET

    main.agentic_turn(
        FakeClient([reply_with(SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session_with(settings.POLICY_ALWAYS),
    )

    assert asked(answers) == []


def test_the_value_reaches_the_script_through_the_prelude_and_not_os_environ(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U1 and N2 together: the same single emission site a typed value uses.

    Under the env-direct design SPEC-INPUT-001 3.7 rejected — generated code
    reading `os.environ` itself — `values` stays empty, `params.secret_values()`
    returns nothing, and `sensitive_excluded` silently governs NOTHING. Asserting
    the prelude is asserting that the whole of SPEC-INPUT-001 still applies.
    """
    preludes: list[str] = []
    real_run = main.run_python

    def recording(code: str, timeout: int = main.EXEC_TIMEOUT_SEC, prelude: str = ""):
        preludes.append(prelude)
        return real_run(code, timeout, prelude)

    monkeypatch.setattr(main, "run_python", recording)
    keychain_env["API_KEY"] = SOURCED_SECRET

    main.agentic_turn(
        FakeClient([reply_with(SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session_with(settings.POLICY_ALWAYS),
    )

    assert preludes == [f"api_key = {SOURCED_SECRET!r}"]


def test_the_dollar_bearing_value_round_trips_into_the_script_intact(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str],
) -> None:
    """AC-TRANSPORT's container-side half, driven through the REAL executor.

    Asserted on the ROUND-TRIPPED VALUE — its `repr` and its length — and never
    on the exit status, because the transport this SPEC forbids also exits 0. A
    corrupted credential surfaces as a 401 from a remote service, at which point
    the self-correction loop hands the model a stderr dump and it rewrites a
    script that was already correct.

    The launcher-side half — that `--env-from-file` and `-e NAME=value` appear
    nowhere — is asserted at source level in tests/test_source_seam.py, because
    only the launcher can get that wrong and the launcher has no harness.
    """
    keychain_env["API_KEY"] = TRANSPORT_VALUE
    probe = (
        '# @param api_key: secret = "API key"\n'
        "print(len(api_key))\n"
        "print(repr(api_key))"
    )

    main.agentic_turn(
        FakeClient([reply_with(probe), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session_with(settings.POLICY_ALWAYS),
    )

    (stored,) = tmp_store.recent(1)
    assert repr(TRANSPORT_VALUE) in stored.stdout
    assert f"\n{len(TRANSPORT_VALUE)}\n" in "\n" + stored.stdout
    assert len(TRANSPORT_VALUE) == 19


def test_capture_still_receives_the_very_object_extraction_returned(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-CAP re-asserted under a keychain fixture, and the repetition is the point.

    SPEC-INPUT-001 built this property; this SPEC INHERITS it. A keychain-sourced
    secret is a secret the user never typed and may never think about again, so
    it is the value most likely to be forgotten in a refactor — and the property
    protecting it is one this SPEC did not build. Re-asserting it costs one test
    and makes the inheritance explicit rather than assumed.

    Identity, not string equality: a string comparison passes under
    `code = prelude + code` whenever the prelude happens to be empty, which is
    almost every test in this file.
    """
    extracted: list[str] = []
    real_extract = main.extract_last_python_block

    def recording_extract(text: str):
        block = real_extract(text)
        extracted.append(block)
        return block

    captured: list[str] = []
    real_capture = main._capture_turn

    def recording_capture(client, store, task, thought, code, stdout, recall, warned):
        captured.append(code)
        return real_capture(client, store, task, thought, code, stdout, recall, warned)

    monkeypatch.setattr(main, "extract_last_python_block", recording_extract)
    monkeypatch.setattr(main, "_capture_turn", recording_capture)
    keychain_env["API_KEY"] = SOURCED_SECRET

    main.agentic_turn(
        FakeClient([reply_with(SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session_with(settings.POLICY_ALWAYS),
    )

    assert len(captured) == 1
    assert captured[0] is extracted[-1]


def test_a_sourced_declaration_is_returned_so_redaction_can_see_it(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str],
) -> None:
    """`_collect_params()` returns `pending`, not `asked`.

    main.py:974 accumulates the return value into `param_declared` and
    main.py:987 feeds that to `params.secret_values()` to build the redaction
    set. A keychain-sourced declaration dropped from the return value is a secret
    redaction never sees — and the turn looks identical either way unless the
    script prints it, which this one does.
    """
    keychain_env["API_KEY"] = SOURCED_SECRET
    session = session_with(settings.POLICY_SENSITIVE)
    declarations = params.parse_declarations(ECHO_SECRET_CODE)
    values: dict[str, object] = {}

    returned = main._collect_params(declarations, values, session)

    assert [decl.name for decl in returned] == ["api_key"]
    assert params.secret_values(returned, values) == [SOURCED_SECRET]


def test_a_masked_confirmation_line_is_still_emitted_for_a_sourced_secret(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str], status_lines: list[dict],
) -> None:
    """E5. A sourced secret must be as visible in the transcript as a typed one,
    and exactly one line says where it came from."""
    keychain_env["API_KEY"] = SOURCED_SECRET

    main.agentic_turn(
        FakeClient([reply_with(SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session_with(settings.POLICY_ALWAYS),
    )

    messages = [line["message"] for line in status_lines if line["tag"] == "Params"]
    sourced = [line for line in messages if main.PARAM_SOURCED_MSG.format(name="api_key") == line]
    assert len(sourced) == 1
    assert f"api_key = {params.SECRET_MASK}" in messages
    assert SOURCED_SECRET not in "\n".join(messages)


def test_a_non_secret_declaration_is_prompted_even_with_a_matching_variable(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str],
) -> None:
    """S3, driven end to end. One predicate governs all five behaviours."""
    keychain_env["CITY"] = "Busan"
    answers["city"] = "Seoul"

    main.agentic_turn(
        FakeClient([reply_with(CITY_CODE), ANSWER_REPLY]),
        conv, "weather", tmp_store, session_with(settings.POLICY_ALWAYS),
    )

    assert asked(answers) == ["city"]
    (stored,) = tmp_store.recent(1)
    assert "Seoul" in stored.stdout
    assert "Busan" not in stored.stdout


def test_a_value_typed_on_attempt_one_is_not_replaced_on_attempt_two(
    tmp_store: VectorStore, conv: main.Conversation, keychain_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S2, driven through the real retry loop rather than through prefill alone.

    The keychain variable is absent on attempt 1 and present from attempt 2 —
    which cannot happen in the product, and is precisely why it is the right
    fixture: it makes the cache the ONLY thing that can produce the right answer.
    """
    preludes: list[str] = []
    real_run = main.run_python

    def recording(code: str, timeout: int = main.EXEC_TIMEOUT_SEC, prelude: str = ""):
        preludes.append(prelude)
        keychain_env["API_KEY"] = SOURCED_SECRET  # arrives too late, by construction
        return real_run(code, timeout, prelude)

    monkeypatch.setattr(main, "run_python", recording)
    monkeypatch.setattr(main, "_ask_param", lambda decl, retry: "typed-by-hand")

    failing = reply_with(
        '# @param api_key: secret = "API key"\nprint(api_key)\nraise SystemExit(3)'
    )
    main.agentic_turn(
        FakeClient([failing, failing]), conv, "call the API", tmp_store,
        session_with(settings.POLICY_ALWAYS),
    )

    assert len(preludes) == 2
    assert preludes[0] == preludes[1] == "api_key = 'typed-by-hand'"


def test_an_empty_keychain_value_is_prompted_for_instead(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str],
) -> None:
    """U3, on the container side. An empty secret is not a secret."""
    keychain_env["API_KEY"] = ""
    answers["api_key"] = "typed-instead"

    main.agentic_turn(
        FakeClient([reply_with(SECRET_CODE), ANSWER_REPLY]),
        conv, "call the API", tmp_store, session_with(settings.POLICY_ALWAYS),
    )

    assert asked(answers) == ["api_key"]


def test_a_turn_declaring_nothing_is_still_byte_for_byte_the_pre_feature_turn(
    tmp_store: VectorStore, conv: main.Conversation, answers: dict[str, str],
    keychain_env: dict[str, str], status_lines: list[dict],
    isolated_settings: Path,
) -> None:
    """The `if not pending: return pending` guard is unchanged and must stay so.

    A registered secret plus a turn that declares nothing must not resolve a
    policy, must not create settings.json, and must not print a Params line.
    """
    keychain_env["API_KEY"] = SOURCED_SECRET

    main.agentic_turn(FakeClient([CODE_REPLY, ANSWER_REPLY]), conv, "compute", tmp_store)

    assert [line for line in status_lines if line["tag"] == "Params"] == []
    assert not isolated_settings.exists()
    assert tmp_store.count() == 1


def test_the_system_prompt_never_learns_that_a_keychain_exists() -> None:
    """N2, asserted on the prompt text in the family of
    tests/test_source_seam.py:297-311.

    The model declares `# @param` and uses a bare name, and that is all it knows.
    It is never told to read `os.environ`, never told a variable might be set,
    and never told a keychain exists — because the moment it is, it starts
    writing `os.environ["..."]` instead of a bare name and every property
    SPEC-INPUT-001 established stops applying (spec.md 4.4).
    """
    source = (Path(main.__file__).read_text(encoding="utf-8"))
    prompt = source[source.index("SYSTEM_PROMPT = ") : source.index("# Data model")]

    for forbidden in ("os.environ", "environ", "keychain", "CODERUNNER_SECRET"):
        assert forbidden not in prompt, f"SYSTEM_PROMPT mentions {forbidden!r}"


# ------------------------------------------------------------------------------
# SPEC-BANNER-001 — the wordmark, and not erasing what the launcher said
# ------------------------------------------------------------------------------


def _banner_console(width: int, *, tty: bool) -> tuple[Console, io.StringIO]:
    buffer = io.StringIO()
    return Console(file=buffer, width=width, force_terminal=tty), buffer


def test_the_logo_fits_the_width_it_declares_it_needs() -> None:
    """Self-consistency, and the reason LOGO_MIN_WIDTH is not a round number.

    A logo wider than the terminal wraps, and a wrapped logo is worse than no
    logo — the letters break mid-glyph and the result reads as corruption. The
    threshold is derived from the art rather than chosen, so widening the art
    without widening the gate fails here instead of in somebody's terminal.
    """
    widest = max(len(line) for line in main.LOGO.splitlines())
    assert widest <= main.LOGO_MIN_WIDTH, (
        f"the logo is {widest} columns but is printed at {main.LOGO_MIN_WIDTH}"
    )
    assert len(main.LOGO.splitlines()) == 5, "the logo is no longer five rows"


def test_the_logo_is_printed_when_the_terminal_is_wide_enough(monkeypatch) -> None:
    console, buffer = _banner_console(main.LOGO_MIN_WIDTH, tty=False)
    monkeypatch.setattr(main, "console", console)
    main.show_banner()
    assert main.LOGO.splitlines()[0] in buffer.getvalue()


def test_the_logo_is_suppressed_rather_than_wrapped_on_a_narrow_terminal(monkeypatch) -> None:
    """80 columns is still Terminal.app's default, and this art needs 61 of them
    plus slack. One column under the gate must lose the logo, not fold it."""
    console, buffer = _banner_console(main.LOGO_MIN_WIDTH - 1, tty=False)
    monkeypatch.setattr(main, "console", console)
    main.show_banner()
    rendered = buffer.getvalue()
    assert main.LOGO.splitlines()[0] not in rendered
    assert "CodeRunner" in rendered, "the text banner must still appear"


def test_the_screen_is_not_cleared_when_the_launcher_warned(monkeypatch) -> None:
    """The whole reason `_clear_is_safe` exists rather than a bare console.clear().

    SPEC-KEYCHAIN-001 U4 requires exactly one status line per launch telling the
    user a declared secret will be prompted rather than sourced. It is printed
    by the launcher, before this process starts. Clearing here erases it.
    """
    console, _ = _banner_console(100, tty=True)
    monkeypatch.setattr(main, "console", console)

    monkeypatch.delenv("CODERUNNER_LAUNCH_WARNED", raising=False)
    assert main._clear_is_safe() is True

    monkeypatch.setenv("CODERUNNER_LAUNCH_WARNED", "1")
    assert main._clear_is_safe() is False


def test_the_screen_is_not_cleared_when_output_is_not_a_terminal(monkeypatch) -> None:
    """Clear codes in a pipe or a log corrupt it."""
    console, _ = _banner_console(100, tty=False)
    monkeypatch.setattr(main, "console", console)
    monkeypatch.delenv("CODERUNNER_LAUNCH_WARNED", raising=False)
    assert main._clear_is_safe() is False


def test_show_banner_actually_honours_the_clear_decision(monkeypatch) -> None:
    """The predicate and its use, asserted together — a correct predicate that
    nothing consults is the failure mode this repository met twice this week."""
    console, _ = _banner_console(100, tty=True)
    monkeypatch.setattr(main, "console", console)
    calls: list[int] = []
    monkeypatch.setattr(console, "clear", lambda *a, **k: calls.append(1))

    monkeypatch.setenv("CODERUNNER_LAUNCH_WARNED", "1")
    main.show_banner()
    assert calls == [], "show_banner cleared over the launcher's warning"

    monkeypatch.delenv("CODERUNNER_LAUNCH_WARNED", raising=False)
    main.show_banner()
    assert calls == [1], "show_banner did not clear when it was safe to"
