# ==============================================================================
#  CodeRunner.AI  ::  memory.py — the /memory REPL command
# ------------------------------------------------------------------------------
#  Project : SPEC-MEMORY-001, task T7
#  Covers  : AC-9 (user control) in full.
#
#  `handle_memory_command` lives in memory.py rather than main.py, with an
#  injected `emit` callable rather than a rich Console (user-approved
#  deviation). That is what keeps this suite runnable on bare pytest and keeps
#  memory.py free of third-party imports.
# ==============================================================================

from __future__ import annotations

import pytest

import memory
from vectorstore import VectorStore

from conftest import EMBED_MODEL, make_record


class Emitter:
    """Collects emitted lines so assertions can read the rendered output."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, line: str) -> None:
        self.lines.append(line)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@pytest.fixture()
def emit() -> Emitter:
    return Emitter()


@pytest.fixture()
def store_of_three(tmp_store: VectorStore) -> VectorStore:
    for index in range(3):
        tmp_store.insert(make_record(task=f"task number {index}"), max_records=500)
    return tmp_store


# ------------------------------------------------------------------------------
# Dispatch contract
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "/memory",
        "  /memory  ",
        "/MEMORY",
        "/memory list",
        "/memory list 2",
        "/memory forget 1",
        "/memory clear",
        "/memory clear --yes",
        "/memory something-unknown",
    ],
)
def test_every_memory_input_is_handled_locally(
    store_of_three: VectorStore, emit: Emitter, text: str
) -> None:
    """AC-9: handled locally, so agentic_turn() is never invoked."""
    assert memory.handle_memory_command(store_of_three, text, emit) is True
    assert emit.lines, "a handled command must always say something"


@pytest.mark.parametrize(
    "text",
    ["", "   ", "/exit", "/quit", "hello world", "what is /memory", "/memoryfoo"],
)
def test_non_memory_input_is_not_handled(
    store_of_three: VectorStore, emit: Emitter, text: str
) -> None:
    # `/memoryfoo` is a different word, not a `/memory` subcommand. Claiming it
    # would silently swallow input the user meant for the model.
    assert memory.handle_memory_command(store_of_three, text, emit) is False
    assert emit.lines == []


def test_commands_are_handled_even_when_the_store_is_unavailable(
    emit: Emitter,
) -> None:
    # M5: a degraded store must not make /memory raise or fall through to the
    # model. The user gets told memory is off.
    assert memory.handle_memory_command(None, "/memory", emit) is True
    assert "unavailable" in emit.text.lower() or "disabled" in emit.text.lower()


# ------------------------------------------------------------------------------
# Bare /memory — the status report
# ------------------------------------------------------------------------------


def test_bare_memory_reports_every_field_ac9_requires(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    memory.handle_memory_command(store_of_three, "/memory", emit)
    text = emit.text

    assert str(store_of_three.path) in text  # database path
    assert "3" in text  # total count
    assert EMBED_MODEL in text  # embedding model
    assert "eligible" in text.lower()  # eligible count
    assert "dim" in text.lower()  # dimension
    assert "byte" in text.lower() or "kb" in text.lower()  # on-disk size


def test_bare_memory_reports_effective_config_values_when_given_them(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    # AC-8: /memory shows EFFECTIVE values, not raw environment strings.
    config = memory.MemoryConfig(
        enabled=True,
        embed_model=EMBED_MODEL,
        chat_model="llama3.1:8b",
        db_path=store_of_three.path,
        top_k=1,
        min_sim=0.65,
        max_records=10,
    )
    memory.handle_memory_command(store_of_three, "/memory", emit, config)
    text = emit.text
    assert "0.65" in text
    assert "10" in text


# ------------------------------------------------------------------------------
# /memory list
# ------------------------------------------------------------------------------


def test_list_honours_an_explicit_count(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    memory.handle_memory_command(store_of_three, "/memory list 2", emit)
    text = emit.text
    assert "task number 2" in text
    assert "task number 1" in text
    assert "task number 0" not in text  # only the 2 most recent


def test_list_without_a_count_shows_everything_up_to_the_default(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    memory.handle_memory_command(store_of_three, "/memory list", emit)
    for index in range(3):
        assert f"task number {index}" in emit.text


def test_list_shows_record_ids_so_forget_can_be_used(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    memory.handle_memory_command(store_of_three, "/memory list", emit)
    ids = [record.id for record in store_of_three.recent(3)]
    for record_id in ids:
        assert str(record_id) in emit.text


@pytest.mark.parametrize("count", ["abc", "-4", "0", ""])
def test_list_with_a_bad_count_does_not_raise(
    store_of_three: VectorStore, emit: Emitter, count: str
) -> None:
    # M5: no ValueError may escape a memory-subsystem code path.
    assert memory.handle_memory_command(
        store_of_three, f"/memory list {count}".strip(), emit
    ) is True


def test_list_truncates_a_very_long_task_to_one_line(
    tmp_store: VectorStore, emit: Emitter
) -> None:
    tmp_store.insert(make_record(task="x" * 500), max_records=500)
    memory.handle_memory_command(tmp_store, "/memory list", emit)

    listed = [line for line in emit.lines if line.strip().startswith("[")]
    assert len(listed) == 1
    assert "…" in listed[0]
    assert len(listed[0]) < 120  # stays on one terminal line


def test_list_collapses_newlines_so_one_record_is_one_line(
    tmp_store: VectorStore, emit: Emitter
) -> None:
    tmp_store.insert(make_record(task="first line\nsecond line"), max_records=500)
    memory.handle_memory_command(tmp_store, "/memory list", emit)

    listed = [line for line in emit.lines if line.strip().startswith("[")]
    assert len(listed) == 1
    assert "first line second line" in listed[0]


def test_status_reports_the_store_size_at_every_scale(
    tmp_store: VectorStore, emit: Emitter
) -> None:
    """AC-9's on-disk figure, driven directly across all four tiers.

    The MB and GB tiers are not decoration at v1.1.0: the 100,000-record cap of
    C9 puts a healthy store at ~0.9 GB and a worst case at ~1.4 GB, and the KB
    tier alone would render that as "943718.4 KB" — on the single number
    spec.md 4.1 obliges this product to state plainly.
    """
    assert memory._human_bytes(0) == "0 bytes"
    assert memory._human_bytes(1023) == "1023 bytes"
    assert memory._human_bytes(1024) == "1.0 KB"
    assert memory._human_bytes(1024 * 1024) == "1.0 MB"
    assert memory._human_bytes(618 * 1024 * 1024) == "618.0 MB"  # V4: vectors at the cap
    assert memory._human_bytes(1024**3) == "1.00 GB"
    assert memory._human_bytes(int(1.4 * 1024**3)) == "1.40 GB"  # C11 worst case


def test_list_on_an_empty_store_says_so(tmp_store: VectorStore, emit: Emitter) -> None:
    memory.handle_memory_command(tmp_store, "/memory list", emit)
    assert "no" in emit.text.lower() or "empty" in emit.text.lower()


# ------------------------------------------------------------------------------
# /memory forget
# ------------------------------------------------------------------------------


def test_forget_deletes_the_named_record(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    target = store_of_three.recent(1)[0].id
    assert memory.handle_memory_command(
        store_of_three, f"/memory forget {target}", emit
    ) is True
    assert store_of_three.count() == 2
    assert str(target) in emit.text


def test_forget_a_missing_id_prints_not_found_and_raises_nothing(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    """AC-9 verbatim: `/memory forget 99999`."""
    assert memory.handle_memory_command(store_of_three, "/memory forget 99999", emit) is True
    assert "not found" in emit.text.lower()
    assert store_of_three.count() == 3


@pytest.mark.parametrize("argument", ["", "abc", "1 2 3"])
def test_forget_with_a_bad_argument_deletes_nothing(
    store_of_three: VectorStore, emit: Emitter, argument: str
) -> None:
    assert memory.handle_memory_command(
        store_of_three, f"/memory forget {argument}".strip(), emit
    ) is True
    assert store_of_three.count() == 3


# ------------------------------------------------------------------------------
# /memory clear
# ------------------------------------------------------------------------------


def test_clear_without_yes_deletes_nothing_and_prints_the_required_form(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    assert memory.handle_memory_command(store_of_three, "/memory clear", emit) is True
    assert store_of_three.count() == 3
    assert "--yes" in emit.text


def test_clear_with_yes_deletes_everything(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    assert memory.handle_memory_command(store_of_three, "/memory clear --yes", emit) is True
    assert store_of_three.count() == 0
    assert "3" in emit.text


def test_clear_with_yes_on_an_empty_store_is_harmless(
    tmp_store: VectorStore, emit: Emitter
) -> None:
    assert memory.handle_memory_command(tmp_store, "/memory clear --yes", emit) is True
    assert tmp_store.count() == 0


# ------------------------------------------------------------------------------
# The AC-9 sequence, end to end
# ------------------------------------------------------------------------------


def test_the_ac9_sequence_progresses_3_3_2_0(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    """AC-9: `/memory`, `/memory list 2`, `/memory forget <id>`, `/memory clear --yes`."""
    assert memory.handle_memory_command(store_of_three, "/memory", emit) is True
    assert store_of_three.count() == 3

    assert memory.handle_memory_command(store_of_three, "/memory list 2", emit) is True
    assert store_of_three.count() == 3

    target = store_of_three.recent(1)[0].id
    assert memory.handle_memory_command(
        store_of_three, f"/memory forget {target}", emit
    ) is True
    assert store_of_three.count() == 2

    assert memory.handle_memory_command(store_of_three, "/memory clear --yes", emit) is True
    assert store_of_three.count() == 0


def test_an_unknown_subcommand_prints_usage_and_changes_nothing(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    assert memory.handle_memory_command(store_of_three, "/memory bogus", emit) is True
    assert store_of_three.count() == 3
    assert "/memory" in emit.text


def test_no_command_raises_when_the_store_is_broken(
    store_of_three: VectorStore, emit: Emitter
) -> None:
    # Every subcommand must survive a store that has gone away underneath it.
    store_of_three.close()
    for text in ("/memory", "/memory list", "/memory forget 1", "/memory clear --yes"):
        assert memory.handle_memory_command(store_of_three, text, emit) is True
