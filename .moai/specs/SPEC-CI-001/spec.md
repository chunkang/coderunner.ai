---
id: SPEC-CI-001
version: "1.0.0"
status: "draft"
created: "2026-08-05"
updated: "2026-08-05"
author: "Chun Kang"
priority: "HIGH"
---

## HISTORY

### v1.0.0 (2026-08-05) — Initial specification

Written against `tech.md` §8.3 ("No CI"), which is the gap this SPEC closes and which states
the case better than a restatement would: *"A gate that exists, passes locally, and is never
executed by anything but a human is one commit away from being decorative."* SPEC-MEMORY-001
delivered a substantial test suite and a **per-file** coverage gate (`conftest.py:187-225`),
and nothing runs either of them automatically.

Three findings shaped the design, and two of them changed it:

- **F1 — the container is not required to run the tests.** *(Measured 2026-08-05, twice,
  independently.)* `uv run --python 3.11 --with-requirements requirements.txt
  --with-requirements requirements-dev.txt pytest` yields **282 passed, 0 skipped**, with
  `memory.py` 100%, `recall.py` 100%, `vectorstore.py` 100%, on Python **3.11.14**. The same
  run with `requirements-dev.txt` **alone** yields **242 passed and 1 skipped** — the skip is
  `tests/test_main_integration.py:25-27`, which guards on `rich`, and `rich` is
  `requirements.txt:1`, a runtime dependency absent from the dev file. This retires the
  premise in `pytest.ini:6-14` that the supported invocation is a bind mount of the repository
  into `coderunner-ai:latest`. A plain host job installing **both** requirements files runs
  the whole suite, so the `image` job does not need to run pytest at all.

- **F2 — the stale-image hazard is not hypothetical, and it is total.** *(Measured
  2026-08-05.)* **All five** source files in the local `coderunner-ai:latest` differ from the
  working tree. The image was created **2026-08-04T07:00:03Z**. SHA-256, first 12 hex digits,
  image vs. working tree:

  | File | In image | In working tree |
  |---|---|---|
  | `main.py` | `179765b3d808` | `e49e18fa1c08` |
  | `vectorstore.py` | `e2886902fb77` | `0dc5be2335d1` |
  | `memory.py` | `044ca91b3f73` | `fb021a8dd4be` |
  | `recall.py` | `819ce5c88bf4` | `ea575466365b` |
  | `tools.py` | `9c12bf4a3195` | `a6ec6f5e8211` |

  `coderunner:163` builds **only when `docker image inspect` fails**, i.e. only when the image
  is absent, so this divergence will never self-correct. This is `product.md` §6.3 not as a
  documented risk but as the present state of the machine. It is why the `image` job compares
  hashes rather than merely building.

- **F3 — the engine floor is lower than the pin suggests.** *(Reported from PyPI metadata;
  **NOT** independently verified in this repository. Treat as a lead, not as a measurement.)*
  `pymilvus 3.0.1` declares `milvus-lite>=2.4.0`, so the project's real engine floor is
  **2.4.0**, not 3.0.1. Across that range `milvus-lite` changed from platform-specific wheels
  (2.5.1, 2025-06-30) to `py3-none-any` pure Python (3.0 on 2026-05-13, then 3.1.0 and 3.1.1),
  with `requires_dist` covering `faiss-cpu`, `grpcio`, `numpy` and `pyarrow`. `tech.md` §6.5
  documents four undocumented engine quirks the implementation stands on, and **three of the
  four fail silently**. A floating dependency on a storage engine whose contract is partly
  folklore is exactly the thing a weekly canary exists to watch.

**Baseline resolution recorded at authoring time** (to be re-recorded by T7 as the canary's
first data point): `pymilvus 3.0.1`, `milvus-lite 3.1.1`, `numpy 2.4.6`, `ollama 0.6.2`,
`httpx 0.28.1`, `rich 15.0.0`, `pytest 9.1.1`, `pytest-cov 7.1.0`.

---

# SPEC-CI-001 — Continuous Integration

