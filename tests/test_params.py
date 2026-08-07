# ==============================================================================
#  CodeRunner.AI  ::  params.py — grammar, collection, literal safety
# ------------------------------------------------------------------------------
#  Project : SPEC-INPUT-001, task T10
#  Covers  : AC-INJ (the renderer half), AC-ONCE (the caching half), AC-MASK
#            (the prompt half), AC-FUTURE, and the O4 skip-don't-abort rule.
#
#  params.py imports stdlib only, so everything here runs on BARE PYTEST with no
#  third-party package installed — the same guarantee memory.py carries, and for
#  the same reason. The end-to-end halves of AC-INJ, AC-CAP, AC-ONCE and AC-MASK,
#  which need `run_python()` and `agentic_turn()`, live in
#  tests/test_main_integration.py.
# ==============================================================================

from __future__ import annotations

from collections.abc import Sequence

import pytest

import params
from params import Declaration

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


def decl(name: str = "city", type_: str = "str", prompt: str = "Which city?") -> Declaration:
    return Declaration(name=name, type=type_, prompt=prompt)


class Asker:
    """A scripted stand-in for the user, recording every prompt it was shown."""

    def __init__(self, answers: Sequence[str], raises: BaseException | None = None) -> None:
        self.answers = list(answers)
        self.raises = raises
        self.calls: list[tuple[str, bool]] = []

    def __call__(self, declaration: Declaration, retry: bool) -> str:
        self.calls.append((declaration.name, retry))
        if self.raises is not None:
            raise self.raises
        return self.answers.pop(0) if self.answers else ""

    @property
    def count(self) -> int:
        return len(self.calls)


# ------------------------------------------------------------------------------
# The grammar
# ------------------------------------------------------------------------------


def test_a_declaration_inside_the_fence_is_parsed() -> None:
    code = '# @param city: str = "Which city?"\nprint(city)'
    assert params.parse_declarations(code) == [
        Declaration(name="city", type="str", prompt="Which city?")
    ]


@pytest.mark.parametrize("declared", ["str", "int", "float", "secret"])
def test_every_declared_type_is_accepted(declared: str) -> None:
    code = f'# @param v: {declared} = "give me v"'
    assert params.parse_declarations(code)[0].type == declared


def test_the_type_token_is_case_insensitive() -> None:
    """Widening acceptance without widening the parse: R1 is the likeliest failure."""
    assert params.parse_declarations('# @param v: SECRET = "k"')[0].type == "secret"


def test_single_quotes_are_accepted_as_well_as_double() -> None:
    """spec.md 3.1 writes only "…", but an 8B model will reach for either.

    Accepting both cannot produce an ambiguous parse — the closing quote must
    match the opening one — so it widens acceptance at no cost, and R1 says the
    model missing the syntax is the highest-probability failure in this SPEC.
    """
    assert params.parse_declarations("# @param v: str = 'give me v'")[0].prompt == "give me v"


def test_declarations_keep_their_order() -> None:
    code = (
        '# @param city: str = "Which city?"\n'
        '# @param days: int = "How many days?"\n'
        "print(city, days)"
    )
    assert [d.name for d in params.parse_declarations(code)] == ["city", "days"]


def test_a_repeated_name_keeps_the_first_occurrence() -> None:
    """The user is asked once, with the prompt text they were shown first."""
    code = '# @param city: str = "first"\n# @param city: str = "second"'
    found = params.parse_declarations(code)
    assert len(found) == 1
    assert found[0].prompt == "first"


def test_leading_indentation_and_spacing_do_not_defeat_the_match() -> None:
    code = '    #@param  city :str="Which city?"   '
    assert params.parse_declarations(code)[0].name == "city"


@pytest.mark.parametrize(
    "line",
    [
        '# @param 9city: str = "no"',  # not an identifier
        '# @param city: bytes = "no"',  # not a declared type
        '# @param city: str = ""',  # prompt present but empty
        "# @param city: str = no quotes",  # no prompt string at all
        '# @param city = "no type"',
        '# param city: str = "no at-sign"',
        'city = "not a comment at all"',
        '# @param city: str = "unterminated',
    ],
)
def test_a_malformed_declaration_is_skipped_not_fatal(line: str) -> None:
    """O4: a bad declaration must not abandon the turn.

    It becomes a `NameError` from the script instead, which the self-correction
    loop at main.py:872-884 already handles — and which the user can watch the
    model fix, rather than being handed nothing at all.
    """
    assert params.parse_declarations(line + "\nprint(1)") == []


