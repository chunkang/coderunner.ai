# SPEC-CI-001 — Implementation Plan (v1.0.0)

> Requirements are in `spec.md`. Acceptance criteria are in `acceptance.md`.

## 0. Starting position

The repository already contains everything CI needs to run and nothing that runs it.

| Present | Evidence |
|---|---|
| A test suite of **282 tests**, all passing, none skipped, on a bare host | measured 2026-08-05 (F1) |
| A **per-file** coverage gate that `--cov-fail-under` cannot express | `conftest.py:187-225`; rationale at `conftest.py:169-185` |
| A declared lint standard reporting **zero findings** | `ruff.toml`; measured with ruff 0.16.1 |
| A buildable image with sensible layer order | `Dockerfile:31-32` before `Dockerfile:34` |
| A compose service to build it by name | `docker-compose.yml:58-62` |
| `.github/workflows/` | **exists, empty** |

So this is not a "build a pipeline" plan. It is a "wire up the gates that already exist, then
prove each of them can fail" plan. T8 is where the value is; T2 through T7 are the setup that
makes T8 possible.

**One correction to make in passing:** `tech.md:635` states "`.github/` does not exist". The
directory exists and is empty. T9 owns the fix.

---

## 1. Task decomposition

Ten tasks. Eight are automated; **T10 is deliberately manual**, and three are deferred (§2).

| # | Task | Artefact | Depends on |
|---|---|---|---|
| **T1** | **Pin the linter at `ruff==0.16.1`.** Choose between adding it to `requirements-dev.txt` (visible to humans running the suite locally, at the cost of putting a CI-only tool in the dev file) and pinning it inline in the workflow step (keeps the dev file about testing, at the cost of a version literal in YAML). **Record the choice and the reason in the workflow header**, because the next reader will otherwise assume the other option was overlooked. The measured baseline is 0.16.1 with zero findings; the pin exists so that "zero findings" keeps meaning the same thing. | `requirements-dev.txt` or `ci.yml` | — |
| **T2** | **Write the `test` job.** `ubuntu-latest`; `actions/checkout`; `actions/setup-python` with `python-version: '3.11'` and `cache: pip`; `pip install -r requirements.txt -r requirements-dev.txt` (**both** — F1); preflight import step (E3); `ruff check .`; `pytest`. No coverage threshold appears anywhere in the YAML (N5). Set `GRPC_VERBOSITY=NONE` and `GLOG_minloglevel=3` to match `Dockerfile:22-23` (O4). | `.github/workflows/ci.yml` | T1 |
| **T3** | **Verify T2 on a branch.** Assert **282 passed / 0 skipped**, and all three coverage floors met — `memory.py` 100%, `recall.py` 100%, `vectorstore.py` ≥ 85% — with the literal line `Per-file coverage gate passed` in the log (`conftest.py:225`). **This is the first execution of this codebase on x86_64**; every prior measurement, including all of SPEC-MEMORY-001's, was aarch64 (`.moai/specs/SPEC-MEMORY-001/spec.md:160`). Treat the result as data, not as a formality. | — | T2 |
| **T4** | **Write the `image` job.** `docker compose build coderunner` with `type=gha` cache; then `docker run --rm --entrypoint python coderunner-ai:latest -c "import main, memory, recall, vectorstore, tools"`; then SHA-256 compare the five `/app` files named at `Dockerfile:34` against the checkout. No pytest inside the container (N6; see `spec.md` §3.2 for the three accommodations avoided). | `.github/workflows/ci.yml` | T1 |
| **T5** | **Verify T4 and RECORD the build durations — cold and warm, as separate numbers.** These are not incidental: they are the entire cost claim this SPEC makes, and R1's mitigation is chosen from them. Do not report a single "build time". | — | T4 |
| **T6** | **Add the cross-cutting settings.** `permissions: contents: read`; `workflow_dispatch` on both workflows; `concurrency.group: ${{ github.workflow }}-${{ github.ref }}` with `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`. The expression is the point — a literal `true` would silently discard verdicts on `main`. | `.github/workflows/ci.yml`, `canary.yml` | T2, T4 |
| **T7** | **Write `canary.yml` and record today's resolution as the baseline.** Weekly `schedule` plus `workflow_dispatch`; **no cache**; `--upgrade`; resolved versions to `$GITHUB_STEP_SUMMARY` **regardless of outcome**; full suite. Record the authoring-time baseline — `pymilvus 3.0.1`, `milvus-lite 3.1.1`, `numpy 2.4.6`, `ollama 0.6.2`, `httpx 0.28.1`, `rich 15.0.0`, `pytest 9.1.1`, `pytest-cov 7.1.0` — in the workflow header, so the first canary run has something to be a delta *from*. **Gate: re-verify F3 before freezing this baseline.** The version list above is inherited from an unverified PyPI-metadata reading (§0, R2); a baseline is worth exactly what its provenance is worth, and a canary calibrated against a wrong starting point reports drift that did not happen and misses drift that did. Confirm the resolved set by `pip freeze` in a clean 3.11 environment, and record *that* — not this table — as the baseline. | `.github/workflows/canary.yml` | T1 |
| **T8** | **Break each gate once, deliberately, and confirm red.** Four separate experiments, each reverted immediately: (a) introduce a ruff finding and confirm the job fails at `ruff check .`; (b) delete a covered line's test so `recall.py` drops below 100% and confirm the failure names `recall.py` and its floor; (c) **uninstall `rich` and confirm the PREFLIGHT step fails**, rather than the suite quietly skipping `tests/test_main_integration.py` and exiting 0 with 242 passed; (d) edit `main.py` **without** rebuilding and confirm the hash comparison fails. **A gate never observed failing is not known to be a gate.** | — | T2, T4, T6 |
| **T9** | **Documentation.** Rewrite `tech.md` §8.3 (`tech.md:633-647`) — its opening sentence at `tech.md:635`, "`.github/` does not exist", is **already stale** and must go regardless of this SPEC's outcome; the section becomes a description of what runs and what it does **not** cover (§8.1, §8.4, §8.5, §8.6 remain open). Amend `product.md` §6.3 (`product.md:246-251`) to record that the stale-image hazard is now **detected in CI** on `main` and PRs, while remaining unfixed for local users. Add a **CI** section to `README.md` — sensibly between "Files" (`README.md:159`) and "License" (`README.md:175`) — stating the three jobs, the badge, and the fact that the checks are advisory until T10. | `tech.md`, `product.md`, `README.md` | T3, T5, T8 |
| **T10** | **Manual follow-up, recorded rather than automated: enable branch protection on `main`** so that `test` and `image` are **required** rather than advisory. This cannot be delivered by a commit — it is a repository setting on `git@github.com:chunkang/coderunner.ai.git`, and `git-strategy.yaml` runs `mode: personal` with `auto_pr: false`, so nothing in the workflow will prompt for it. Until it is done, a red run blocks nothing. | GitHub settings | T9 |

