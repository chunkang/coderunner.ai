# ==============================================================================
#  CodeRunner.AI  ::  probe — the runner
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-PROMPT-001, tasks T1 / T2
#
#  HOW TO RUN IT. Records go to STDOUT and the HOST shell redirects them. The
#  container runs as uid 1000 against a host-owned bind mount, so requiring the
#  process to open a file for writing inside /work is a permission failure
#  waiting to happen; the shell that owns the directory does the writing.
#
#    docker compose run --rm -v "$PWD":/work -w /work \
#      --entrypoint python coderunner -m probe.run_probe \
#      --variant V0 --task target --n 30 \
#      >> .moai/specs/SPEC-PROMPT-001/probe-runs/v0-target.jsonl
#
#  `-m probe.run_probe`, NOT `probe/run_probe.py`. Invoking by PATH puts
#  /work/probe on sys.path instead of /work, and `from main import ...` then
#  raises ModuleNotFoundError (measured 2026-08-08). `-m` puts the working
#  directory on the path, which is where main.py is bind-mounted.
#
#  Progress goes to STDERR, so it stays on the terminal and out of the data.
#  Use `>>` with --resume-from pointed at the same file: at ~128 s per trial
#  (measured 2026-08-08, CPU-only sidecar) a 30-trial cell is about an hour, and
#  starting over after a crash is the thing resumability exists to prevent.
#
#  SAMPLING IS NOT SET HERE AND MUST NEVER BE (spec.md N10). This drives
#  main.stream_llm() (main.py:209-221), which passes no options= to client.chat,
#  so the probe inherits PRODUCTION sampling by construction. Pinning
#  temperature or setting a seed would produce a cleaner number about a
#  different distribution from the one that produced the reported refusal.
#  tests/test_probe.py asserts the absence by AST.
#
#  WHAT IS RECORDED INSTEAD is provenance: the model tag and digest read back
#  from the RUNNING SERVER, the modelfile parameters, and the observed
#  OLLAMA_HOST. docker-compose.yml:46 and :78 are ${CODERUNNER_MODEL:-llama3.1:8b}
#  — a DEFAULT, not a pin — so the compose file states an intention and only the
#  server states a fact (spec.md S4).
# ==============================================================================

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections.abc import Iterable, Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from main import MODEL_NAME, OLLAMA_HOST, stream_llm
from probe import tasks as task_module
from probe import variants as variant_module
from probe.classify import classify, fence_matches

_ROOT = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------------------
# Provenance
# ------------------------------------------------------------------------------


def _get(payload: Any, key: str, default: Any = None) -> Any:
    """Subscript first, attribute second.

    conftest.py's FakeEmbedClient banner records why: ollama 0.3.0 returns a
    TypedDict (a plain dict at runtime) and 0.6.2 returns a pydantic model.
    Subscript works on both; attribute access raises on 0.3.0. The fallback is
    for nested pydantic objects that are not subscriptable at all.
    """
    try:
        return payload[key]
    except (KeyError, TypeError, IndexError):
        return getattr(payload, key, default)


def _head_commit(root: Path) -> str | None:
    """Read HEAD out of .git with the stdlib, because the image has no git binary.

    Returns None rather than guessing. An unknown commit recorded as None is a
    gap; an unknown commit recorded as a plausible string is a lie.
    """
    head_file = root / ".git" / "HEAD"
    if not head_file.is_file():
        return None
    head = head_file.read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head or None

    ref = head[len("ref: ") :].strip()
    ref_file = root / ".git" / ref
    if ref_file.is_file():
        return ref_file.read_text(encoding="utf-8").strip() or None

    packed = root / ".git" / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line.endswith(f" {ref}"):
                return line.split(maxsplit=1)[0]
    return None


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_provenance(
    client: Any,
    host: str = OLLAMA_HOST,
    server_version: str | None = None,
) -> dict:
    """Read the model back from the running server. Never from configuration.

    NO NETWORK BEYOND THE CLIENT. server_version is passed in rather than
    fetched, so this function stays callable from a fully offline test with a
    fake client — which is what tests/test_probe.py does.
    """
    listing = _get(client.list(), "models", []) or []
    digest = None
    for entry in listing:
        name = _get(entry, "model", None) or _get(entry, "name", None)
        if name == MODEL_NAME:
            digest = _get(entry, "digest", None)
            break

    shown = client.show(MODEL_NAME)
    details = _get(shown, "details", {}) or {}

    head = _head_commit(_ROOT)
    return {
        "model_tag": MODEL_NAME,
        "model_digest": digest,
        "quantisation": _get(details, "quantization_level", None),
        "parameter_size": _get(details, "parameter_size", None),
        "family": _get(details, "family", None),
        "model_format": _get(details, "format", None),
        # Whatever the modelfile pins. The harness pins nothing (N10); this is
        # the record of what it therefore inherited.
        "modelfile_parameters": _get(shown, "parameters", None),
        "ollama_server_version": server_version,
        "host": host,
        # HEAD at run time, for BOTH, and the sha256 below is what actually
        # anchors the bytes: HEAD does not know whether the tree is dirty, and
        # the image carries no git binary to ask.
        "harness_commit": head,
        "main_commit": head,
        "main_sha256": _sha256(_ROOT / "main.py"),
        "python_version": sys.version.split()[0],
    }


def server_version(host: str) -> str | None:
    """Ask the server its version. Called only from main(), never from a test."""
    import httpx

    try:
        response = httpx.get(f"{host.rstrip('/')}/api/version", timeout=5.0)
        return _get(response.json(), "version", None)
    except (httpx.HTTPError, ValueError):
        return None


