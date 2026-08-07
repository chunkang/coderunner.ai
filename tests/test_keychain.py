# ==============================================================================
#  CodeRunner.AI  ::  keychain.py — the container's whole half of the feature
# ------------------------------------------------------------------------------
#  Project : SPEC-KEYCHAIN-001, task T8
#  Covers  : U1, U3, E3, E4, S2, S3 — and the 100% floor conftest.py:200-206
#            sets for this module.
#
#  The module under test contains NO subprocess, NO sys.platform and no
#  `security`/`secret-tool` string: every platform decision this feature makes
#  is in bash, which is the answer to the question the SPEC started from. What
#  is left in Python is a dictionary reader, and this file drives all of it.
#
#  Runs on a BARE INTERPRETER with nothing but pytest — keychain.py and params.py
#  are both stdlib-only leaves.
# ==============================================================================

from __future__ import annotations

import ast
import sys
from pathlib import Path

import keychain
import params

_ROOT = Path(__file__).resolve().parent.parent


def decl(name: str, declared_type: str = params.TYPE_SECRET) -> params.Declaration:
    return params.Declaration(name=name, type=declared_type, prompt=f"value for {name}")


# Built as dict literals rather than through a `**kwargs` helper: a keyword
# argument whose NAME looks like a credential is S106, and silencing the rule in
# the one suite that verifies secret handling is the wrong direction.


# ------------------------------------------------------------------------------
# load() — read, and POP
# ------------------------------------------------------------------------------


def test_the_prefix_is_the_one_the_launcher_builds() -> None:
    """The launcher writes `CODERUNNER_SECRET_$UPPER` and nothing negotiates it.

    Asserted as a literal rather than derived, because the two halves of this
    name live in different languages and a rename on one side is invisible to
    the other until a user is prompted for a value they stored.
    """
    assert keychain.ENV_PREFIX == "CODERUNNER_SECRET_"


def test_load_reads_a_prefixed_variable_and_strips_the_prefix() -> None:
    environ = {"CODERUNNER_SECRET_API_KEY": "sk-live-DEADBEEF"}

    assert keychain.load(environ) == {"API_KEY": "sk-live-DEADBEEF"}


def test_load_pops_every_prefixed_variable_out_of_the_mapping() -> None:
    """E3, and the reason `load()` runs at IMPORT rather than at first use.

    `run_python()` passes no `env=` (main.py:496-503), so a child inherits
    whatever `os.environ` holds when it starts. Any script run before the pop
    would read the value with a one-line `print(os.environ)`.

    Measured 2026-08-07 inside the image: after the pop a `python -I` child reads
    `None`. It does NOT close `/proc/self/environ` or `/proc/1/environ` — see
    AC-EXPOSE. The pop is worth its one line and it is not a fix.
    """
    environ = {
        "CODERUNNER_SECRET_API_KEY": "sk-live-DEADBEEF",
        "CODERUNNER_SECRET_TOKEN": "t0ken",
        "PATH": "/usr/bin",
    }

    keychain.load(environ)

    assert "CODERUNNER_SECRET_API_KEY" not in environ
    assert "CODERUNNER_SECRET_TOKEN" not in environ
    assert environ == {"PATH": "/usr/bin"}


def test_load_leaves_every_unprefixed_variable_exactly_where_it_was() -> None:
    environ = {"PATH": "/usr/bin", "OLLAMA_HOST": "http://x", "CODERUNNER_MODEL": "l3:8b"}

    assert keychain.load(environ) == {}
    assert environ == {"PATH": "/usr/bin", "OLLAMA_HOST": "http://x", "CODERUNNER_MODEL": "l3:8b"}


def test_an_empty_value_is_popped_but_never_kept() -> None:
    """U3's second half, on the container side.

    An item that exists with an empty value is rc 0 and still not a secret. The
    launcher already refuses to pass one; this is the same predicate held on both
    sides of the boundary, so a future client that prints a bare newline lands in
    the same branch as the two failures that were measured.
    """
    environ = {"CODERUNNER_SECRET_API_KEY": "", "CODERUNNER_SECRET_TOKEN": "t0ken"}

    assert keychain.load(environ) == {"TOKEN": "t0ken"}
    assert "CODERUNNER_SECRET_API_KEY" not in environ, "an empty one must still be popped"


