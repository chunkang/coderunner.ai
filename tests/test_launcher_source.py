# ==============================================================================
#  CodeRunner.AI  ::  source-level assertions about the launcher
# ------------------------------------------------------------------------------
#  Project : SPEC-KEYCHAIN-001, task T8
#  Covers  : the checkable halves of AC-TRANSPORT (E2, N3, N4), AC-BOOT (E1, E6,
#            N6), AC-LAUNCH (S6, N8), AC-DOCTOR (U5, E7, N5) and AC-EXPOSE's
#            documentation clause (U6).
#
#  WHY SOURCE LEVEL, AND WHY A NEW FILE. The launcher has no test harness and is
#  not getting one: `spec.md` 8 item 9 scopes that out and says why — a framework
#  introduced as a rider on a LOW-priority feature is a framework nobody
#  maintains. What this file does instead is assert the four properties whose
#  failure is INVISIBLE and TOTAL:
#
#    * `--env-from-file` CORRUPTS the credential (measured 2026-08-07: `$bc`
#      expanded away, three characters lost, rc 0, no warning). It surfaces as a
#      401 from a remote service, nowhere near its cause.
#    * `-e NAME=value` publishes the credential to the host process table for the
#      whole session, because coderunner:260-263 deliberately does not `exec`.
#    * an unguarded empty-array expansion under `set -u` KILLS THE LAUNCHER on
#      bash 3.2.57, which is stock macOS `/bin/bash` — for every user who has
#      NOT used this feature, which on day one is everybody.
#    * a stored value printed by `--doctor` goes into whatever bug report the
#      user pastes it into.
#
#  Everything here reads text on disk or runs `bash -n`. Nothing imports the
#  application, so this file runs on bare pytest, exactly like
#  tests/test_source_seam.py.
# ==============================================================================

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_LAUNCHER = _ROOT / "coderunner"


def source() -> str:
    return _LAUNCHER.read_text(encoding="utf-8")


def code(text: str | None = None) -> str:
    """The launcher with whole-line comments removed.

    The four constructions this file forbids are forbidden BY NAME in the
    launcher's own comments, because a reader who does not know why
    `--env-from-file` is absent will add it. A raw-text check would make that
    warning unwritable — which is the reason tests/test_source_seam.py:73 gives
    for checking `order_by` on the syntax tree rather than on the source, applied
    to a language that has no syntax tree here.

    Whole lines only: every comment in this launcher is a whole line, and
    stripping a trailing `#` correctly would mean parsing shell quoting.
    """
    lines = (source() if text is None else text).splitlines()
    return "\n".join(
        line for line in lines if not line.lstrip().startswith("#") or line.startswith("#!")
    )


def words(text: str) -> list[str]:
    return text.split()


def doctor_branch(text: str) -> str:
    start = text.index('if [[ "${1:-}" == "--doctor" ]]')
    return text[start : text.index("# --- 8. run ephemerally", start)]


def field_labels(text: str) -> list[str]:
    """Every `--doctor` field label, deduplicated in order.

    Derived from the printf FORMATS rather than counted as printf STATEMENTS:
    the embed-model row is printed from two arms of one `if`, so a statement
    count says 13 where the product prints 12 rows. `product.md:123` documents
    rows, and a documented count that is wrong is worse than no count.
    """
    labels: list[str] = []
    for match in re.finditer(r"printf '  (\S[^:]*?)\s*: ", text):
        label = match.group(1)
        if label not in labels:
            labels.append(label)
    return labels


# ------------------------------------------------------------------------------
# AC-TRANSPORT — the value arrives intact, and not through the flag that corrupts
# ------------------------------------------------------------------------------


def test_the_launcher_never_reaches_for_env_from_file() -> None:
    """N3. Measured 2026-08-07 with `sk-a$bc de#f "g" \\h`:

        compose run --env-from-file FILE   ->   sk-a de#f "g" \\h

    Compose parses the file with dotenv semantics and expands `$bc` to nothing.
    Three characters gone. No error, no warning, exit status 0.

    This is the option someone reaches for while thinking carefully about the
    process table, and the argument for it is correct as far as it goes. A
    transport that silently alters a credential is worse than one that exposes
    it, because exposure is detectable and corruption is diagnosed at the far end
    of a network call — where the self-correction loop (main.py:925) then hands
    the model a stderr dump and it rewrites a script that was already right.
    """
    executable = code()
    assert "--env-from-file" not in executable
    assert "env-file" not in executable