def test_a_malformed_line_does_not_take_its_neighbours_with_it() -> None:
    code = '# @param 9bad: str = "x"\n# @param good: str = "y"'
    assert [d.name for d in params.parse_declarations(code)] == ["good"]


def test_code_with_no_declarations_yields_none() -> None:
    assert params.parse_declarations("print(42)\n# an ordinary comment") == []


# ------------------------------------------------------------------------------
# AC-ONCE — the turn's cache
# ------------------------------------------------------------------------------


def test_pending_skips_names_already_collected() -> None:
    declarations = [decl("city"), decl("days", "int", "How many?")]
    assert [d.name for d in params.pending_declarations(declarations, {"city": "Seoul"})] == [
        "days"
    ]


def test_collect_asks_once_and_reuses_the_value_on_a_retry() -> None:
    """E4: attempt 2 re-declares the same parameter and must not re-prompt.

    The obvious implementation — parse and prompt at the top of each loop
    iteration — is simpler, passes a single-attempt test, and asks the user for
    their API key three times before the turn gives up.
    """
    ask = Asker(["Seoul"])
    values: dict[str, object] = {}
    declarations = [decl("city")]

    params.collect_values(params.pending_declarations(declarations, values), ask, values)
    params.collect_values(params.pending_declarations(declarations, values), ask, values)

    assert ask.count == 1
    assert values == {"city": "Seoul"}


def test_a_name_first_seen_on_attempt_two_prompts_for_itself_only() -> None:
    ask = Asker(["Seoul", "3"])
    values: dict[str, object] = {}

    first = [decl("city")]
    params.collect_values(params.pending_declarations(first, values), ask, values)
    second = [decl("city"), decl("days", "int", "How many?")]
    params.collect_values(params.pending_declarations(second, values), ask, values)

    assert [name for name, _ in ask.calls] == ["city", "days"]
    assert values == {"city": "Seoul", "days": 3}


# ------------------------------------------------------------------------------
# Type coercion
# ------------------------------------------------------------------------------


def test_an_int_is_parsed_before_it_is_injected() -> None:
    values: dict[str, object] = {}
    params.collect_values([decl("n", "int", "How many?")], Asker([" 7 "]), values)
    assert values == {"n": 7}


def test_a_float_is_parsed_before_it_is_injected() -> None:
    values: dict[str, object] = {}
    params.collect_values([decl("x", "float", "Ratio?")], Asker(["0.5"]), values)
    assert values == {"x": 0.5}


def test_a_string_keeps_the_spaces_the_user_typed() -> None:
    """A leading or trailing space can be part of a path; trimming it silently
    would produce a value the user cannot see is wrong."""
    values: dict[str, object] = {}
    params.collect_values([decl("p")], Asker(["  /tmp/x  "]), values)
    assert values == {"p": "  /tmp/x  "}


def test_an_unparseable_number_is_reprompted_exactly_once(
) -> None:
    """E5: once, then `None`. Not until the user gets it right."""
    ask = Asker(["banana", "12"])
    values: dict[str, object] = {}
    params.collect_values([decl("n", "int", "How many?")], ask, values)

    assert ask.calls == [("n", False), ("n", True)]
    assert values == {"n": 12}


def test_two_failed_parses_inject_the_literal_none() -> None:
    """The script then fails on its own terms into the existing loop."""
    ask = Asker(["banana", "pear"])
    values: dict[str, object] = {}
    params.collect_values([decl("n", "int", "How many?")], ask, values)

    assert ask.count == 2
    assert values == {"n": None}
    assert params.render_prelude([decl("n", "int", "How many?")], values) == "n = None"


def test_an_unparseable_float_is_reprompted_then_injected_as_none() -> None:
    ask = Asker(["banana", "pear"])
    values: dict[str, object] = {}
    params.collect_values([decl("x", "float", "Ratio?")], ask, values)

    assert ask.calls == [("x", False), ("x", True)]
    assert values == {"x": None}


