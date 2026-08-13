#!/usr/bin/env bash
# ==============================================================================
#  CodeRunner.AI  ::  Installer
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Purpose : Put a `coderunner` command on your PATH so the REPL can be started
#            from any directory, without moving or copying the repository.
#
#  WHAT IT INSTALLS, AND WHY IT IS A WRAPPER RATHER THAN A SYMLINK.
#  `coderunner:12` resolves its own directory with
#      SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#  which does NOT follow symlinks. Through a symlink at ~/bin/coderunner that
#  expands to ~/bin, the launcher would cd there and then fail on the first
#  `docker compose` call, because docker-compose.yml lives in the repository.
#  The failure is late and its message names compose rather than the symlink.
#
#  So this writes a small wrapper that `exec`s the real launcher by ABSOLUTE
#  path. `exec` replaces the wrapper process, so the launcher keeps this shell's
#  stdin, stdout and TTY — which the interactive REPL and readline both need —
#  and its EXIT trap still fires, so the Ollama sidecar is still stopped on the
#  way out. Nothing about the launcher changes; it is not patched, copied or
#  moved, and `git pull` in the repository updates the installed command too.
#
#  USAGE
#      ./install.sh                 install to ~/bin
#      ./install.sh --dir /usr/local/bin
#      ./install.sh --force         overwrite whatever is already there
#      ./install.sh --uninstall     remove it again
#
#  Written for bash 3.2 — the version macOS still ships at /bin/bash. No
#  associative arrays, no ${var^^}, no mapfile.
# ==============================================================================
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$REPO_DIR/coderunner"
TARGET_DIR="${CODERUNNER_INSTALL_DIR:-$HOME/bin}"
COMMAND_NAME="coderunner"
FORCE=0
UNINSTALL=0

# The marker is how --force and --uninstall tell OUR wrapper apart from a file
# that merely shares the name. Overwriting or deleting somebody else's script
# because it sat at the path we wanted is not a thing an installer may do.
MARKER="# installed-by: coderunner.ai/install.sh"

red()  { printf '\033[31m%s\033[0m\n' "$*" >&2; }
warn() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
ok()   { printf '\033[32m%s\033[0m\n' "$*"; }
info() { printf '%s\n' "$*"; }
die()  { red "error: $*"; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dir)       [ $# -ge 2 ] || die "--dir needs a directory"; TARGET_DIR="$2"; shift 2 ;;
    --dir=*)     TARGET_DIR="${1#--dir=}"; shift ;;
    --name)      [ $# -ge 2 ] || die "--name needs a value"; COMMAND_NAME="$2"; shift 2 ;;
    --name=*)    COMMAND_NAME="${1#--name=}"; shift ;;
    --force|-f)  FORCE=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help)   sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^#\{1,2\} \{0,1\}//'; exit 0 ;;
    *)           die "unknown argument: $1  (try --help)" ;;
  esac
done

TARGET="$TARGET_DIR/$COMMAND_NAME"

# --- uninstall ----------------------------------------------------------------
if [ "$UNINSTALL" -eq 1 ]; then
  if [ ! -e "$TARGET" ]; then
    info "nothing to remove: $TARGET does not exist"
    exit 0
  fi
  if ! grep -qF "$MARKER" "$TARGET" 2>/dev/null && [ "$FORCE" -ne 1 ]; then
    die "$TARGET was not written by this installer. Remove it yourself, or pass --force."
  fi
  rm -f "$TARGET"
  ok "removed $TARGET"
  exit 0
fi

# --- checks -------------------------------------------------------------------
[ -f "$LAUNCHER" ] || die "launcher not found at $LAUNCHER — run this from the repository."
[ -x "$LAUNCHER" ] || die "$LAUNCHER is not executable. Try: chmod +x '$LAUNCHER'"

