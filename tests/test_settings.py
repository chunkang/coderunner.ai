# ==============================================================================
#  CodeRunner.AI  ::  settings.py — the capture policy, and every way it degrades
# ------------------------------------------------------------------------------
#  Project : SPEC-INPUT-001, task T10
#  Covers  : AC-DEGRADE (every row of spec.md 4.4, driven separately) and
#            AC-SETTINGS (first run asks once; precedence is unambiguous).
#
#  settings.py imports stdlib only, so this whole file runs on BARE PYTEST.
#
#  THE ONE THING TO READ FIRST: the fallback is `never` and the recommended
#  default is `sensitive_excluded`. Those being DIFFERENT VALUES is deliberate,
#  and it will read as a bug — which is why it is asserted here rather than left
#  in a comment. A file we cannot parse is exactly the file that might have said
#  `never`.
# ==============================================================================

from __future__ import annotations

import json
from pathlib import Path

import pytest

import settings

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


class Recorder:
    """Collects emitted lines so "exactly one status line" can be asserted."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, line: str) -> None:
        self.lines.append(line)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@pytest.fixture()
def settings_path(tmp_path: Path) -> Path:
    return tmp_path / "settings.json"


def write(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    write(path, json.dumps(payload))


# ------------------------------------------------------------------------------
# AC-SETTINGS — a well-formed file
# ------------------------------------------------------------------------------


@pytest.mark.parametrize("policy", settings.POLICIES)
def test_a_valid_file_is_read_and_named_as_the_provenance(
    settings_path: Path, policy: str
) -> None:
    write_json(settings_path, {"schema_version": 1, settings.POLICY_KEY: policy})
    resolved = settings.resolve_policy(path=settings_path, environ={})

    assert resolved.value == policy
    assert resolved.provenance == settings.PROV_FILE
    assert resolved.message is None


def test_an_absent_file_is_not_a_fault_and_says_nothing(settings_path: Path) -> None:
    """It is the first-run path, not a degradation. The caller asks the user."""
    resolved = settings.resolve_policy(path=settings_path, environ={})

    assert resolved.provenance == settings.PROV_ABSENT
    assert resolved.message is None
    assert resolved.value == settings.FALLBACK_POLICY  # safe until the user chooses
    assert not settings_path.exists()


def test_unknown_extra_keys_are_ignored_silently(settings_path: Path) -> None:
    write_json(
        settings_path,
        {"schema_version": 1, settings.POLICY_KEY: "always", "future_key": 7},
    )
    resolved = settings.resolve_policy(path=settings_path, environ={})

    assert resolved.value == "always"
    assert resolved.message is None


def test_a_key_shadowing_an_environment_variable_is_ignored_with_one_line(
    settings_path: Path,
) -> None:
    """N6: settings.json is not a configuration file. tech.md 4 remains the
    description of how CodeRunner is configured."""
    write_json(
        settings_path,
        {
            "schema_version": 1,
            settings.POLICY_KEY: "always",
            "CODERUNNER_TIMEOUT": 900,
        },
    )
    resolved = settings.resolve_policy(path=settings_path, environ={})

    assert resolved.value == "always"  # the file still works
    assert resolved.message is not None
    assert "CODERUNNER_TIMEOUT" in resolved.message


def test_the_eleven_environment_variables_are_all_guarded() -> None:
    assert len(settings.ENVIRONMENT_KEYS) == 11


# ------------------------------------------------------------------------------
# AC-DEGRADE — every unusable condition, driven separately
# ------------------------------------------------------------------------------


def test_a_truncated_file_degrades_to_never_in_one_line_without_rewriting_it(
    settings_path: Path,
) -> None:
    """The scenario named in AC-DEGRADE: valid-looking, missing its closing
    brace, which is what a hand edit or an interrupted write produces."""
    body = '{ "schema_version": 1, "param_capture_policy": "sensitive_excluded"'
    write(settings_path, body)

    resolved = settings.resolve_policy(path=settings_path, environ={})

    assert resolved.value == settings.POLICY_NEVER
    assert resolved.provenance == settings.PROV_FALLBACK
    assert resolved.message is not None
    # Not rewritten: it may be a typo in a deliberate edit, and overwriting it
    # destroys the user's intent along with their mistake.
    assert settings_path.read_text(encoding="utf-8") == body


@pytest.mark.parametrize("payload", [[], "x", None, 7])
def test_valid_json_that_is_not_an_object_degrades_to_never(
    settings_path: Path, payload: object
) -> None:
    write_json(settings_path, payload)
    resolved = settings.resolve_policy(path=settings_path, environ={})

    assert resolved.value == settings.POLICY_NEVER
    assert resolved.message is not None


@pytest.mark.parametrize("policy", ["capture_everything", "", None, 3])
def test_an_unrecognised_policy_value_degrades_to_never_and_names_it(
    settings_path: Path, policy: object
) -> None:
    write_json(settings_path, {"schema_version": 1, settings.POLICY_KEY: policy})
    resolved = settings.resolve_policy(path=settings_path, environ={})

    assert resolved.value == settings.POLICY_NEVER
    assert resolved.message is not None
    assert repr(policy) in resolved.message


def test_a_newer_schema_version_degrades_to_never(settings_path: Path) -> None:
    """Written by a build that knew something this one does not."""
    write_json(
        settings_path,
        {"schema_version": settings.SCHEMA_VERSION + 1, settings.POLICY_KEY: "always"},
    )
    resolved = settings.resolve_policy(path=settings_path, environ={})

    assert resolved.value == settings.POLICY_NEVER
    assert resolved.message is not None


def test_a_non_integer_schema_version_degrades_to_never(settings_path: Path) -> None:
    write_json(settings_path, {"schema_version": "1", settings.POLICY_KEY: "always"})
    assert settings.resolve_policy(path=settings_path, environ={}).value == settings.POLICY_NEVER


def test_a_missing_schema_version_is_read_as_the_current_one(settings_path: Path) -> None:
    write_json(settings_path, {settings.POLICY_KEY: "always"})
    assert settings.resolve_policy(path=settings_path, environ={}).value == "always"


def test_an_unreadable_file_degrades_to_never(tmp_path: Path) -> None:
    """The `PermissionError` / `OSError` row of spec.md 4.4.

    Driven with a directory in the file's place rather than with `chmod(0)`,
    deliberately: a permission-based test is defeated by root, which is who this
    suite runs as in some containers, and a `skipif` guarding it would then
    silently fire — while CI asserts `skipped == 0` precisely to catch that.
    The branch reached is the same one.
    """
    target = tmp_path / "settings.json"
    target.mkdir()
    resolved = settings.resolve_policy(path=target, environ={})

    assert resolved.value == settings.POLICY_NEVER
    assert resolved.provenance == settings.PROV_FALLBACK
    assert resolved.message is not None


def test_every_degraded_condition_produces_exactly_one_line(settings_path: Path) -> None:
    """U4: exactly one, never a list. The Policy field is singular for this."""
    write(settings_path, "{ oops")
    session = settings.PolicySession()
    emit, warn = Recorder(), Recorder()

    settings.ensure_policy(session, None, emit, warn, path=settings_path, environ={})

    assert len(warn.lines) == 1
    assert emit.lines == []


def test_the_fallback_and_the_recommended_default_are_different_values() -> None:
    """Asserted rather than commented, because it reads as a bug.

    `sensitive_excluded` is what a user is OFFERED when asked. `never` is what an
    unusable file falls back to. A choice made in answer to a question carries
    information; a fallback carries none, and must assume the strictest thing the
    missing information could have said.
    """
    assert settings.DEFAULT_POLICY == settings.POLICY_SENSITIVE
    assert settings.FALLBACK_POLICY == settings.POLICY_NEVER
    assert settings.DEFAULT_POLICY != settings.FALLBACK_POLICY


# ------------------------------------------------------------------------------
# S3 / O1 — the environment override
# ------------------------------------------------------------------------------


@pytest.mark.parametrize("policy", settings.POLICIES)
def test_a_recognised_environment_override_wins_over_the_file(
    settings_path: Path, policy: str
) -> None:
    write_json(settings_path, {"schema_version": 1, settings.POLICY_KEY: "never"})
    resolved = settings.resolve_policy(
        path=settings_path, environ={settings.ENV_OVERRIDE: f"  {policy} "}
    )

    assert resolved.value == policy
    assert resolved.provenance == settings.PROV_ENVIRONMENT


def test_an_unrecognised_override_is_ignored_rather_than_obeyed(
    settings_path: Path,
) -> None:
    """A typo must not silently disable capture."""
    write_json(settings_path, {"schema_version": 1, settings.POLICY_KEY: "always"})
    resolved = settings.resolve_policy(
        path=settings_path, environ={settings.ENV_OVERRIDE: "sensitive"}
    )

    assert resolved.value == "always"
    assert resolved.provenance == settings.PROV_FILE
    assert resolved.message is not None
    assert "sensitive" in resolved.message


def test_an_unrecognised_override_does_not_add_a_second_line_to_a_broken_file(
    settings_path: Path,
) -> None:
    """U4's "exactly one" survives two faults at once: the line that explains
    the OUTCOME wins, and the note about the ignored override is dropped."""
    write(settings_path, "{ oops")
    resolved = settings.resolve_policy(
        path=settings_path, environ={settings.ENV_OVERRIDE: "sensitive"}
    )

    assert resolved.value == settings.POLICY_NEVER
    assert "not valid JSON" in (resolved.message or "")


def test_an_empty_override_is_treated_as_unset(settings_path: Path) -> None:
    write_json(settings_path, {"schema_version": 1, settings.POLICY_KEY: "always"})
    resolved = settings.resolve_policy(
        path=settings_path, environ={settings.ENV_OVERRIDE: "   "}
    )
    assert resolved.provenance == settings.PROV_FILE


def test_the_real_environment_and_the_real_path_are_the_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercises the `path is None` / `environ is None` arms without reading the
    developer's own home directory."""
    target = tmp_path / "settings.json"
    write_json(target, {"schema_version": 1, settings.POLICY_KEY: "always"})
    monkeypatch.setattr(settings, "SETTINGS_PATH", target)
    monkeypatch.delenv(settings.ENV_OVERRIDE, raising=False)

    assert settings.resolve_policy().value == "always"

    monkeypatch.setenv(settings.ENV_OVERRIDE, settings.POLICY_NEVER)
    assert settings.resolve_policy().provenance == settings.PROV_ENVIRONMENT