def test_collect_values_never_re_asks_for_a_name_it_already_holds() -> None:
    """The guard lives in collect_values as well as in pending_declarations.

    Both are on the E4 path and a caller can reasonably use either; the one that
    prompts is the one that must refuse to prompt twice.
    """
    ask = Asker(["ignored"])
    values: dict[str, object] = {"city": "Seoul"}
    params.collect_values([decl("city")], ask, values)

    assert ask.count == 0
    assert values == {"city": "Seoul"}


@pytest.mark.parametrize("typed", ["inf", "-inf", "nan"])
def test_a_non_finite_float_is_rejected(typed: str) -> None:
    """`repr(float("inf"))` is `inf` — a bare NAME in the prelude and a NameError
    in the script. A parse that succeeds and then fails at a distance."""
    values: dict[str, object] = {}
    params.collect_values([decl("x", "float", "Ratio?")], Asker([typed, typed]), values)
    assert values == {"x": None}


def test_a_declined_value_is_an_empty_string_not_a_skip() -> None:
    """spec.md 3.4: there is no "skip this parameter" state."""
    values: dict[str, object] = {}
    params.collect_values([decl("city")], Asker([""]), values)
    assert values == {"city": ""}
    assert params.render_prelude([decl("city")], values) == "city = ''"


def test_a_closed_stdin_is_a_declined_value_and_not_a_crash() -> None:
    """An EOFError here would escape agentic_turn() and take the REPL down:
    main.py:1016-1023 catches ollama, httpx and KeyboardInterrupt, not this."""
    values: dict[str, object] = {}
    params.collect_values([decl("city")], Asker([], raises=EOFError()), values)
    assert values == {"city": ""}


# ------------------------------------------------------------------------------
# AC-MASK — the two prompt paths, and why they must stay different
# ------------------------------------------------------------------------------


def test_the_plain_prompt_brackets_every_escape_for_readline() -> None:
    """The same assertion as main.py's PROMPT, and for the same reason.

    readline counts every unbracketed prompt byte as a visible column, computes
    every redraw from a wrong origin, and corrupts the line the moment the user
    presses Up. Asserting on the rendered prompt would catch none of it — it
    looks correct either way. The assertion has to be on what readline COUNTS.
    """
    import re

    prompt = params.plain_prompt(decl())
    counted = re.sub("\001[^\002]*\002", "", prompt)

    assert "\033" not in counted
    assert counted == "Which city? [city] ➜ "


def test_the_secret_prompt_carries_no_bracketing_at_all() -> None:
    """AC-MASK: `getpass` is not readline. It writes the prompt string RAW, so
    \\001 and \\002 would be emitted as literal SOH/STX control bytes rather
    than interpreted, and the colour escapes would be counted by nothing."""
    prompt = params.secret_prompt(decl("api_key", "secret", "OpenWeather API key"))

    assert "\001" not in prompt
    assert "\002" not in prompt
    assert "\033" not in prompt
    assert prompt == "OpenWeather API key [api_key] ➜ "


@pytest.mark.parametrize("render", [params.plain_prompt, params.secret_prompt])
def test_a_reprompt_says_why_it_is_asking_again(render) -> None:
    assert "not a number" in render(decl("n", "int", "How many?"), True)


# ------------------------------------------------------------------------------
# The status lines
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("types", "expected"),
    [
        (["str"], "This script needs 1 value."),
        (["str", "int"], "This script needs 2 values."),
        (["str", "secret"], "This script needs 2 values, one of them marked secret."),
        (
            ["secret", "secret", "str"],
            "This script needs 3 values, 2 of them marked secret.",
        ),
    ],
)
def test_the_batch_announcement_counts_what_it_is_about_to_ask_for(
    types: list[str], expected: str
) -> None:
    declarations = [decl(f"v{i}", declared, "p") for i, declared in enumerate(types)]
    assert params.announcement(declarations) == expected


def test_a_confirmation_line_shows_a_plain_value_and_masks_a_secret() -> None:
    declarations = [decl("city"), decl("api_key", "secret", "key")]
    values: dict[str, object] = {"city": "Seoul", "api_key": "sk-live-123"}

    lines = params.confirmations(declarations, values)

    assert lines == ["city = 'Seoul'", f"api_key = {params.SECRET_MASK}"]
    assert "sk-live-123" not in " ".join(lines)


