# ==============================================================================
#  CodeRunner.AI  ::  probe — prompt variants
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-PROMPT-001, task T1
#
#  V0 IS main.SYSTEM_PROMPT. It is imported, never transcribed, and
#  tests/test_probe.py asserts OBJECT IDENTITY rather than equality — because a
#  transcription is correct on the day it is made and wrong on some later day
#  nobody is watching, and a baseline measured against a stale copy is not a
#  baseline of anything.
#
#  V1 and V2 are DERIVED from V0 by exact-substring surgery, so they cannot
#  drift either: if main.py's wording moves, the anchor below stops matching and
#  this module raises at import rather than silently measuring a prompt that no
#  longer exists.
#
#  WHOSE WORDING IS THIS. The V1 and V2 texts here are the HARNESS's drafts, not
#  ratified prompt copy. plan.md T4 owns what ships, and it may replace either
#  wording outright. What T1 owes is an instrument that can carry three
#  variants; what it must not do is pre-empt the edit the gate has not yet
#  authorised (spec.md S5).
#
#  N9 APPLIES TO EVERYTHING HERE. New prompt material is INDENTED AND UNFENCED.
#  tests/test_source_seam.py:547 pins SYSTEM_PROMPT at exactly one fenced block,
#  and a second one makes CODE_BLOCK_RE.findall() return a single empty match
#  that routes the turn silently to DIRECT. A prompt demonstrating that form
#  teaches the model the defect this SPEC exists to remove.
# ==============================================================================

from __future__ import annotations

import textwrap

from main import SYSTEM_PROMPT

#: The baseline. The production object itself, not a copy of it.
V0 = SYSTEM_PROMPT


def _replace_once(text: str, old: str, new: str, *, what: str) -> str:
    """Substitute exactly one occurrence, or refuse to build the variant.

    A silent no-op here is the worst available failure: the run completes, the
    numbers look plausible, and V1 was V0 all along. So a missing or ambiguous
    anchor raises at import time, where it costs a traceback instead of a night
    of trials.
    """
    found = text.count(old)
    if found != 1:
        raise ValueError(
            f"variant {what}: anchor matched {found} times, expected exactly 1. "
            "main.py's SYSTEM_PROMPT has moved and this variant is now a fiction."
        )
    return text.replace(old, new)


# ------------------------------------------------------------------------------
# V1 — the routing contradiction repaired (spec.md D1)
# ------------------------------------------------------------------------------
# main.py:126-129's "or needs live data you don't have" is the clause that
# routes an actionable, network-reachable task to DIRECT. It contradicts the
# network permission at :143-145 and the tie-break at :174, and what settles the
# contradiction in practice is the example set at :146-153 rather than any rule.
#
# The repair makes DIRECT mean "no computation and no fetch would answer this"
# instead of "you personally do not hold this right now" — which is true of
# every network task the prompt elsewhere encourages.

_V1_ANCHOR = (
    "question is conversational, opinion, general knowledge, or needs live data\n"
    "you don't have), follow the DIRECT protocol."
)

_V1_REPAIR = (
    "question is conversational, opinion, or general knowledge, AND no\n"
    "computation and no fetch would answer it), follow the DIRECT protocol.\n"
    "Not holding the data yourself is NOT a reason to choose DIRECT: if the\n"
    "answer is reachable over the network, or computable, that is CODE."
)

V1 = _replace_once(V0, _V1_ANCHOR, _V1_REPAIR, what="V1")


# ------------------------------------------------------------------------------
# V2 — V1 plus the capability section (spec.md D2, D3)
# ------------------------------------------------------------------------------
# Inserted BELOW the @param passage (N3), so SPEC-KEYCHAIN-001 N2's already-stale
# line citation does not move a third time.
#
# Every statement carries a worked example (U3, N4), because the prompt's
# EFFECTIVE capability surface is measured to be its example set rather than its
# rules — which is the whole diagnosis in spec.md HISTORY.
#
# The signature below is tools.py:77 as it actually is: web_search(query,
# limit=5) returning a list of dicts keyed title / snippet / url / source
# (tools.py:95 shows the shape on the error path). Advertising a signature the
# module does not have would be a new instance of the defect being repaired.

_INSERT_AFTER = (
    "     Types: str, int, float, secret. Use secret for keys and passwords —\n"
    "     it is masked when typed. Never emit a second fenced block for these."
)

_CAPABILITY_SECTION = textwrap.dedent(
    """
       - A helper module is copied next to your script in every sandbox, so
         "from tools import web_search" resolves with no PYTHONPATH set. It is
         stdlib-only and returns a list of dicts keyed title, snippet, url,
         source. Reach for it when no specific API fits the question:

             from tools import web_search
             hits = web_search("uv python package manager criticism", limit=5)
             for hit in hits:
                 print(hit["title"], hit["url"])

       - Anything reachable over the network is in scope, not only the three
         sites exampled above. A public JSON API, an HTML page, or a search
         through the helper are all ordinary CODE work:

             import requests
             r = requests.get("https://api.github.com/repos/python/cpython",
                              timeout=10, headers={"User-Agent": "coderunner"})
             print(r.json()["open_issues_count"])
    """
).rstrip()

V2 = _replace_once(V1, _INSERT_AFTER, _INSERT_AFTER + "\n" + _CAPABILITY_SECTION, what="V2")


# ------------------------------------------------------------------------------
# V3 — V0 plus the capability section, WITHOUT the routing repair
# ------------------------------------------------------------------------------
# spec.md A5 / S6, plan.md T3b. CONDITIONAL: owed only if the gate records M-b.
#
# Under M-b the routing repair does not ship but the advertisement still does —
# advertising a helper has no safety component. What ships is then exactly this
# string, and V0, V1 and V2 are none of them it. Without V3 the SPEC would ship,
# on its own most-likely-adverse branch, the one variant it never measured.

V3 = _replace_once(V0, _INSERT_AFTER, _INSERT_AFTER + "\n" + _CAPABILITY_SECTION, what="V3")


VARIANTS: dict[str, str] = {"V0": V0, "V1": V1, "V2": V2, "V3": V3}