### 1.1 Dependencies and critical path

```
T1 ──┬── T2 ── T3 ──┐
     │              │
     ├── T4 ── T5 ──┼── T8 ── T9 ── T10
     │              │
     └── T7 ────────┘
              T6 ───┘
```

**Critical path: T1 → T2 → T3 → T8 → T9.**

`T4`/`T5` and `T7` run in parallel with `T2`/`T3`; `T6` is a small edit to files both branches
produce and joins before T8. T8 is the convergence point, and it must not start until every
gate it intends to break actually exists.

### 1.2 Priority

| Priority | Tasks | Rationale |
|---|---|---|
| **High** | T1, T2, T3, T8 | The suite and the coverage gate are the assets `tech.md` §8.3 says are one commit from decorative |
| **Medium** | T4, T5, T6, T7 | The image job addresses a defect that was **measured and then observed to cost a shipped feature** — `f946142`'s status-icon pulse was absent from the running container for a day (F2). Remediated locally on 2026-08-06 by a 12.4 s rebuild, which is the point: the fix was never the hard part, noticing was. The canary addresses an **unverified** lead (F3) |
| **Low** | T9, T10 | Necessary for the work to hold, but nothing in the pipeline depends on them |

Final goal is T10. Optional goal: none — every task listed is required for the SPEC to be
complete.

---

## 2. Execution decision — what gets committed, and what does not

