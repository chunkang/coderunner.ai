---
id: SPEC-CI-001
version: "1.0.2"
status: "draft"
created: "2026-08-05"
updated: "2026-08-07"
author: "Chun Kang"
priority: "HIGH"
---

## HISTORY

### v1.0.2 (2026-08-07) — the `image` job's file list becomes a gate; citations corrected

Three changes, one of which is a scope amendment and two of which are corrections to claims that
had gone stale in this document while the code moved underneath it.

**The hole, and why §5 moved to close it.** `ci.yml:456-458` warned in plain words that a file
added to `Dockerfile:43` and not to the workflow's `FILES=` list "can go stale unobserved". The
next day, `479d700` did exactly that with `keychain.py` — the module that reads the user's
credential store. An **absent** module fails the build loudly; a **stale** one builds, imports,
and passes every check the `image` job runs, which is F2 reopened for one file. §5 now admits
`tests/test_source_seam.py` so the invariant is enforced by a test that asserts **set equality**
between the two lists and reports the symmetric difference by side. The full argument, including
why a test about `.github/` does not breach the boundary the original §5 was drawing, is at
**§5.1**. The test was observed failing against the seven-file list before the fix; `FILES=` and
the in-image import smoke now both carry `keychain.py`.

**Citations corrected, and the sweep stated exactly.** Four files were swept: **`spec.md`,
`plan.md`, `acceptance.md` and `.github/workflows/ci.yml`.** The first draft of this entry said
"this SPEC, `plan.md` and `acceptance.md`", which omitted `ci.yml` and so read as a completeness
claim that was not complete — the same defect one level up. `ci.yml` carried five stale
`conftest.py` citations of its own and they are corrected in the same change.

The gate has moved down `conftest.py` twice since v1.0.0 and every line reference to it in those
four files was wrong: `PER_FILE_COVERAGE_TARGETS` is at **`conftest.py:204-212`** (cited as
`:187-192`), the `pytest_sessionfinish` hook at **`:215-245`** (cited as `:195-225`), the emitted
line `Per-file coverage gate passed` at **`:245`** (cited as `:225`), and the
`coverage unavailable` branch at **`:227-229`** (cited as `:206-209`).

`479d700` also inserted a comment block into the `Dockerfile`, moving the `COPY` line from `:34`
to **`:43`** and everything below it. All four swept files cited `:34` — seven times here, three
in `plan.md`, two in `acceptance.md`, five in `ci.yml` — and all now cite `:43`. **None of those
seventeen was a historical measurement:** each describes the current design, or the `479d700`
incident itself, at which point `:43` was already the correct line. Two genuinely historical
citations were therefore *not* rewritten — `tests/test_source_seam.py`'s AC-IMAGE comment, which
now names both the old and current line, and `verification-T3.md` §2.3, which cites
`git show b8b3259:Dockerfile` line 34 and is correct **for that ref**.

Corrected in the same pass, each verified against the file rather than assumed. In `ci.yml`:
`Dockerfile:42-46` → **`:51-55`**, `Dockerfile:48` → **`:57`**, `main.py:802` → **`:1295`**,
`tests/test_main_integration.py:25-27` → **`:29-31`**, `coderunner:163` → **`:462`**. In
`tests/test_source_seam.py`: two further `coderunner:163` → **`:462`**, both pre-existing and
both stating the build-if-absent rule in the present tense.

**Known-wrong citations left standing, because they are outside this SPEC's scope to edit** —
recorded so the next reader does not trust them, and so that fixing them needs no re-derivation:

| Cites | Correct | Where |
|---|---|---|
| `conftest.py:221-223` for `coverage unavailable` | `conftest.py:227-229` | `pytest.ini:45` |
| `Dockerfile:42-46` for the uid-1000 block | `Dockerfile:51-55` | `spec.md:241` (§2.3), `spec.md:275` (§3.2); `plan.md:124` (§3.2), `plan.md:153` (R4) |
| `tests/test_main_integration.py:25-27` for the `importorskip` guards | `:29-31` | `spec.md:116` (F1), `spec.md:341` (N3); `plan.md:137` (§3.3); `acceptance.md:54` (AC-1) |
| `coderunner:163` for the build-if-absent rule | `coderunner:462` | `spec.md:82` (HISTORY v1.0.1), `spec.md:135` (F2); `acceptance.md:114`, `:157` (AC-2) |