# ------------------------------------------------------------------------------
# Saving, and S4 — a write failure must be distinguishable from a decision
# ------------------------------------------------------------------------------


def test_saving_writes_the_versioned_schema(settings_path: Path) -> None:
    assert settings.save_policy(settings.POLICY_ALWAYS, path=settings_path) is True
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        settings.POLICY_KEY: settings.POLICY_ALWAYS,
    }


def test_saving_creates_the_directory_it_needs(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "deeper" / "settings.json"
    assert settings.save_policy(settings.POLICY_NEVER, path=target) is True
    assert target.exists()


def test_a_failed_save_returns_false_rather_than_raising(tmp_path: Path) -> None:
    """Dockerfile:36-46 makes a volume seeded by a CURRENT image writable, but
    Docker seeds ownership only into an EMPTY volume at first mount: a
    coderunner_app_data created by an older image stays root-owned forever."""
    blocked = tmp_path / "a_file"
    blocked.write_text("not a directory", encoding="utf-8")
    assert settings.save_policy(settings.POLICY_NEVER, path=blocked / "settings.json") is False


def test_the_default_save_location_is_the_module_constant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", target)
    assert settings.save_policy(settings.POLICY_NEVER) is True
    assert target.exists()


# ------------------------------------------------------------------------------
# AC-SETTINGS — the first-run question
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("1", settings.POLICY_SENSITIVE),
        ("2", settings.POLICY_NEVER),
        ("3", settings.POLICY_ALWAYS),
        (" 2 ", settings.POLICY_NEVER),
        ("", settings.DEFAULT_POLICY),  # the documented [1] default
        ("banana", settings.DEFAULT_POLICY),
    ],
)
def test_the_first_run_answer_is_persisted_and_never_asked_again(
    settings_path: Path, answer: str, expected: str
) -> None:
    session = settings.PolicySession()
    emit, warn = Recorder(), Recorder()
    asked: list[str] = []

    def ask(prompt: str) -> str:
        asked.append(prompt)
        return answer

    first = settings.ensure_policy(
        session, ask, emit, warn, path=settings_path, environ={}
    )
    assert first.value == expected
    assert first.provenance == settings.PROV_FILE
    assert warn.lines == []
    assert emit.lines == list(settings.FIRST_RUN_LINES)
    assert json.loads(settings_path.read_text(encoding="utf-8"))[settings.POLICY_KEY] == expected

    # Same session: cached, no second question.
    settings.ensure_policy(session, ask, emit, warn, path=settings_path, environ={})
    assert len(asked) == 1

    # Next launch: the file answers, so the question is not asked again either.
    settings.ensure_policy(
        settings.PolicySession(), ask, emit, warn, path=settings_path, environ={}
    )
    assert len(asked) == 1