def test_every_dash_e_in_the_launcher_carries_a_bare_name() -> None:
    """N4. Measured: `-e NAME=value` puts the value in `ps -Ao args` for the
    lifetime of the `docker compose` process, which under coderunner:260-263 is
    the whole session — that block does not `exec`, deliberately, so the EXIT
    trap still runs. On Linux `/proc/<pid>/cmdline` is world-readable by default,
    so this hands the credential to every local user.

    Asserted over every `-e` in the file rather than over the one line that
    builds the array, so that a second, later `-e` cannot be added the wrong way.
    """
    # Matched with a regex rather than by splitting on whitespace, because the
    # form this feature actually uses is `RUN_ENV+=(-e "NAME")` — where a naive
    # split yields the single token `RUN_ENV+=(-e` and the check silently
    # inspects nothing at all. A test that cannot see the construction it forbids
    # is worse than no test, because it is believed.
    following = re.findall(r"(?:^|[\s(])-e\s+(\S+)", code(), flags=re.MULTILINE)
    assert following, "the fixture is vacuous: no -e was found in the launcher"

    offences = [token for token in following if "=" in token]
    assert offences == [], f"a -e in the launcher carries a value: {offences}"


def test_the_environment_variable_name_is_the_one_keychain_py_reads() -> None:
    """The two halves of this name live in different languages, and nothing
    negotiates it. A rename on either side is invisible until a user is prompted
    for a value they stored."""
    assert 'KEYCHAIN_ENV_PREFIX="CODERUNNER_SECRET_"' in source()
    assert "CODERUNNER_SECRET_" in (_ROOT / "keychain.py").read_text(encoding="utf-8")


def test_the_value_is_exported_rather_than_interpolated_into_the_argument() -> None:
    """The mechanism behind `-e NAME`: compose reads the value from the
    launcher's own exported environment, so it never enters an argument list."""
    text = source()
    assert re.search(r'export "\$\{KEYCHAIN_ENV_PREFIX\}\$\{upper\}=\$value"', text)
    assert re.search(r'RUN_ENV\+=\(-e "\$\{KEYCHAIN_ENV_PREFIX\}\$\{upper\}"\)', text)


# ------------------------------------------------------------------------------
# AC-LAUNCH — a user with no stored secrets launches exactly as before
# ------------------------------------------------------------------------------


def test_the_run_env_array_is_never_expanded_unguarded() -> None:
    """N8, and the population it protects is the wrong way round from every other
    risk in this SPEC: it does not break users of the feature, it breaks users
    who have NEVER TOUCHED IT.

    Measured 2026-08-07:

        $ /bin/bash --version
        GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)
        $ /bin/bash -c 'set -Eeuo pipefail; A=(); printf "%s\\n" "${A[@]}"'
        /bin/bash: A[@]: unbound variable
        rc=1

    `coderunner:1` is `#!/usr/bin/env bash` and `coderunner:10` is
    `set -Eeuo pipefail`. On a stock Mac that resolves to /bin/bash 3.2.57 and an
    empty array expansion is FATAL. On a machine with Homebrew bash 5 — which is
    most developer machines — it is not, which is exactly what makes it dangerous:
    it passes every check the author runs and breaks on the first clean Mac.
    """
    text = source()
    assert "RUN_ENV+=" in text, "the fixture is vacuous: there is no RUN_ENV array"

    unguarded = [
        line
        for line in text.splitlines()
        if '"${RUN_ENV[@]}"' in line and "${RUN_ENV[@]+" not in line
    ]
    assert unguarded == [], f"unguarded empty-array expansion: {unguarded}"
    assert '${RUN_ENV[@]+"${RUN_ENV[@]}"}' in text


def test_the_launcher_uses_no_construction_bash_3_2_lacks() -> None:
    """The other half of the same risk, and the one a source check can see.

    `${var^^}` (uppercase), `declare -A` (associative arrays), `mapfile` and
    `readarray` are all bash 4. Each of them fails on stock macOS and works on
    the machine of anybody likely to add one.
    """
    executable = code()
    for construction in ("^^}", "declare -A", "mapfile", "readarray", "local -n"):
        assert construction not in executable, (
            f"{construction!r} needs bash 4; /bin/bash on stock macOS is 3.2.57"
        )


