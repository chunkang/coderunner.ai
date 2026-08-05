# ==============================================================================
#  CodeRunner.AI  ::  memory.py primitives — env parsing, vectors, task hashing
# ------------------------------------------------------------------------------
#  Project : SPEC-MEMORY-001, task T2
#  Covers  : AC-8 (configuration robustness) at helper level; the float32
#            round-trip contract that every later similarity assertion rests on.
# ==============================================================================

from __future__ import annotations

import math
from array import array

import pytest

import memory
from conftest import FLOAT32_TOL

# ------------------------------------------------------------------------------
# memory.py must stay free of third-party imports (plan.md 1.1)
# ------------------------------------------------------------------------------


def test_memory_module_imports_only_stdlib() -> None:
    """The whole point of the two-module split: this suite runs on bare pytest.

    If someone adds `import ollama`/`import rich`/`import numpy` to memory.py,
    every storage test silently acquires a third-party dependency and the
    testability constraint in acceptance.md quietly stops being true.
    """
    import ast
    import sys
    from pathlib import Path

    source = Path(memory.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported_roots.add(node.module.split(".")[0])

    imported_roots.discard("__future__")
    non_stdlib = imported_roots - set(sys.stdlib_module_names)
    assert non_stdlib == set(), f"memory.py must import stdlib only; found {sorted(non_stdlib)}"


# ------------------------------------------------------------------------------
# env_bool
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("  yes  ", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("No", False),
        ("off", False),
    ],
)
def test_env_bool_recognised_values(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
) -> None:
    monkeypatch.setenv("CR_TEST_BOOL", raw)
    assert memory.env_bool("CR_TEST_BOOL", not expected) is expected


@pytest.mark.parametrize("raw", ["", "   ", "maybe", "2", "yeah"])
def test_env_bool_unparseable_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setenv("CR_TEST_BOOL", raw)
    assert memory.env_bool("CR_TEST_BOOL", True) is True
    assert memory.env_bool("CR_TEST_BOOL", False) is False


def test_env_bool_unset_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # AC-8: an absent variable (`None` from os.environ.get) yields the default.
    monkeypatch.delenv("CR_TEST_BOOL", raising=False)
    assert memory.env_bool("CR_TEST_BOOL", True) is True
    assert memory.env_bool("CR_TEST_BOOL", False) is False


# ------------------------------------------------------------------------------
# env_int / env_float  — AC-8
# ------------------------------------------------------------------------------


def test_env_int_parses_and_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CR_TEST_INT", "3")
    assert memory.env_int("CR_TEST_INT", 1, 1, 5) == 3


def test_env_int_non_numeric_falls_back_to_default_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # AC-8: CODERUNNER_MEMORY_TOP_K=abc -> 1. No ValueError escapes, in
    # deliberate contrast to the bare int(os.environ.get(...)) at main.py:53-54
    # which crashes at import time before any Rich rendering.
    monkeypatch.setenv("CR_TEST_INT", "abc")
    assert memory.env_int("CR_TEST_INT", 1, 1, 5) == 1


def test_env_int_zero_clamps_to_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    # AC-8: CODERUNNER_MEMORY_MAX_RECORDS=0 -> clamped to the documented
    # minimum of 10, never accepted as a degenerate value.
    monkeypatch.setenv("CR_TEST_INT", "0")
    assert memory.env_int("CR_TEST_INT", 500, 10, 50000) == 10


def test_env_int_above_maximum_clamps_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CR_TEST_INT", "999999")
    assert memory.env_int("CR_TEST_INT", 500, 10, 50000) == 50000


def test_env_int_negative_clamps_to_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CR_TEST_INT", "-7")
    assert memory.env_int("CR_TEST_INT", 1, 1, 5) == 1


def test_env_int_unset_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CR_TEST_INT", raising=False)
    assert memory.env_int("CR_TEST_INT", 1, 1, 5) == 1


def test_env_int_empty_string_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CR_TEST_INT", "")
    assert memory.env_int("CR_TEST_INT", 1, 1, 5) == 1


def test_env_float_parses_and_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CR_TEST_FLOAT", "0.42")
    assert memory.env_float("CR_TEST_FLOAT", 0.65, 0.0, 1.0) == pytest.approx(0.42, abs=FLOAT32_TOL)


def test_env_float_empty_string_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # AC-8: CODERUNNER_MEMORY_MIN_SIMILARITY="" -> 0.65 (constraint C5).
    monkeypatch.setenv("CR_TEST_FLOAT", "")
    assert memory.env_float("CR_TEST_FLOAT", 0.65, 0.0, 1.0) == pytest.approx(0.65, abs=FLOAT32_TOL)