def test_the_mask_is_a_fixed_width_not_the_length_of_the_secret() -> None:
    """The length of a secret is itself information."""
    short = params.confirmations([decl("k", "secret", "k")], {"k": "a"})
    long = params.confirmations([decl("k", "secret", "k")], {"k": "a" * 64})
    assert short == long


def test_a_confirmation_shows_a_trailing_space_that_a_paste_picked_up() -> None:
    """The prelude is never displayed (N2), so this line is the only place a
    value that arrived with invisible whitespace can be seen at all."""
    assert params.confirmations([decl("p")], {"p": "/data/x "}) == ["p = '/data/x '"]


# ------------------------------------------------------------------------------
# AC-INJ — the renderer
# ------------------------------------------------------------------------------

#: Measured 2026-08-06. Naively interpolated this EXECUTES `id`; through repr()
#: it arrives as a 39-character string. Both exit 0 (acceptance.md AC-INJ).
HOSTILE = 'Seoul"; import os; os.system("id"); x="'

#: A value needing no quote character at all: naively interpolated it yields
#: four statements where the author wrote one.
HOSTILE_NEWLINES = 'a\nimport os\nos.system("id")\nb = "'


@pytest.mark.parametrize("value", [HOSTILE, HOSTILE_NEWLINES])
def test_a_hostile_value_is_rendered_as_one_literal(value: str) -> None:
    """The renderer half of AC-INJ; the execution half is in the main suite.

    Asserted by round-tripping the literal through `eval`, not by checking for
    absence of a crash: `f'city = "{value}"'` produces source that also parses,
    also runs, and also exits 0 — it just runs something else as well.
    """
    line = params.render_prelude([decl("city")], {"city": value})
    namespace: dict[str, object] = {}
    exec(compile(line, "<prelude>", "exec"), namespace)  # noqa: S102

    assert namespace["city"] == value
    assert line.count("\n") == 0  # one assignment, not four


def test_the_hostile_value_arrives_intact_rather_than_mangled() -> None:
    """Safety here is NOT bought by sanitising the input, which is why a later
    "just strip quotes and semicolons" defence would be weaker AND lossier."""
    line = params.render_prelude([decl("city")], {"city": HOSTILE})
    namespace: dict[str, object] = {}
    exec(compile(line, "<prelude>", "exec"), namespace)  # noqa: S102
    assert len(namespace["city"]) == 39


def test_the_prelude_is_one_assignment_per_declared_value() -> None:
    declarations = [decl("city"), decl("days", "int", "How many?")]
    rendered = params.render_prelude(declarations, {"city": "Seoul", "days": 3})
    assert rendered == "city = 'Seoul'\ndays = 3"


def test_the_prelude_is_empty_when_nothing_was_declared() -> None:
    assert params.render_prelude([], {}) == ""


def test_the_prelude_carries_only_names_this_attempt_declared() -> None:
    """The turn's cache outlives one attempt and may hold a name the corrected
    block no longer mentions."""
    values: dict[str, object] = {"city": "Seoul", "days": 3}
    assert params.render_prelude([decl("city")], values) == "city = 'Seoul'"


def test_a_declaration_with_no_collected_value_emits_no_line() -> None:
    assert params.render_prelude([decl("city")], {}) == ""


# ------------------------------------------------------------------------------
# AC-FUTURE — a `from __future__` import survives the prelude
# ------------------------------------------------------------------------------
#
# Measured 2026-08-06: a file whose first statement is an assignment and whose
# second is `from __future__ import annotations` fails with
# "SyntaxError: from __future__ imports must occur at the beginning of the file".
#
# THIS SPEC CREATES THE HAZARD. SCRIPT_HEADER (main.py:422-431) is comments only,
# and comments are not statements, so a prelude is the first thing this program
# has ever put in front of the model's code. Low probability, TOTAL impact: the
# script does not run at all and the model is handed a SyntaxError for code it
# wrote correctly, then burns its remaining attempts "fixing" it.


def compiles(source: str) -> bool:
    try:
        compile(source, "<script>", "exec")
    except SyntaxError:
        return False
    return True


def test_the_prelude_lands_after_a_future_import() -> None:
    code = "from __future__ import annotations\nprint(city)"
    spliced = params.splice_prelude(code, "city = 'Seoul'")

    assert spliced.splitlines()[0] == "from __future__ import annotations"
    assert spliced.splitlines()[1] == "city = 'Seoul'"
    assert compiles(spliced)