def test_the_launcher_parses_under_bash() -> None:
    """`bash -n` on the whole file. Cheap, and it is the only thing standing
    between a typo in forty new lines of shell and a user's first launch."""
    completed = subprocess.run(
        ["bash", "-n", str(_LAUNCHER)], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_the_guarded_expansion_survives_an_empty_array_under_set_u() -> None:
    """The guard itself, driven rather than read — with the exact `set` line the
    launcher uses (coderunner:10) and the exact expansion it contains.

    Extracted from the launcher rather than retyped, so that editing the
    expansion to the unguarded form fails here instead of on a stock Mac.
    """
    text = source()
    expansion = next(
        line.strip() for line in text.splitlines() if '${RUN_ENV[@]+"${RUN_ENV[@]}"}' in line
    )
    assert "run --rm" in expansion, "the guard has drifted off the compose run line"

    script = (
        'set -Eeuo pipefail\nRUN_ENV=()\nset -- ${RUN_ENV[@]+"${RUN_ENV[@]}"}\necho "argc=$#"\n'
    )
    completed = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "argc=0"


# ------------------------------------------------------------------------------
# AC-BOOT — storing a password does not install Docker
# ------------------------------------------------------------------------------

SUBCOMMANDS = ("--set-secret", "--forget-secret", "--list-secrets")


@pytest.mark.parametrize("flag", SUBCOMMANDS)
def test_the_secret_subcommands_are_dispatched_before_the_bootstrap(flag: str) -> None:
    """N6, asserted on POSITION, because position is the whole requirement.

    `product.md` 6.4 records the mistake this must not repeat, in the project's
    own words: the `--doctor` branch sits at coderunner:233, AFTER the entire
    bootstrap, so `./coderunner --doctor` on a clean machine installs Docker,
    starts the daemon, builds the image, starts the Ollama sidecar and pulls a
    multi-GB model BEFORE printing a single diagnostic line.

    `--set-secret` is a command a user runs once, in a hurry, to put a password
    somewhere. It needs no daemon, no image, no compose, no Ollama and no model.
    """
    text = source()
    dispatch = text.index(f"{flag})")
    bootstrap = text.index(': >"$LOG_FILE"')
    compose_run = text.index("run --rm --name")

    assert dispatch < bootstrap, f"{flag} is dispatched after the bootstrap begins"
    assert dispatch < compose_run
    assert text.index('OS="$(uname -s)"') < dispatch, f"{flag} is dispatched before $OS is known"


def test_no_subcommand_falls_through_to_compose_run() -> None:
    """They must EXIT. coderunner:263 forwards `"$@"` into a main.py that parses
    nothing and discards it silently, so falling through means the flag becomes
    an invisible no-op and the user's password is never stored."""
    text = source()
    dispatch = text[text.index("--set-secret)") : text.index(': >"$LOG_FILE"')]
    assert dispatch.count("exit 0") >= len(SUBCOMMANDS)


def test_the_store_path_never_puts_the_value_in_an_argument() -> None:
    """E6. `security add-generic-password -h` states it outright:

        Use of the -p or -w options is insecure. Specify -w as the last option
        to be prompted.

    Given LAST and with NO VALUE, `security` prompts and masks the value itself,
    so it never appears in an argv, a shell variable, or the launcher's
    environment. `secret-tool store` reads stdin and has the same property. This
    is a genuinely free win and the way to throw it away is to "simplify" it to
    `-w "$value"`.
    """
    executable = code()
    assert '-w "' not in executable
    assert "-w '" not in executable
    assert "-p " not in executable, (
        "the -p option is insecure for the same reason passing a value to -w is"
    )

    text = source()
    store = text[text.index("keychain_store()") : text.index("keychain_delete()")]
    assert store.rstrip().endswith("}")
    for line in store.splitlines():
        if "add-generic-password" in line:
            command = line.split(";;")[0].strip()
            assert command.endswith("-w"), (
                f"-w is not the last option, so `security` will not prompt: {command!r}"
            )


def test_the_registry_write_also_keeps_the_text_out_of_argv() -> None:
    """The registry holds NAMES and never a value, so this is not strictly a
    secret-handling requirement — but it goes through the same client on the same
    code path, and a `-w "$text"` here is one copy-paste away from being a
    `-w "$value"` there.

    Measured 2026-08-07: `security` asks for the text TWICE (`password data for
    new item:` then `retype password for new item:`), so a single-line pipe
    stores an EMPTY item with rc 0 — which is the U3 "exists but empty" case,
    arriving silently from our own write path. Fed twice, rc 0 and
    `sk-a$bc de#f "g" \\h` round-tripped byte-identical.
    """
    text = source()
    write = text[text.index("keychain_write_registry()") : text.index("keychain_registry_names()")]
    assert "printf '%s\\n%s\\n'" in write, (
        "security asks for the text twice; a single feed stores an EMPTY item with rc 0"
    )
    assert "add-generic-password" in write

    for line in write.splitlines():
        if "$text" in line and not line.lstrip().startswith("#"):
            assert line.strip().startswith(("local ", "printf ")), (
                "the registry text reaches a client argument rather than its stdin: "
                f"{line.strip()!r}"
            )


# ------------------------------------------------------------------------------
# AC-DEGRADE — one predicate, per-name isolation, no repair
# ------------------------------------------------------------------------------


def test_a_name_is_supplied_only_on_rc_zero_and_a_non_empty_value() -> None:
    """U3, asserted as ONE rule rather than seven cases.

    Not "rc 0"; not "non-empty". Both — so that a failure nobody has met yet (a
    future `security` exiting 0 with a diagnostic on stdout, a client that prints
    a trailing newline and nothing else) lands in the same branch as the two that
    were measured: rc 44 with a message on stderr, rc 128 with nothing at all.
    """
    text = source()
    collect = text[text.index("keychain_collect_env()") : text.index("# --- 1. install Docker")]

    assert 'if ! value="$(keychain_read "$name")"; then' in collect  # rc
    assert 'if [[ -z "$value" ]]; then' in collect  # non-empty
    assert collect.count("continue") >= 2, "a failing name must be skipped, not fatal"


def test_one_unreadable_name_does_not_stop_the_others() -> None:
    """S5. A loop that aborts on the first failure passes a one-name test and
    silently disables the feature for anyone with a stale registry entry — which
    is everyone, eventually, since `security delete-generic-password` exists
    outside our subcommand."""
    text = source()
    collect = text[text.index("keychain_collect_env()") : text.index("# --- 1. install Docker")]

    assert "continue" in collect
    assert "return 1" not in collect, "a per-name fault must not end the fetch"
    assert "die " not in collect, "no keychain fault may abort the launcher (U4)"


def test_registry_drift_is_never_repaired_automatically() -> None:
    """A name whose item cannot be read stays in the registry.

    Pruning on a failed read would delete a registration because the keychain
    happened to be LOCKED — measured rc 128, indistinguishable at this level from
    a genuinely deleted item — and silently forgetting a user's registration is
    worse than carrying a stale one.
    """
    text = source()
    collect = text[text.index("keychain_collect_env()") : text.index("# --- 1. install Docker")]
    assert "keychain_write_registry" not in collect
    assert "keychain_delete" not in collect


def test_the_disable_switch_short_circuits_before_anything_is_probed() -> None:
    """O1, and the reason it never reaches the container.

    `CODERUNNER_KEYCHAIN` is launcher-only, in the pattern of
    CODERUNNER_DOCKER_BOOT_TIMEOUT and CODERUNNER_BOOTSTRAP_LOG
    (coderunner:17-18). SPEC-INPUT-001's N7 records the trap it therefore cannot
    spring: every variable in docker-compose.yml is written `${VAR:-default}`, so
    anything added there is ALWAYS set inside the container.
    """
    text = source()
    collect = text[text.index("keychain_collect_env()") : text.index("# --- 1. install Docker")]
    body = collect[collect.index("{") :]

    disabled = body.index("keychain_disabled")
    assert disabled < body.index("keychain_client"), "the client is probed before the switch"
    assert disabled < body.index("keychain_registry_names")


def test_the_never_used_state_emits_no_line_and_a_fault_emits_one() -> None:
    """The distinction is one `if` apart in the implementation and the wrong side
    of it turns a status convention into furniture.

    A missing registry item is not a fault — it is what every user who has never
    run `--set-secret` looks like, which on the day this ships is everybody. A
    yellow line there would appear on every launch of every session forever, and
    `product.md:138`'s convention is one line PER FAULT, not one line per absence
    of an opt-in feature. A LOCKED keychain, by contrast, is a fault and says so.
    """
    text = source()
    collect = text[text.index("keychain_collect_env()") : text.index("# --- 1. install Docker")]

    assert "KEYCHAIN_RC_ABSENT" in collect, "absent and unavailable are not distinguished"
    assert 'KEYCHAIN_RC_ABSENT="44"' in text  # measured on Darwin


# ------------------------------------------------------------------------------
# AC-DOCTOR — fourteen fields, names only
# ------------------------------------------------------------------------------


def test_doctor_prints_fourteen_fields() -> None:
    labels = field_labels(doctor_branch(source()))

    assert len(labels) == 14, f"--doctor prints {len(labels)} fields: {labels}"
    assert "keychain backend" in labels
    assert "stored secrets" in labels


def test_the_two_new_fields_keep_the_existing_column() -> None:
    """The same `printf '  %-17s : %s\\n'` shape, spelled the way the other twelve
    are spelled — as literal padding rather than a format width, because that is
    what the file already does and a mixed convention is how a column drifts."""
    branch = doctor_branch(source())
    assert "printf '  keychain backend : %s\\n'" in branch
    assert "printf '  stored secrets   : %s\\n'" in branch


def test_doctor_reads_the_registry_and_never_a_stored_value() -> None:
    """N5, asserted against the WHOLE report rather than against one field.

    `--doctor` output is the single most likely piece of this program's output to
    be published verbatim by someone who has not read it first. A value printed
    there is a value in a public issue tracker — and unlike every other exposure
    in this SPEC it is neither transient nor bounded by who can reach the Docker
    daemon.

    Asserting on the whole branch means a future field that happens to include a
    value — a debug dump, a "raw registry" line — fails this test rather than
    passing it by living somewhere else.
    """
    branch = doctor_branch(source())

    assert "keychain_read" not in branch, "--doctor must not read a stored value"
    assert "keychain_registry_names" in branch, "--doctor reports the registered names"


def test_doctor_still_exits_before_the_run_block() -> None:
    branch = doctor_branch(source())
    assert branch.rstrip().endswith("fi")
    assert "exit 0" in branch


# ------------------------------------------------------------------------------
# N7 — docker-compose.yml is not part of this feature
# ------------------------------------------------------------------------------


def test_compose_never_learns_that_the_keychain_exists() -> None:
    """SPEC-INPUT-001's N7 trap, restated: every variable in docker-compose.yml
    is written `${VAR:-default}` (docker-compose.yml:78-103), so anything added
    there is ALWAYS SET inside the container, always with a value. A launcher-only
    variable never reaches the container, never needs a compose entry, and cannot
    spring it."""
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "CODERUNNER_KEYCHAIN" not in compose
    assert "CODERUNNER_SECRET" not in compose


# ------------------------------------------------------------------------------
# AC-EXPOSE — the documentation clause  (U6, R5)
# ------------------------------------------------------------------------------

#: The documentation this SPEC ships and is answerable for. `.moai/specs/` is
#: excluded deliberately: `plan.md` R5 QUOTES the forbidden sentence in order to
#: forbid it, and a scan that cannot tell a warning from a claim is a scan that
#: makes the warning unwritable. `.claude/` is vendored agent tooling, excluded
#: for the same reason ruff.toml excludes it.
DOC_FILES = ("README.md", ".moai/project/product.md", ".moai/project/tech.md")

#: Affirmative phrasings only. Each is the sentence a README wants to write —
#: true, flattering, and read as a claim about the session, which is exactly
#: wrong: during the session the value is in `docker inspect` in plaintext.
FORBIDDEN_CLAIMS = (
    "stored securely",
    "securely stored",
    "stored safely",
    "safely stored",
    "secrets are private",
    "secret is private",
    "keeps your secrets private",
    "keeps it private",
    "kept private",
    "no one else can read",
    "nobody else can read",
)


@pytest.mark.parametrize("name", DOC_FILES)
def test_no_document_claims_this_makes_a_secret_private(name: str) -> None:
    """U6 and R5. **Certain unless actively prevented.**

    "Your secrets are stored securely in the system keychain" is true, flattering,
    and reads as a claim about the session. It is the sentence this feature
    invites, it will be believed, and it will be acted on by someone deciding
    whether to put a production key into it.
    """
    text = (_ROOT / name).read_text(encoding="utf-8").lower()

    hits = [claim for claim in FORBIDDEN_CLAIMS if claim in text]
    assert hits == [], f"{name} claims privacy this feature does not provide: {hits}"


@pytest.mark.parametrize("name", ("README.md", ".moai/project/tech.md"))
def test_the_docker_inspect_sink_is_named_where_a_user_will_read_it(name: str) -> None:
    """AC-EXPOSE's documentation clause. A limitation that is documented but never
    executed is a limitation that drifts; this is the assertion that notices.

    Measured 2026-08-07:

        $ docker run -d -e MY_SECRET=hunter2 … coderunner-ai:latest
        $ docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' <id>
        MY_SECRET=hunter2
    """
    text = (_ROOT / name).read_text(encoding="utf-8")

    assert "docker inspect" in text
    assert "does not" in text and "private" in text


def test_the_never_policy_no_longer_bounds_the_exposure_and_says_so() -> None:
    """spec.md 4.4's last row, which is the one that must reach the user.

    `never` was offered by SPEC-INPUT-001 as the option for people who need a
    guarantee rather than a reduction. For a keychain-sourced value it is still
    the strongest capture policy and it NO LONGER BOUNDS THE EXPOSURE, because
    the exposure is now outside the store the policy governs. A user who chose
    `never` deserves to be told this.
    """
    for name in ("README.md", ".moai/project/tech.md"):
        text = (_ROOT / name).read_text(encoding="utf-8")
        assert "never" in text
        assert "Config.Env" in text or "docker inspect" in text


# ------------------------------------------------------------------------------
# The banner must not erase what the launcher said (SPEC-BANNER-001)
# ------------------------------------------------------------------------------


def test_warn_records_that_the_launcher_said_something() -> None:
    """`main.py` clears the terminal at startup, and must not when there is
    something on it worth reading.

    Five of this file's six `warn()` calls are SPEC-KEYCHAIN-001 U4 degradation
    lines — "'api_key' is registered but could not be read — it will be
    prompted." — and every one of them is printed BEFORE the container starts.
    A banner that wipes the screen erases them in the instant before they are
    read, and the user then meets a getpass prompt with no idea why. Recording
    the fact in `warn()` itself rather than at each call site is what makes that
    impossible to forget at the sixth.
    """
    text = code()
    assert "LAUNCH_WARNED=0" in text, "the flag is never initialised"
    assert re.search(r"warn\(\)\s*\{\s*LAUNCH_WARNED=1;", text), (
        "warn() no longer records that it fired; main.py will clear over it"
    )


def test_the_launch_warned_flag_reaches_the_container_only_when_it_is_set() -> None:
    """Passed conditionally, so a clean launch is byte-for-byte what it was.

    The variable is exported and the `-e` carries a BARE NAME, which
    test_every_dash_e_in_the_launcher_carries_a_bare_name above asserts over
    every `-e` in the file — including this one, so N4 covers it without
    needing a second copy here.
    """
    text = code()
    assert 'if [ "$LAUNCH_WARNED" -eq 1 ]; then' in text, "the flag is passed unconditionally"
    assert "export CODERUNNER_LAUNCH_WARNED=1" in text
    assert "RUN_ENV+=(-e CODERUNNER_LAUNCH_WARNED)" in text
    assert "CODERUNNER_LAUNCH_WARNED" in (_ROOT / "main.py").read_text(encoding="utf-8"), (
        "the launcher exports a name main.py never reads"
    )


# ------------------------------------------------------------------------------
# Stale-image rebuild gate — the two defects that make this section silently wrong
# ------------------------------------------------------------------------------
#
# Measured 2026-08-15, and both were found by testing rather than by reading. The
# gate before this one was `if ! docker image inspect` alone, which builds only
# when the image is ABSENT; the author's own image dated 2026-08-07 and had no
# keychain.py in /app at all, so five days of merged work never ran. Dockerfile:37
# had predicted exactly that. Replacing the gate introduced two more failures that
# look correct in the source, which is why they are pinned here.


def stale_gate(text: str) -> str:
    """The staleness helpers and the build gate, comments already stripped.

    Bounded by `have_model()` rather than by the `# --- 5a.` section marker:
    `code()` strips whole-line comments, so every section marker in this file's
    input is already gone by the time a slice could look for one.
    """
    return text[text.index("mtime_of()") : text.index("have_model()")]


def test_the_gate_dates_the_image_by_last_tag_time_and_not_by_created() -> None:
    """`.Created` DOES NOT MOVE when the content hash is unchanged.

    Measured by touching main.py without altering a byte and building twice:

        .Created              10:24:28 -> 10:24:28   (unchanged)
        .Metadata.LastTagTime 10:28:23 -> 10:31:05   (advances)

    BuildKit reuses the cached image config, so a gate reading `.Created` never
    clears: `git checkout` writes a fresh mtime, the rebuild changes nothing,
    the timestamp stays put, and EVERY subsequent launch announces a rebuild.
    The failure is invisible in review — `.Created` is the obvious field, and
    the obvious field is the wrong one.
    """
    gate = stale_gate(code())
    assert ".Metadata.LastTagTime" in gate, "the gate no longer dates the image by its tag time"
    assert ".Created" not in gate, (
        "the gate reads .Created, which does not advance on a cache-hit build; "
        "the rebuild prompt will never clear"
    )


def test_the_mtime_comparison_admits_an_edit_made_in_the_same_second() -> None:
    """`-ge`, not `-gt`. Both sides are whole seconds.

    A no-op build takes 0.375s, so an edit landing in the same second as the
    build before it is genuinely newer and compares EQUAL. Measured: `touch
    settings.py` immediately after a build reported FRESH under `-gt`, which is
    the one answer that loses an edit. `-ge` costs at most one spare no-op
    rebuild and cannot latch, because each build advances LastTagTime.
    """
    gate = stale_gate(code())
    assert re.search(r'\[ "\$mtime" -ge "\$built" \]', gate), (
        "the comparison is not -ge; an edit sharing a second with the last build is lost"
    )
    assert "-gt" not in gate, "-gt reads a same-second edit as fresh"


def test_the_file_list_is_derived_from_the_dockerfile_rather_than_restated() -> None:
    """A second copy of the COPY line is the failure this whole section prevents.

    `params.py` and `settings.py` were missing from the Dockerfile's own COPY
    line for a full SPEC (fc19a07). A launcher that restated that list would
    reproduce the same class of drift one file further away, so the list is read
    out of the Dockerfile at run time — the rule tests/test_source_seam.py
    already applies to main.py's import block.
    """
    gate = stale_gate(code())
    assert "sed -n" in gate and "Dockerfile" in gate, (
        "the file list is no longer read from the Dockerfile"
    )
    modules = ["main.py", "memory.py", "recall.py", "vectorstore.py", "params.py", "settings.py"]
    restated = [name for name in modules if name in gate]
    assert not restated, f"the launcher restates the Dockerfile's COPY list: {restated}"


def test_an_undatable_image_rebuilds_rather_than_being_assumed_fresh() -> None:
    """Unreadable is stale. A spare 0.375s is the cheaper of the two errors."""
    gate = stale_gate(code())
    assert re.search(r'built="\$\(image_epoch\)" \|\| return 0', gate), (
        "an image whose tag time cannot be read is treated as fresh"
    )
    assert re.search(r"case \"\$built\" in ''\|\*\[!0-9\]\*\) return 1", gate), (
        "a non-numeric or empty timestamp is no longer rejected"
    )


def test_the_gate_still_builds_when_the_image_is_absent() -> None:
    """The original first-run behaviour survives beside the new branch."""
    gate = stale_gate(code())
    assert 'if ! docker image inspect "$IMAGE_NAME"' in gate
    assert "elif image_is_stale; then" in gate


def test_the_rebuild_notice_does_not_cost_the_user_their_banner() -> None:
    """say(), never warn().

    warn() sets LAUNCH_WARNED, whose entire purpose is to stop main.py clearing
    the screen so a keychain degradation line survives to be read
    (coderunner:27-34). "I rebuilt because you edited something" is not worth
    that.
    """
    gate = stale_gate(code())
    assert "warn " not in gate and "warn(" not in gate, (
        "the rebuild notice suppresses the banner clear"
    )
    assert 'say "Source is newer than' in gate