def test_env_float_non_numeric_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CR_TEST_FLOAT", "high")
    assert memory.env_float("CR_TEST_FLOAT", 0.65, 0.0, 1.0) == pytest.approx(0.65, abs=FLOAT32_TOL)


@pytest.mark.parametrize(("raw", "expected"), [("-1.5", 0.0), ("2.5", 1.0)])
def test_env_float_clamps_out_of_range(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: float
) -> None:
    monkeypatch.setenv("CR_TEST_FLOAT", raw)
    assert memory.env_float("CR_TEST_FLOAT", 0.65, 0.0, 1.0) == pytest.approx(
        expected, abs=FLOAT32_TOL
    )


def test_env_float_unset_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CR_TEST_FLOAT", raising=False)
    assert memory.env_float("CR_TEST_FLOAT", 0.65, 0.0, 1.0) == pytest.approx(0.65, abs=FLOAT32_TOL)


def test_env_float_nan_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # float("nan") parses cleanly but would poison every downstream comparison,
    # so it must be treated as unparseable rather than clamped.
    monkeypatch.setenv("CR_TEST_FLOAT", "nan")
    assert memory.env_float("CR_TEST_FLOAT", 0.65, 0.0, 1.0) == pytest.approx(0.65, abs=FLOAT32_TOL)


# ------------------------------------------------------------------------------
# l2_normalise
# ------------------------------------------------------------------------------


def test_l2_normalise_yields_unit_length() -> None:
    normalised = memory.l2_normalise([3.0, 4.0])
    assert normalised == pytest.approx([0.6, 0.8], abs=FLOAT32_TOL)
    assert math.sqrt(sum(v * v for v in normalised)) == pytest.approx(1.0, abs=FLOAT32_TOL)


def test_l2_normalise_is_idempotent() -> None:
    once = memory.l2_normalise([1.0, 2.0, 2.0])
    twice = memory.l2_normalise(once)
    assert twice == pytest.approx(once, abs=FLOAT32_TOL)


def test_l2_normalise_of_zero_vector_does_not_divide_by_zero() -> None:
    assert memory.l2_normalise([0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]


def test_l2_normalise_of_empty_vector_is_empty() -> None:
    assert memory.l2_normalise([]) == []


# ------------------------------------------------------------------------------
# dot
# ------------------------------------------------------------------------------


def test_dot_of_identical_unit_vectors_is_one() -> None:
    vec = memory.l2_normalise([1.0, 2.0, 3.0])
    assert memory.dot(vec, vec) == pytest.approx(1.0, abs=FLOAT32_TOL)


def test_dot_of_orthogonal_unit_vectors_is_zero() -> None:
    assert memory.dot([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0, abs=FLOAT32_TOL)


def test_dot_survives_the_float32_round_trip() -> None:
    """The realistic path: normalise in float64, persist as float32, compare.

    Milvus FLOAT_VECTOR is single precision, exactly as the SQLite BLOB was, so
    self-similarity comes back at ~0.9999997 and occasionally a hair above 1.0.
    `array('f')` stands in for the engine here so that this stays a bare-pytest
    test of the CONTRACT every similarity assertion rests on — pack_vector and
    unpack_vector went with the BLOB codec they existed for.
    """
    vec = memory.l2_normalise([0.37, -0.91, 0.15, 0.44])
    restored = list(array("f", vec))
    assert restored != vec  # the round trip really is lossy
    assert memory.dot(vec, restored) == pytest.approx(1.0, abs=FLOAT32_TOL)


def test_dot_of_mismatched_lengths_is_zero_not_an_exception() -> None:
    # A length mismatch means the pair is not comparable at all. Returning 0.0
    # makes it a guaranteed miss; raising would put an exception in the middle
    # of a turn, which M5 forbids.
    assert memory.dot([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0


# ------------------------------------------------------------------------------
# normalise_task / task_hash
# ------------------------------------------------------------------------------


def test_normalise_task_strips_casefolds_and_collapses_whitespace() -> None:
    assert memory.normalise_task("  Sum   THE\tFirst\n10 Primes  ") == "sum the first 10 primes"


def test_normalise_task_of_blank_input_is_empty() -> None:
    assert memory.normalise_task("   \t\n ") == ""


def test_task_hash_is_a_sha256_hexdigest() -> None:
    digest = memory.task_hash("anything")
    assert len(digest) == 64
    assert all(char in "0123456789abcdef" for char in digest)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("Sum the primes", "  sum the primes  "),
        ("Sum the primes", "SUM   THE\tPRIMES"),
        ("Sum\nthe primes", "Sum the primes"),
    ],
)
def test_task_hash_is_stable_across_normalisation(left: str, right: str) -> None:
    assert memory.task_hash(left) == memory.task_hash(right)


def test_task_hash_differs_for_different_tasks() -> None:
    assert memory.task_hash("sum the primes") != memory.task_hash("sum the squares")
