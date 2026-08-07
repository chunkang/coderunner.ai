# ==============================================================================
#  CodeRunner.AI  ::  source-level assertions about the storage seam
# ------------------------------------------------------------------------------
#  Project : SPEC-MEMORY-001 v1.1.0, task T-VS11
#  Covers  : AC-13 (`order_by` appears nowhere) and AC-14 (the seam holds).
#
#  Source-level assertions are unusual, and both are justified by the same
#  property: the failures they prevent are INVISIBLE AT RUNTIME. `order_by` is
#  accepted and silently ignored, so the wrong records are deleted, the counts
#  are right and nothing is logged; and a `pymilvus` import leaking into
#  memory.py breaks nothing at all until someone tries to run the primitive
#  suite on a bare interpreter and finds a 352 MB dependency in the way.
#
#  Everything here is AST analysis of text on disk. Nothing is imported, so this
#  file runs on BARE PYTEST with no third-party package installed at all.
# ==============================================================================

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent

#: The first-party product modules. `.claude/` and `.moai/` are agent tooling
#: and are not product code; `conftest.py` and `tests/` are the harness.
FIRST_PARTY = (
    "keychain.py",
    "main.py",
    "memory.py",
    "params.py",
    "recall.py",
    "settings.py",
    "tools.py",
    "vectorstore.py",
)


def parse(name: str) -> ast.Module:
    return ast.parse((_ROOT / name).read_text(encoding="utf-8"))


def imported_roots(tree: ast.Module) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    roots.discard("__future__")
    return roots


# ------------------------------------------------------------------------------
# AC-13 — `order_by` appears nowhere  (trap C, R13)
# ------------------------------------------------------------------------------


@pytest.mark.parametrize("name", FIRST_PARTY)
def test_order_by_is_never_passed_to_anything(name: str) -> None:
    """AC-13: V5 proved the parameter is swallowed by the dynamic-kwargs path.

    It raises nothing and returns insertion order, unsorted:

        inserted in order          : [50, 10, 90, 30, 70, 20, 80, 40, 60, 0]
        query limit=5, order_by=seq: [50, 10, 90, 30, 70]   <- IDENTICAL

    So an implementation that queries "the oldest N" and deletes them evicts
    ARBITRARY records while every count stays correct. The check is on the AST
    rather than on the raw text precisely so that the WARNING COMMENT the next
    test requires does not have to be written in code that lies about itself.
    """
    tree = parse(name)

    keywords = [
        node.arg
        for node in ast.walk(tree)
        if isinstance(node, ast.keyword) and node.arg == "order_by"
    ]
    assert keywords == [], f"{name} passes order_by=, which Milvus silently ignores"

    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value == "order_by"
    ]
    assert literals == [], f"{name} carries an 'order_by' string literal"


def test_the_pruning_site_records_why_the_loop_must_stay_a_loop() -> None:
    """AC-13: the comment is PART of the criterion, not decoration.

    The next reader, seeing a converging delete-by-filter loop where a one-line
    sorted query would "obviously" do, will otherwise reintroduce the bug — and
    nothing at runtime will tell them.
    """
    source = (_ROOT / "vectorstore.py").read_text(encoding="utf-8")
    prune = source[source.index("    def _prune(") : source.index("    def delete(")]
    flat = " ".join(prune.split())

    assert "order_by" in flat
    assert "SILENTLY IGNORED" in flat.upper()
    assert "16,384" in flat  # query() cannot enumerate the collection either
    assert 'DO NOT "simplify" this into a sorted query.' in flat


# ------------------------------------------------------------------------------
# AC-14 — the storage seam holds  (C12/D5)
# ------------------------------------------------------------------------------