def test_load_of_an_empty_mapping_is_an_empty_dict() -> None:
    environ: dict[str, str] = {}

    assert keychain.load(environ) == {}
    assert environ == {}


def test_a_bare_prefix_with_no_name_after_it_is_ignored() -> None:
    """`CODERUNNER_SECRET_` alone names no parameter, so it can fill none.

    It is still popped: anything carrying the prefix is this feature's, and
    leaving it behind would hand a generated script a variable whose provenance
    reads exactly like a secret's.
    """
    environ = {"CODERUNNER_SECRET_": "orphan"}

    assert keychain.load(environ) == {}
    assert environ == {}


def test_the_dollar_bearing_value_survives_the_read_intact() -> None:
    """AC-TRANSPORT's fixture, on the Python side of the boundary.

    A `$`-free value round-trips identically under the corrupting transport too
    (`--env-from-file`, measured 2026-08-07 to expand `$bc` away and deliver
    three characters fewer). The `$` is not decoration; it is the entire
    discriminating power of the fixture.
    """
    value = 'sk-a$bc de#f "g" \\h'
    environ = {"CODERUNNER_SECRET_API_KEY": value}

    loaded = keychain.load(environ)

    assert repr(loaded["API_KEY"]) == repr(value)
    assert len(loaded["API_KEY"]) == 19


# ------------------------------------------------------------------------------
# prefill() — fill `values` BEFORE collect_values, so the existing skip works
# ------------------------------------------------------------------------------


def test_prefill_fills_a_declared_secret_and_names_what_it_filled() -> None:
    values: dict[str, object] = {}

    filled = keychain.prefill([decl("api_key")], values, {"API_KEY": "sk-live"})

    assert filled == ["api_key"]
    assert values == {"api_key": "sk-live"}


def test_prefill_uppercases_the_declared_name_to_reach_the_variable() -> None:
    """Declared names are `[A-Za-z_][A-Za-z0-9_]*` (params.py:75), every
    character of which is legal in an environment variable name, so no escaping
    is needed and none is invented."""
    values: dict[str, object] = {}

    keychain.prefill([decl("api_key_2")], values, {"API_KEY_2": "v"})

    assert values == {"api_key_2": "v"}


def test_a_non_secret_declaration_is_never_sourced_even_with_a_matching_variable() -> None:
    """S3. One predicate governs the mask (params.py:297), the redaction set
    (params.py:408), the `getpass` route (main.py:823), the policy gate
    (main.py:988) and this. A user who stores `city` is prompted for it anyway,
    because the model declared it `str`."""
    values: dict[str, object] = {}

    for declared_type in (params.TYPE_STR, params.TYPE_INT, params.TYPE_FLOAT):
        filled = keychain.prefill([decl("city", declared_type)], values, {"CITY": "Seoul"})
        assert filled == []

    assert values == {}


def test_a_value_already_in_the_turns_cache_wins_over_the_keychain() -> None:
    """S2. A value typed on attempt 1 must not be replaced on attempt 2."""
    values: dict[str, object] = {"api_key": "typed-by-hand"}

    filled = keychain.prefill([decl("api_key")], values, {"API_KEY": "from-keychain"})

    assert filled == []
    assert values == {"api_key": "typed-by-hand"}


def test_a_cached_none_still_wins_because_presence_is_the_test() -> None:
    """`collect_values()` writes `None` for a value it could not coerce
    (params.py:207), and `pending_declarations()` keys on PRESENCE, not on
    truthiness (params.py:133). Sourcing on a falsy cached value would resurrect
    a name the turn has already settled."""
    values: dict[str, object] = {"api_key": None}

    assert keychain.prefill([decl("api_key")], values, {"API_KEY": "from-keychain"}) == []
    assert values == {"api_key": None}


def test_a_declaration_with_no_matching_variable_is_left_to_the_prompt() -> None:
    values: dict[str, object] = {}

    assert keychain.prefill([decl("api_key")], values, {"OTHER": "v"}) == []
    assert values == {}


