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
FIRST_PARTY = ("main.py", "memory.py", "recall.py", "tools.py", "vectorstore.py")


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