**Title:** Continuous integration for the test suite, the per-file coverage gate, and the
container image

## 1. Scope statement

On every push to `main` and every pull request to `main`, run the existing test suite and the
existing per-file coverage gate on a hosted runner, and independently verify that the
container image can be built from the current tree and that the source it carries matches that
tree. Separately, on a weekly schedule, resolve every dependency afresh and run the same suite,
so that a silent change beneath an unpinned floor is discovered by a scheduled run rather than
by a user.

This SPEC **detects** drift. It does not prevent it. Pinning, lockfiles and digests are
`tech.md` §8.5's problem and are deliberately left there (§6 item 3).

Nothing here changes product behaviour. No first-party module is edited, no gate threshold
moves, and the only file outside `.github/` that this SPEC may touch is `requirements-dev.txt`,
to pin the linter.

## 2. Verified environment

### 2.1 The suite on a bare host (measured 2026-08-05, twice)

| Invocation | Result |
|---|---|
| `uv run --python 3.11 --with-requirements requirements.txt --with-requirements requirements-dev.txt pytest` | **282 passed, 0 skipped**; `memory.py` 100%, `recall.py` 100%, `vectorstore.py` 100%; Python 3.11.14 |
| the same, omitting `requirements.txt` | **242 passed, 1 skipped** — and it still **exits 0** |

The second row is the whole reason AC-1 asserts a count and a zero-skip rather than an exit
code. Both runs are green. Only one of them tested `main.py`'s integration surface.

`milvus_lite` imported and ran on the host in both cases, so `vectorstore.py`'s suite — which
runs against a **real** embedded engine on `tmp_path` (`conftest.py:147-161`) — is not
container-bound either.

### 2.2 Platform (unverified)

Every measurement this project has ever taken, including all of SPEC-MEMORY-001's, was on
**aarch64** (`.moai/specs/SPEC-MEMORY-001/spec.md:160`). `ubuntu-latest` is **x86_64**. This
code has never been executed on that architecture. That is a fact about this SPEC's risk, not
a reason to avoid it — see `plan.md` R3.

### 2.3 Toolchain and repository facts

| Fact | Evidence |
|---|---|
| Python is pinned at **3.11** for the runtime image | `Dockerfile:9` (`FROM python:3.11-slim`) |
| ruff targets **py311**, line length **100** | `ruff.toml:10-11` |
| `uvx ruff check .` reports **zero findings** today | measured 2026-08-05, ruff **0.16.1** |
| `uvx ruff format --check .` reports **8 files would be reformatted** | measured 2026-08-05 — the project has **deliberately declined** the formatter |
| The image runs as **uid/gid 1000** (`runner`) | `Dockerfile:42-46` |
| Image size | **754 MB** on disk, 172 MB content |
| Build layer order already favours caching | `Dockerfile:31-32` install requirements **before** `Dockerfile:34` copies source |
| Remote | `git@github.com:chunkang/coderunner.ai.git` |
| Git mode | `git-strategy.yaml` — `mode: personal`, `main_branch: main`, `auto_pr: false` |
| `.github/workflows/` | exists and is **empty**. `tech.md:635`'s "`.github/` does not exist" is **stale** and is corrected by T9 |

## 3. Architecture — three jobs

Two workflow files. Three jobs. Each answers a different question, and none answers another's.

### 3.1 Job 1 — `test` (in `.github/workflows/ci.yml`)

`ubuntu-latest`, Python 3.11.

1. `actions/checkout`
2. `actions/setup-python` with `python-version: '3.11'` and `cache: pip`
3. `pip install -r requirements.txt -r requirements-dev.txt` — **both**, per F1
4. **Preflight import assertion** — import `rich`, `ollama`, `httpx`, `pymilvus`,
   `milvus_lite` and fail the job if any is missing, **before pytest is invoked**
5. `ruff check .`
6. `pytest`

The coverage gate is **not** re-expressed here. It lives in `pytest_sessionfinish`
(`conftest.py:195-225`) with its floors at `conftest.py:187-192`, and the workflow's only
relationship to it is invoking `pytest` and honouring the exit status.