def test_the_naive_order_really_is_a_syntax_error() -> None:
    """The measurement the guard exists for, asserted rather than remembered."""
    assert not compiles("city = 'Seoul'\nfrom __future__ import annotations\n")


def test_comments_a_docstring_and_blank_lines_do_not_defeat_the_detection() -> None:
    code = (
        "# a leading comment\n"
        "\n"
        '"""A module docstring."""\n'
        "\n"
        "from __future__ import annotations\n"
        "print(city)\n"
    )
    spliced = params.splice_prelude(code, "city = 'Seoul'")

    assert compiles(spliced)
    assert spliced.index("city = 'Seoul'") > spliced.index("from __future__")


def test_several_future_imports_are_all_cleared() -> None:
    code = (
        "from __future__ import annotations\n"
        "from __future__ import division\n"
        "print(city)\n"
    )
    assert compiles(params.splice_prelude(code, "city = 'Seoul'"))


def test_a_future_import_on_the_last_line_without_a_newline_still_works() -> None:
    spliced = params.splice_prelude("from __future__ import annotations", "city = 1")
    assert compiles(spliced)
    assert spliced == "from __future__ import annotations\ncity = 1\n"


def test_with_no_future_import_the_prelude_goes_in_front() -> None:
    assert params.splice_prelude("print(city)", "city = 'Seoul'") == "city = 'Seoul'\nprint(city)"


def test_an_empty_prelude_leaves_the_code_untouched() -> None:
    code = "from __future__ import annotations\nprint(1)"
    assert params.splice_prelude(code, "") is code


def test_code_that_does_not_parse_still_receives_its_prelude() -> None:
    """A script that was going to fail anyway; the prelude adds no new error."""
    broken = "def f(:\n    pass"
    assert params.splice_prelude(broken, "city = 1") == "city = 1\n" + broken


# ------------------------------------------------------------------------------
# Redaction
# ------------------------------------------------------------------------------


def test_secret_values_returns_only_the_secrets() -> None:
    declarations = [decl("city"), decl("api_key", "secret", "key")]
    values: dict[str, object] = {"city": "Seoul", "api_key": "sk-1"}
    assert params.secret_values(declarations, values) == ["sk-1"]


def test_secret_values_ignores_a_secret_that_was_declined_or_never_collected() -> None:
    declarations = [decl("a", "secret", "a"), decl("b", "secret", "b")]
    assert params.secret_values(declarations, {"a": ""}) == []


def test_secret_values_ignores_a_non_string_value() -> None:
    assert params.secret_values([decl("n", "secret", "n")], {"n": None}) == []


def test_secret_values_are_returned_longest_first() -> None:
    """Replacing the shorter first splits the longer one and leaves half of it."""
    declarations = [decl("a", "secret", "a"), decl("b", "secret", "b")]
    values: dict[str, object] = {"a": "abc", "b": "abcdef"}

    assert params.secret_values(declarations, values) == ["abcdef", "abc"]
    assert params.redact("abcdef", params.secret_values(declarations, values)) == (
        params.REDACTION_MARKER
    )


def test_redact_replaces_every_occurrence() -> None:
    text = "key=sk-1 and again sk-1"
    assert "sk-1" not in params.redact(text, ["sk-1"])


def test_redact_ignores_an_empty_secret() -> None:
    """Replacing the empty string would insert the marker between every
    character of the output."""
    assert params.redact("hello", [""]) == "hello"


def test_redact_leaves_text_alone_when_there_is_nothing_to_find() -> None:
    assert params.redact("hello", []) == "hello"


def test_redaction_cannot_see_a_transformed_value() -> None:
    """Asserted so the LIMIT is a tested fact rather than a caveat in prose.

    `sensitive_excluded` reduces the exposure of secrets in captured stdout; it
    does not eliminate it. A script printing `token[:8]`, a base64 encoding, a
    hash or a percent-encoded key leaks material no substring search matches.
    `never` exists for users who need the guarantee rather than the reduction —
    which is why it is offered rather than treated as the paranoid option.
    """
    secret = "sk-live-abcdef"
    assert params.redact(secret[:8], [secret]) == "sk-live-"
