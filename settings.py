# ==============================================================================
#  CodeRunner.AI  ::  settings.json — the capture policy, its provenance, its
#                     failure modes
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-INPUT-001
#  Purpose : One user-chosen setting — how solution memory should treat a turn
#            that used declared parameters — loaded from, and persisted to,
#            /home/runner/.coderunner/settings.json. Plus the `/params` command
#            that reports and changes it.
#
#  IMPORTS : stdlib ONLY. `json` and `pathlib` are stdlib, so tech.md's "no
#            python-dotenv dependency" stays true even though its "no config
#            file" does not — see the reversal record below.
#
#  THIS FILE REVERSES A DOCUMENTED PROPERTY, and that is recorded here rather
#  than buried, because a property that can be reversed quietly is not a
#  property. tech.md:204-207 states without qualification: "All configuration is
#  environment-variable based. There is no config file, no .env loading, and no
#  python-dotenv dependency."
#
#  Why a file is right here and an environment variable is not: every one of the
#  eleven existing variables (main.py:66-71, main.py:87-96) is set by an operator
#  BEFORE the process starts. This one is chosen INTERACTIVELY, BY THE USER,
#  MID-SESSION, in answer to a question the program asks — and it must survive
#  `docker compose run --rm`. A running process cannot write an environment
#  variable the next container will see. A file on the persistent volume can.
#
#  THE FALLBACK IS `never`, AND IT IS NOT THE DEFAULT. That will read as a bug
#  to whoever maintains this, so: `sensitive_excluded` is what a user is OFFERED
#  when asked; `never` is what an unusable file falls back to. A file we cannot
#  parse is exactly the file that might have said `never`. Falling back to the
#  recommended default would mean capturing turns from a user who explicitly
#  asked that they not be captured, on the strength of a file we have just
#  admitted we could not read. A choice made in answer to a question carries
#  information; a fallback carries none, and must assume the strictest thing the
#  missing information could have said (spec.md 4.4, plan.md 2.3).
# ==============================================================================

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

# ------------------------------------------------------------------------------
# Schema and location
# ------------------------------------------------------------------------------

#: Versioned from the first line so that a future key is a migration and not a
#: guess. A file declaring a HIGHER version is not read: it was written by a
#: build that knew something this one does not.
SCHEMA_VERSION = 1

#: Inside the app_data volume mounted at docker-compose.yml:75 and named
#: coderunner_app_data at docker-compose.yml:114-115 — the only path that
#: survives the `--rm` lifecycle, already holding memory.milvus.db and history.
#: Dockerfile:36-46 creates and chowns this directory before `USER runner`, so a
#: volume seeded by a current image is writable; one created by an older image
#: stays root-owned forever, which is what S4 exists for.
SETTINGS_PATH = Path.home() / ".coderunner" / "settings.json"

POLICY_KEY = "param_capture_policy"

POLICY_SENSITIVE = "sensitive_excluded"
POLICY_NEVER = "never"
POLICY_ALWAYS = "always"
POLICIES = (POLICY_SENSITIVE, POLICY_NEVER, POLICY_ALWAYS)

#: Offered to a user who is asked; keeps solution memory working, which is the
#: whole of SPEC-MEMORY-001's value, while removing the one class of content
#: nobody intends to persist.
DEFAULT_POLICY = POLICY_SENSITIVE
#: Applied when the file cannot be trusted or the user cannot be asked. Read the
#: banner above before "fixing" the difference.
FALLBACK_POLICY = POLICY_NEVER

#: O1. Optional rather than required, and deliberately ABSENT from
#: docker-compose.yml (N7): every memory variable there is written as
#: `${VAR:-default}` (docker-compose.yml:82-104), so the variable would ALWAYS be
#: set inside the container, always with a value. By the precedence below the
#: environment then wins unconditionally, and settings.json would be written,
#: read and overruled on every launch — a file that exists, is correct, and does
#: nothing. Reachable only through an explicit `docker compose run -e`, exactly
#: as OLLAMA_HOST already is.
ENV_OVERRIDE = "CODERUNNER_PARAM_CAPTURE"