The last two rows carry a wrinkle worth naming rather than smoothing: several of those sites sit
inside **historical** passages — F2's incident, AC-2's motivating evidence — where the cited line
may well have been correct when the measurement was taken. But each states its claim in the
**present tense** (*"`coderunner:163` builds only when `docker image inspect` fails"*), so a
reader today follows the number and lands on nothing. Whoever fixes them should decide per site
whether to repoint or to mark as superseded; this entry deliberately does not pre-empt that.

**Two enumerations replaced by the sets they were copying.** `T3` asserted **three** coverage
floors; `conftest.py:204-212` now declares **six**. `T3` now asserts *every floor declared in
`PER_FILE_COVERAGE_TARGETS`, whatever that set currently is* — the same set-derived form as the
seam test above, for the same reason. Likewise the `MIN_PASSED` literal is deleted from
`plan.md` T3 and from `acceptance.md` AC-1 and its gates table; **AC-1 had been restating the
number inside the very sentence asserting it is "held in exactly one place"**, which is N5
violated by the criterion that cites N5. It is now cited by symbol only.

**What is unchanged.** No requirement, no acceptance criterion's Given/When/Then, no threshold,
no job design. `S3` and `AC-1` still enumerate three floors in prose; they are left as written
because this amendment's remit was `T3`, and they are flagged rather than silently widened.

### v1.0.1 (2026-08-05) — F2 promoted from measurement to incident; hashes marked historical

No requirement, acceptance criterion or task changed. What changed is the strength of the
evidence behind the `image` job, and the tense of a claim that had quietly become false.