### 3.2 Job 2 — `image` (in `.github/workflows/ci.yml`)

1. `docker compose build coderunner` (`docker-compose.yml:58-62`), with `type=gha` layer cache
2. `docker run --rm --entrypoint python coderunner-ai:latest -c "import main, memory, recall, vectorstore, tools"`
3. Hash-compare the five files that `Dockerfile:34` copies into `/app` against the checkout

It **deliberately does not run pytest**. F1 makes an in-container run redundant, and the cost
is not zero: the image runs as uid 1000 (`Dockerfile:42-46`) while the runner's checkout is
owned by a different uid, so a bind mount would need `--user`, a writable `HOME` for
`pip install --user`, and `COVERAGE_FILE=/tmp/.coverage` — three accommodations for **zero**
additional coverage.

### 3.3 Job 3 — `canary` (in a separate workflow file)

Weekly `schedule`, plus `workflow_dispatch`. **No caching. `--upgrade`.** It resolves every
dependency from scratch, writes the resolved versions to `$GITHUB_STEP_SUMMARY`
**regardless of outcome**, and runs the full suite.

It exists to catch F3-class drift: a change beneath a `>=` floor that no commit caused. It
**pins nothing** — pinning is the fix this SPEC declines to make (§6 item 3), and a canary that
pins is a canary that cannot sing.

### 3.4 Cross-cutting

| Setting | Value | Why |
|---|---|---|
| Triggers | `push: [main]`, `pull_request: [main]`, `workflow_dispatch` | |
| `permissions` | `contents: read` | Nothing here writes to the repository |
| `concurrency.group` | `${{ github.workflow }}-${{ github.ref }}` | |
| `concurrency.cancel-in-progress` | `${{ github.event_name == 'pull_request' }}` | **Never cancel a `main` run.** Every commit on `main` keeps its own verdict; superseding a PR push is free, superseding a `main` push destroys evidence |
| ruff | pinned at **`0.16.1`** | An unpinned linter turns "zero findings" into a moving target |

---

## 4. EARS requirements

All five EARS requirement types are represented.

### 4.1 Ubiquitous — always true

| # | Requirement |
|---|---|
| **U1** | The pipeline **shall always** run on **Python 3.11**, matching the runtime pin at `Dockerfile:9` and ruff's `target-version = "py311"` (`ruff.toml:10`). A CI interpreter that differs from the shipped one tests a product nobody runs. |
| **U2** | The pipeline **shall always** enforce the per-file coverage floors through the **existing** `pytest_sessionfinish` hook (`conftest.py:195-225`) and its `PER_FILE_COVERAGE_TARGETS` (`conftest.py:187-192`), by invoking `pytest` and honouring its exit status. There **shall** be exactly one source of truth for those thresholds, and it is `conftest.py`. |
| **U3** | The pipeline **shall always** declare `permissions: contents: read` and **shall** consume no secrets, no tokens beyond the default read-scoped `GITHUB_TOKEN`, and no registry credentials. |
| **U4** | Every job **shall always** be reproducible by a human from a single documented command run against a clean checkout. A step whose failure cannot be reproduced locally is a step that will be disabled the first time it is inconvenient. |

### 4.2 Event-driven — WHEN … THEN …

| # | Requirement |
|---|---|
| **E1** | **WHEN** a commit is pushed to `main`, **THEN** the pipeline **shall** run the `test` job and the `image` job. |
| **E2** | **WHEN** a pull request targeting `main` is opened or updated, **THEN** the pipeline **shall** run the same two jobs, with the same steps and the same thresholds. |
| **E3** | **WHEN** dependency installation completes, **THEN** the `test` job **shall**, *before invoking pytest*, import `rich`, `ollama`, `httpx`, `pymilvus` and `milvus_lite`, and **shall** fail the job naming the missing package if any import fails. This is the sole defence against F1's silent-skip mode. |
| **E4** | **WHEN** the image build completes, **THEN** the `image` job **shall** (a) run `python -c "import main, memory, recall, vectorstore, tools"` inside the image with `--entrypoint python`, and (b) compare the SHA-256 of each of the five files at `/app` — the exact set named at `Dockerfile:34` — against the corresponding file in the checkout, failing on any mismatch. |
| **E5** | **WHEN** the weekly schedule fires, **THEN** the `canary` job **shall** resolve all dependencies with `--upgrade` and no cache, write the resolved versions to `$GITHUB_STEP_SUMMARY`, and run the full suite. |
| **E6** | **WHEN** a new run supersedes an in-flight run in the same concurrency group, **THEN** the older run **shall** be cancelled **only if** `github.event_name == 'pull_request'`. |

