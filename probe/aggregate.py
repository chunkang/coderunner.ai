# ==============================================================================
#  CodeRunner.AI  ::  probe — JSONL to tables
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-PROMPT-001, task T1
#
#  THE VACUITY GUARD IS THE POINT OF THIS MODULE, not a precondition inside it.
#
#  An aggregator that reports 0/0 as "0.0%" makes three different things print
#  the same line: the file was empty, the filter matched nothing, and the model
#  never routed DIRECT. The last is a finding; the first two are bugs. This
#  repository has been burned twice in two days by parsers that silently matched
#  nothing — tests/test_launcher_source.py's whitespace tokenizer on 2026-08-07,
#  which "had been inspecting nothing and would have passed against the one form
#  the SPEC forbids", and the ci.yml regexes that
#  test_the_ci_yml_parsers_are_not_vacuous now guards.
#
#  So emptiness RAISES here. It does not report.
# ==============================================================================

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from probe.classify import CODE, DIRECT

#: Transcribed from spec.md T1 rather than imported from run_probe, so that this
#: module and the writer have to AGREE rather than merely share a constant.
REQUIRED_FIELDS: tuple[str, ...] = (
    "variant_id",
    "task_id",
    "task_text",
    "reply",
    "classification",
    "fence_matches",
    "trial_index",
    "model_tag",
    "model_digest",
    "host",
    "harness_commit",
    "main_commit",
    "timestamp",
)

#: Two-sided 95%. Named rather than inlined because the interval is the whole
#: reason a clean 0/30 must not be read as zero.
_Z_95 = 1.959963984540054


@dataclass(frozen=True)
class Cell:
    """One (variant, task) cell of the measurement."""

    variant_id: str | None
    task_id: str | None
    n: int
    code: int
    direct: int
    fence_trap: int
    direct_unfenced: int

    @property
    def direct_rate(self) -> float:
        """The GATED quantity (spec.md E6, and the rule pre-registered in 4)."""
        return self.direct / self.n

    @property
    def code_rate(self) -> float:
        return self.code / self.n

    @property
    def wilson_95(self) -> tuple[float, float]:
        """95% Wilson score interval on the DIRECT rate.

        Wilson rather than normal-approximation because the interesting cells
        are at or near a boundary, where the normal interval degenerates to
        [0, 0] and invites the reading this whole SPEC is trying to avoid: that
        0/30 means "never". It does not. The upper bound here is about 11%,
        roughly one turn in nine, which is entirely consistent with a user
        having seen exactly one refusal.
        """
        n = float(self.n)
        p = self.direct_rate
        z2 = _Z_95 * _Z_95
        denom = 1.0 + z2 / n
        centre = (p + z2 / (2.0 * n)) / denom
        half = (_Z_95 / denom) * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
        return (max(0.0, centre - half), min(1.0, centre + half))


def _validate(record: dict, position: int) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(
            f"record {position} is missing required field(s): {', '.join(missing)}. "
            "A truncated final line is what a crash mid-write actually produces, "
            "and averaging it into the cell as if it were a trial is how a lost "
            "trial becomes a wrong number."
        )


def summarise(
    records: Sequence[dict],
    variant_id: str | None = None,
    task_id: str | None = None,
) -> Cell:
    """Reduce records to one Cell, or RAISE if there is nothing to reduce.

    Raises ValueError when the selection is empty — see this module's banner.
    """
    selected = [
        record
        for record in records
        if (variant_id is None or record.get("variant_id") == variant_id)
        and (task_id is None or record.get("task_id") == task_id)
    ]

    if not selected:
        raise ValueError(
            f"empty record set for variant={variant_id!r} task={task_id!r} — "
            f"{len(records)} record(s) were offered and none matched. Refusing to "
            "report 0/0 as 0.0%, because that reads identically to a measured zero."
        )

    for position, record in enumerate(selected):
        _validate(record, position)

    code = sum(1 for record in selected if record["classification"] == CODE)
    direct = sum(1 for record in selected if record["classification"] == DIRECT)
    trap = sum(
        1
        for record in selected
        if record["classification"] == DIRECT and int(record["fence_matches"]) > 0
    )

    unclassified = len(selected) - code - direct
    if unclassified:
        raise ValueError(
            f"{unclassified} record(s) carry a classification that is neither "
            f"{CODE} nor {DIRECT}; the cell would silently under-count."
        )

    return Cell(
        variant_id=variant_id,
        task_id=task_id,
        n=len(selected),
        code=code,
        direct=direct,
        fence_trap=trap,
        direct_unfenced=direct - trap,
    )


def load_jsonl(lines: Iterable[str]) -> list[dict]:
    """Parse JSONL, skipping only a truncated FINAL line.

    A malformed line anywhere else is a corrupted run rather than an interrupted
    one, and silently dropping it would shrink N without saying so.
    """
    parsed: list[dict] = []
    pending = [line for line in (raw.strip() for raw in lines) if line]
    for position, line in enumerate(pending):
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            if position != len(pending) - 1:
                raise
    return parsed


def format_cell(cell: Cell) -> str:
    """One human-readable line, carrying N and the interval every time."""
    low, high = cell.wilson_95
    return (
        f"variant={cell.variant_id} task={cell.task_id} "
        f"N={cell.n} CODE={cell.code} DIRECT={cell.direct} "
        f"direct_rate={cell.direct_rate:.1%} "
        f"wilson95=[{low:.1%}, {high:.1%}] "
        f"fence_trap={cell.fence_trap} direct_unfenced={cell.direct_unfenced}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Summarise probe JSONL into cells.")
    parser.add_argument("path", nargs="?", default="-", help="JSONL file, or - for stdin")
    args = parser.parse_args(argv)

    if args.path == "-":
        lines = sys.stdin.readlines()
    else:
        with open(args.path, encoding="utf-8") as handle:
            lines = handle.readlines()

    records = load_jsonl(lines)
    if not records:
        raise ValueError(f"empty record set: {args.path} yielded no parsable records")

    seen = sorted({(record["variant_id"], record["task_id"]) for record in records})
    for variant_id, task_id in seen:
        print(format_cell(summarise(records, variant_id=variant_id, task_id=task_id)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