def test_prefill_with_nothing_loaded_fills_nothing() -> None:
    values: dict[str, object] = {}

    assert keychain.prefill([decl("api_key")], values, {}) == []
    assert values == {}


def test_prefill_of_no_declarations_is_an_empty_list() -> None:
    values: dict[str, object] = {}

    assert keychain.prefill([], values, {"API_KEY": "sk-live"}) == []
    assert values == {}


def test_an_empty_loaded_value_is_refused_at_the_second_gate_too() -> None:
    """`load()` already drops these. Asserted here as well because `prefill()`
    takes the mapping as an argument and must not depend on who built it."""
    values: dict[str, object] = {}

    assert keychain.prefill([decl("api_key")], values, {"API_KEY": ""}) == []
    assert values == {}


def test_several_declarations_are_filled_in_declaration_order() -> None:
    values: dict[str, object] = {}
    declarations = [decl("alpha"), decl("city", params.TYPE_STR), decl("beta")]

    filled = keychain.prefill(
        declarations, values, {"ALPHA": "a", "BETA": "b", "CITY": "Seoul"}
    )

    assert filled == ["alpha", "beta"]
    assert values == {"alpha": "a", "beta": "b"}


def test_two_names_differing_only_in_case_collide_on_one_variable() -> None:
    """The collision the launcher's O2 check refuses at `--set-secret` time.

    Asserted here so the container-side consequence is on the record: nothing in
    Python can tell the two apart, so both declarations receive the SAME value.
    That is why the refusal has to happen where the names are registered, and it
    is why this test asserts the collision rather than a resolution of it.
    """
    values: dict[str, object] = {}

    filled = keychain.prefill([decl("api_key"), decl("API_KEY")], values, {"API_KEY": "one"})

    assert filled == ["api_key", "API_KEY"]
    assert values == {"api_key": "one", "API_KEY": "one"}


# ------------------------------------------------------------------------------
# The token this module may not import
# ------------------------------------------------------------------------------


def test_the_secret_token_is_the_same_one_params_declares() -> None:
    """keychain.py duplicates the token as a literal rather than importing
    `params`, for the same reason settings.py duplicates ENVIRONMENT_KEYS
    (settings.py:95-98): the stdlib-only assertion at
    tests/test_source_seam.py:156-167 admits no first-party import at all.

    Duplication without a cross-check is drift with a delay, so here is the
    cross-check. If the token is ever renamed, this fails rather than the feature
    silently sourcing nothing.
    """
    assert keychain.SECRET_TYPE == params.TYPE_SECRET


def _identifiers(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def _string_constants(tree: ast.Module) -> list[str]:
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def test_keychain_holds_no_platform_knowledge_of_any_kind() -> None:
    """Definition of done, item 1, asserted rather than reviewed.

    Every platform decision is in bash and stays there. If a third platform is
    ever supported, keychain.py does not change and neither does this file.

    Checked on the SYNTAX TREE and not on the raw text, for the reason
    tests/test_source_seam.py:73 already gives about `order_by`: the file's own
    banner has to be able to say which names it refuses to contain, and a
    substring check would make that warning unwritable in a file that tells the
    truth about itself.
    """
    tree = ast.parse((_ROOT / "keychain.py").read_text(encoding="utf-8"))
    names = _identifiers(tree)

    for forbidden in ("subprocess", "platform", "shutil", "os", "Path", "open"):
        assert forbidden not in names, f"keychain.py uses {forbidden!r}"

    for text in _string_constants(tree):
        lowered = text.lower()
        # Docstrings are Constants too, so this reaches them; none of them may
        # carry a client name either.
        assert "secret-tool" not in lowered, "keychain.py names a platform client"
        assert "/usr/bin" not in lowered, "keychain.py names a platform path"


def test_keychain_imports_nothing_outside_the_standard_library() -> None:
    """The same assertion tests/test_source_seam.py makes, duplicated on purpose.

    That one is part of the seam criterion; this one keeps THIS suite runnable on
    a bare interpreter, exactly as memory.py's two copies do
    (tests/test_source_seam.py:114-122).
    """
    tree = ast.parse((_ROOT / "keychain.py").read_text(encoding="utf-8"))

    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    roots.discard("__future__")

    assert roots - set(sys.stdlib_module_names) == set()
