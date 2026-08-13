# ==============================================================================
#  CodeRunner.AI  ::  source-level and generated-wrapper assertions for install.sh
# ------------------------------------------------------------------------------
#  Covers  : the properties of the installer whose failure is either SILENT or
#            DESTRUCTIVE, which is a different set from "the properties it has".
#
#  WHY THIS FILE EXISTS. install.sh is thirty lines of decision and a hundred of
#  explanation, and four of its choices are load-bearing in ways a reader will
#  not see:
#
#    * IT MUST NOT INSTALL A SYMLINK. `coderunner:12` resolves its own directory
#      with `dirname "${BASH_SOURCE[0]}"`, which does not follow symlinks.
#      Through a symlink at ~/bin/coderunner that expands to ~/bin, the launcher
#      cds there and dies on the first `docker compose` call — late, with a
#      message naming compose. The correct fix looks like the wrong one: a
#      symlink is the obvious install and it is the broken install.
#
#    * THE WRAPPER MUST `exec`. Not for tidiness: `exec` replaces the process, so
#      the launcher inherits the caller's TTY — which the REPL and readline both
#      require — and its own EXIT trap still fires, so the Ollama sidecar is
#      still stopped when the session ends. A wrapper that CALLED instead would
#      look identical in every interactive test and leak a container per run.
#
#    * THE WRAPPER MUST USE `${1+"$@"}`. Under `set -u` on bash 3.2.57 — stock
#      macOS /bin/bash — a bare "$@" with no arguments is an unbound-variable
#      abort. So `coderunner` with no arguments, which is the ONLY way anybody
#      starts the REPL, would die. Same class as SPEC-KEYCHAIN-001's N8.
#
#    * IT MUST NOT DELETE OR OVERWRITE A FILE IT DID NOT WRITE. An installer that
#      claims ~/bin/coderunner because it wanted the name is an installer that
#      destroys somebody's script.
#
#  Everything here reads text on disk, runs `bash -n`, or installs into pytest's
#  tmp_path. Nothing imports the application, nothing touches ~/bin, and nothing
#  invokes Docker — so this file runs on bare pytest, like
#  tests/test_launcher_source.py and tests/test_source_seam.py.
# ==============================================================================

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_INSTALLER = _ROOT / "install.sh"
_LAUNCHER = _ROOT / "coderunner"

_RC_FILES = ("zshrc", "bash_profile", "bashrc", ".profile", "config.fish")
_BASH4_ONLY = ("declare -A", "${var^^}", "^^}", ",,}", "mapfile", "readarray", "local -n")


def source() -> str:
    return _INSTALLER.read_text(encoding="utf-8")


def code(text: str | None = None) -> str:
    """The installer with whole-line comments removed.

    install.sh names the constructions it forbids — "symlink", the rc files it
    declines to edit — in its own comments, because a reader who does not know
    why a symlink is wrong will replace the wrapper with one. Checking raw text
    would make that explanation unwritable, which is the reasoning
    tests/test_launcher_source.py applies to the launcher and
    tests/test_source_seam.py applies to `order_by`.
    """
    lines = (source() if text is None else text).splitlines()
    return "\n".join(
        line for line in lines if not line.lstrip().startswith("#") or line.startswith("#!")
    )


