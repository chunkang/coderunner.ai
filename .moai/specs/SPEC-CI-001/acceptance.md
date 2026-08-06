# SPEC-CI-001 — Acceptance Criteria (v1.0.0)

> Requirements are in `spec.md`. Implementation detail is in `plan.md`.

**Status at authoring:** none of these criteria has been observed on a hosted runner. The
workflows are drafted and committed but **not pushed** (`plan.md` §2), so AC-1 through AC-6 are
**specified, not verified**. T3, T5 and T8 discharge them.

A single theme runs through AC-1, AC-3 and AC-4: **an assertion that cannot distinguish the
working case from the broken one is not an acceptance criterion.** Each of those three exists
because a plausible pipeline is green while testing less than it appears to.

---

## AC-1 — The full suite runs, with nothing skipped

Covers U1, U2, S3, N3, E3.

**Given** a hosted `ubuntu-latest` runner with Python 3.11 and a clean checkout, and the
`test` job's install step having run `pip install -r requirements.txt -r requirements-dev.txt`
— **both files**

**When** the `test` job runs `pytest`

**Then**

- the summary line reports **282 passed** and **0 skipped**;
- coverage reports **`memory.py` 100%**, **`recall.py` 100%**, **`vectorstore.py` ≥ 85%**
  (measured at 100% on the host, 2026-08-05), against the floors at `conftest.py:187-192`;
- the log contains the literal line **`Per-file coverage gate passed`**, emitted by
  `conftest.py:225`;
- the job exits 0.

**And** the assertion is on the **count and the skip count**, not on the exit status.

### Why this criterion is written the way it is

This is the sharpest thing in the document, so it is spelled out rather than implied.

| | Working job | Broken job |
|---|---|---|
| Install | `requirements.txt` **and** `requirements-dev.txt` | `requirements-dev.txt` only |
| Result | **282 passed, 0 skipped** | **242 passed, 1 skipped** |
| Exit status | **0** | **0** |
| Coverage gate | passes | passes |
| `Per-file coverage gate passed` in log | yes | yes |
| Appearance in the Actions UI | green tick | green tick |

Both were measured on 2026-08-05. The broken job is green, its coverage gate passes, and it has
**not tested `main.py`'s integration surface at all** — `tests/test_main_integration.py:25-27`
guards on `rich`, `ollama` and `httpx`, and `rich` is `requirements.txt:1`, a **runtime**
dependency that `requirements-dev.txt` does not carry (`requirements-dev.txt:5` says so
outright: these are for `pytest` only).

At a glance the two are indistinguishable. **The count and the zero-skip assertion are the only
things that separate them.** Any future change that relaxes this criterion to "the job exits 0"
silently readmits the broken column.

---

## AC-2 — A stale or mismatched image fails the build

Covers E4, N6.

**Given** the `image` job has run `docker compose build coderunner`
(`docker-compose.yml:58-62`) against the current checkout

**When** it runs
`docker run --rm --entrypoint python coderunner-ai:latest -c "import main, memory, recall, vectorstore, tools"`
and then compares the SHA-256 of the five files at `/app` — the exact set copied by
`Dockerfile:34` — against the same five files in the checkout

**Then**

- the import smoke succeeds, exercising the real `python:3.11-slim` base (`Dockerfile:9`) with
  the real installed dependency set;
- **all five hashes match**;
- the job exits 0.

**And** if any hash differs, the job fails and the failure message names **which** file
differed and both digests.

**And** no pytest is invoked inside the container, and the workspace is **not** bind-mounted
(N6).

### Motivating evidence — an incident, not a hypothesis

**Historical as of 2026-08-06T06:02:19Z**, when the image was rebuilt and all five files were
confirmed to match. The measurement below is the record of what happened; it is deliberately
not refreshed, because a matching pair of hashes demonstrates nothing.

Measured 2026-08-05 against the local `coderunner-ai:latest`, created **2026-08-04T07:00:03Z**.
SHA-256, first 12 hex digits:

| File | In image | In working tree | Match |
|---|---|---|---|
| `main.py` | `179765b3d808` | `e49e18fa1c08` | **no** |
| `vectorstore.py` | `e2886902fb77` | `0dc5be2335d1` | **no** |
| `memory.py` | `044ca91b3f73` | `fb021a8dd4be` | **no** |
| `recall.py` | `819ce5c88bf4` | `ea575466365b` | **no** |
| `tools.py` | `9c12bf4a3195` | `a6ec6f5e8211` | **no** |

**Five out of five.** Not one drifted file — the entire copied source set. `coderunner:163`
builds only when `docker image inspect` **fails**, i.e. only when the image is **absent**, so
this will never self-correct; the launcher kept running 2026-08-04's code for a day and would
have continued indefinitely. That is `product.md` §6.3 as present tense rather than as a
documented hazard.

A build-only job would have passed against this image. The hash comparison is what makes the
criterion able to fail.

