# ==============================================================================
#  CodeRunner.AI  ::  meter — what a turn cost, and how long it took
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-SKILL-001, task T1
#
#  EVERY NUMBER HERE IS THE SERVER'S. Ollama reports six fields on the final
#  streamed chunk -- prompt_eval_count, eval_count, total_duration,
#  load_duration, prompt_eval_duration, eval_duration -- and this module reads
#  them and computes none of them. Nothing is derived from a character count, a
#  word count, or a clock in this process (spec.md N2, D1).
#
#  WHY THAT IS A HARD RULE AND NOT A PREFERENCE. This SPEC's only deliverable of
#  consequence is a claim that something got cheaper or faster. A tokeniser
#  bolted on here would have a vocabulary that is not the server's, so its
#  numbers would be a different model's approximation of this model's cost --
#  precise-looking, wrong, and indistinguishable from data in the same table.
#  This project has already had to retract one documented claim written without
#  its provenance; product.md §5.5 is that retraction.
#
#  SO THE SHARPEST BEHAVIOUR IN THIS FILE IS THE ONE THAT REFUSES. A chunk with
#  no counts produces an UNMEASURED round trip, not an estimated one, and an
#  unmeasured round trip contributes to no total. The temptation is real and
#  cheap to yield to -- the reply text is right there in the chunk -- which is
#  why tests/test_meter.py asserts it behaviourally AND against this source.
#
#  THE TWO DIMENSIONS FAIL INDEPENDENTLY. A server may report counts and omit
#  durations. Discarding a cost figure because a latency figure is missing would
#  throw away a measurement that was actually taken, so `measured` and `timed`
#  are separate flags.
#
#  STDLIB ONLY, AND THAT IS ENFORCED. tests/test_meter.py walks this module's
#  AST and asserts every imported root is in sys.stdlib_module_names. The final
#  chunk arrives as a duck-typed mapping through `Receipt`, so `ollama` never
#  appears here -- the same device memory.py uses to type its `store` parameter
#  as Any (tech.md §1.2).
#
#  SIZES ARE NOT COUNTS. `record_sizes()` stores characters, under `unit =
#  "characters"`, in a structure with a different name from the one holding
#  counts. Per-MESSAGE token attribution is not obtainable -- the server reports
#  one prompt_eval_count for the whole prompt and exposes no tokenize endpoint
#  (spec.md v1.1.1) -- and a character share is enough to rank the components
#  against each other, which is the only job attribution had (plan.md R2).
#  Presenting one as the other is the failure this module exists to avoid.
# ==============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: The purposes a round trip can serve. `code` is the pass that produces the
#: fenced block; `grounded` is the second pass that narrates real stdout. Keeping
#: them apart is what lets T4 ask what the grounded pass costs, which is the
#: question that decides whether it can be skipped.
CODE = "code"
GROUNDED = "grounded"

#: Read from the chunk and never computed. The order is the order ollama
#: documents them; it is spelled out rather than derived so that a field
#: disappearing upstream is a test failure and not a silent None.
_COUNT_FIELDS = ("prompt_eval_count", "eval_count")
_DURATION_FIELDS = (
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
)


def _read(chunk: Any, key: str) -> int | None:
    """Return an int field from a chunk, or None if it is not readable.

    Deliberately total. A chunk that is not a mapping, a field that is absent, a
    value that is not an integer -- each yields None, which becomes an unmeasured
    round trip upstream. The meter must never be the reason a turn fails
    (spec.md S2), and "I could not read this" is a better answer than a guess.
    """
    try:
        value = chunk[key]
    except (TypeError, KeyError, IndexError):
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def component_sizes(messages: Any) -> dict[str, int]:
    """Classify a request's messages and total each component's CHARACTERS.

    Not tokens, and the distinction is the whole reason this function exists in
    this form. Per-message token attribution is not obtainable -- the server
    reports one prompt_eval_count for the whole prompt and exposes no tokenize
    endpoint (spec.md v1.1.1) -- so the meter records the thing that IS
    obtainable and labels it a size.

    **Position discriminates, not wording.** The system prompt is seeded once
    outside the turn loop, and `inject_recall()` returns a NEW list carrying the
    recall block as a system message. A second system message therefore cannot
    arrive by any other route, so classifying by position needs no knowledge of
    the block's text and cannot drift when that text changes.

    **Feedback injections are counted inside `history`, and that is a stated
    limit rather than an oversight.** They enter as ordinary `user` messages
    (main.py's `conv.user(feedback)`), so separating them would mean matching on
    our own prompt wording -- coupling the meter to a string that T4 may well
    rewrite. `history` is still the ranking plan.md R2 needs: if it dominates,
    T5 is the task worth doing, and whether the bulk is dialogue or feedback is
    a question T5 can ask with a sharper instrument.

    Total by construction: anything unreadable contributes nothing rather than
    raising, because the meter must never be the reason a turn fails (S2).
    """
    sizes: dict[str, int] = {}
    seen_system = False
    try:
        iterator = iter(messages)
    except TypeError:
        return sizes
    for message in iterator:
        try:
            role = message["role"]
        except (TypeError, KeyError, IndexError):
            role = None
        try:
            content = message["content"]
        except (TypeError, KeyError, IndexError):
            content = ""
        size = len(content) if isinstance(content, str) else 0
        if role == "system" and not seen_system:
            seen_system = True
            key = "system"
        elif role == "system":
            key = "skill"
        else:
            key = "history"
        sizes[key] = sizes.get(key, 0) + size
    return sizes