# ------------------------------------------------------------------------------
# One trial
# ------------------------------------------------------------------------------


def run_trial(
    client: Any,
    variant_id: str,
    task: task_module.Task,
    trial_index: int,
    provenance: dict,
) -> dict:
    """Drive one trial and return one record.

    A FRESH TWO-MESSAGE CONVERSATION, every time: the system prompt and one user
    message, with no recall block and no accumulated history. That is the
    first-turn shape which produced the reported refusal (spec.md 2.4). Carrying
    the previous trial's exchange forward would measure a conversation instead,
    and the cell would stop being N independent observations.
    """
    prompt = variant_module.VARIANTS[variant_id]
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": task.text},
    ]

    started = time.monotonic()
    reply = "".join(stream_llm(client, messages))
    elapsed = time.monotonic() - started

    return {
        "variant_id": variant_id,
        "task_id": task.id,
        "task_kind": task.kind,
        "task_text": task.text,
        "expect_direct": task.expect_direct,
        "reply": reply,
        "classification": classify(reply),
        "fence_matches": fence_matches(reply),
        "trial_index": trial_index,
        "elapsed_sec": round(elapsed, 3),
        "timestamp": datetime.now(UTC).isoformat(),
        "model_tag": provenance["model_tag"],
        "model_digest": provenance["model_digest"],
        "host": provenance["host"],
        "harness_commit": provenance["harness_commit"],
        "main_commit": provenance["main_commit"],
        "main_sha256": provenance["main_sha256"],
        "quantisation": provenance["quantisation"],
        "ollama_server_version": provenance["ollama_server_version"],
    }


# ------------------------------------------------------------------------------
# Resumability
# ------------------------------------------------------------------------------


def completed_keys(lines: Iterable[str]) -> set[tuple[str, str, int]]:
    """Read back (variant, task, index) triples already on disk.

    At 20-90 s per trial on a CPU-only sidecar a 220-trial baseline is hours, so
    a crash must cost one cell rather than a night. THE INDEX IS PART OF THE KEY:
    without it a resumed run either repeats a whole cell or skips one it never
    finished.

    A truncated final line is the NORMAL case after a crash, not an edge case, so
    an unparsable line is skipped rather than fatal.
    """
    keys: set[tuple[str, str, int]] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        try:
            keys.add((record["variant_id"], record["task_id"], int(record["trial_index"])))
        except (KeyError, TypeError, ValueError):
            continue
    return keys


def _resolve_tasks(selector: str) -> list[task_module.Task]:
    if selector == "all":
        return list(task_module.ALL_TASKS)
    if selector == "measurement":
        return list(task_module.MEASUREMENT_TASKS)
    if selector == "controls":
        return list(task_module.CONTROL_SET)
    if selector in task_module.TASKS:
        return [task_module.TASKS[selector]]
    known = ", ".join(sorted(task_module.TASKS))
    raise SystemExit(f"unknown --task {selector!r}; expected one of: all, measurement, {known}")


def iter_records(
    client: Any,
    variant_id: str,
    selected: Sequence[task_module.Task],
    provenance: dict,
    override_n: int | None,
    done: set[tuple[str, str, int]],
) -> Iterator[dict]:
    for task in selected:
        planned = override_n if override_n is not None else task.n
        for index in range(planned):
            if (variant_id, task.id, index) in done:
                print(f"  skip {variant_id}/{task.id}#{index} (already recorded)", file=sys.stderr)
                continue
            record = run_trial(client, variant_id, task, index, provenance)
            print(
                f"  {variant_id}/{task.id}#{index + 1}/{planned} "
                f"-> {record['classification']} "
                f"(fences={record['fence_matches']}, {record['elapsed_sec']}s)",
                file=sys.stderr,
            )
            yield record


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Drive one prompt variant against one task set, N times.",
    )
    parser.add_argument("--variant", required=True, choices=sorted(variant_module.VARIANTS))
    parser.add_argument("--task", required=True, help="a task id, or all / measurement / controls")
    parser.add_argument("--n", type=int, default=None, help="override the task's planned N")
    parser.add_argument("--host", default=OLLAMA_HOST, help="Ollama host; default is main.py's")
    parser.add_argument(
        "--resume-from",
        default=None,
        help="an existing JSONL whose (variant, task, index) triples are skipped",
    )
    args = parser.parse_args(argv)

    import ollama

    selected = _resolve_tasks(args.task)
    client = ollama.Client(host=args.host)
    provenance = collect_provenance(
        client,
        host=args.host,
        server_version=server_version(args.host),
    )

    done: set[tuple[str, str, int]] = set()
    if args.resume_from:
        resume_path = Path(args.resume_from)
        if resume_path.is_file():
            with resume_path.open(encoding="utf-8") as handle:
                done = completed_keys(handle)

    print(f"probe: variant={args.variant} host={args.host}", file=sys.stderr)
    tag, digest = provenance["model_tag"], provenance["model_digest"]
    print(f"probe: model={tag} digest={digest}", file=sys.stderr)
    print(f"probe: quantisation={provenance['quantisation']}", file=sys.stderr)
    print(f"probe: resuming past {len(done)} recorded trial(s)", file=sys.stderr)

    written = 0
    for record in iter_records(client, args.variant, selected, provenance, args.n, done):
        sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        written += 1

    print(f"probe: wrote {written} record(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