### What the divergence actually cost

This criterion exists because the hazard had already consumed a shipped feature before the
SPEC was written.

Commit `f946142` — *"feat(tui): pulse the status icon while a phase is processing"* — was
authored **2026-08-05T08:01:53-07:00**, more than a day after the image was built. The author
ran `./coderunner` and reported never having seen the pulse.

| Probe | Image `/app/main.py` | Working tree `main.py` |
|---|---|---|
| `_PulsingLine`, `PULSE_HALF_PERIOD_SEC`, `def processing` | **0** | **6** |

The feature was never defective. Driven directly against a forced terminal it produces 9
bright and 8 dim frames over 1.3 s, emits zero `\x1b[5m`, and settles correctly on exit —
matching `f946142`'s own verification note. It had never been inside the container being run.

Three properties of this incident are what the criterion is shaped around:

| Property | Consequence for the design |
|---|---|
| **Detected by a human noticing a missing animation** | The weakest possible detector. A change with no visible symptom — a boundary condition in `run_python()`, a truncation limit in `memory.py` — would have surfaced nothing at all. The pipeline must not depend on a symptom being visible. |
| **The fix took 12.4 seconds** | Every layer but the final `COPY` was cached, per `Dockerfile:31-32`. The hazard does not persist because rebuilding is costly; it persists because **nothing announces that a rebuild is due**. That is a statement a pipeline can make and `coderunner:163`, as written, structurally cannot. |
| **Five of five, not one of five** | There is no reading under which the artefact was partly trustworthy. Every manual acceptance run against `./coderunner` between 2026-08-04 07:00 and the rebuild exercised code that no longer existed in the repository. |

The middle row is the one that generalises: **the import smoke check would have passed against
that image.** A stale image imports perfectly well — it is a valid, coherent, working build of
older source. Only the hash comparison distinguishes "this builds" from "this is the tree."

---

## AC-3 — A silently disarmed gate fails loudly

Covers E3, N3, S3.

**Given** the `test` job, and an environment in which one of `rich`, `ollama`, `httpx`,
`pymilvus` or `milvus_lite` is absent — whether through a resolver change, a dropped platform
wheel (R2), or an editing mistake in an install step

**When** the preflight step runs, **before `pytest` is invoked**

**Then**

- the job **fails at the preflight step**;
- the failure message **names the missing package**;
- **`pytest` never starts**.

**And** the run never reaches the state it exists to prevent: a green run in which
`conftest.py:153` and `tests/test_vectorstore.py:22` skip the store-dependent suites, the
`coverage unavailable` branch at `conftest.py:206-209` fires or is bypassed, and
`vectorstore.py` goes **unexercised** while the summary still reads green.

**And** the ordering is load-bearing: a preflight placed *after* `pytest` would report the same
missing package **after** the suite had already skipped around it, which is a log message
rather than a gate.

`requirements-dev.txt:22-26` states the governing principle directly — the
`importorskip("milvus_lite")` guard is a safety net for a platform with no wheel, **NOT a
licence to skip the gate**. This criterion is that sentence made executable.

---

## AC-4 — Lint is gated; formatting is not

Covers S4, N1.

**Given** ruff pinned at **0.16.1** (T1) and the project's declared standard in `ruff.toml`
(`target-version = "py311"`, `line-length = 100`, and the deliberate per-file ignores at
`ruff.toml:32-60`)

**When** the `test` job runs `ruff check .`

**Then**

- the output is **`All checks passed!`** — the measured baseline on 2026-08-05;
- any finding fails the job. The baseline is zero, so a finding is a **regression**, not a
  backlog entry.

**And**, asserted by inspection of the workflow files rather than by execution: **no step
anywhere invokes `ruff format` or `ruff format --check`.**

The inspection assertion matters because the alternative is not neutral. `ruff format --check .`
currently reports **8 files would be reformatted, 8 files already formatted** (measured
2026-08-05). Adding it would fail the pipeline on day one and would force a formatting decision
the project has **deliberately declined**, through a SPEC that is nominally about CI. The
absence is the requirement.

---

## AC-5 — The canary detects drift and attributes it correctly

Covers E5, S2, O2.

**Given** the weekly `canary` workflow, running with **no cache** and `--upgrade`, on a
schedule rather than on a commit

**When** it resolves dependencies and runs the full suite

**Then**

- the **resolved versions are written to `$GITHUB_STEP_SUMMARY`** — on success **and** on
  failure, without exception;
- the summary is comparable against the recorded baseline: `pymilvus 3.0.1`,
  `milvus-lite 3.1.1`, `numpy 2.4.6`, `ollama 0.6.2`, `httpx 0.28.1`, `rich 15.0.0`,
  `pytest 9.1.1`, `pytest-cov 7.1.0`;
- the full suite runs under whatever was resolved.

