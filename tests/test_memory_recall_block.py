# ==============================================================================
#  CodeRunner.AI  ::  memory.py — the recall block and its injection
# ------------------------------------------------------------------------------
#  Project : SPEC-MEMORY-001, task T4 (retargeted at v1.1.0 by T-VS11)
#  Covers  : AC-2 (injection, in full, as a pure unit test) and the M4 framing.
#
#  Ranking, the threshold boundary and the eligibility filter moved to
#  tests/test_vectorstore.py when `search()` became a method on the storage
#  seam. Everything here is pure memory.py and runs on BARE PYTEST — no rich,
#  no ollama, no pymilvus, no numpy, no Docker, no network.
# ==============================================================================

from __future__ import annotations

import pytest

import memory
from conftest import CHAT_MODEL, EMBED_MODEL
from memory import SolutionRecord


# ------------------------------------------------------------------------------
# format_recall_block()  — M4 framing
# ------------------------------------------------------------------------------


@pytest.fixture()
def sample_record() -> SolutionRecord:
    return SolutionRecord(
        id=7,
        created_at="2026-08-02T00:00:00+00:00",
        task="What is the current weather in Seoul in Celsius?",
        thought="Fetch wttr.in JSON and read temp_C.",
        code="import requests\nprint(requests.get('https://wttr.in/Seoul?format=j1').json())",
        stdout="Seoul: 29C",
        chat_model=CHAT_MODEL,
        embed_model=EMBED_MODEL,
        dim=3,
        embedding=[1.0, 0.0, 0.0],
    )


def test_recall_block_carries_the_adapt_or_ignore_framing(
    sample_record: SolutionRecord,
) -> None:
    block = memory.format_recall_block(sample_record)
    assert memory.ADAPT_OR_IGNORE_SENTENCE in block

    # Also assert it whitespace-insensitively, so re-wrapping the paragraph
    # cannot silently drop the requirement M4 makes non-negotiable.
    flat = " ".join(block.split())
    assert "ignore it entirely and solve the current task from scratch" in flat
    assert "reference only" in flat.lower()
    assert "do not copy it blindly" in flat.lower()


def test_recall_block_contains_all_four_captured_fields(
    sample_record: SolutionRecord,
) -> None:
    block = memory.format_recall_block(sample_record)
    assert sample_record.task in block
    assert sample_record.thought in block
    assert sample_record.code in block
    assert sample_record.stdout in block


def test_recall_block_fences_the_code_as_python(sample_record: SolutionRecord) -> None:
    assert "```python" in memory.format_recall_block(sample_record)


def test_recall_block_never_instructs_the_model_to_reproduce(
    sample_record: SolutionRecord,
) -> None:
    flat = " ".join(memory.format_recall_block(sample_record).split()).lower()
    for forbidden in ("reuse this code", "run the following", "execute the script"):
        assert forbidden not in flat


# ------------------------------------------------------------------------------
# inject_recall()  — AC-2 in full
# ------------------------------------------------------------------------------


@pytest.fixture()
def conversation_messages() -> list[dict]:
    return [
        {"role": "system", "content": "SYSTEM_PROMPT"},
        {"role": "user", "content": "an earlier task"},
        {"role": "assistant", "content": "an earlier answer"},
        {"role": "user", "content": "the current task"},
    ]


def test_inject_recall_returns_a_new_list_one_longer(
    conversation_messages: list[dict],
) -> None:
    result = memory.inject_recall(conversation_messages, "BLOCK")
    assert result is not conversation_messages
    assert len(result) == len(conversation_messages) + 1


def test_inject_recall_places_the_block_immediately_before_the_user_message(
    conversation_messages: list[dict],
) -> None:
    result = memory.inject_recall(conversation_messages, "BLOCK")
    assert result[-2] == {"role": "system", "content": "BLOCK"}
    assert result[-1] is conversation_messages[-1]


def test_inject_recall_does_not_mutate_the_input_in_length_or_identity(
    conversation_messages: list[dict],
) -> None:
    """AC-2: Conversation.messages (main.py:124) is unchanged by the injection.

    Identity, not just equality: the block must be ephemeral to one request so
    it cannot accumulate across turns and worsen the unbounded-context problem
    in product.md 6.6.
    """
    snapshot = list(conversation_messages)
    result = memory.inject_recall(conversation_messages, "BLOCK")

    assert len(conversation_messages) == len(snapshot)
    assert all(a is b for a, b in zip(conversation_messages, snapshot))

    carried = result[:-2] + result[-1:]
    assert all(a is b for a, b in zip(carried, conversation_messages))


def test_inject_recall_is_pure_and_repeatable(conversation_messages: list[dict]) -> None:
    first = memory.inject_recall(conversation_messages, "BLOCK")
    second = memory.inject_recall(conversation_messages, "BLOCK")
    assert first == second
    assert first is not second


def test_inject_recall_matches_the_documented_slice_expression(
    conversation_messages: list[dict],
) -> None:
    # plan.md 6 states the request list verbatim; assert the identity rather
    # than trusting the prose.
    recall_msg = {"role": "system", "content": "BLOCK"}
    expected = (
        conversation_messages[:-1] + [recall_msg] + conversation_messages[-1:]
    )
    assert memory.inject_recall(conversation_messages, "BLOCK") == expected


def test_inject_recall_into_an_empty_list_yields_just_the_block() -> None:
    assert memory.inject_recall([], "BLOCK") == [{"role": "system", "content": "BLOCK"}]


def test_inject_recall_into_a_single_message_puts_the_block_first() -> None:
    messages = [{"role": "user", "content": "only"}]
    result = memory.inject_recall(messages, "BLOCK")
    assert [message["role"] for message in result] == ["system", "user"]
    assert result[-2]["content"] == "BLOCK"