def install_into(directory: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the real installer into a throwaway directory.

    `--dir` is what makes this safe to run in a test at all: no HOME is touched,
    no PATH is changed, and the only artefact is inside tmp_path.
    """
    return subprocess.run(
        ["/bin/bash", str(_INSTALLER), "--dir", str(directory), *args],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
        check=False,
    )


@pytest.fixture
def wrapper(tmp_path: Path) -> Path:
    result = install_into(tmp_path)
    assert result.returncode == 0, result.stderr
    return tmp_path / "coderunner"


# ------------------------------------------------------------------------------
# Vacuity — every check below reads something. Prove there is something to read.
# ------------------------------------------------------------------------------


def test_the_installer_and_its_stripped_form_are_both_non_empty() -> None:
    """The guard, and it is not ceremony.

    Twice in four days this repository shipped a check that matched nothing and
    passed: tests/test_launcher_source.py's whitespace tokenizer, which never
    saw `RUN_ENV+=(-e "…")` at all, and `keychain.py` missing from ci.yml's
    FILES list. Both were green. A `code()` that returned "" would make every
    "X is absent" assertion below trivially true, and the suite would report a
    clean sweep of an empty string.
    """
    assert _INSTALLER.is_file(), "install.sh is missing"
    raw = source()
    assert len(raw) > 1000, f"install.sh is implausibly short: {len(raw)} chars"
    stripped = code()
    assert stripped.strip(), "comment stripping consumed the entire file"
    assert "TARGET_DIR" in stripped, "the stripped form lost its executable body"
    assert len(stripped) < len(raw), "comment stripping removed nothing — is the regex right?"


# ------------------------------------------------------------------------------
# It installs a wrapper, not a symlink
# ------------------------------------------------------------------------------


def test_the_installer_never_creates_a_symlink() -> None:
    """`coderunner:12` does not follow symlinks, so a symlink is the broken install.

    This is asserted on the stripped source because install.sh explains the trap
    at length in its own header, and that explanation is the reason the next
    person will not re-introduce it.
    """
    body = code()
    assert "ln -s" not in body, "install.sh creates a symlink; coderunner:12 cannot follow one"
    assert "ln -sf" not in body
    assert "symlink" not in body, "a symlink is discussed in executable text rather than in comment"


def test_the_launcher_still_resolves_its_directory_the_way_this_depends_on() -> None:
    """The premise of the whole design, asserted against the launcher itself.

    If `coderunner` ever gains symlink resolution — `readlink -f`, or a resolve
    loop — the wrapper stops being necessary and this file's central claim
    becomes false. Better to fail here than to keep asserting a reason that has
    expired.
    """
    launcher = _LAUNCHER.read_text(encoding="utf-8")
    assert 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"' in launcher, (
        "coderunner no longer resolves its directory the way install.sh assumes"
    )
    assert "readlink -f" not in launcher, "coderunner now resolves symlinks; revisit install.sh"


# ------------------------------------------------------------------------------
# The generated wrapper — exec, an absolute path, and ${1+"$@"}
# ------------------------------------------------------------------------------


def test_the_generated_wrapper_execs_rather_than_calls(wrapper: Path) -> None:
    """`exec` is load-bearing twice, and neither failure is visible interactively.

    Replacing the process hands the launcher this shell's TTY, which the REPL
    and readline require; and it lets the launcher's own EXIT trap fire, which
    is what stops the Ollama sidecar and returns its RAM. A wrapper that called
    the launcher as a child would pass every interactive smoke test a person is
    likely to run, and leak a container per session.
    """
    text = wrapper.read_text(encoding="utf-8")
    exec_lines = [ln for ln in text.splitlines() if ln.strip().startswith("exec ")]
    assert len(exec_lines) == 1, f"expected exactly one exec line, found {len(exec_lines)}"
    assert "/coderunner" in exec_lines[0]


def test_the_generated_wrapper_bakes_in_an_absolute_path(wrapper: Path) -> None:
    """Resolved at install time, not at run time.

    The wrapper must not depend on its own location, on the caller's working
    directory, or on any variable being set in the environment that runs it —
    all three of which vary, and the third of which a user can break without
    touching this project at all.
    """
    text = wrapper.read_text(encoding="utf-8")
    match = re.search(r'^REPO_DIR="(/[^"]*)"$', text, re.MULTILINE)
    assert match, "the wrapper does not bake in an absolute REPO_DIR"
    baked = Path(match.group(1))
    assert baked.is_absolute()
    assert baked == _ROOT, f"wrapper points at {baked}, not {_ROOT}"
    assert (baked / "coderunner").is_file()


def test_the_generated_wrapper_survives_being_called_with_no_arguments(wrapper: Path) -> None:
    """`${1+"$@"}`, not `"$@"`. bash 3.2.57 + `set -u`.

    Stock macOS /bin/bash is 3.2.57, where a bare "$@" with no positional
    parameters is an unbound-variable error. The wrapper sets `set -Eeuo
    pipefail`, so a bare "$@" would abort — on `coderunner` with no arguments,
    which is the only way anybody starts the REPL. The feature would be broken
    for every user in exactly the case that is not the edge case.

    Asserted twice: on the text, and by running it against a stub launcher, so
    a future rewrite that keeps the behaviour but changes the spelling still
    passes and one that keeps the spelling but breaks the behaviour does not.
    """
    text = wrapper.read_text(encoding="utf-8")
    assert '${1+"$@"}' in text, 'the wrapper uses a bare "$@"; bash 3.2 + set -u aborts on it'

    stub_repo = wrapper.parent / "stub"
    stub_repo.mkdir()
    (stub_repo / "coderunner").write_text(
        '#!/usr/bin/env bash\nprintf "%d\\n" "$#"\n', encoding="utf-8"
    )
    (stub_repo / "coderunner").chmod(0o755)
    stubbed = wrapper.parent / "stubbed"
    stubbed.write_text(
        re.sub(r'^REPO_DIR=".*"$', f'REPO_DIR="{stub_repo}"', text, flags=re.MULTILINE),
        encoding="utf-8",
    )
    stubbed.chmod(0o755)

    none = subprocess.run(["/bin/bash", str(stubbed)], capture_output=True, text=True, check=False)
    assert none.returncode == 0, f"zero-argument invocation failed: {none.stderr}"
    assert none.stdout.strip() == "0"

    spaced = subprocess.run(
        ["/bin/bash", str(stubbed), "--doctor", "two words"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert spaced.stdout.strip() == "2", "an argument containing a space was split"


def test_the_generated_wrapper_fails_loudly_when_the_repository_moves(wrapper: Path) -> None:
    """A moved repository must say so, not produce a compose error.

    Without this branch the wrapper execs a path that no longer exists and the
    user reads bash's own "no such file" against a path they never typed.
    """
    text = wrapper.read_text(encoding="utf-8")
    assert 'if [ ! -x "$REPO_DIR/coderunner" ]' in text
    assert "exit 127" in text


# ------------------------------------------------------------------------------
# bash 3.2 — the interpreter this has to run under, not the one we develop on
# ------------------------------------------------------------------------------


def test_the_installer_parses_under_bin_bash() -> None:
    """/bin/bash explicitly, not `env bash`.

    Running this under a Homebrew bash 5 proves nothing about the population it
    protects — the same argument SPEC-KEYCHAIN-001's AC-LAUNCH makes about the
    launcher, and for the same interpreter.
    """
    result = subprocess.run(
        ["/bin/bash", "-n", str(_INSTALLER)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"install.sh does not parse under /bin/bash:\n{result.stderr}"


@pytest.mark.parametrize("construction", _BASH4_ONLY)
def test_the_installer_uses_no_construction_bash_3_2_lacks(construction: str) -> None:
    """Parsing is necessary and not sufficient — some of these parse and misbehave."""
    assert construction not in code(), f"install.sh uses {construction!r}, absent from bash 3.2"


# ------------------------------------------------------------------------------
# It destroys nothing it did not create
# ------------------------------------------------------------------------------


def test_the_installer_gates_overwrite_and_removal_on_its_own_marker() -> None:
    """The marker is the only thing separating "install" from "delete a stranger's file"."""
    body = code()
    assert 'MARKER="# installed-by: coderunner.ai/install.sh"' in body
    assert body.count('grep -qF "$MARKER"') >= 2, (
        "the marker is checked fewer than twice; both --force and --uninstall must gate on it"
    )


def test_the_installer_refuses_a_file_it_did_not_write(tmp_path: Path) -> None:
    """Observed, not asserted on the source: run it against a foreign file."""
    foreign = tmp_path / "coderunner"
    foreign.write_text("#!/bin/sh\necho not ours\n", encoding="utf-8")
    before = foreign.read_text(encoding="utf-8")

    install = install_into(tmp_path)
    assert install.returncode == 1
    assert foreign.read_text(encoding="utf-8") == before, "the installer overwrote a foreign file"

    uninstall = install_into(tmp_path, "--uninstall")
    assert uninstall.returncode == 1
    assert foreign.is_file(), "the installer deleted a foreign file"


def test_the_installer_edits_no_shell_startup_file() -> None:
    """It advises; it does not modify.

    install.sh names ~/.zshrc and friends in the advice it prints, so the check
    is on REDIRECTION rather than on the filenames: no line may both name an rc
    file and write to one. Silently rewriting a login script is not a thing a
    tool may do to somebody, and a check that forbade the names would forbid the
    advice as well.
    """
    for line in code().splitlines():
        if any(rc in line for rc in _RC_FILES):
            assert ">>" not in line and not re.search(r"(?<![0-9<>])>(?!&)", line), (
                f"install.sh writes to a shell startup file: {line.strip()!r}"
            )
    assert "tee" not in code(), "install.sh reaches for tee; check what it is writing"


# ------------------------------------------------------------------------------
# Regression — the bug this installer shipped with, for about an hour
# ------------------------------------------------------------------------------


def test_the_idempotency_check_reads_the_repo_comment_not_the_exec_line() -> None:
    """Measured 2026-08-12, on the first re-install this script ever performed.

    The check originally parsed the installed repository path out of the `exec`
    line. That line reads `exec "$REPO_DIR/coderunner" ${1+"$@"}` — it holds a
    VARIABLE, not a value — so the comparison was the literal string `$REPO_DIR`
    against a real path, and every re-install would have refused with
    "currently points at: $REPO_DIR". The `# repo:` line is written for exactly
    this and must be what is read.
    """
    body = code()
    assert "sed -n 's/^# repo: //p'" in body, "the idempotency check no longer reads `# repo:`"
    assert 'sed -n \'s/^exec "' not in body, "the idempotency check parses the exec line again"


def test_reinstalling_over_our_own_wrapper_refreshes_rather_than_refusing(tmp_path: Path) -> None:
    """The behavioural half of the same regression."""
    first = install_into(tmp_path)
    assert first.returncode == 0
    second = install_into(tmp_path)
    assert second.returncode == 0, f"re-install refused:\n{second.stdout}{second.stderr}"
    assert "$REPO_DIR" not in second.stdout + second.stderr, (
        "an unexpanded variable reached the user-facing output"
    )


def test_uninstalling_our_own_wrapper_removes_it(tmp_path: Path) -> None:
    installed = install_into(tmp_path)
    assert installed.returncode == 0
    target = tmp_path / "coderunner"
    assert target.is_file()

    removed = install_into(tmp_path, "--uninstall")
    assert removed.returncode == 0
    assert not target.exists()