#: N6. settings.json is NOT a general configuration file. A key naming one of
#: the eleven environment variables (main.py:66-71, main.py:87-96 via
#: MemoryConfig.from_env) is ignored, with one status line. Duplicated here as
#: literals rather than imported, because importing main.py would drag rich,
#: ollama and httpx into a module whose point is to need none of them.
ENVIRONMENT_KEYS = frozenset(
    {
        "OLLAMA_HOST",
        "CODERUNNER_MODEL",
        "CODERUNNER_TIMEOUT",
        "CODERUNNER_MAX_RETRIES",
        "CODERUNNER_HISTORY",
        "CODERUNNER_MEMORY",
        "CODERUNNER_EMBED_MODEL",
        "CODERUNNER_MEMORY_DB",
        "CODERUNNER_MEMORY_TOP_K",
        "CODERUNNER_MEMORY_MIN_SIMILARITY",
        "CODERUNNER_MEMORY_MAX_RECORDS",
    }
)

# ------------------------------------------------------------------------------
# Provenance
# ------------------------------------------------------------------------------
# U5: a policy whose origin cannot be named is a policy nobody can debug — and
# the fallback and the default are DIFFERENT VALUES precisely so that provenance
# is the only way to tell a choice apart from a degradation.

PROV_ENVIRONMENT = "environment"
PROV_FILE = "file"
PROV_FALLBACK = "fallback"
PROV_SESSION = "session"
#: No file yet. The caller asks the user; until then the value is the safe one.
PROV_ABSENT = "absent"

PROVENANCE_LABELS = {
    PROV_ENVIRONMENT: f"{ENV_OVERRIDE} (environment override)",
    PROV_FILE: "settings.json",
    PROV_FALLBACK: "fallback (the file could not be used)",
    PROV_SESSION: "this session only (the file could not be written)",
    PROV_ABSENT: "not chosen yet",
}


@dataclass(frozen=True)
class Policy:
    """The effective capture policy, where it came from, and the one line to say.

    ``message`` is at most ONE line, never a list. U4 requires exactly one status
    line per fault and a turn otherwise identical to the pre-feature product
    (product.md:138); making the field singular is what stops a second message
    from being added without someone noticing the requirement.
    """

    value: str
    provenance: str
    message: str | None = None


@dataclass
class PolicySession:
    """The policy for one REPL session, resolved lazily on first use.

    Mutable and threaded through `agentic_turn()` rather than read per turn,
    because S4 makes the two cases different: a choice that was PERSISTED is
    re-read from the file next turn anyway, while a choice that could NOT be
    persisted must still hold for the rest of this session and be asked again
    next launch. Only session state can tell those apart.
    """

    policy: Policy | None = None


# ------------------------------------------------------------------------------
# Loading
# ------------------------------------------------------------------------------


def _fallback(message: str) -> Policy:
    return Policy(FALLBACK_POLICY, PROV_FALLBACK, message)