def test_memory_py_imports_only_stdlib() -> None:
    """AC-14: the same assertion as tests/test_memory_primitives.py, verbatim.

    Duplicated on purpose. That one exists to keep memory.py's own suite
    runnable on a bare interpreter; this one is part of the seam criterion, and
    losing either half would be a silent loss.
    """
    non_stdlib = imported_roots(parse("memory.py")) - set(sys.stdlib_module_names)
    assert non_stdlib == set(), f"memory.py must import stdlib only; found {sorted(non_stdlib)}"


def test_vectorstore_is_the_only_first_party_module_importing_pymilvus() -> None:
    importers = {name for name in FIRST_PARTY if "pymilvus" in imported_roots(parse(name))}
    assert importers == {"vectorstore.py"}


def test_recall_imports_ollama_but_not_pymilvus_and_not_the_store() -> None:
    """recall.py isolates the embedding backend; it must not acquire a second.

    Importing vectorstore.py here would drag `pymilvus` in transitively, and
    tests/test_recall.py would stop being runnable without a live Milvus — one
    of the four testability constraints acceptance.md fixes.
    """
    roots = imported_roots(parse("recall.py"))
    assert "ollama" in roots
    assert "pymilvus" not in roots
    assert "vectorstore" not in roots


@pytest.mark.parametrize("name", FIRST_PARTY)
def test_no_first_party_module_imports_numpy(name: str) -> None:
    """AC-14: numpy is ACCEPTED as a transitive dependency, not ADOPTED.

    It arrives in the image with pymilvus[milvus_lite] whether we like it or
    not (V4 1). Out-of-scope item 7 permits its presence and forbids its use;
    without this assertion "it is already installed" becomes a standing
    argument for importing it anywhere, and C6's replacement — a single storage
    seam — quietly stops being the only place vector maths happens.
    """
    assert "numpy" not in imported_roots(parse(name))


def test_params_and_settings_and_keychain_import_only_stdlib() -> None:
    """SPEC-INPUT-001 spec.md 5.2, extended by SPEC-KEYCHAIN-001 spec.md 5: three
    stdlib-only leaves, extending the seam rather than departing from it.

    All three are gated at 100%, and none has vectorstore.py's excuse for 85%:
    with no external dependency there is no line in any of them that a test
    cannot reach. The moment a third-party import lands here, that stops being
    true and the floor becomes something to argue about rather than something to
    meet.

    keychain.py's claim is the strongest of the three and the assertion is what
    holds it: it may not import `params` either, which is why it duplicates the
    `secret` token as a literal (keychain.py:SECRET_TYPE) with a cross-check in
    tests/test_keychain.py. Reach for `import params` here and this fails.
    """
    for name in ("params.py", "settings.py", "keychain.py"):
        non_stdlib = imported_roots(parse(name)) - set(sys.stdlib_module_names)
        assert non_stdlib == set(), f"{name} must import stdlib only; found {sorted(non_stdlib)}"


# ------------------------------------------------------------------------------
# AC-IMAGE — every first-party module main.py imports is in the image
# ------------------------------------------------------------------------------
#
# This criterion exists because the repository has already got this wrong.
# `Dockerfile:34` shipped five modules for a whole SPEC while `main.py` imported
# seven, and `import params` inside `coderunner-ai:latest` raised
# ModuleNotFoundError. It went unnoticed because `coderunner:163` builds only
# when the image is ABSENT, so editing source never triggers a rebuild and the
# stale image kept importing an older `main.py` that needed neither module —
# product.md 6.3's "stale-image hazard", concealing a second defect underneath
# itself.
#
# The module list is derived from main.py's OWN IMPORT BLOCK rather than from a
# hand-maintained second list, so the next module added to the application fails
# this test instead of shipping missing. A second list would have to be updated
# by exactly the person who just forgot to update the first one.