### 4.3 State-driven — IF/WHILE … THEN …

| # | Requirement |
|---|---|
| **S1** | **WHILE** the pip cache key matches the current `requirements.txt` **and** `requirements-dev.txt`, the `test` job **shall** restore the cache. Any change to either file **shall** invalidate it. |
| **S2** | **WHILE** the `canary` job is running, caching **shall** be disabled and resolution **shall** use `--upgrade`. A cache hit in the canary defeats the canary. |
| **S3** | **IF** any of `memory.py`, `recall.py` or `vectorstore.py` reports coverage below its floor (`conftest.py:187-192`) — **including** the `coverage unavailable` branch at `conftest.py:206-209`, which fires when a gated file produced no data at all — **THEN** the job **shall** fail. "No data" is a stronger failure than "low percentage", not a lesser one. |
| **S4** | **IF** `ruff check .` reports any finding, **THEN** the job **shall** fail. The baseline is **zero** (measured 2026-08-05 with ruff 0.16.1), so any finding is a regression rather than a backlog item. |

### 4.4 Unwanted — shall not

| # | Requirement |
|---|---|
| **N1** | The pipeline **shall not** gate on `ruff format`. The project has considered and declined the formatter; `ruff format --check .` currently reports **8 files would be reformatted**, and adopting it here would smuggle a large, unrelated diff in through a CI SPEC. |
| **N2** | The pipeline **shall not** invoke `./coderunner`, `./coderunner --doctor`, `docker compose up`, or pull any model. `--doctor` sits **after** the entire bootstrap (`product.md` §6.4) and on a clean runner would install Docker, start the daemon, build the image, start the Ollama sidecar and pull a multi-GB model before printing one diagnostic line. |
| **N3** | The pipeline **shall not** report success while any test is skipped. The `importorskip` guards at `tests/test_main_integration.py:25-27`, `tests/test_vectorstore.py:22` and `conftest.py:153` are safety nets for a platform with no wheel, **not a licence to skip the gate in CI** — `requirements-dev.txt:22-26` says so in as many words. |
| **N4** | The pipeline **shall not** push, tag, publish, create releases, or write to the repository in any form. |
| **N5** | The pipeline **shall not** restate the coverage thresholds in YAML — no `--cov-fail-under` override, no `coverage report --fail-under` step, no threshold literal anywhere under `.github/`. Two copies of a threshold is one copy too many, and the YAML copy is the one that will drift. |
| **N6** | The pipeline **shall not** bind-mount the workspace into the container as a writable path. See §3.2 for the accommodations that would be required and the zero coverage they would buy. |

### 4.5 Optional — where possible

| # | Requirement |
|---|---|
| **O1** | **Where** GitHub Actions layer caching is available, the `image` job **should** use `type=gha` cache. `Dockerfile:31-32` already orders the expensive `pip install` before the source `COPY` at `Dockerfile:34`, so warm builds should re-run only the copy. |
| **O2** | **Where** the canary runs, it **should** write the resolved dependency versions to `$GITHUB_STEP_SUMMARY` on success **and** on failure. A failing canary with no version list is a puzzle; with one, it is a diff. |
| **O3** | **Where** a coverage summary can be surfaced in the job summary, it **should** be — as **reporting only**. It **shall never** become a second gate (see N5). |
| **O4** | **Where** gRPC noise pollutes the host job's log, `GRPC_VERBOSITY=NONE` and `GLOG_minloglevel=3` **should** be set on the `test` job, matching `Dockerfile:22-23`. The C-core writes beneath Python's logging module, so nothing in `vectorstore.py` can suppress it. |