@dataclass(frozen=True)
class RoundTrip:
    """One model call, as the server described it.

    ``measured`` and ``timed`` are separate because the dimensions fail
    separately: a server may report counts without durations. Both default to
    False, so a chunk this module could not read is unmeasured by construction
    rather than by remembering to set a flag.
    """

    purpose: str
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_duration: int | None = None
    eval_duration: int | None = None

    @property
    def measured(self) -> bool:
        """True only when the SERVER supplied both counts."""
        return self.prompt_eval_count is not None and self.eval_count is not None

    @property
    def timed(self) -> bool:
        """True only when the server supplied a total duration.

        `load_duration` is deliberately not required here. It is the model being
        loaded into memory, nothing in this SPEC can reduce it, and it is
        reported separately so a comparison can exclude it (spec.md U5, N6).
        """
        return self.total_duration is not None


@dataclass(frozen=True)
class SizeRecord:
    """How many CHARACTERS each prompt component contributed.

    Not tokens. `unit` is stored rather than assumed so that the figure cannot be
    read as a count by a later reader or a later change (spec.md U6).
    """

    purpose: str
    sizes: dict[str, int]
    unit: str = "characters"


class Receipt:
    """A one-slot mailbox a streaming generator fills and its caller reads.

    ``stream_llm()`` yields strings and is consumed through ``prime_stream()``,
    so there is no return value on which the final chunk could travel. The caller
    constructs a Receipt, hands it in, and reads it after the stream is drained.

    It keeps the LAST chunk it is given because ollama sends the metadata on the
    final one; earlier chunks carry only content.
    """

    __slots__ = ("chunk",)

    def __init__(self) -> None:
        self.chunk: Any = None

    def set(self, chunk: Any) -> None:
        self.chunk = chunk


@dataclass
class Meter:
    """The per-session record of what was spent and what was refused.

    Totals sum only over round trips the server actually measured. An unmeasured
    round trip is counted in ``unmeasured_round_trips`` and contributes nothing
    to any total, which is the difference between reporting a gap and filling it.
    """

    round_trips: list[RoundTrip] = field(default_factory=list)
    size_records: list[SizeRecord] = field(default_factory=list)

    def record(self, *, purpose: str, chunk: Any) -> RoundTrip:
        """Record one round trip from the server's final chunk.

        Anything unreadable -- a malformed chunk, a missing field, a
        non-integer -- lands as None and therefore as unmeasured. There is no
        branch here that consults the chunk's text, and there must never be one.
        """
        values: dict[str, int | None] = {
            name: _read(chunk, name) for name in _COUNT_FIELDS + _DURATION_FIELDS
        }
        trip = RoundTrip(purpose=purpose, **values)
        self.round_trips.append(trip)
        return trip

    def record_sizes(self, *, purpose: str, sizes: dict[str, int]) -> SizeRecord:
        """Record the character size of each prompt component (spec.md U6)."""
        record = SizeRecord(purpose=purpose, sizes=dict(sizes))
        self.size_records.append(record)
        return record

    # -- totals, over measured round trips only -------------------------------

    @property
    def measured_round_trips(self) -> int:
        return sum(1 for t in self.round_trips if t.measured)

    @property
    def unmeasured_round_trips(self) -> int:
        return sum(1 for t in self.round_trips if not t.measured)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(t.prompt_eval_count or 0 for t in self.round_trips if t.measured)

    @property
    def total_completion_tokens(self) -> int:
        return sum(t.eval_count or 0 for t in self.round_trips if t.measured)

    @property
    def is_empty(self) -> bool:
        """No round trip at all -- distinct from round trips that cost nothing.

        Zero turns and zero tokens are different facts, and a report that
        conflates them passes every other assertion while being useless
        (acceptance.md Scenario 4).
        """
        return not self.round_trips

    def prompt_tokens_by_purpose(self) -> dict[str, int]:
        """Measured prompt tokens, attributed per round trip (spec.md U1)."""
        totals: dict[str, int] = {}
        for trip in self.round_trips:
            if trip.measured and trip.prompt_eval_count is not None:
                totals[trip.purpose] = totals.get(trip.purpose, 0) + trip.prompt_eval_count
        return totals

    def largest_component(self) -> str | None:
        """The component contributing the most characters, or None.

        This is the ranking plan.md R2 needs: which of the system prompt, the
        history, the skill block or the feedback dominates the prompt, and
        therefore which of T3/T4/T5 is worth doing. It is a ranking of SIZES and
        it is not a token count.
        """
        totals: dict[str, int] = {}
        for record in self.size_records:
            for name, size in record.sizes.items():
                totals[name] = totals.get(name, 0) + size
        if not totals:
            return None
        return max(totals, key=lambda name: totals[name])