**Decision taken by the user at planning time: the workflow files are to be written and
committed, but NOT pushed. T8 is left for the user to execute.**

The consequence is explicit, and is recorded here rather than discovered later:

| Task | Requires a push to `origin`? | Status |
|---|---|---|
| T1 | no | deliverable now |
| T2 | no | deliverable now |
| **T3** | **yes** — GitHub Actions only runs from a pushed ref | **deferred** |
| T4 | no | deliverable now |
| **T5** | **yes** — the durations are properties of the hosted runner, not of a local build | **deferred** |
| T6 | no | deliverable now |
| T7 | no | deliverable now |
| **T8** | **yes** — a gate is observed failing on the runner or not at all | **deferred, user-executed** |
| T9 | no, but see below | blocked on T3/T5/T8 |
| T10 | n/a — a settings change | manual |

**T9 must not be written from expectation.** It documents measured behaviour — build
durations from T5, a confirmed red from T8 — and writing it before those exist would put
claims into `tech.md` of exactly the kind §8 exists to catalogue.

Until T3, T5 and T8 have run, this SPEC is **specified and drafted, not verified**. Say so in
any status report.

---

## 3. Technical approach — the three decisions worth defending

### 3.1 The gate stays in `conftest.py`

`pytest.ini:38-45` sets `--cov-fail-under=85`, which compares the **combined** total only;
`conftest.py:169-185` explains at length why that is insufficient, and
`conftest.py:187-192` holds the real floors. The workflow's entire relationship with coverage
is `pytest` plus an exit status.

The temptation to add `coverage report --include=recall.py --fail-under=100` to the YAML —
"for visibility" — must be refused. Two copies of a threshold do not agree for long, and the
copy in YAML is the one nobody re-reads.

### 3.2 The host runs the tests; the container does not

F1 settled this. `pytest.ini:6-14` documents the in-container bind mount as **the** supported
invocation, and that was true when the only reliable environment was the image. It is no longer
the only one: a host job installing both requirements files runs all 282 tests including
`vectorstore.py`'s real-engine suite.

Running pytest in the container as well would cost `--user`, a writable `HOME`, and
`COVERAGE_FILE=/tmp/.coverage` — because `Dockerfile:42-46` makes the image run as uid 1000
while the checkout belongs to the runner's user — and would buy no coverage that the host job
does not already produce.

So the `image` job answers only the questions the host job cannot: *does it build*, *does it
import*, and *is what is inside it what is in the tree*.

### 3.3 The preflight import is not redundant with `pip install`

It looks redundant. It is not, and F1 is the proof: a job that installs only
`requirements-dev.txt` **exits 0** with 242 passed and 1 skipped. `pip install` succeeding tells
you the resolver was satisfied, not that the right set was requested. The preflight asserts the
**post-condition** — these five modules import — which is the thing the suite silently assumes
via `tests/test_main_integration.py:25-27`, `tests/test_vectorstore.py:22` and
`conftest.py:153`.

`requirements-dev.txt:22-26` already states the principle: the `importorskip` guard is a safety
net for a platform with no wheel, **not** a licence to skip the gate in CI. The preflight is
what turns that sentence into an enforced condition.

---

## 4. Risks and mitigations