if [ -e "$TARGET" ] && [ "$FORCE" -ne 1 ]; then
  if grep -qF "$MARKER" "$TARGET" 2>/dev/null; then
    # Read it from the `# repo:` line, which is written for this purpose. The
    # `exec` line holds "$REPO_DIR/coderunner" — a variable, not a value — so
    # parsing that yields the literal string $REPO_DIR and every comparison
    # fails. Measured 2026-08-12, on the first re-install this script ever did.
    EXISTING="$(sed -n 's/^# repo: //p' "$TARGET" | head -1)"
    if [ "$EXISTING" = "$REPO_DIR" ]; then
      info "already installed and pointing here; refreshing."
    else
      warn "$TARGET currently points at: ${EXISTING:-unknown}"
      warn "re-run with --force to repoint it at $REPO_DIR"
      exit 1
    fi
  else
    die "$TARGET already exists and was not written by this installer. Pass --force to overwrite it."
  fi
fi

mkdir -p "$TARGET_DIR" || die "could not create $TARGET_DIR"
[ -w "$TARGET_DIR" ] || die "$TARGET_DIR is not writable. Try: sudo ./install.sh --dir '$TARGET_DIR'"

# --- write the wrapper --------------------------------------------------------
# REPO_DIR is expanded HERE, into the file, on purpose: the wrapper must not
# depend on its own location, on the caller's cwd, or on any variable being set
# at run time. The quoted heredoc keeps everything else literal.
{
  printf '%s\n' '#!/usr/bin/env bash'
  printf '%s\n' "$MARKER"
  printf '%s\n' "# repo: $REPO_DIR"
  printf '%s\n' '#'
  printf '%s\n' '# Generated. Re-run install.sh in the repository to update or move it;'
  printf '%s\n' '# `install.sh --uninstall` removes it.'
  printf '%s\n' '#'
  printf '%s\n' '# exec, not a call: the launcher inherits this TTY (the REPL and readline'
  printf '%s\n' '# need it) and its own EXIT trap still runs, so the Ollama sidecar is'
  printf '%s\n' '# still stopped when the session ends.'
  printf '%s\n' 'set -Eeuo pipefail'
  printf '%s\n' "REPO_DIR=\"$REPO_DIR\""
  printf '%s\n' 'if [ ! -x "$REPO_DIR/coderunner" ]; then'
  printf '%s\n' '  printf "coderunner: launcher missing at %s\\n" "$REPO_DIR/coderunner" >&2'
  printf '%s\n' '  printf "the repository may have been moved or deleted; re-run install.sh there\\n" >&2'
  printf '%s\n' '  exit 127'
  printf '%s\n' 'fi'
  # ${1+"$@"} rather than "$@": bash 3.2 under `set -u` treats an unset $@ as an
  # unbound variable, so a bare `coderunner` with no arguments would die here.
  printf '%s\n' 'exec "$REPO_DIR/coderunner" ${1+"$@"}'
} > "$TARGET"

chmod +x "$TARGET"
ok "installed: $TARGET  ->  $LAUNCHER"

# --- PATH advice --------------------------------------------------------------
# An installer that reports success for a command the shell cannot find has not
# succeeded. This checks rather than assumes, and it edits no rc file: silently
# rewriting a login script is not something a tool should do to somebody.
case ":${PATH}:" in
  *":$TARGET_DIR:"*)
    ok "$TARGET_DIR is already on your PATH — run: $COMMAND_NAME"
    ;;
  *)
    warn ""
    warn "$TARGET_DIR is NOT on your PATH, so '$COMMAND_NAME' will not be found yet."
    case "${SHELL##*/}" in
      zsh)  RC="~/.zshrc" ;;
      bash) RC="~/.bash_profile" ;;
      fish) RC="~/.config/fish/config.fish" ;;
      *)    RC="your shell's startup file" ;;
    esac
    if [ "${SHELL##*/}" = "fish" ]; then
      warn "Add this to $RC:"
      warn "    fish_add_path $TARGET_DIR"
    else
      warn "Add this to $RC, then open a new terminal:"
      warn "    export PATH=\"$TARGET_DIR:\$PATH\""
    fi
    warn ""
    warn "Until then it still works by full path: $TARGET"
    ;;
esac

info ""
info "Try:  $COMMAND_NAME --doctor"
