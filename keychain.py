# ==============================================================================
#  CodeRunner.AI  ::  Host-keychain values, as seen from inside the container
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-KEYCHAIN-001
#  Purpose : The user stores a value in the macOS keychain or the Linux Secret
#            Service with `./coderunner --set-secret NAME`. The launcher fetches
#            it before the container starts and hands it in as
#            `CODERUNNER_SECRET_<NAME>`. This module reads those variables, pops
#            them, and fills them into the turn's value cache BEFORE
#            `params.collect_values()` runs — so `params.py:201-203`'s existing
#            skip is what suppresses the prompt, and `ask` is simply never
#            called. main.py owns only the wiring (spec.md 5).
#
#  IMPORTS : stdlib ONLY, and here that is a stronger claim than it is in
#            params.py or settings.py. There is no `subprocess`, no
#            `sys.platform`, no `security`, no `secret-tool` and no `Path` in
#            this file, because EVERY PLATFORM DECISION THIS FEATURE MAKES LIVES
#            IN BASH. That is the whole answer to the question the SPEC started
#            from — can private information be stored with system libraries and
#            no dependency — and it is why the answer costs zero entries in
#            requirements.txt: the launcher is not Python. If a third platform is
#            ever supported, this file does not change and neither does its test.
#
#  WHAT THIS DOES NOT DO, said here rather than discovered later. A value passed
#  into the container's environment is NOT private. Measured 2026-08-07:
#  `docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}'` prints
#  it in plaintext, and `/proc/1/environ` inside the container carries it and is
#  readable by `runner` — the same uid generated code runs as. `load()` pops the
#  variables, which closes the `os.environ` route for children started by
#  `run_python()` (measured) and closes NEITHER `/proc` route (measured). The pop
#  is worth its one line and it is not a fix. See spec.md 4.1 and 4.3.
# ==============================================================================

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

#: Written by the launcher as `CODERUNNER_SECRET_` + the declared name
#: uppercased. Declared names are `[A-Za-z_][A-Za-z0-9_]*` (params.py:75), every
#: character of which is already legal in an environment variable name, so no
#: escaping is needed and none is invented. Two declared names differing only in
#: case therefore collide on one variable; `--set-secret` refuses the second one
#: rather than letting this module pick a winner (O2).
ENV_PREFIX = "CODERUNNER_SECRET_"

#: Duplicated from `params.TYPE_SECRET` as a LITERAL rather than imported, for
#: exactly the reason settings.py duplicates its eleven environment names
#: (settings.py:95-98): the stdlib-only assertion at
#: tests/test_source_seam.py:156-167 admits no first-party import at all, and
#: this module's whole claim is that it is a leaf. Duplication without a
#: cross-check is drift with a delay, so tests/test_keychain.py asserts the two
#: tokens are equal — a rename then fails a test instead of silently sourcing
#: nothing.
SECRET_TYPE = "secret"  # noqa: S105 — a declared type token, not a password


def load(environ: MutableMapping[str, str]) -> dict[str, str]:
    """Read and **pop** every ``CODERUNNER_SECRET_*`` variable; keep the non-empty.

    Called ONCE, at ``main.py`` import, and not at first use (E3). ``run_python()``
    passes no ``env=`` (main.py:496-503), so a child inherits whatever
    ``os.environ`` holds when it starts, and a script run before the pop would
    read the value out of it with a one-line ``print(os.environ)``.

    Popped whether or not the value survives the emptiness test: anything
    carrying the prefix belongs to this feature, and leaving an empty one behind
    would hand a generated script a variable whose name reads exactly like a
    secret's.

    The emptiness test is the container-side half of U3's single rule — a name is
    supplied only if the client exited 0 **and** printed something. The launcher
    holds the other half. Both, so that a client nobody has met yet — one that
    exits 0 and prints a bare newline — lands in the same branch as the two
    failures that were measured.
    """
    found: dict[str, str] = {}
    # A list, not the live view: popping while iterating a mapping raises.
    for key in [key for key in environ if key.startswith(ENV_PREFIX)]:
        value = environ.pop(key)
        name = key[len(ENV_PREFIX) :]
        if name and value:
            found[name] = value
    return found


def prefill(
    declarations: Sequence[Any],
    values: MutableMapping[str, object],
    loaded: Mapping[str, str],
) -> list[str]:
    """Fill ``values`` from ``loaded`` for eligible declarations; name what was filled.

    Called BEFORE ``params.collect_values()``, which is the entire mechanism
    (spec.md 3.6). ``collect_values()`` already skips a name present in ``values``
    (params.py:201-203) and ``pending_declarations()`` already filters to names
    that are not (params.py:123-133), so nothing in ``params.py`` needs to learn
    that a keychain exists, no branch is added to a module gated at 100%, and
    ``ask`` is never invoked for a sourced name. The absence of a call is easier
    to verify than the presence of a guard.

    ``declarations`` is typed ``Any`` rather than ``params.Declaration`` for the
    reason in the banner: importing ``params`` would cost this file its
    stdlib-only claim. Only ``.name`` and ``.type`` are read.

    Two exclusions, both load-bearing:

    * **S3 — ``type == secret`` only.** The same one predicate governs the mask
      (params.py:297), the redaction set (params.py:408), the ``getpass`` route
      (main.py:823) and the policy gate (main.py:988). Joining it means one
      condition governs five behaviours instead of two conditions that can
      disagree. A user who stores ``city`` is prompted for it anyway, because the
      model declared it ``str``.
    * **S2 — the turn's cache wins.** A value typed on attempt 1 must not be
      replaced by a keychain value on attempt 2. The test is PRESENCE, not
      truthiness: ``collect_values()`` writes ``None`` for a value it could not
      coerce (params.py:207) and ``pending_declarations()`` treats that as
      settled, so sourcing over it would resurrect a name the turn has finished
      with.
    """
    filled: list[str] = []
    for decl in declarations:
        if decl.type != SECRET_TYPE:
            continue
        if decl.name in values:
            continue
        value = loaded.get(decl.name.upper())
        if not value:
            continue
        values[decl.name] = value
        filled.append(decl.name)
    return filled
