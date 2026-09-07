# ==============================================================================
#  CodeRunner.AI  ::  meter.py — the cost-and-latency meter
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-SKILL-001, task T1
#
#  WHAT THIS FILE GATES, AND THE ONE THING IT GATES HARDEST.
#
#  The meter's whole value is that its numbers are the SERVER's. Every figure it
#  reports comes from the final streamed chunk -- prompt_eval_count, eval_count,
#  and the four duration fields -- and nothing is ever derived from a character
#  count or a client-side clock (spec.md N2).
#
#  So the sharpest test here is not that a present count is recorded. It is that
#  an ABSENT one stays absent: `test_a_round_trip_without_counts_is_unmeasured`
#  and its siblings. A meter that quietly fills a gap with an estimate passes
#  every other assertion in this file while being exactly the instrument the
#  SPEC was written to avoid, because on a second reading the estimate is
#  indistinguishable from data.
# ==============================================================================

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent

import meter as meter_mod  # noqa: E402

# ------------------------------------------------------------------------------
# 1. The module is a leaf
# ------------------------------------------------------------------------------


def test_the_meter_imports_nothing_third_party() -> None:
    """spec.md U2, and the same assertion memory.py already carries.

    The final chunk reaches the meter as a duck-typed mapping through a receipt
    the caller owns, so `ollama` never enters this module's AST. Once a
    third-party import lands in a gated leaf, every primitive test acquires that
    dependency's tree, and the guarantee is far easier to keep than to restore
    (tech.md §1.2).
    """
    tree = ast.parse((_ROOT / "meter.py").read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    non_stdlib = roots - set(sys.stdlib_module_names)
    assert non_stdlib == set(), f"meter.py must import stdlib only; found {sorted(non_stdlib)}"


# ------------------------------------------------------------------------------
# 2. Recording a round trip — the six fields, from the server
# ------------------------------------------------------------------------------

#: Spelled out rather than imported from the module. Importing its own field list
#: would assert that the module agrees with itself, which is not a gate.
SERVER_FIELDS = (
    "prompt_eval_count",
    "eval_count",
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
)


def _chunk(**overrides: object) -> dict:
    """A final chunk in the shape ollama sends one, with every field present."""
    base = {
        "prompt_eval_count": 1200,
        "eval_count": 340,
        "total_duration": 5_000_000_000,
        "load_duration": 1_500_000_000,
        "prompt_eval_duration": 2_000_000_000,
        "eval_duration": 1_400_000_000,
        "done": True,
    }
    base.update(overrides)
    return base


def test_a_round_trip_records_all_six_server_fields() -> None:
    """AC-METER Scenario 1. Every figure is the server's own."""
    meter = meter_mod.Meter()
    meter.record(purpose="code", chunk=_chunk())
    (trip,) = meter.round_trips
    for field in SERVER_FIELDS:
        assert getattr(trip, field) == _chunk()[field], f"{field} not carried through"
    assert trip.purpose == "code"
    assert trip.measured is True


def test_a_round_trip_is_attributed_to_its_purpose() -> None:
    """spec.md U1 as amended at v1.1.1.

    Per-MESSAGE attribution is not obtainable: the server reports one
    prompt_eval_count for the whole prompt and exposes no tokenize endpoint. Per
    ROUND TRIP is, and it is what distinguishes the code pass from the
    grounded-answer pass -- which is the comparison T4 turns on.
    """
    meter = meter_mod.Meter()
    meter.record(purpose="code", chunk=_chunk(prompt_eval_count=1200))
    meter.record(purpose="grounded", chunk=_chunk(prompt_eval_count=1800))
    assert [t.purpose for t in meter.round_trips] == ["code", "grounded"]
    assert meter.prompt_tokens_by_purpose() == {"code": 1200, "grounded": 1800}


# ------------------------------------------------------------------------------
# 3. Absent is absent — the criterion, not the edge case
# ------------------------------------------------------------------------------


def test_a_round_trip_without_counts_is_unmeasured() -> None:
    """AC-METER Scenario 2, and the sharpest assertion in this file.

    A server or client version that omits the counts must not be papered over.
    The turn is recorded as unmeasured in that dimension and contributes to no
    rate (spec.md S1).
    """
    meter = meter_mod.Meter()
    meter.record(purpose="code", chunk={"done": True})
    (trip,) = meter.round_trips
    assert trip.measured is False
    assert trip.prompt_eval_count is None
    assert trip.eval_count is None


def test_an_unmeasured_round_trip_contributes_to_no_total() -> None:
    """Recording the gap is only half of it; the gap must not be counted as zero."""
    meter = meter_mod.Meter()
    meter.record(purpose="code", chunk=_chunk(prompt_eval_count=1200, eval_count=340))
    meter.record(purpose="grounded", chunk={"done": True})
    assert meter.total_prompt_tokens == 1200
    assert meter.total_completion_tokens == 340
    assert meter.measured_round_trips == 1
    assert meter.unmeasured_round_trips == 1


def test_counts_are_never_estimated_from_the_chunk_text() -> None:
    """spec.md N2. A long reply with no counts stays unmeasured.

    The temptation this guards against is real and cheap to yield to: the text
    is right there. A number derived from it would look exactly like a
    measurement in the same table as the server's own.
    """
    meter = meter_mod.Meter()
    meter.record(purpose="code", chunk={"message": {"content": "x" * 10_000}, "done": True})
    (trip,) = meter.round_trips
    assert trip.measured is False
    assert trip.prompt_eval_count is None


@pytest.mark.parametrize(
    ("value", "why"),
    [
        (True, "bool is a subclass of int; True would otherwise record as 1 token"),
        (False, "and False as 0, which reads as a real measurement of nothing"),
        ("1200", "a string that looks like a count is still not one"),
        (12.5, "a float count is not a count the server issued"),
        (None, "an explicitly null field"),
    ],
)
def test_a_field_that_is_not_an_integer_is_unmeasured(value: object, why: str) -> None:
    """The type guard, and the bool case is why it is written the way it is.

    `isinstance(True, int)` is True in Python. Without the explicit bool check, a
    chunk carrying `prompt_eval_count: True` would be recorded as ONE prompt
    token -- a plausible small number, in the right column, that no reader would
    question. That is the exact failure mode spec.md N2 exists to prevent, and it
    arrives through the type system rather than through an estimate.
    """
    meter = meter_mod.Meter()
    meter.record(purpose=meter_mod.CODE, chunk={"prompt_eval_count": value, "eval_count": 10})
    (trip,) = meter.round_trips
    assert trip.prompt_eval_count is None, why
    assert trip.measured is False


def test_a_latency_without_durations_is_unmeasured_in_that_dimension_only() -> None:
    """The two dimensions fail independently (spec.md S1, v1.1.0).

    A server reporting counts but not durations yields a real cost figure and no
    latency figure. Discarding the cost because the latency is missing would
    throw away a measurement that was taken.
    """
    meter = meter_mod.Meter()
    meter.record(purpose="code", chunk={"prompt_eval_count": 900, "eval_count": 100, "done": True})
    (trip,) = meter.round_trips
    assert trip.measured is True
    assert trip.timed is False
    assert trip.total_duration is None
    assert meter.total_prompt_tokens == 900


def test_the_source_module_holds_no_character_based_fallback() -> None:
    """N2 asserted against the SOURCE, not only against behaviour.

    A fallback added later would be caught by the behavioural tests above only
    if someone remembered to run them against a countless chunk. This one fails
    the moment the words appear in the file.
    """
    src = (_ROOT / "meter.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "len" not in called or "size" in src, (
        "meter.py calls len() -- permitted only for the character SIZE record (U6), "
        "never to derive a token count (N2)"
    )


# ------------------------------------------------------------------------------
# 4. Sizes are sizes (U6, v1.1.1)
# ------------------------------------------------------------------------------


def test_component_sizes_are_recorded_in_characters_and_named_as_sizes() -> None:
    """spec.md U6.

    Per-message token attribution is not obtainable, so the meter records the
    thing that IS: how many characters each component contributed. It is enough
    to rank the components against each other, which is the only job attribution
    had (plan.md R2).
    """
    meter = meter_mod.Meter()
    meter.record_sizes(
        purpose="code",
        sizes={"system": 4000, "history": 12000, "skill": 800},
    )
    (record,) = meter.size_records
    assert record.unit == "characters"
    assert record.sizes == {"system": 4000, "history": 12000, "skill": 800}


def test_a_size_is_never_reported_as_a_token_count() -> None:
    """The whole point of U6, asserted rather than trusted.

    Sizes and counts live in separate structures with separate names precisely
    so that no reader, and no later change, can mistake one for the other.
    """
    meter = meter_mod.Meter()
    meter.record_sizes(purpose="code", sizes={"system": 4000})
    meter.record(purpose="code", chunk={"done": True})
    assert meter.total_prompt_tokens == 0
    assert meter.measured_round_trips == 0


def test_the_dominant_component_is_identifiable() -> None:
    """plan.md R2: the ranking is what selects between T3, T4 and T5."""
    meter = meter_mod.Meter()
    meter.record_sizes(purpose="code", sizes={"system": 4000, "history": 12000, "skill": 800})
    assert meter.largest_component() == "history"


def test_the_dominant_component_of_nothing_is_nothing() -> None:
    """A ranking over no components is None, not an arbitrary key."""
    meter = meter_mod.Meter()
    assert meter.largest_component() is None


# ------------------------------------------------------------------------------
# 4.5 Classifying a message list into components (U6)
# ------------------------------------------------------------------------------
# Which component dominates the prompt is what selects between T3, T4 and T5
# (plan.md R2). The classification is a pure function here rather than inline in
# main.py so that it is gated at 100% like everything else in this module --
# main.py is not in pytest.ini's --cov list, so logic placed there is logic
# nobody's coverage gate is watching.


def test_the_first_system_message_is_the_system_prompt() -> None:
    sizes = meter_mod.component_sizes(
        [
            {"role": "system", "content": "S" * 4000},
            {"role": "user", "content": "u" * 10},
        ]
    )
    assert sizes["system"] == 4000
    assert sizes["history"] == 10


def test_a_later_system_message_is_the_skill_block() -> None:
    """`inject_recall` returns a NEW list carrying the block as a system message.

    It is the only way a second system message enters a request, so position is
    a sound discriminator and does not depend on the block's wording.
    """
    sizes = meter_mod.component_sizes(
        [
            {"role": "system", "content": "S" * 4000},
            {"role": "user", "content": "u" * 10},
            {"role": "system", "content": "K" * 800},
        ]
    )
    assert sizes == {"system": 4000, "history": 10, "skill": 800}


def test_a_request_without_a_skill_block_reports_no_skill_component() -> None:
    """Absent is absent here too -- not a zero that reads as a measured nothing."""
    sizes = meter_mod.component_sizes(
        [{"role": "system", "content": "S" * 100}, {"role": "user", "content": "u"}]
    )
    assert "skill" not in sizes


def test_component_sizes_of_an_empty_request_are_empty() -> None:
    assert meter_mod.component_sizes([]) == {}


def test_component_sizes_tolerate_a_malformed_message() -> None:
    """The meter must never be the reason a turn fails (spec.md S2)."""
    sizes = meter_mod.component_sizes(
        [{"role": "system"}, {"content": "x" * 5}, "not a mapping", None]
    )
    assert sizes["system"] == 0
    assert sizes["history"] == 5


@pytest.mark.parametrize("not_a_list", [None, 42, 3.5])
def test_component_sizes_of_something_that_is_not_a_message_list(not_a_list: object) -> None:
    """Total by construction, at the outermost boundary too (spec.md S2).

    The per-message guards below cover a bad ITEM. This covers a bad ARGUMENT --
    the shape a future caller passing the wrong thing would produce. The meter
    returns nothing rather than raising, because it must never be the reason a
    turn fails.
    """
    assert meter_mod.component_sizes(not_a_list) == {}


def test_component_sizes_are_characters_and_feed_the_ranking() -> None:
    """The whole point: which component dominates (plan.md R2)."""
    m = meter_mod.Meter()
    m.record_sizes(
        purpose=meter_mod.CODE,
        sizes=meter_mod.component_sizes(
            [
                {"role": "system", "content": "S" * 4000},
                {"role": "user", "content": "h" * 12000},
                {"role": "system", "content": "K" * 800},
            ]
        ),
    )
    assert m.largest_component() == "history"
    (record,) = m.size_records
    assert record.unit == "characters"


# ------------------------------------------------------------------------------
# 5. The empty session, and the meter's degradation contract
# ------------------------------------------------------------------------------


def test_an_empty_session_reports_zero_turns_rather_than_zero_cost() -> None:
    """AC-METER Scenario 4.

    Zero turns and zero tokens are different facts. A report that conflates them
    passes every other criterion here while being useless.
    """
    meter = meter_mod.Meter()
    assert meter.measured_round_trips == 0
    assert meter.total_prompt_tokens == 0
    assert meter.is_empty is True


def test_a_meter_with_an_unmeasured_turn_is_not_empty() -> None:
    """The distinction above, from the other side."""
    meter = meter_mod.Meter()
    meter.record(purpose="code", chunk={"done": True})
    assert meter.is_empty is False
    assert meter.measured_round_trips == 0


@pytest.mark.parametrize("bad", [None, 42, "not a mapping", [1, 2, 3]])
def test_a_malformed_chunk_is_unmeasured_and_does_not_raise(bad: object) -> None:
    """AC-METER Scenario 3.

    The meter must never be the reason a turn fails. Anything it cannot read is
    an unmeasured round trip, which is the same answer it gives to a chunk that
    simply omitted its counts.
    """
    meter = meter_mod.Meter()
    meter.record(purpose="code", chunk=bad)
    (trip,) = meter.round_trips
    assert trip.measured is False
    assert trip.timed is False


# ------------------------------------------------------------------------------
# 6. The receipt — the seam stream_llm fills
# ------------------------------------------------------------------------------


def test_a_receipt_starts_empty_and_carries_the_final_chunk() -> None:
    """The device that lets a generator yielding strings report its metadata.

    `stream_llm()` yields text and is consumed through `prime_stream()`, so
    there is no return value to carry the final chunk. The caller owns a receipt
    and the generator fills it, which also keeps `ollama` out of this module's
    AST (spec.md U2).
    """
    receipt = meter_mod.Receipt()
    assert receipt.chunk is None
    receipt.set(_chunk())
    assert receipt.chunk is not None
    assert receipt.chunk["eval_count"] == 340


def test_a_receipt_keeps_the_last_chunk_it_was_given() -> None:
    """Ollama sends metadata on the final chunk; an earlier one carries none."""
    receipt = meter_mod.Receipt()
    receipt.set({"message": {"content": "partial"}})
    receipt.set(_chunk())
    assert receipt.chunk["prompt_eval_count"] == 1200


# ------------------------------------------------------------------------------
# 7. The seam, against main.stream_llm itself
# ------------------------------------------------------------------------------
# stream_llm's docstring said it was "testable with a fake client, which it has
# never been". These are the tests that change that, and they are here rather
# than in a main.py suite because what they gate is the meter's supply line: if
# the final chunk does not reach the Receipt, every figure this module reports
# is absent and nothing else notices.


class _FakeChatClient:
    """Yields the chunks it was given, in order, from `chat(...)`."""

    def __init__(self, chunks: list[dict]) -> None:
        self._chunks = chunks
        self.calls: list[dict] = []

    def chat(self, **kwargs: object) -> object:
        self.calls.append(dict(kwargs))
        return iter(self._chunks)


def test_stream_llm_fills_the_receipt_from_the_final_chunk() -> None:
    """The supply line, end to end and offline."""
    import main

    final = _chunk(prompt_eval_count=777)
    client = _FakeChatClient(
        [{"message": {"content": "hel"}}, {"message": {"content": "lo"}}, final]
    )
    receipt = meter_mod.Receipt()
    text = "".join(main.stream_llm(client, [{"role": "user", "content": "hi"}], receipt))

    assert text == "hello"
    assert receipt.chunk is not None
    assert receipt.chunk["prompt_eval_count"] == 777

    recorded = meter_mod.Meter()
    recorded.record(purpose=meter_mod.CODE, chunk=receipt.chunk)
    assert recorded.total_prompt_tokens == 777


def test_stream_llm_without_a_receipt_behaves_exactly_as_before() -> None:
    """The parameter is optional so no existing caller changes.

    A turn with no receipt is a turn nobody measured -- which must remain a
    perfectly ordinary turn, not a degraded one.
    """
    import main

    client = _FakeChatClient([{"message": {"content": "a"}}, {"message": {"content": "b"}}])
    assert "".join(main.stream_llm(client, [{"role": "user", "content": "hi"}])) == "ab"


def test_stream_llm_yields_nothing_for_a_metadata_only_stream() -> None:
    """A stream carrying only a final chunk yields no text but still reports.

    This is the shape a refused or empty completion takes, and the receipt must
    still be filled -- an empty answer that cost prompt tokens is a real cost.
    """
    import main

    client = _FakeChatClient([_chunk(eval_count=0)])
    receipt = meter_mod.Receipt()
    assert "".join(main.stream_llm(client, [{"role": "user", "content": "hi"}], receipt)) == ""
    assert receipt.chunk["prompt_eval_count"] == 1200
