# ==============================================================================
#  CodeRunner.AI  ::  Declared parameters — grammar, collection, literal safety
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-INPUT-001
#  Purpose : The model declares a value it needs with a `# @param` comment inside
#            the Python fence it already emits; CodeRunner asks the user for it
#            and injects it as a Python LITERAL in a prelude assembled at
#            execution time. This module owns every decision in that sentence:
#            the grammar, the parser, type coercion, the prompt strings, the
#            prelude renderer, the `from __future__` splice point and the
#            redaction helper. main.py owns only the wiring (spec.md 5.3).
#
#  IMPORTS : stdlib ONLY — no rich, no ollama, no httpx, no pymilvus, no numpy.
#            Same reason as memory.py:12: this module is gated at 100% and its
#            suite must run on a bare interpreter with nothing but pytest.
#
#  THE ONE THING TO GET RIGHT is `_literal()`. Measured 2026-08-06, with
#  value = 'Seoul"; import os; os.system("id"); x="':
#
#      f'city = "{value}"'   -> rc 0, stdout begins `uid=501(kurapa) …`
#      f'city = {value!r}'   -> rc 0, stdout `39 'Seoul"; …'`
#
#  BOTH EXIT 0. Both print. The difference is two characters inside an f-string
#  that reads correctly either way, and no test asserting `result.ok` can tell
#  them apart — which is why AC-INJ asserts the ROUND-TRIPPED VALUE, and why
#  `_literal()` is the only place in this module that turns a user value into
#  source text. There is deliberately no second path a raw value could take.
# ==============================================================================

from __future__ import annotations

import ast
import math
import re
from collections.abc import Callable, Iterable, MutableMapping, Sequence
from dataclasses import dataclass

# ------------------------------------------------------------------------------
# Grammar
# ------------------------------------------------------------------------------

TYPE_STR = "str"
TYPE_INT = "int"
TYPE_FLOAT = "float"
# Suppressed inline rather than through a per-file ignore in ruff.toml: S105 is
# exactly the check you want live in the module that handles secrets, so it is
# silenced on the two lines that demonstrably are not credentials, and nowhere
# else in this file.
TYPE_SECRET = "secret"  # noqa: S105 — a declared type token, not a password

#: `secret` is a TYPE rather than a separate flag for two reasons (spec.md 3.1):
#: one token is easier for an 8B model to hit than two, and it makes the
#: sensitive case impossible to express half-way.
DECLARED_TYPES = (TYPE_STR, TYPE_INT, TYPE_FLOAT, TYPE_SECRET)