| # | Risk | Assessment | Mitigation |
|---|---|---|---|
| **R1** | **Image build cost.** The image is **754 MB** on disk / 172 MB content, dominated by `pymilvus[milvus_lite]` and its transitive numpy. A slow `image` job on every PR is the classic reason a pipeline gets trimmed six weeks after it lands. | `Dockerfile:31-32` already installs requirements **before** `Dockerfile:34` copies source, so a warm build should re-run only the copy. **But that is an inference from layer order, not a measurement.** | `type=gha` cache; **T5 must MEASURE cold and warm separately rather than trust the layer order**. If the cold build exceeds ~5 minutes, demote the `image` job to `push: [main]` plus `workflow_dispatch` and drop it from the PR path — PR feedback on the image is worth less than PR feedback that arrives. |
| **R2** | **`milvus_lite` wheel availability on the runner.** The original form of this risk — "no linux/x86_64 wheel, so `importorskip` fires and the `vectorstore.py` gate silently evaporates" — was the sharpest thing on this list. | **Largely retired.** Per F3, `milvus-lite 3.1.1` is `py3-none-any` (pure Python), and its `faiss-cpu` dependency ships an **abi3 `manylinux_2_28` x86_64** wheel covering 3.11. Note F3 is PyPI metadata, **not** independently verified here. | Residual risk is a **future** abi3 drop or a platform-tag change forcing a source build. The **preflight (E3) converts that from a silent skip into a loud failure**, which is the whole point of it. |
| **R3** | **x86_64 is a new platform for this code.** Every measurement in the project's history is aarch64 (`.moai/specs/SPEC-MEMORY-001/spec.md:160`). Float behaviour, wheel provenance and gRPC-over-loopback timing are all architecture-adjacent, and `conftest.py:36-41` documents float32 round-trip sensitivity the suite already had to accommodate. | A day-one failure is plausible. | **Treat a day-one failure as a finding worth having, not as a reason to weaken the gate.** If a test fails on x86_64, that is a real portability defect discovered by the mechanism built to discover it. Do not add `xfail`, do not relax a tolerance, and do not pin the runner to arm — investigate. |
| **R4** | **Bind-mount uid mismatch.** `Dockerfile:42-46` runs as uid/gid 1000; the runner's checkout is owned by a different uid. A bind-mounted pytest run would fail on `pip install --user`, on `HOME`, and on writing `.coverage`. | **Not live**, because this SPEC does not bind-mount (N6). | Recorded so that a future SPEC reinstating in-container pytest budgets for `--user`, a writable `HOME`, and `COVERAGE_FILE=/tmp/.coverage` rather than rediscovering all three. |
| **R5** | **Unpinned tooling makes the gate flap.** A ruff release adds a rule; a green `main` turns red with no commit. Two of those and the lint step gets `continue-on-error`. | Certain over a long enough window. | **T1 pins `ruff==0.16.1`.** Upgrading becomes a deliberate commit with a visible diff — which is the correct place for a new rule to be argued about. |
| **R6** | **The canary becomes noise and gets muted.** A scheduled job that fails for reasons no commit caused is the most-ignored kind of job there is. | The real failure mode of canaries generally. | **Weekly, not daily**; a **distinct workflow name** so it is never confused with the PR gate; **versions in the step summary** so triage starts from a diff rather than a mystery. And a second-order signal: **if the canary fires more than roughly quarterly, that is itself evidence a lockfile SPEC is due** — the answer then is `tech.md` §8.5, not a quieter canary. |
| **R7** | **The documentation goes stale on delivery.** `tech.md:635` already asserts something false about `.github/`; the same section will be wrong in the opposite direction the moment these workflows land. | Demonstrated, not hypothetical. | **T9 is on the critical path**, not a follow-up. It runs after T3/T5/T8 so that what it records is measured. |
| **R8** | **Green but advisory.** Without branch protection, a red run blocks nothing; a merge over a failing check looks exactly like a merge over a passing one in the commit graph. | Live from the moment the workflows land until T10 is done. `git-strategy.yaml` has `mode: personal`, `auto_pr: false`, so no PR-review habit compensates. | **T10**, recorded as a manual follow-up with an owner. Until then, `README.md` and `tech.md` §8.3 must both say **advisory** in plain words — an overstated CI claim is worse than no CI claim, because it is trusted. |

---

## 5. Follow-up notes

- **`.dockerignore` (`tech.md` §8.6) is the immediate next thing.** It is out of scope here
  (`spec.md` §6 item 5) because it is build hygiene rather than CI, but the `image` job sends
  the full repository — `.git/`, `.claude/`, `.moai/` — to the daemon on **every** run, so this
  SPEC materially raises the cost of not having one. Flag it the day T5 reports its numbers.
- **`tech.md` §8.5 is untouched and gets sharper.** The canary makes drift **visible**; it does
  nothing to make builds **reproducible**. Every row of that table stands. If R6's quarterly
  threshold is crossed, this is the SPEC to write next.
- **Do not re-derive the image size.** 754 MB on disk / 172 MB content is measured. The
  provenance of that number, and the correction it went through, is at
  `.moai/specs/SPEC-MEMORY-001/spec.md:62-71`.
