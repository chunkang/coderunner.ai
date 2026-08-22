# ==============================================================================
#  CodeRunner.AI  ::  probe — the task set and the control set
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-PROMPT-001, task T1  (spec.md 4, D5; plan.md R2)
#
#  THE PROMPTS ARE FIXED HERE ONCE AND QUOTED VERBATIM INTO verification-T3.md.
#  V0, V1, V2 and V3 must all see byte-identical task text or the columns of
#  that table are not comparable, which is the quiet way a before/after
#  measurement stops being one.
#
#  THE Ns ARE spec.md 4's, AND THEY ARE HERE SO A BUDGET CUT SHOWS UP IN A DIFF.
#  Target 30 (the gated cell), off-example 20, tool-reachable 20, control 30 per
#  prompt. If budget forces a cut it comes off the NUMBER of control prompts —
#  floor 3, one of each kind — and never off N below 20. Three prompts at N=30
#  is a measurement; five at N=6 is a rumour.
# ==============================================================================

from __future__ import annotations

from dataclasses import dataclass

CONVERSATIONAL = "conversational"
OPINION = "opinion"
GENERAL_KNOWLEDGE = "general_knowledge"


@dataclass(frozen=True)
class Task:
    """One task cell: a prompt, what it is for, and how many trials it gets."""

    id: str
    text: str
    kind: str
    n: int
    expect_direct: bool


# ------------------------------------------------------------------------------
# The measurement cells
# ------------------------------------------------------------------------------

TARGET = Task(
    id="target",
    # The reported request, VERBATIM, including its lower-case "gmail" and its
    # missing punctuation. This SPEC exists because of this exact string, and
    # tidying it would measure a prompt nobody sent.
    text="check my gmail for recent 7 days and let me know the interview opportunities",
    kind="target",
    n=30,
    expect_direct=False,
)

OFF_EXAMPLE = Task(
    id="off_example",
    # Network-reachable, outside the three exampled domains at main.py:146-153,
    # and involving no account and no credential. This cell is what separates a
    # routing effect from an account-shaped one: if it improves and the target
    # does not, the residue belongs to SPEC-ACCOUNT-001.
    text="how many open issues does the cpython repository have on GitHub right now?",
    kind="off_example_network",
    n=20,
    expect_direct=False,
)

TOOL_REACHABLE = Task(
    id="tool_reachable",
    # The cell that actually closes product.md 6.1 (spec.md N8). Expected to be
    # ZERO at V0: SYSTEM_PROMPT contains no occurrence of "tools" or
    # "web_search", so the model has no channel through which to learn the name.
    # A non-zero V0 here is a finding that changes the SPEC.
    text=(
        "search the web and summarise the three main criticisms people have of "
        "the uv Python package manager"
    ),
    kind="tool_reachable",
    n=20,
    expect_direct=False,
)

MEASUREMENT_TASKS: tuple[Task, ...] = (TARGET, OFF_EXAMPLE, TOOL_REACHABLE)


# ------------------------------------------------------------------------------
# The control set — these MUST route DIRECT
# ------------------------------------------------------------------------------
# spec.md S2, D5; plan.md R2. This is the only defence that exists against the
# highest-blast-radius risk in the SPEC: narrowing DIRECT is exactly what the
# reported defect needs, and it is also how the product becomes one that writes
# and executes Python to answer "how are you". That regression has no error
# message, no log line and no test.

CONTROL_SET: tuple[Task, ...] = (
    Task(
        id="c1_conversational",
        text="hey, how are you doing today?",
        kind=CONVERSATIONAL,
        n=30,
        expect_direct=True,
    ),
    Task(
        id="c2_conversational",
        text="what can you help me with?",
        kind=CONVERSATIONAL,
        n=30,
        expect_direct=True,
    ),
    Task(
        id="c3_opinion",
        text="what do you think of Python as a first programming language?",
        kind=OPINION,
        n=30,
        expect_direct=True,
    ),
    Task(
        id="c4_general_knowledge",
        # THE SHARPEST PROMPT IN THE SET, and it is here on purpose. It asks for
        # an EXAMPLE, so the model may well emit an illustrative fenced Python
        # block — at which point the product does not illustrate it, it EXECUTES
        # it. That is not the control failing; it is the control finding the
        # place where DIRECT and CODE genuinely blur, and it is the prompt most
        # likely to move when D1 narrows DIRECT.
        text="explain what a Python closure is, with a short example",
        kind=GENERAL_KNOWLEDGE,
        n=30,
        expect_direct=True,
    ),
    Task(
        id="c5_general_knowledge",
        text='who wrote the book "The Mythical Man-Month"?',
        kind=GENERAL_KNOWLEDGE,
        n=30,
        expect_direct=True,
    ),
)

ALL_TASKS: tuple[Task, ...] = MEASUREMENT_TASKS + CONTROL_SET

TASKS: dict[str, Task] = {task.id: task for task in ALL_TASKS}