#: The declaration lives INSIDE the python fence, and that is measured, not
#: preferred. A ```params``` block placed before the ```python``` block makes
#: `CODE_BLOCK_RE.findall()` (main.py:414) return `['']` — the closing fence of
#: the first block pairs with the opening fence of the second — so
#: `extract_last_python_block()` yields the empty string, `if not code:` at
#: main.py:826 is TRUE, and the turn silently takes the "No code produced"
#: branch. Nothing anywhere reports an error (spec.md M2, N5).
#:
#: Matched line-by-line rather than through `ast`: these are comments, which
#: `ast.parse` discards outright, and reaching for the tokeniser to recover them
#: is more machinery than a line scan deserves (plan.md T1).
#:
#: Both quote styles are accepted although spec.md 3.1 writes only `"…"`. That
#: widens acceptance without introducing an ambiguous parse, and R1 — the model
#: failing to emit the syntax — is the highest-probability failure in this SPEC.
_DECLARATION_RE = re.compile(
    r"""
    ^[ \t]*\#[ \t]*@param[ \t]+
    (?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*
    :[ \t]*(?P<type>[A-Za-z]+)[ \t]*
    =[ \t]*(?P<quote>["'])(?P<prompt>.*?)(?P=quote)[ \t]*$
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Declaration:
    """One `# @param name: type = "prompt"` line the model emitted."""

    name: str
    type: str
    prompt: str


def parse_declarations(code: str) -> list[Declaration]:
    """Every well-formed declaration in ``code``, in order, deduplicated by name.

    A malformed line is SKIPPED, never fatal (O4). The failure then surfaces as a
    `NameError` from the script, which the self-correction loop at
    main.py:872-884 already handles — whereas abandoning the turn would hand the
    user nothing at all for a comment the model got slightly wrong.

    First occurrence wins on a repeated name, so the value the user is asked for
    matches the prompt text they were shown first.
    """
    found: list[Declaration] = []
    seen: set[str] = set()
    for line in code.splitlines():
        match = _DECLARATION_RE.match(line)
        if match is None:
            continue
        declared_type = match.group("type").casefold()
        if declared_type not in DECLARED_TYPES:
            continue
        prompt = match.group("prompt").strip()
        if not prompt:
            continue  # present but useless; O4 treats it as malformed
        name = match.group("name")
        if name in seen:
            continue
        seen.add(name)
        found.append(Declaration(name=name, type=declared_type, prompt=prompt))
    return found


def pending_declarations(
    declarations: Sequence[Declaration], values: MutableMapping[str, object]
) -> list[Declaration]:
    """The declarations still needing a value — the whole of E4, in one line.

    Collection happens ONCE PER TURN. On attempts 2 and 3 (main.py:792) the
    model re-emits the same declarations, and asking again would mean typing an
    API key three times to watch a script fail three times. The principle is not
    new here: main.py:762-764 already states it for embeddings.
    """
    return [decl for decl in declarations if decl.name not in values]


# ------------------------------------------------------------------------------
# Collection
# ------------------------------------------------------------------------------


def _coerce(decl: Declaration, raw: str) -> tuple[bool, object]:
    """Parse one raw answer into the declared type. ``(ok, value)``; never raises.

    Strings are kept EXACTLY as typed, unstripped: a leading or trailing space
    can be part of a path or a token, and silently trimming it would produce a
    value the user cannot see is wrong.

    Non-finite floats are rejected rather than accepted, and that is not
    pedantry: ``repr(float("inf"))`` is ``inf``, which is a bare name in the
    prelude and a `NameError` in the script — a parse that succeeds and then
    fails at a distance.
    """
    if decl.type in (TYPE_STR, TYPE_SECRET):
        return True, raw
    text = raw.strip()
    if decl.type == TYPE_INT:
        try:
            return True, int(text)
        except ValueError:
            return False, None
    try:
        value = float(text)
    except ValueError:
        return False, None
    if not math.isfinite(value):
        return False, None
    return True, value


def _read(ask: Callable[[Declaration, bool], str], decl: Declaration, retry: bool) -> str:
    """Ask once, treating a closed stdin as a declined value.

    An `EOFError` here would escape `agentic_turn()` and take the REPL down —
    main.py:1016-1023 catches ollama, httpx and KeyboardInterrupt, not this.
    A declined value is already a defined state (spec.md 3.4): the empty string,
    injected as ``''``, after which the script fails on its own terms.
    """
    try:
        return ask(decl, retry)
    except EOFError:
        return ""


def collect_values(
    declarations: Sequence[Declaration],
    ask: Callable[[Declaration, bool], str],
    values: MutableMapping[str, object],
) -> None:
    """Fill ``values`` for every declaration, asking through ``ask``.

    ``ask(declaration, retry)`` returns the raw text the user typed. Taking it
    as a callable — the same shape `handle_memory_command()` takes `emit`
    (memory.py:451) — is what keeps `input()`, `getpass` and Rich out of a
    module gated at 100%, and keeps main.py's share to wiring.

    E5: an unparseable `int`/`float` is re-prompted EXACTLY ONCE, then injected
    as the literal `None` so the script fails normally into the self-correction
    loop. Looping until the user gets it right would trap them in a turn they
    cannot leave except by Ctrl+C.
    """
    for decl in declarations:
        if decl.name in values:
            continue
        ok, value = _coerce(decl, _read(ask, decl, False))
        if not ok:
            ok, value = _coerce(decl, _read(ask, decl, True))
        values[decl.name] = value if ok else None


# ------------------------------------------------------------------------------
# Prompt strings
# ------------------------------------------------------------------------------

_PROMPT_COLOUR = "\033[1;36m"
_PROMPT_RESET = "\033[0m"
_PROMPT_TAIL = " ➜ "

#: A fixed mask, not one sized to the value: the length of a secret is itself
#: information, and O2 asks for a mask rather than a redaction of the real text.
SECRET_MASK = "●●●●●●"  # noqa: S105 — the mask shown INSTEAD of a value

#: Replaces a secret wherever it is found in stdout or stderr (E6).
REDACTION_MARKER = "[redacted]"


def _question(decl: Declaration, retry: bool) -> str:
    prefix = "not a number, once more — " if retry else ""
    return f"{prefix}{decl.prompt} [{decl.name}]"


def plain_prompt(decl: Declaration, retry: bool = False) -> str:
    """The `input()` prompt, with every colour escape bracketed for readline.

    The reasoning at main.py:960-973 applies here verbatim: readline counts every
    unbracketed prompt byte as a visible column, computes every redraw from a
    wrong origin, and corrupts the line the moment the user presses Up. The
    prompt renders perfectly until then, which is what makes the bug worth
    restating rather than assuming.
    """
    return (
        "\001"
        + _PROMPT_COLOUR
        + "\002"
        + _question(decl, retry)
        + "\001"
        + _PROMPT_RESET
        + "\002"
        + _PROMPT_TAIL
    )


def secret_prompt(decl: Declaration, retry: bool = False) -> str:
    """The `getpass.getpass()` prompt — PLAIN, and deliberately inconsistent.

    `getpass` is not readline. It writes the prompt string raw to the terminal,
    so `\\001` and `\\002` would be emitted as literal SOH/STX control bytes
    rather than interpreted, and the colour escapes would then be counted by
    nothing at all. Reusing `plain_prompt()` here would be the tidy thing and
    the wrong one.

    The asymmetry is what invites a later "unify the two prompt paths" cleanup,
    so the OTHER reason is recorded at the call site in main.py and in N3:
    `_install_history()` (main.py:930-957) wires readline and registers an
    `atexit` writer, so any line read through `input()` enters the history buffer
    and is written to CODERUNNER_HISTORY — which compose pins to
    /home/runner/.coderunner/history on the volume that survives `--rm`
    (docker-compose.yml:107). A secret typed at an `input()` prompt would be
    persisted in plaintext by a mechanism NO capture policy in this SPEC
    inspects. `getpass` does not use readline and so does not do this.
    """
    return _question(decl, retry) + _PROMPT_TAIL


def announcement(declarations: Sequence[Declaration]) -> str:
    """The one status line that opens the collection block (spec.md 3.3)."""
    total = len(declarations)
    noun = "value" if total == 1 else "values"
    secrets = sum(1 for decl in declarations if decl.type == TYPE_SECRET)
    if not secrets:
        return f"This script needs {total} {noun}."
    marked = "one of them" if secrets == 1 else f"{secrets} of them"
    return f"This script needs {total} {noun}, {marked} marked secret."


def confirmations(
    declarations: Sequence[Declaration], values: MutableMapping[str, object]
) -> list[str]:
    """One line per collected value, naming it without disclosing a secret (O2).

    Non-secret values go through the same `_literal()` the prelude uses, so a
    trailing space picked up from a paste is visible here rather than diagnosed
    later from the script's behaviour. It is emphatically NOT the prelude: N2
    forbids rendering that for any value, sensitive or not.
    """
    lines: list[str] = []
    for decl in declarations:
        if decl.type == TYPE_SECRET:
            lines.append(f"{decl.name} = {SECRET_MASK}")
        else:
            lines.append(f"{decl.name} = {_literal(values.get(decl.name))}")
    return lines


# ------------------------------------------------------------------------------
# The prelude — the one place a user value becomes source text
# ------------------------------------------------------------------------------


def _literal(value: object) -> str:
    """Render ``value`` as a Python literal. THE ONLY EMISSION SITE IN THIS FILE.

    One function, one call to `repr()`, so there is exactly one line for AC-INJ
    to protect and no path through this module that a raw value could take. The
    unsafe version of the prelude — `f'{name} = "{value}"'` — is one character
    away, reads correctly, runs the script successfully, and executes whatever
    the user typed. A reviewer reads both as "put the city in the script".

    `repr()` and not a hand-built quoted literal, and not a sanitiser: the
    measurement at the head of this file shows the hostile value arriving
    INTACT, all 39 characters of it, as a usable string. Safety here is not
    bought by mangling the input, so a later "just strip quotes and semicolons"
    defence would be both weaker and lossier.
    """
    return repr(value)


def render_prelude(
    declarations: Sequence[Declaration], values: MutableMapping[str, object]
) -> str:
    """One assignment per declared value; the empty string when there are none.

    Takes the declarations rather than the value dict alone so that ONLY names
    this attempt declared reach the script. The turn's cache outlives a single
    attempt (E4) and may hold a name the corrected block no longer mentions;
    emitting it anyway would be harmless but untrue to what was asked for.
    """
    lines = [
        f"{decl.name} = {_literal(values[decl.name])}"
        for decl in declarations
        if decl.name in values
    ]
    return "\n".join(lines)


def _future_end_line(code: str) -> int:
    """Last line of a leading ``from __future__`` import; 0 when there is none.

    R4, measured 2026-08-06: a file whose first statement is an assignment and
    whose second is `from __future__ import annotations` fails outright with
    "from __future__ imports must occur at the beginning of the file". THIS SPEC
    CREATES THAT HAZARD — `SCRIPT_HEADER` (main.py:422-431) is comments only,
    and comments are not statements, so prepending a prelude is the first thing
    this program has ever put in front of the model's code.

    `ast` rather than a line scan, and only here: AC-FUTURE requires that
    comments, blank lines and a leading docstring do not defeat the detection,
    and reimplementing a docstring scanner by hand to avoid one stdlib call is
    the wrong trade. Code that does not parse is a script that was going to fail
    anyway; the prelude then goes in front, where it adds no new error.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0
    end = 0
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            end = max(end, node.end_lineno or 0)
    return end


def splice_prelude(code: str, prelude: str) -> str:
    """Insert ``prelude`` into ``code`` at the only legal point.

    Called from `run_python()` and nowhere else, which is the whole design
    (plan.md 2.1). Assembling the combined text inside the executor means there
    is NO VARIABLE IN `agentic_turn()`'s SCOPE holding a user value alongside
    code — so the injected value's absence from solution memory is a fact about
    the program's shape rather than a filter somebody has to maintain (U3, N4).
    """
    if not prelude:
        return code
    line = _future_end_line(code)
    if line == 0:
        return prelude + "\n" + code
    lines = code.splitlines(keepends=True)
    head = "".join(lines[:line])
    if not head.endswith("\n"):
        head += "\n"
    return head + prelude + "\n" + "".join(lines[line:])


# ------------------------------------------------------------------------------
# Redaction
# ------------------------------------------------------------------------------


def secret_values(
    declarations: Sequence[Declaration], values: MutableMapping[str, object]
) -> list[str]:
    """Every collected `secret` value, longest first.

    Longest first is load-bearing when one secret contains another: replacing
    the shorter one first splits the longer one and leaves half of it on screen.
    """
    found: set[str] = set()
    for decl in declarations:
        if decl.type != TYPE_SECRET:
            continue
        value = values.get(decl.name)
        if isinstance(value, str) and value:
            found.add(value)
    return sorted(found, key=len, reverse=True)


def redact(text: str, secrets: Iterable[str]) -> str:
    """Replace every secret in ``text`` by exact substring match (E6).

    WHAT THIS CANNOT DO, said here rather than discovered later. Substring
    redaction removes what it can find. It does not find a value the script
    TRANSFORMED before printing: base64, a hash, `token[:8]`, a key spliced into
    a percent-encoded URL. `sensitive_excluded` therefore REDUCES the exposure of
    secrets in captured stdout; it does not eliminate it, and any documentation
    saying "secrets are not stored" would be false. Users for whom that residual
    matters have the `never` policy, which is why `never` is offered rather than
    being treated as the paranoid option (spec.md 3.6, plan.md R5).
    """
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTION_MARKER)
    return text