---

## 5. In scope

1. `.github/workflows/ci.yml` — the `test` and `image` jobs.
2. `.github/workflows/canary.yml` — the weekly `canary` job.
3. A pin for **`ruff==0.16.1`**, so the lint gate cannot flap under a linter release.
4. The **preflight import assertion** in the `test` job (E3) — the one genuinely new piece of
   verification logic this SPEC introduces.
5. Documentation: `tech.md` §8.3, `product.md` §6.3, and a CI section in `README.md`.

## 6. Out of scope

1. **Type checking.** `tech.md` §8.1 — no `mypy.ini`, no `pyrightconfig.json`, no checker in
   either requirements file. Adding one is a separate decision with a separate backlog.
2. **`ruff format` adoption.** 8 files would be reformatted; the project has deliberately
   declined it. See N1.
3. **Dependency pinning, lockfiles, `--require-hashes`, base-image digests.** `tech.md` §8.5.
   This SPEC **detects** drift; it does not **prevent** it. Conflating the two would make the
   canary pointless and this SPEC unbounded.
4. **Packaging metadata.** `tech.md` §8.4 — no `pyproject.toml`, no version string, no entry
   point. CI does not need one and should not be the reason one appears.
5. **`.dockerignore`.** `tech.md` §8.6 — the full repository, including `.git/`, `.claude/`
   and `.moai/`, is sent to the daemon on every build. That is **build hygiene**, not CI, and
   it is flagged as an **immediate follow-up** rather than folded in here.
6. **A Python version matrix.** `Dockerfile:9` pins 3.11. Testing 3.12 or 3.13 would assert
   support the product does not claim and would produce failures nobody has agreed to own.
7. **Coverage gates on `main.py` / `tools.py`.** `.moai/specs/SPEC-MEMORY-001/acceptance.md:489-491`
   scopes this out explicitly; a repository-wide gate would fail for reasons unrelated to any
   work in flight.
8. **Any live Ollama, model pull, or `./coderunner` / `--doctor` invocation.** See N2 and
   `product.md` §6.4.
9. **Registry publishing, release automation, tagging.** The repository has no release process
   and this SPEC does not create one.
10. **Branch protection.** It is a repository **setting**, not a file, so no commit can deliver
    it and no reviewer can verify it in a diff. Recorded as manual follow-up **T10**. Until it
    is on, every check here is **advisory**.

---

## 7. Traceability

| Artefact | Location |
|---|---|
| Requirements | this file, §4 (U1–U4, E1–E6, S1–S4, N1–N6, O1–O4) |
| Task decomposition, dependency graph, risks | `.moai/specs/SPEC-CI-001/plan.md` |
| Acceptance criteria | `.moai/specs/SPEC-CI-001/acceptance.md` |
| The gate being protected | `conftest.py:187-225`, `pytest.ini:38-45` |
| Artefacts to be created | `.github/workflows/ci.yml`, `.github/workflows/canary.yml` |
| Artefact possibly amended | `requirements-dev.txt` (ruff pin, T1) |
| Documentation to be corrected | `tech.md` §8.3 (`tech.md:633-647`), `product.md` §6.3 (`product.md:246-251`), `README.md` |
| Source under specification | `Dockerfile`, `docker-compose.yml`, `conftest.py`, `pytest.ini`, `ruff.toml`, `requirements.txt`, `requirements-dev.txt` |
| Project context | `.moai/project/product.md`, `.moai/project/structure.md`, `.moai/project/tech.md` |

| Requirement group | Primary acceptance criteria |
|---|---|
| U1, U2, S3, N3, E3 | **AC-1**, **AC-3** |
| E4, N6 | **AC-2** |
| S4, N1 | **AC-4** |
| E5, S2, O2 | **AC-5** |
| E6, U3 | **AC-6** |
