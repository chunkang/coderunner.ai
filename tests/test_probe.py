# ==============================================================================
#  CodeRunner.AI  ::  the probe harness — offline assertions
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-PROMPT-001, task T1
#
#  WHAT THIS FILE IS FOR, AND WHAT IT DELIBERATELY CANNOT DO.
#
#  `probe/` drives a real model. Nothing here does. Every test below runs with
#  no network, no model and no container, against a fake client in the style of
#  conftest.py's FakeEmbedClient, so the harness's STRUCTURE is gated by CI while
#  its RESULTS are not gated by anything (they cannot be — the thing under
#  measurement is a model's behaviour, spec.md 5).
#
#  WHY `probe/` IS NOT UNDER `tests/`. pytest.ini sets `testpaths = tests`, so
#  `probe/` is never collected. That siting is load-bearing rather than tidy:
#  .github/workflows/ci.yml asserts `skipped == 0`, and a model-dependent test
#  under `tests/` would either skip on a GitHub runner (red) or block on a model
#  that is not there (worse). So the harness lives outside collection and this
#  file — which IS collected — carries no `importorskip` and no marker, because
#  a test that can skip is a test that can be absent without anyone noticing.
# ==============================================================================

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parent.parent

import probe.aggregate as aggregate  # noqa: E402
import probe.classify as classify  # noqa: E402
import probe.run_probe as run_probe  # noqa: E402
import probe.tasks as tasks  # noqa: E402
import probe.variants as variants  # noqa: E402

BACKTICK = "`"
FENCE = BACKTICK * 3


# ------------------------------------------------------------------------------
# A fake chat client, in conftest.py's FakeEmbedClient style
# ------------------------------------------------------------------------------


