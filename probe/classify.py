# ==============================================================================
#  CodeRunner.AI  ::  probe — trial classification
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-PROMPT-001, task T1  (spec.md E6, E7; plan.md R7)
#
#  THIS MODULE OWNS NO LOGIC. It is a name for two things main.py already does,
#  and its whole value is that it CANNOT drift from them.
#
#  spec.md R7: a probe carrying its own copy of the fence regex can pass while
#  the product still fails, and the measurement becomes fiction. The success
#  criterion of the measurement and the mechanism of the defect have to be the
#  same line of code. So both names below are imported from main, and
#  tests/test_probe.py asserts by AST that this file contains no .compile() call
#  and no string literal carrying a fence character.
# ==============================================================================

from __future__ import annotations

from main import CODE_BLOCK_RE, extract_last_python_block

#: The two routing protocols, named as main.py's branch names them.
CODE = "CODE"
DIRECT = "DIRECT"


def classify(reply: str) -> str:
    """Return CODE or DIRECT, using the production predicate and nothing else.

    spec.md E6: a trial is DIRECT iff extract_last_python_block() returns falsy.
    That is literally the condition at main.py:1032 which produced the reported
    behaviour, so a trial classified DIRECT here is a turn the product would
    have answered without executing anything.
    """
    return CODE if extract_last_python_block(reply) else DIRECT


def fence_matches(reply: str) -> int:
    """Return len(CODE_BLOCK_RE.findall(reply)) — spec.md E7.

    READ THE NUMBER CAREFULLY; it is not the count of blocks. Measured
    2026-08-08 inside the image, against the three shapes that matter:

        one block   -> findall returns one non-empty group   -> 1
        two blocks  -> findall returns one EMPTY group       -> 1
        no block    -> findall returns nothing               -> 0

    The two-block case is one match, not two, because the closing delimiter of
    the first block pairs with the opening delimiter of the second and the
    captured group between them is empty. The empty string is falsy, so
    extract_last_python_block() returns it, the caller's truth test fails, and
    the turn routes DIRECT while the model refused nothing at all. That is the
    trap recorded at tests/test_source_seam.py:533-548, and is_fence_trap()
    below is the only way to see it after the run is over.
    """
    return len(CODE_BLOCK_RE.findall(reply))


def is_fence_trap(reply: str) -> bool:
    """True when a reply routes DIRECT despite the model having emitted a block.

    This is the contamination check for the gated rate. A trial in this state is
    a formatting accident, not a refusal: counting it as one inflates the
    secondary refusal figure and, more seriously, moves the DIRECT rate that
    spec.md 4's pre-registered rule is decided on.
    """
    return classify(reply) == DIRECT and fence_matches(reply) > 0