**The incident.** Between v1.0.0 being written and this amendment, F2 was found to have
already cost a shipped feature. `f946142` (*"feat(tui): pulse the status icon while a phase is
processing"*, authored 2026-08-05T08:01:53-07:00) had been invisible for a day: the image
predated it by over 24 hours, and `coderunner:163` never rebuilds an image that exists. The
author ran `./coderunner` repeatedly and reported the feature missing. It was not missing —
it was not *there*, because the container held 2026-08-04's source. Recorded in full under F2
and in `acceptance.md` AC-2.

This is a better argument than the hash table it supplements, for a reason worth stating: the
divergence was detected **by a person noticing an animation was absent**. Nothing in the
repository detected it, and nothing would have, for any change without a visible symptom.

**The correction.** The image was rebuilt 2026-08-06T06:02:19Z; all five files now match the
tree. The F2 hash table therefore describes a machine state that no longer exists, and both it
and AC-2's copy are now explicitly labelled **historical**. They are retained rather than
refreshed: a table of matching hashes would demonstrate nothing. `plan.md` §1.2's description
of F2 as "currently-live" is corrected in the same pass.

**What is unchanged.** The `image` job's design, E4, N6, AC-2's Given/When/Then, and the T1-T10
decomposition all stand exactly as written in v1.0.0 — the incident vindicated the design
rather than revising it. T3, T5 and T8 remain deferred and unverified.

### v1.0.0 (2026-08-05) — Initial specification

Written against `tech.md` §8.3 ("No CI"), which is the gap this SPEC closes and which states
the case better than a restatement would: *"A gate that exists, passes locally, and is never
executed by anything but a human is one commit away from being decorative."* SPEC-MEMORY-001
delivered a substantial test suite and a **per-file** coverage gate (`conftest.py:204-245`),
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
  is absent, so a divergence once opened never self-corrects. At the time of measurement this
  was `product.md` §6.3 not as a documented risk but as the live state of the machine — see
  the incident below, and the status note at the end of this finding. It is why the `image`
  job compares hashes rather than merely building.

  **What it cost, before this SPEC was written.** The divergence above is not an abstraction
  about hashes; it had already swallowed a shipped feature. Commit `f946142`
  (*"feat(tui): pulse the status icon while a phase is processing"*) was authored
  **2026-08-05T08:01:53-07:00**, over a day *after* the image was built. The author then ran
  `./coderunner` and reported never having seen the pulse. Diagnosis, measured: the image's
  `/app/main.py` contained **zero** occurrences of `_PulsingLine`, `PULSE_HALF_PERIOD_SEC` or
  `def processing`, against **six** in the working tree. The feature itself was never at fault —
  driven directly with a forced terminal it renders 9 bright and 8 dim frames over 1.3 s and
  emits no `\x1b[5m` — it had simply never been inside the container being run.

  Three details make this the strongest argument in the document for the `image` job:

  1. **It was not detected by anything.** It surfaced because a human noticed a visual effect
     was missing. Had `f946142` changed something without a visible symptom — a boundary
     condition in `run_python()`, a truncation limit — nothing would have surfaced it at all.
  2. **The cost of the fix was 12.4 seconds.** `docker compose build coderunner` reused every
     cached layer, because `Dockerfile:31-32` copies `requirements.txt` before the source, so
     only the final `COPY` was invalidated. The hazard did not persist because rebuilding is
     expensive. It persisted because **nothing says when a rebuild is due**, which is precisely
     the thing a pipeline can say and a launcher, as written, cannot.
  3. **It was total, not partial.** Five of five. So there was no reading under which the
     artefact was partly trustworthy, and the import smoke check alone would have passed
     cleanly against it — the stale image imports perfectly well. Only the hash comparison
     separates the two cases.

  **Status of the table above: historical.** The image was rebuilt on **2026-08-06T06:02:19Z**
  and all five files now match the tree. The measurement stands as the record of the incident,
  not as a description of the machine today. It is retained rather than refreshed because a
  currently-matching pair of hashes would argue nothing.

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

Nothing here changes product behaviour. No first-party module is edited and no gate threshold
moves. Two files outside `.github/` may be touched: `requirements-dev.txt`, to pin the linter,
and `tests/test_source_seam.py`, to assert that the `image` job's file lists still agree with
`Dockerfile:43`. The second was added by amendment on 2026-08-07 and its justification is at
§5.1 — it is a test **about** `.github/`, not a change to the tree being measured.

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
| Build layer order already favours caching | `Dockerfile:31-32` install requirements **before** `Dockerfile:43` copies source |
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
(`conftest.py:215-245`) with its floors at `conftest.py:204-212`, and the workflow's only
relationship to it is invoking `pytest` and honouring the exit status.

### 3.2 Job 2 — `image` (in `.github/workflows/ci.yml`)

1. `docker compose build coderunner` (`docker-compose.yml:58-62`), with `type=gha` layer cache
2. `docker run --rm --entrypoint python coderunner-ai:latest -c "import main, memory, recall, vectorstore, tools"`
3. Hash-compare the five files that `Dockerfile:43` copies into `/app` against the checkout

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
| **U2** | The pipeline **shall always** enforce the per-file coverage floors through the **existing** `pytest_sessionfinish` hook (`conftest.py:215-245`) and its `PER_FILE_COVERAGE_TARGETS` (`conftest.py:204-212`), by invoking `pytest` and honouring its exit status. There **shall** be exactly one source of truth for those thresholds, and it is `conftest.py`. |
| **U3** | The pipeline **shall always** declare `permissions: contents: read` and **shall** consume no secrets, no tokens beyond the default read-scoped `GITHUB_TOKEN`, and no registry credentials. |
| **U4** | Every job **shall always** be reproducible by a human from a single documented command run against a clean checkout. A step whose failure cannot be reproduced locally is a step that will be disabled the first time it is inconvenient. |

### 4.2 Event-driven — WHEN … THEN …

| # | Requirement |
|---|---|
| **E1** | **WHEN** a commit is pushed to `main`, **THEN** the pipeline **shall** run the `test` job and the `image` job. |
| **E2** | **WHEN** a pull request targeting `main` is opened or updated, **THEN** the pipeline **shall** run the same two jobs, with the same steps and the same thresholds. |
| **E3** | **WHEN** dependency installation completes, **THEN** the `test` job **shall**, *before invoking pytest*, import `rich`, `ollama`, `httpx`, `pymilvus` and `milvus_lite`, and **shall** fail the job naming the missing package if any import fails. This is the sole defence against F1's silent-skip mode. |
| **E4** | **WHEN** the image build completes, **THEN** the `image` job **shall** (a) run `python -c "import main, memory, recall, vectorstore, tools"` inside the image with `--entrypoint python`, and (b) compare the SHA-256 of each of the five files at `/app` — the exact set named at `Dockerfile:43` — against the corresponding file in the checkout, failing on any mismatch. |
| **E5** | **WHEN** the weekly schedule fires, **THEN** the `canary` job **shall** resolve all dependencies with `--upgrade` and no cache, write the resolved versions to `$GITHUB_STEP_SUMMARY`, and run the full suite. |
| **E6** | **WHEN** a new run supersedes an in-flight run in the same concurrency group, **THEN** the older run **shall** be cancelled **only if** `github.event_name == 'pull_request'`. |

### 4.3 State-driven — IF/WHILE … THEN …

| # | Requirement |
|---|---|
| **S1** | **WHILE** the pip cache key matches the current `requirements.txt` **and** `requirements-dev.txt`, the `test` job **shall** restore the cache. Any change to either file **shall** invalidate it. |
| **S2** | **WHILE** the `canary` job is running, caching **shall** be disabled and resolution **shall** use `--upgrade`. A cache hit in the canary defeats the canary. |
| **S3** | **IF** any of `memory.py`, `recall.py` or `vectorstore.py` reports coverage below its floor (`conftest.py:204-212`) — **including** the `coverage unavailable` branch at `conftest.py:227-229`, which fires when a gated file produced no data at all — **THEN** the job **shall** fail. "No data" is a stronger failure than "low percentage", not a lesser one. |
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
| **O1** | **Where** GitHub Actions layer caching is available, the `image` job **should** use `type=gha` cache. `Dockerfile:31-32` already orders the expensive `pip install` before the source `COPY` at `Dockerfile:43`, so warm builds should re-run only the copy. |
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
5. `tests/test_source_seam.py` — assertions that the `image` job's hand-maintained file lists
   still agree with `Dockerfile:43`. **Added by amendment 2026-08-07; see below.**
6. Documentation: `tech.md` §8.3, `product.md` §6.3, and a CI section in `README.md`.

### 5.1 Why item 5 exists, and why it required amending this section

The original §5 permitted `.github/` and `requirements-dev.txt`, on the reasoning that a CI SPEC
that edits the tree it is meant to be measuring has stopped being a CI SPEC. That reasoning
holds, and item 5 is not an exception to it: the file admitted is a **test**, it asserts a
property **of `.github/workflows/ci.yml`**, and it changes no product behaviour, no threshold and
no first-party module. It is the `image` job's own correctness expressed where correctness can be
checked, rather than in the job it is a property of.

What forced the amendment is that the invariant in question was already written down, in the
right place, in plain words, and was violated anyway. `ci.yml:456-458` says of the `FILES=` list:

> *If that COPY line changes, change this list — a file added there and not here is a file that
> can go stale unobserved.*

That comment was written 2026-08-06. On **2026-08-07**, commit `479d700` added `keychain.py` to
`Dockerfile:43` and not to `FILES=` — **the exact omission the comment names, within one day, on
the file it names.** The pattern had been followed correctly for `params.py` and `settings.py`
and was missed for the one module that reads the user's credential store.

The asymmetry is what makes it worth a test rather than a firmer comment. A file **absent** from
the image fails the build immediately, because `main.py` cannot import it. A file **stale** in
the image builds, imports, and passes every check the `image` job runs — which is F2 exactly,
reopened for one module. An unlisted file is not half-protected; it is precisely as unprotected
as it was before this SPEC existed.

**Converting an invariant enforced by a comment into an invariant enforced by a gate is what this
SPEC is for.** `tech.md` §8.3's sentence — *"a gate that exists, passes locally, and is never
executed by anything but a human is one commit away from being decorative"* — applies with more
force to a gate that was never executed by anything at all. The scope boundary as written would
have required leaving the hole open or closing it in a way that could reopen silently; neither is
a defensible reading of a SPEC whose subject is exactly this failure mode. So the boundary moves,
by one file, on the record, with the counterexample attached.

The test derives both lists rather than restating either — it reuses the existing
`Dockerfile`-COPY parser in that file and parses `FILES=` and the import-smoke module list out of
`ci.yml`, then asserts **set equality** and reports the symmetric difference by side. A second
parser, or a third hand-maintained list, would be the same defect one level up. It also carries a
vacuity guard: a regex that matches nothing would make the assertion permanently green, which is
worse than no assertion because it is counted.

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
| Verification record for T3 | `.moai/specs/SPEC-CI-001/verification-T3.md` |
| The gate being protected | `conftest.py:204-245`, `pytest.ini:38-45` |
| Artefacts to be created | `.github/workflows/ci.yml`, `.github/workflows/canary.yml` |
| Artefacts possibly amended | `requirements-dev.txt` (ruff pin, T1); `tests/test_source_seam.py` (the `image` job's file lists, §5 item 5 / §5.1) |
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