def _from_file(path: Path) -> Policy:
    """Read the file, degrading to ``never`` on every unusable condition.

    Every branch here is a row of spec.md 4.4, and none of them raises: U4
    forbids a settings fault from reaching the REPL at all.

    A MALFORMED FILE IS NEVER REWRITTEN. It may be a hand edit with a typo, and
    overwriting it destroys the user's intent along with their mistake. Degrade,
    say so, leave it alone.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Policy(FALLBACK_POLICY, PROV_ABSENT)
    except OSError as err:
        return _fallback(
            f"Could not read {path} ({err.__class__.__name__}); "
            "parameterised turns will not be stored."
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _fallback(f"{path} is not valid JSON; parameterised turns will not be stored.")

    if not isinstance(data, dict):
        return _fallback(
            f"{path} does not contain a JSON object; parameterised turns will not be stored."
        )

    version = data.get("schema_version", SCHEMA_VERSION)
    if not isinstance(version, int) or version > SCHEMA_VERSION:
        return _fallback(
            f"{path} declares schema_version {version!r}, which this build does not know; "
            "parameterised turns will not be stored."
        )

    chosen = data.get(POLICY_KEY)
    if chosen not in POLICIES:
        return _fallback(
            f"{path} carries an unrecognised {POLICY_KEY} {chosen!r}; "
            "parameterised turns will not be stored."
        )

    # Reached only on the success path, so an unusable file reports its fault
    # rather than a bookkeeping note. Unknown extra keys are ignored SILENTLY;
    # only a key shadowing one of the eleven environment variables says anything.
    shadowed = sorted(set(data) & ENVIRONMENT_KEYS)
    note = (
        f"Ignoring {', '.join(shadowed)} in {path}: settings.json is not a configuration file."
        if shadowed
        else None
    )
    return Policy(chosen, PROV_FILE, note)


def resolve_policy(
    *, path: Path | None = None, environ: Mapping[str, str] | None = None
) -> Policy:
    """Resolve the effective policy: environment -> settings.json -> fallback.

    Rule 2 of spec.md 4.3, stated now so nobody has to decide it under pressure:
    ON ANY OVERLAP THE ENVIRONMENT WINS, UNCONDITIONALLY. That preserves tech.md
    4 as the description of how CodeRunner is CONFIGURED; settings.json describes
    only what the user CHOSE.

    An override set to something unrecognised is ignored rather than obeyed —
    a typo must not silently disable capture — and it only gets a line of its
    own when the file resolution produced none, so U4's "exactly one" holds.
    """
    path = SETTINGS_PATH if path is None else path
    environ = os.environ if environ is None else environ

    note: str | None = None
    raw = environ.get(ENV_OVERRIDE, "").strip()
    if raw:
        if raw in POLICIES:
            return Policy(raw, PROV_ENVIRONMENT)
        note = (
            f"Ignoring {ENV_OVERRIDE}={raw!r}: expected one of {', '.join(POLICIES)}."
        )

    policy = _from_file(path)
    if note is not None and policy.message is None:
        return Policy(policy.value, policy.provenance, note)
    return policy


def save_policy(policy: str, *, path: Path | None = None) -> bool:
    """Persist the chosen policy. ``False`` if it could not be written.

    Returning a bool rather than raising is what makes S4 expressible: the
    session keeps the policy the user just chose, one line states that it was NOT
    persisted, and the user is asked again next launch. Silently accepting a
    choice that was never saved is the failure this SPEC most wants to avoid,
    because it looks identical to success — and on a `coderunner_app_data` volume
    created before Dockerfile:43-44 landed, it is the expected outcome.
    """
    path = SETTINGS_PATH if path is None else path
    body = {"schema_version": SCHEMA_VERSION, POLICY_KEY: policy}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


# ------------------------------------------------------------------------------
# The first-run question
# ------------------------------------------------------------------------------
# Asked LAZILY, on the first turn that declares a parameter — never at startup.
# A user who never uses this feature is never asked and settings.json is never
# created for them, so the reversal recorded in the banner costs nothing to
# anyone who does not opt in. Since introducing the file reverses a documented
# property, the smallest honest version of the reversal is one where the file
# only exists for users who used the feature that needs it.

FIRST_RUN_LINES = (
    "Before asking: how should solution memory treat parameterised turns?",
    "  1) Store the turn, but never a secret value   (recommended)",
    "  2) Never store a turn that used parameters",
    "  3) Store everything, including secrets",
)
FIRST_RUN_CHOICE_PROMPT = "Choice [1]: "

CHOICES = {"1": POLICY_SENSITIVE, "2": POLICY_NEVER, "3": POLICY_ALWAYS}

NON_INTERACTIVE_MSG = (
    "stdin is not interactive, so the capture policy cannot be chosen; "
    "parameterised turns will not be stored."
)
NOT_PERSISTED_MSG = (
    "Capture policy applies to this session only — {path} could not be written. "
    "You will be asked again next launch."
)


def policy_for_choice(raw: str) -> str | None:
    """Map ``1``/``2``/``3`` to a policy. ``None`` for anything else.

    Strict on purpose. `/params capture xyz` must print usage rather than
    silently setting the recommended policy; the first-run path applies the
    documented `[1]` default by falling back explicitly at its own call site.
    """
    return CHOICES.get(raw.strip())


def _ask_first_run(
    ask: Callable[[str], str] | None,
    emit: Callable[[str], None],
    warn: Callable[[str], None],
    path: Path,
) -> Policy:
    if ask is None:
        # A piped session or a test. The question cannot be asked, so nothing is
        # written and the conservative policy applies (spec.md 4.5).
        warn(NON_INTERACTIVE_MSG)
        return Policy(FALLBACK_POLICY, PROV_FALLBACK)

    for line in FIRST_RUN_LINES:
        emit(line)
    try:
        answer = ask(FIRST_RUN_CHOICE_PROMPT)
    except EOFError:
        answer = ""
    chosen = policy_for_choice(answer) or DEFAULT_POLICY

    if save_policy(chosen, path=path):
        return Policy(chosen, PROV_FILE)
    warn(NOT_PERSISTED_MSG.format(path=path))
    return Policy(chosen, PROV_SESSION)


def ensure_policy(
    session: PolicySession,
    ask: Callable[[str], str] | None,
    emit: Callable[[str], None],
    warn: Callable[[str], None],
    *,
    path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Policy:
    """The policy for this session, asking the user once if there is no file yet.

    ``ask`` is ``None`` when stdin is not interactive. ``emit`` prints the
    question block; ``warn`` prints the single degradation line. Two callables
    rather than one because they render differently — the question is a plain
    indented block, a degradation is a yellow status line — and because keeping
    both out of this module is what lets its whole suite run on bare pytest,
    exactly as `handle_memory_command()`'s `emit` does (memory.py:451).
    """
    if session.policy is not None:
        return session.policy

    path = SETTINGS_PATH if path is None else path
    policy = resolve_policy(path=path, environ=environ)
    if policy.message:
        warn(policy.message)
    if policy.provenance == PROV_ABSENT:
        policy = _ask_first_run(ask, emit, warn, path)

    session.policy = policy
    return policy


# ------------------------------------------------------------------------------
# The /params REPL command
# ------------------------------------------------------------------------------
# Not folded into the /memory family, despite the policy being a memory concern,
# for one mechanical reason: handle_memory_command() lives in memory.py, and
# memory.py performs NO FILE I/O today — its only Path use is construction at
# memory.py:287. Routing a settings write through it would put I/O and its
# failure branches into the module whose stated purpose (memory.py:12) is to be
# the stdlib-only, dependency-free core (spec.md 4.5, 5.1).

PARAMS_COMMAND = "/params"

_USAGE_LINES = (
    "Usage:",
    "  /params                   show the capture policy and where it came from",
    "  /params capture <1|2|3>   set and persist the policy",
    "      1) Store the turn, but never a secret value   (recommended)",
    "      2) Never store a turn that used parameters",
    "      3) Store everything, including secrets",
)


def handle_params_command(
    text: str,
    emit: Callable[[str], None],
    current: Policy | None = None,
    *,
    path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[bool, Policy | None]:
    """Handle a ``/params`` REPL command. ``(handled, replacement policy)``.

    ``True`` tells the REPL the input was consumed locally and `agentic_turn()`
    must not run, mirroring `handle_memory_command()` (memory.py:451) and the
    exit-word check beside it.

    Dispatch is on the FIRST WHITESPACE TOKEN, not on a prefix: `/paramsfoo` is a
    different word and belongs to the model, not to us.
    """
    parts = text.strip().split()
    if not parts or parts[0].casefold() != PARAMS_COMMAND:
        return False, None

    environ = os.environ if environ is None else environ
    location = SETTINGS_PATH if path is None else path

    if len(parts) == 1:
        policy = (
            current
            if current is not None
            else resolve_policy(path=location, environ=environ)
        )
        emit("Parameter capture policy")
        emit(f"  policy : {policy.value}")
        # The provenance is the useful half. Without it a policy that silently
        # fell back is indistinguishable from one the user chose.
        emit(f"  source : {PROVENANCE_LABELS[policy.provenance]}")
        emit(f"  file   : {location}")
        return True, None

    if parts[1].casefold() != "capture" or len(parts) != 3:
        for line in _USAGE_LINES:
            emit(line)
        return True, None

    chosen = policy_for_choice(parts[2])
    if chosen is None:
        emit(f"Not a policy choice: {parts[2]}")
        for line in _USAGE_LINES:
            emit(line)
        return True, None

    if not save_policy(chosen, path=location):
        emit(NOT_PERSISTED_MSG.format(path=location))
        return True, Policy(chosen, PROV_SESSION)

    emit(f"Capture policy set to {chosen}, saved to {location}.")
    if environ.get(ENV_OVERRIDE, "").strip() in POLICIES:
        # Saved, correct, and inert until the override goes away. Reporting it
        # here is the only way anyone would find out (AC-SETTINGS).
        emit(f"  note   : {ENV_OVERRIDE} is set and overrides this for the session.")
    return True, Policy(chosen, PROV_FILE)