**And** a failure is **attributable to the dependency delta and not to any commit** — because
**no commit triggered the run**. That is the entire diagnostic value of a scheduled job, and it
survives only if the version list is present in the failure case. A red canary with no summary
is an unattributable failure, which is the state that gets a workflow muted.

**And** the canary **pins nothing**. Per `spec.md` §6 item 3 this SPEC detects drift rather
than preventing it; a canary that pins is a canary that cannot detect.

### The drift class this is aimed at

Per F3 — **PyPI metadata, not independently verified here** — `pymilvus 3.0.1` declares
`milvus-lite>=2.4.0`, so the real engine floor is **2.4.0**, not 3.0.1, and across that range
`milvus-lite` moved from platform wheels (2.5.1) to `py3-none-any` pure Python (3.0, 3.1.0,
3.1.1). `tech.md` §6.5 catalogues four undocumented engine quirks the implementation stands on,
and **three of the four fail silently**. A silent engine change beneath a `>=` floor is
precisely a failure with no commit to blame.

---

## AC-6 — Concurrency preserves the verdict on `main`

Covers E6, U3.

**Given** `concurrency.group: ${{ github.workflow }}-${{ github.ref }}` with
`cancel-in-progress: ${{ github.event_name == 'pull_request' }}`

**When** three commits are pushed to `main` in a single `git push`

**Then**

- **three runs exist, and none is cancelled**;
- each commit carries **its own verdict**, so a later bisect has a per-commit signal rather
  than a single result attributed to the tip.

**And when** a second push lands on an open pull request's branch

**Then**

- the superseded run **is cancelled**, and only the newest PR run continues.

**And** the distinction is produced by the **expression**, not by a literal. A
`cancel-in-progress: true` would look correct on a PR and would quietly destroy verdicts on
`main`; a `false` would leave PR runs queueing behind superseded ones. Assert the expression
itself by inspection **as well as** asserting the observed behaviour, because the two failure
modes look identical until the day a bisect needs the history.

**And** both workflows declare `permissions: contents: read`, and no job consumes a secret,
a registry credential, or a token beyond the default read-scoped `GITHUB_TOKEN` (U3, N4).

---

## Success criteria and quality gates

### Gates

| Gate | Enforced by | Threshold |
|---|---|---|
| Test count | AC-1 | **282 passed, 0 skipped** |
| Per-file coverage | `conftest.py:195-225` — **never restated in YAML** (N5) | `memory.py` 100%, `recall.py` 100%, `vectorstore.py` ≥ 85% (`conftest.py:187-192`) |
| Lint | AC-4 | `ruff check .` reports zero findings, ruff **0.16.1** |
| Formatting | AC-4 | **not gated**, by design |
| Image integrity | AC-2 | five-of-five SHA-256 match against `Dockerfile:34` |
| Import smoke | AC-2, AC-3 | in-image and on-host, both |

### Verification status

| Criterion | Status | Discharged by |
|---|---|---|
| AC-1 | **not verified on a runner** — the underlying suite result is measured on a host, aarch64 | T3 |
| AC-2 | **not verified on a runner**; the motivating divergence was measured locally and has since been **remediated** (rebuild 2026-08-06T06:02:19Z, five of five now match). The incident it caused — a shipped feature invisible for a day — is recorded above | T5, T8(d) |
| AC-3 | **not verified** | T8(c) |
| AC-4 | baseline measured locally (zero findings; 8 files would reformat); **not verified on a runner** | T3, T8(a) |
| AC-5 | **not verified**; baseline resolution recorded | T7 |
| AC-6 | **not verified** | T3 |

`plan.md` §2 records why: the workflows are committed but **not pushed**, and T3, T5 and T8 all
require a push to `origin`. **T8 is left for the user to execute.**

### Definition of done

1. `.github/workflows/ci.yml` and `.github/workflows/canary.yml` exist, with the ruff pin
   resolved and its rationale recorded in the header (T1).
2. AC-1 through AC-6 have each been **observed** on a hosted runner — not inferred from a
   green tick.
3. **Each of the four gates has been observed failing at least once** (T8): a ruff finding, a
   coverage drop on `recall.py`, a missing `rich` caught by the **preflight** rather than by a
   skip, and an edited `main.py` caught by the hash comparison. *A gate never observed failing
   is not known to be a gate.*
4. Cold and warm image build durations are **recorded as separate numbers** (T5), and R1's
   demotion decision — keep the `image` job on PRs, or move it to `push: [main]` plus
   `workflow_dispatch` — has been taken **on those numbers**.
5. `tech.md` §8.3 no longer claims `.github/` does not exist (`tech.md:635`), `product.md` §6.3
   records that the stale-image hazard is now detected in CI, and `README.md` carries a CI
   section (T9).
6. Both `README.md` and `tech.md` §8.3 state in plain words that the checks are **advisory**
   until branch protection is enabled, and **T10 is recorded with an owner**.