def _dockerfile_copy_sources() -> list[str]:
    """The file names on the Dockerfile `COPY … ./` line that ships the app."""
    lines = (_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    copies = [line.split() for line in lines if line.startswith("COPY ") and "main.py" in line]
    assert len(copies) == 1, "expected exactly one COPY line carrying main.py"
    return copies[0][1:-1]  # drop the COPY keyword and the destination


def _first_party_imports_of_main() -> set[str]:
    """Every module main.py imports that exists as a .py file beside it."""
    return {
        f"{root}.py"
        for root in imported_roots(parse("main.py"))
        if (_ROOT / f"{root}.py").is_file()
    }


def test_the_image_copies_every_first_party_module_main_imports() -> None:
    """AC-IMAGE, asserted at source level so it runs without a Docker daemon.

    The other half of the criterion — a real `docker compose build` followed by
    `import main` inside the resulting image — is a manual verification, because
    the defect this replaces survived a whole SPEC of people READING this line
    and finding it fine. This test is what stops a fourth occurrence; the build
    is what proves the third one is over.
    """
    copied = set(_dockerfile_copy_sources())
    required = _first_party_imports_of_main() | {"main.py"}

    missing = sorted(required - copied)
    assert missing == [], (
        f"Dockerfile does not COPY {missing}; the built image's main.py will die "
        "at import with a ModuleNotFoundError and no diagnostic beyond a traceback"
    )


def test_every_module_the_image_copies_still_exists_in_the_tree() -> None:
    """The other direction, which costs one line and catches a rename.

    A COPY naming a file that no longer exists fails the BUILD rather than the
    run — loudly, but only for whoever builds next, which under coderunner:163's
    build-if-absent rule can be months later.
    """
    for name in _dockerfile_copy_sources():
        assert (_ROOT / name).is_file(), f"Dockerfile copies {name}, which is not in the tree"


# ------------------------------------------------------------------------------
# AC-INJ — params.py has exactly ONE literal-emission site  (SPEC-INPUT-001 U1)
# ------------------------------------------------------------------------------
#
# Measured 2026-08-06, with value = 'Seoul"; import os; os.system("id"); x="':
#
#     f'city = "{value}"'   ->  rc 0, stdout begins `uid=501(kurapa) …`
#     f'city = {value!r}'   ->  rc 0, stdout `39 'Seoul"; …'`
#
# BOTH EXIT 0. Both produce output. In the REPL the first one shows a green
# `Execution OK (rc=0)` panel, the model receives the stdout as success feedback
# and the turn is captured as a solved task. The difference is two characters
# inside an f-string that a reviewer reads as "put the city in the script".
#
# The runtime half of AC-INJ is in tests/test_main_integration.py. This half is
# the structural one: a module with exactly one emission site has exactly one
# line for that criterion to be protecting.


def _quote_adjacent_interpolations(tree: ast.Module) -> list[str]:
    """Every f-string placeholder sitting next to a literal quote character."""
    offences: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                if "'" in part.value or '"' in part.value:
                    offences.append(f"line {node.lineno}: {part.value!r}")
    return offences


def test_params_py_has_exactly_one_literal_emission_site() -> None:
    """One function, one `repr()`, so there is no second path a raw value
    could take. `_literal()` may be CALLED from more than one place; what must
    not exist is a second place that turns a value into source text."""
    tree = parse("params.py")

    repr_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "repr"
    ]
    assert len(repr_calls) == 1, f"params.py makes {len(repr_calls)} repr() calls; expected 1"


def test_no_f_string_in_params_py_puts_a_value_between_quotes() -> None:
    """The forbidden construction, stated as a property of the syntax tree.

    `f'city = "{value}"'` is what M3 measured executing `os.system("id")`. Any
    f-string in this module whose literal parts carry a quote character is either
    that bug or one edit away from it, so the assertion is on the absence of the
    quote rather than on the absence of the adjacency.
    """
    assert _quote_adjacent_interpolations(parse("params.py")) == []