def test_a_non_interactive_session_is_not_asked_and_writes_nothing(
    settings_path: Path,
) -> None:
    """A piped session or a test. `ask is None` is how main.py reports that."""
    emit, warn = Recorder(), Recorder()
    resolved = settings.ensure_policy(
        settings.PolicySession(), None, emit, warn, path=settings_path, environ={}
    )

    assert resolved.value == settings.POLICY_NEVER
    assert resolved.provenance == settings.PROV_FALLBACK
    assert len(warn.lines) == 1
    assert not settings_path.exists()


def test_a_closed_stdin_at_the_question_takes_the_documented_default(
    settings_path: Path,
) -> None:
    def ask(prompt: str) -> str:
        raise EOFError

    resolved = settings.ensure_policy(
        settings.PolicySession(), ask, Recorder(), Recorder(),
        path=settings_path, environ={},
    )
    assert resolved.value == settings.DEFAULT_POLICY


def test_a_choice_that_could_not_be_persisted_holds_for_the_session_and_says_so(
    settings_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S4. Silently accepting a choice that was never saved is the failure this
    SPEC most wants to avoid, because it looks identical to success.

    The write is failed by stubbing `save_policy` rather than by arranging a
    hostile filesystem, and that is not laziness: the file must be ABSENT for the
    question to be asked at all (a malformed file is a broken setting, not an
    absent one), and every portable way to make a write fail at a path whose
    `read_text` raises `FileNotFoundError` turns out to depend on directory
    permissions — which root defeats. `save_policy`'s own failure has its own
    test above; what is under test here is `ensure_policy`'s handling of it.
    """
    monkeypatch.setattr(settings, "save_policy", lambda policy, path=None: False)
    emit, warn = Recorder(), Recorder()

    resolved = settings.ensure_policy(
        settings.PolicySession(),
        lambda prompt: "3",
        emit,
        warn,
        path=settings_path,
        environ={},
    )

    assert resolved.value == settings.POLICY_ALWAYS  # the user's answer is honoured
    assert resolved.provenance == settings.PROV_SESSION
    assert len(warn.lines) == 1
    assert "not persisted" in warn.lines[0] or "could not be written" in warn.lines[0]


def test_the_question_is_never_asked_when_a_file_already_exists(
    settings_path: Path,
) -> None:
    """A malformed file is a BROKEN setting, not an absent one."""
    write(settings_path, "{ oops")
    asked: list[str] = []

    settings.ensure_policy(
        settings.PolicySession(),
        lambda prompt: asked.append(prompt) or "1",
        Recorder(),
        Recorder(),
        path=settings_path,
        environ={},
    )
    assert asked == []


def test_ensure_policy_defaults_to_the_module_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "settings.json"
    write_json(target, {"schema_version": 1, settings.POLICY_KEY: "always"})
    monkeypatch.setattr(settings, "SETTINGS_PATH", target)
    monkeypatch.delenv(settings.ENV_OVERRIDE, raising=False)

    resolved = settings.ensure_policy(
        settings.PolicySession(), None, Recorder(), Recorder()
    )
    assert resolved.value == "always"


def test_policy_for_choice_is_strict() -> None:
    """`/params capture xyz` must print usage, not silently set the default."""
    assert settings.policy_for_choice("1") == settings.POLICY_SENSITIVE
    assert settings.policy_for_choice("4") is None
    assert settings.policy_for_choice("") is None


# ------------------------------------------------------------------------------
# The /params command
# ------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["", "hello", "/paramsfoo", "/memory"])
def test_input_that_is_not_ours_is_not_handled(text: str) -> None:
    """Dispatch is on the first whitespace token, not on a prefix."""
    assert settings.handle_params_command(text, Recorder()) == (False, None)


def test_bare_params_reports_the_policy_and_its_provenance(settings_path: Path) -> None:
    """U5: a policy whose origin cannot be named is a policy nobody can debug —
    and the fallback and the default are different values precisely so that
    provenance is the only way to tell them apart."""
    emit = Recorder()
    current = settings.Policy(settings.POLICY_NEVER, settings.PROV_FALLBACK)

    handled, replacement = settings.handle_params_command(
        " /PARAMS ", emit, current, path=settings_path, environ={}
    )

    assert (handled, replacement) == (True, None)
    assert settings.POLICY_NEVER in emit.text
    assert settings.PROVENANCE_LABELS[settings.PROV_FALLBACK] in emit.text
    assert str(settings_path) in emit.text


def test_bare_params_resolves_the_policy_when_the_session_has_none_yet(
    settings_path: Path,
) -> None:
    """Asked before any parameterised turn, so nothing has been resolved. It must
    still report, and must NOT create the file on the way."""
    write_json(settings_path, {"schema_version": 1, settings.POLICY_KEY: "always"})
    emit = Recorder()

    settings.handle_params_command("/params", emit, None, path=settings_path, environ={})
    assert "always" in emit.text


@pytest.mark.parametrize("policy", settings.PROVENANCE_LABELS)
def test_every_provenance_has_a_label(policy: str) -> None:
    """A missing label would be a KeyError in the middle of a REPL command."""
    emit = Recorder()
    settings.handle_params_command("/params", emit, settings.Policy("x", policy), environ={})
    assert settings.PROVENANCE_LABELS[policy] in emit.text


@pytest.mark.parametrize("text", ["/params capture", "/params nonsense", "/params a b c"])
def test_a_malformed_params_command_prints_usage_and_changes_nothing(text: str) -> None:
    emit = Recorder()
    handled, replacement = settings.handle_params_command(text, emit, environ={})

    assert (handled, replacement) == (True, None)
    assert "Usage:" in emit.text


def test_an_unrecognised_capture_choice_prints_usage(settings_path: Path) -> None:
    emit = Recorder()
    handled, replacement = settings.handle_params_command(
        "/params capture 9", emit, path=settings_path, environ={}
    )

    assert (handled, replacement) == (True, None)
    assert "Usage:" in emit.text
    assert not settings_path.exists()


@pytest.mark.parametrize(
    ("choice", "expected"),
    [("1", settings.POLICY_SENSITIVE), ("2", settings.POLICY_NEVER), ("3", settings.POLICY_ALWAYS)],
)
def test_params_capture_sets_and_persists_the_policy(
    settings_path: Path, choice: str, expected: str
) -> None:
    emit = Recorder()
    handled, replacement = settings.handle_params_command(
        f"/params capture {choice}", emit, path=settings_path, environ={}
    )

    assert handled is True
    assert replacement == settings.Policy(expected, settings.PROV_FILE)
    assert json.loads(settings_path.read_text(encoding="utf-8"))[settings.POLICY_KEY] == expected


def test_params_capture_says_so_when_the_environment_will_overrule_it(
    settings_path: Path,
) -> None:
    """Saved, correct, and inert. Reporting it here is the only way anyone would
    find out — which is also why CODERUNNER_PARAM_CAPTURE is kept OUT of
    docker-compose.yml (N7)."""
    emit = Recorder()
    settings.handle_params_command(
        "/params capture 3",
        emit,
        path=settings_path,
        environ={settings.ENV_OVERRIDE: settings.POLICY_NEVER},
    )
    assert settings.ENV_OVERRIDE in emit.text


def test_params_capture_reports_a_write_it_could_not_make(tmp_path: Path) -> None:
    blocked = tmp_path / "a_file"
    blocked.write_text("not a directory", encoding="utf-8")
    emit = Recorder()

    handled, replacement = settings.handle_params_command(
        "/params capture 2", emit, path=blocked / "settings.json", environ={}
    )

    assert handled is True
    assert replacement == settings.Policy(settings.POLICY_NEVER, settings.PROV_SESSION)
    assert "session only" in emit.text


def test_params_uses_the_real_environment_and_path_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", target)
    monkeypatch.delenv(settings.ENV_OVERRIDE, raising=False)

    handled, replacement = settings.handle_params_command("/params capture 1", Recorder())

    assert handled is True
    assert replacement is not None
    assert target.exists()