class FakeChatClient:
    """Stands in for ``ollama.Client``, exposing only what the probe touches.

    Returns plain dicts on purpose, for the reason conftest.py's FakeEmbedClient
    records: ollama 0.3.0 hands back a TypedDict and 0.6.2 a pydantic model, and
    subscript access is the only form that works on both. Making the fake the
    harsher shape is what turns that constraint from aspirational into enforced.
    """

    def __init__(
        self,
        replies: list[str] | None = None,
        model_tag: str = "llama3.1:8b",
        digest: str = "deadbeef",
    ) -> None:
        self.replies = list(replies) if replies is not None else ["Answer: hi"]
        self.model_tag = model_tag
        self.digest = digest
        self.chat_calls: list[list[dict]] = []
        self.show_calls: list[str] = []
        self.list_calls = 0

    def chat(
        self,
        model: str = "",
        messages: Any = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        self.chat_calls.append(list(messages or []))
        reply = self.replies[(len(self.chat_calls) - 1) % len(self.replies)]
        return [{"message": {"content": reply}}]

    def list(self) -> dict:
        self.list_calls += 1
        return {"models": [{"model": self.model_tag, "digest": self.digest}]}

    def show(self, model: str = "") -> dict:
        self.show_calls.append(model)
        return {
            "details": {"parameter_size": "8.0B", "quantization_level": "Q4_K_M"},
            "parameters": 'stop "<|eot_id|>"',
        }


@pytest.fixture()
def fake_client() -> FakeChatClient:
    return FakeChatClient()


# ------------------------------------------------------------------------------
# 1. The classifier is DELEGATED, not COPIED
# ------------------------------------------------------------------------------


def _classify_tree() -> ast.Module:
    return ast.parse((_ROOT / "probe" / "classify.py").read_text(encoding="utf-8"))


def test_the_classifier_module_imports_the_production_predicate() -> None:
    """R7, stated as an assertion rather than as an intention.

    A probe carrying its own copy of the regex can pass while main.py:1032 still
    fails, and the measurement becomes fiction. spec.md E6 requires the SAME
    predicate, so this asserts the import by AST rather than by grep: a grep for
    the name would also match it inside a comment or a docstring.
    """
    imported: set[str] = set()
    for node in ast.walk(_classify_tree()):
        if isinstance(node, ast.ImportFrom) and node.module == "main":
            imported |= {alias.name for alias in node.names}

    assert "extract_last_python_block" in imported, (
        "probe/classify.py must do `from main import extract_last_python_block` — "
        f"it imports {sorted(imported) or 'nothing'} from main"
    )


def test_the_classifier_module_compiles_no_regex_of_its_own() -> None:
    """The other half of R7: importing the predicate AND rebuilding it is no better.

    Any `re.compile(...)` in this module is a second source of truth for what a
    fenced block is, and the failure it enables is silent — the probe agrees with
    itself and disagrees with the product.
    """
    compiles = [
        node
        for node in ast.walk(_classify_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "compile"
    ]
    assert compiles == [], "probe/classify.py calls .compile() — it must import, not rebuild"


def test_the_classifier_module_contains_no_backtick_literal() -> None:
    """A fence spelled out in this module is a regex in prose.

    The moment a backtick appears in a string here, someone is one edit away from
    counting fences by hand instead of asking main.CODE_BLOCK_RE. The rule is
    cheap to keep and the failure it prevents is R7 again.
    """
    offenders = [
        node.value
        for node in ast.walk(_classify_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and BACKTICK in node.value
    ]
    assert offenders == [], f"probe/classify.py contains backtick literals: {offenders!r}"


def test_the_classifier_agrees_with_the_production_predicate() -> None:
    """Delegation asserted structurally above, and behaviourally here."""
    import main

    reply_with_code = f"Thought: do it\n\n{FENCE}python\nprint(1)\n{FENCE}\n"
    reply_without = "Answer: I can't help with that."

    assert classify.classify(reply_with_code) == classify.CODE
    assert classify.classify(reply_without) == classify.DIRECT
    assert bool(main.extract_last_python_block(reply_with_code)) is True
    assert bool(main.extract_last_python_block(reply_without)) is False


def test_a_two_fence_reply_classifies_direct_and_says_so_in_its_fence_count() -> None:
    """E7, and it is the single most contaminating trial shape in the design.

    Measured at tests/test_source_seam.py:533-548: with TWO fenced blocks the
    closing fence of the first pairs with the opening fence of the second, so
    CODE_BLOCK_RE.findall() returns [''] — falsy — and the turn classifies
    DIRECT. The model refused NOTHING. Without the fence count recorded beside
    the classification, such a trial is indistinguishable from a refusal: it
    inflates the secondary refusal rate and, worse, it lands in the DIRECT rate
    the gate is decided on.

    THE COUNT IS NOT WHAT IT LOOKS LIKE, and this test exists mainly to pin
    that. `len(findall())` on a two-block reply is 1, not 2 — the list is [''],
    ONE match whose captured group is empty (measured 2026-08-08, in the image).
    So the discriminator is not "count >= 2". It is:

        DIRECT and fence_matches == 0  ->  a genuinely unfenced reply
        DIRECT and fence_matches >= 1  ->  the two-block trap, refusing nothing
        CODE   and fence_matches >= 1  ->  ordinary compliance

    An earlier draft of this test asserted `>= 2` and would have passed only
    against a harness that counted fences some other way — which is R7 arriving
    through the test rather than through the harness.
    """
    two_blocks = f"{FENCE}params\nx=1\n{FENCE}\n\n{FENCE}python\nprint(x)\n{FENCE}\n"

    assert classify.classify(two_blocks) == classify.DIRECT
    assert classify.fence_matches(two_blocks) == 1, (
        "a two-block reply must be visible as DIRECT-with-a-match in the record, "
        "or it is silently counted as a refusal"
    )
    assert classify.fence_matches(f"{FENCE}python\nprint(1)\n{FENCE}") == 1
    assert classify.fence_matches("no fences here") == 0
    assert classify.is_fence_trap(two_blocks) is True
    assert classify.is_fence_trap("Answer: I cannot help with that.") is False


# ------------------------------------------------------------------------------
# 2. V0 IS main.SYSTEM_PROMPT, byte for byte
# ------------------------------------------------------------------------------


def test_variant_v0_is_the_production_prompt_object_itself() -> None:
    """A baseline measured against a transcribed copy is not a baseline.

    Identity rather than equality: `is` cannot be satisfied by a copy that
    happens to match today and drifts tomorrow, which is exactly the failure
    mode — a transcription is correct on the day it is made.
    """
    import main

    assert variants.V0 is main.SYSTEM_PROMPT
    assert variants.VARIANTS["V0"] is main.SYSTEM_PROMPT


def test_the_variant_registry_holds_no_transcription_of_the_prompt() -> None:
    """Every variant is DERIVED from V0, so none of them can silently diverge.

    V1 and V2 are drafts owned by T3/T4; what is asserted here is only that they
    are built out of the live prompt rather than pasted beside it.
    """
    for name, text in variants.VARIANTS.items():
        if name == "V0":
            continue
        assert variants.V0[:200] in text, (
            f"variant {name} does not contain V0's opening — it looks transcribed "
            "rather than derived"
        )


def test_no_variant_introduces_a_second_fenced_block() -> None:
    """N9, and it is asserted on the harness for the same reason CI asserts it on main.py.

    tests/test_source_seam.py:547 pins SYSTEM_PROMPT at exactly one fenced block.
    A probe variant that adds a second one measures a prompt the product could
    never ship, and demonstrates by example the two-block form that routes a turn
    silently to DIRECT.
    """
    for name, text in variants.VARIANTS.items():
        assert text.count(FENCE) == 2, (
            f"variant {name} contains {text.count(FENCE) // 2} fenced blocks; "
            "new prompt material must be indented and unfenced (N9)"
        )


# ------------------------------------------------------------------------------
# 3. The control set covers all three required kinds
# ------------------------------------------------------------------------------


def test_the_control_set_covers_all_three_required_kinds() -> None:
    """AC-CONTROL item 1, asserted rather than eyeballed.

    D5 requires a conversational, an opinion and a general-knowledge prompt. The
    regression they guard against has no error message, no log line and no test;
    this assertion is the only thing that notices if a kind is dropped during a
    budget cut.
    """
    kinds = {task.kind for task in tasks.CONTROL_SET}
    assert kinds == {"conversational", "opinion", "general_knowledge"}, (
        f"control set covers {sorted(kinds)}; AC-CONTROL requires all three kinds"
    )


def test_the_control_set_is_not_empty_and_every_prompt_is_distinct() -> None:
    """The vacuity half of the criterion above: a set of zero prompts has every kind."""
    assert tasks.CONTROL_SET, "the control set is EMPTY — every kind assertion above is vacuous"
    texts = [task.text for task in tasks.CONTROL_SET]
    assert len(set(texts)) == len(texts), "duplicate control prompts inflate N without adding power"


def test_the_control_floor_survives_a_budget_cut() -> None:
    """spec.md 4: cuts take the NUMBER of control prompts, floor 3, never N below 20."""
    assert len(tasks.CONTROL_SET) >= 3
    for task in tasks.CONTROL_SET:
        assert task.n >= 20, f"control prompt {task.id} plans N={task.n}, below the floor of 20"


def test_the_task_set_carries_the_three_measurement_cells_with_their_planned_n() -> None:
    """The Ns are spec.md 4's, and they are here so a cut is visible in a diff."""
    assert tasks.TASKS["target"].n == 30
    assert tasks.TASKS["off_example"].n == 20
    assert tasks.TASKS["tool_reachable"].n == 20
    assert "gmail" in tasks.TASKS["target"].text


def test_every_task_id_is_unique_across_the_task_and_control_sets() -> None:
    """Trial records are keyed by (variant, task, index); a collision loses data silently."""
    ids = [task.id for task in tasks.ALL_TASKS]
    assert len(set(ids)) == len(ids), f"duplicate task ids: {ids}"


# ------------------------------------------------------------------------------
# 4. Record schema completeness
# ------------------------------------------------------------------------------

# Spelled out here rather than imported from probe/. Importing the module's own
# field list would assert that the module agrees with itself, which is not a
# criterion. This list is spec.md T1's, transcribed once, on purpose.
REQUIRED_RECORD_FIELDS = frozenset(
    {
        "variant_id",
        "task_id",
        "task_text",
        "reply",
        "classification",
        "fence_matches",
        "trial_index",
        "model_tag",
        "model_digest",
        "host",
        "harness_commit",
        "main_commit",
        "timestamp",
    }
)


def test_a_trial_record_carries_every_required_field(fake_client: FakeChatClient) -> None:
    """AC-MEASURE item 1 and item 4, plus E7 and O3.

    A field missing here is a column that cannot be reconstructed afterwards: the
    run is over, the container is gone, and the model has moved on.
    """
    provenance = run_probe.collect_provenance(fake_client, host="http://ollama:11434")
    record = run_probe.run_trial(
        fake_client,
        variant_id="V0",
        task=tasks.TASKS["target"],
        trial_index=0,
        provenance=provenance,
    )

    missing = REQUIRED_RECORD_FIELDS - set(record)
    assert missing == set(), f"trial record is missing required fields: {sorted(missing)}"


def test_a_trial_record_stores_the_task_and_the_reply_verbatim() -> None:
    """O3. Refusal PHRASING is the only signal that separates M-a from M-b when
    rates are ambiguous, and it exists only if it was stored at the time."""
    reply = "Answer: I can't help you with accessing your personal email account."
    client = FakeChatClient(replies=[reply])
    provenance = run_probe.collect_provenance(client, host="http://ollama:11434")

    record = run_probe.run_trial(
        client,
        variant_id="V0",
        task=tasks.TASKS["target"],
        trial_index=0,
        provenance=provenance,
    )

    assert record["reply"] == reply
    assert record["task_text"] == tasks.TASKS["target"].text
    assert record["classification"] == classify.DIRECT
    assert record["fence_matches"] == 0


def test_a_trial_record_round_trips_through_json(fake_client: FakeChatClient) -> None:
    """The records are written as JSONL to stdout; a value json cannot serialise
    is a trial lost at the moment it is most expensive to repeat."""
    provenance = run_probe.collect_provenance(fake_client, host="http://ollama:11434")
    record = run_probe.run_trial(
        fake_client,
        variant_id="V0",
        task=tasks.TASKS["target"],
        trial_index=3,
        provenance=provenance,
    )

    assert json.loads(json.dumps(record)) == record
    assert record["trial_index"] == 3


def test_each_trial_sends_a_fresh_two_message_conversation(fake_client: FakeChatClient) -> None:
    """The turn shape is the one that produced the reported refusal (spec.md 2.4).

    System + ONE user message, no recall block, no accumulated history. Trial N+1
    must not see trial N's exchange, or the cell measures a conversation rather
    than a first turn.
    """
    provenance = run_probe.collect_provenance(fake_client, host="http://ollama:11434")
    for index in range(3):
        run_probe.run_trial(
            fake_client,
            variant_id="V0",
            task=tasks.TASKS["target"],
            trial_index=index,
            provenance=provenance,
        )

    assert len(fake_client.chat_calls) == 3
    for messages in fake_client.chat_calls:
        assert [msg["role"] for msg in messages] == ["system", "user"]
        assert messages[0]["content"] is variants.V0
        assert messages[1]["content"] == tasks.TASKS["target"].text


def test_the_harness_passes_no_sampling_options_to_the_model() -> None:
    """N10, asserted by AST over probe/, because this is easy to add and invisible once added.

    main.stream_llm() (main.py:209-221) passes no `options=`, so the probe
    inherits production sampling BY CONSTRUCTION. Pinning temperature or setting
    a seed would measure a different distribution from the one that produced the
    reported refusal — a cleaner number about the wrong thing.
    """
    forbidden = {"temperature", "seed", "top_p", "top_k", "num_predict"}
    for path in sorted((_ROOT / "probe").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            names = {kw.arg for kw in node.keywords if kw.arg}
            assert "options" not in names, f"{path.name} passes options= to a call (N10)"
            pinned = sorted(names & forbidden)
            assert not pinned, f"{path.name} pins sampling: {pinned}"


def test_the_probe_calls_the_production_streamer() -> None:
    """The probe must go through main.stream_llm, not build its own client.chat call.

    Rolling its own is how `options=` gets added later without anyone noticing,
    and how the probe's request shape drifts from the product's.
    """
    source = (_ROOT / "probe" / "run_probe.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "main":
            imported |= {alias.name for alias in node.names}
    assert "stream_llm" in imported, "probe/run_probe.py must drive main.stream_llm()"


# ------------------------------------------------------------------------------
# 5. The vacuity guard
# ------------------------------------------------------------------------------


def test_the_aggregator_raises_on_an_empty_record_set() -> None:
    """The vacuity guard, in the style tests/test_source_seam.py:304-331 established.

    An aggregator that reports 0/0 as 0% turns "the file was empty", "the glob
    matched nothing" and "the model never refused" into the same line of output —
    and the last of those is a finding while the first two are bugs. This
    repository has been burned twice in two days by parsers that silently matched
    nothing: tests/test_launcher_source.py's whitespace tokenizer (2026-08-07)
    and the ci.yml regexes that test_the_ci_yml_parsers_are_not_vacuous now
    guards. So emptiness raises. It does not report.
    """
    with pytest.raises(ValueError, match="empty"):
        aggregate.summarise([])


def test_the_aggregator_raises_when_no_record_matches_the_requested_cell() -> None:
    """The subtler half: the file is non-empty, the CELL is empty.

    This is the shape that survives review, because the output looks populated —
    every other cell has numbers in it and the missing one reads as a clean zero.
    """
    records = [_record(variant_id="V0", task_id="target", classification=classify.CODE)]
    with pytest.raises(ValueError, match="empty"):
        aggregate.summarise(records, variant_id="V2", task_id="target")


def test_the_aggregator_counts_direct_and_code_from_the_recorded_classification() -> None:
    records = [
        _record(variant_id="V0", task_id="target", classification=classify.CODE),
        _record(variant_id="V0", task_id="target", classification=classify.CODE),
        _record(variant_id="V0", task_id="target", classification=classify.DIRECT),
    ]
    cell = aggregate.summarise(records, variant_id="V0", task_id="target")

    assert cell.n == 3
    assert cell.code == 2
    assert cell.direct == 1
    assert cell.direct_rate == pytest.approx(1 / 3)


def test_the_aggregator_reports_a_wilson_interval_that_does_not_collapse_at_zero() -> None:
    """A clean 0/30 is not zero, and the report must not let it read as zero.

    By the rule of three the 95% upper bound on 0/30 is about 10%, which is one
    turn in ten — entirely consistent with a user having seen one refusal. An
    aggregator that prints `0.0%` and stops invites exactly the over-reading that
    verification-T3.md 6 warns about.
    """
    records = [
        _record(variant_id="V0", task_id="target", classification=classify.CODE) for _ in range(30)
    ]
    cell = aggregate.summarise(records, variant_id="V0", task_id="target")

    low, high = cell.wilson_95
    assert cell.direct_rate == 0.0
    assert low == pytest.approx(0.0, abs=1e-9)
    assert 0.05 < high < 0.15, f"Wilson upper bound on 0/30 is {high}, which is not credible"


def test_the_aggregator_surfaces_the_two_fence_contamination_count() -> None:
    """E7 carried through from the record into the report.

    A DIRECT-classified trial with two fences refused nothing. If the aggregate
    cannot say how many of those it counted, the gated rate is unauditable.
    """
    records = [
        _record(variant_id="V0", task_id="target", classification=classify.CODE, fence_matches=1),
        _record(variant_id="V0", task_id="target", classification=classify.DIRECT, fence_matches=1),
        _record(variant_id="V0", task_id="target", classification=classify.DIRECT, fence_matches=0),
    ]
    cell = aggregate.summarise(records, variant_id="V0", task_id="target")

    assert cell.direct == 2
    assert cell.fence_trap == 1, "a DIRECT trial with a fence match refused nothing"
    assert cell.direct_unfenced == 1


def test_the_aggregator_rejects_a_record_missing_a_required_field() -> None:
    """A truncated final line — the shape a crash actually produces — must not
    be averaged into the cell as if it were a trial."""
    broken = _record(variant_id="V0", task_id="target", classification=classify.CODE)
    del broken["classification"]
    with pytest.raises(ValueError, match="classification"):
        aggregate.summarise([broken], variant_id="V0", task_id="target")


# ------------------------------------------------------------------------------
# Resumability, and the siting that keeps CI green
# ------------------------------------------------------------------------------


def test_completed_keys_are_read_back_so_a_crash_costs_one_cell_not_a_night() -> None:
    """At 20-90 s per trial on a CPU-only sidecar, a 220-trial baseline is hours.

    Re-running from zero after a crash is the difference between a lost cell and
    a lost evening, and the key has to include the trial index or a resumed run
    silently repeats work it already has.
    """
    lines = [
        json.dumps(_record(variant_id="V0", task_id="target", trial_index=0)),
        json.dumps(_record(variant_id="V0", task_id="target", trial_index=1)),
        json.dumps(_record(variant_id="V0", task_id="off_example", trial_index=0)),
    ]
    keys = run_probe.completed_keys(lines)

    assert ("V0", "target", 0) in keys
    assert ("V0", "target", 1) in keys
    assert ("V0", "off_example", 0) in keys
    assert ("V0", "target", 2) not in keys


def test_a_truncated_final_line_does_not_abort_the_resume() -> None:
    """A crash mid-write leaves half a line. That is the normal case, not an edge one."""
    lines = [
        json.dumps(_record(variant_id="V0", task_id="target", trial_index=0)),
        '{"variant_id": "V0", "task_id": "targ',
    ]
    assert run_probe.completed_keys(lines) == {("V0", "target", 0)}


def test_the_probe_package_is_outside_pytest_collection() -> None:
    """R16, and it is the reason `probe/` is not a subdirectory of `tests/`.

    ci.yml asserts `skipped == 0`. A model-dependent test under `tests/` would
    skip on a runner with no Ollama (red) or block waiting for one (worse).
    """
    ini = (_ROOT / "pytest.ini").read_text(encoding="utf-8")
    testpaths = [
        line.split("=", 1)[1].strip() for line in ini.splitlines() if line.startswith("testpaths")
    ]
    assert testpaths, "parsed an EMPTY testpaths out of pytest.ini — the parse matched nothing"
    assert testpaths[0] == "tests"
    assert "probe" not in testpaths[0]


def test_this_file_carries_no_importorskip_and_no_marker() -> None:
    """A test that can skip is a test that can be absent without anyone noticing.

    ci.yml asserts `skipped == 0` precisely so that "it passed" and "it ran" are
    the same claim; this file keeps its own end of that bargain.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr != "importorskip", "tests/test_probe.py must not skip"
        if isinstance(node, ast.Attribute) and node.attr == "mark":
            raise AssertionError("tests/test_probe.py must carry no markers")


def test_the_probe_package_is_not_copied_into_the_image() -> None:
    """The harness is a measuring instrument, not a runtime dependency.

    tests/test_source_seam.py asserts set EQUALITY between the Dockerfile COPY
    set and ci.yml's hash-checked set, so adding `probe/` here would break that
    pair — and would ship a directory the product never imports.
    """
    dockerfile = (_ROOT / "Dockerfile").read_text(encoding="utf-8")
    copy_lines = [line for line in dockerfile.splitlines() if line.startswith("COPY ")]
    assert copy_lines, "parsed an EMPTY COPY set out of the Dockerfile"
    assert not any("probe" in line for line in copy_lines)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


def _record(
    *,
    variant_id: str = "V0",
    task_id: str = "target",
    classification: str = "CODE",
    fence_matches: int = 1,
    trial_index: int = 0,
) -> dict:
    """A record shaped like the real thing, built here so the tests do not need a client."""
    return {
        "variant_id": variant_id,
        "task_id": task_id,
        "task_text": "…",
        "reply": "…",
        "classification": classification,
        "fence_matches": fence_matches,
        "trial_index": trial_index,
        "model_tag": "llama3.1:8b",
        "model_digest": "deadbeef",
        "host": "http://ollama:11434",
        "harness_commit": "0ef5c86",
        "main_commit": "0ef5c86",
        "timestamp": "2026-08-08T00:00:00+00:00",
    }