def test_params_py_uses_no_percent_formatting_or_str_format() -> None:
    """The same hazard in its two other spellings.

    `'city = "%s"' % value` and `'city = "{}"'.format(value)` are exactly as
    unsafe as the f-string and would slip past a check written only for f-strings.
    """
    tree = parse("params.py")

    modulo = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Mod)
        and isinstance(node.left, ast.Constant)
        and isinstance(node.left.value, str)
    ]
    assert modulo == [], "params.py uses %-formatting on a string literal"

    formats = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
    ]
    assert formats == [], "params.py calls .format() on something"


# ------------------------------------------------------------------------------
# AC-STDIN — the child's stdin is untouched  (SPEC-INPUT-001 U2, N1)
# ------------------------------------------------------------------------------


def test_run_python_passes_no_stdin_argument() -> None:
    """Measured 2026-08-06 against `run_python()`'s exact argument list, for a
    script whose only statement is `input("hi: ")`:

        rc = 1, stdout = 'hi: ', stderr = EOFError: EOF when reading a line

    `capture_output=True` pipes stdout and stderr and says NOTHING about stdin,
    so the child inherits the parent's descriptor 0. Under pytest that is closed
    or a pipe, hence the EOFError. Inside the container it is the REPL's own TTY
    (docker-compose.yml:67-68), so the child would BLOCK, consuming the user's
    keystrokes, for the full CODERUNNER_TIMEOUT — a silent thirty-second hijack
    of the terminal the user is sitting at.

    Asserted at source level rather than by observing a run, so it survives a
    refactor: SPEC-INPUT-001 adds a `prelude` argument to this function and the
    property being protected is that it added nothing else.
    """
    tree = parse("main.py")

    subprocess_runs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]
    assert subprocess_runs, "main.py no longer calls subprocess.run at all"

    for call in subprocess_runs:
        passed = {keyword.arg for keyword in call.keywords}
        assert "stdin" not in passed, "run_python() now passes stdin= to the child"


def test_the_prompt_still_forbids_input_and_now_offers_an_alternative() -> None:
    """N1: main.py:136 is AMENDED, NOT DELETED. M1 is why it is there.

    Read from the source rather than from an import so this runs on a bare
    interpreter with the rest of the file.
    """
    source = (_ROOT / "main.py").read_text(encoding="utf-8")
    prompt = source[source.index("SYSTEM_PROMPT = ") : source.index("# Data model")]

    assert "No input()" in prompt
    assert "do NOT call input()" in prompt
    assert "# @param" in prompt


def test_the_prompt_describes_no_second_fenced_block() -> None:
    """AC-SYN, asserted on the instruction rather than only on the parser.

    Measured 2026-08-06: a ```params``` block placed BEFORE the ```python``` block
    makes CODE_BLOCK_RE.findall() return `['']` — the closing fence of the first
    pairs with the opening fence of the second — so extract_last_python_block()
    returns the empty string, `if not code:` is TRUE, and the turn silently
    answers as if no code had been produced. No exception, no failed execution,
    no retry. Reverse the order and it works, which is why N5 forbids the form
    outright rather than mandating an order.
    """
    source = (_ROOT / "main.py").read_text(encoding="utf-8")
    prompt = source[source.index("SYSTEM_PROMPT = ") : source.index("# Data model")]

    assert prompt.count("```") == 2, "SYSTEM_PROMPT now describes more than one fenced block"
    assert "```params" not in prompt


def test_the_sandbox_still_receives_only_the_tools_module() -> None:
    """No memory module may be copied into a generated script's sandbox (R6).

    `run_python()` copies TOOLS_MODULE and nothing else. Adding memory.py,
    recall.py or vectorstore.py would hand model-written code a direct handle
    on ~1 GB of the user's task history. No change was required here — the
    requirement is simply not to make one.
    """
    source = (_ROOT / "main.py").read_text(encoding="utf-8")
    body = source[source.index("def run_python(") : source.index("# Status renderers")]

    assert "shutil.copy2(TOOLS_MODULE" in body
    for forbidden in ("memory.py", "recall.py", "vectorstore.py", "MEMORY_DB"):
        assert forbidden not in body
