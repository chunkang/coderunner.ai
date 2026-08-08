# SPEC-CI-001 — T3 verification record

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. Acceptance criteria are in
> `acceptance.md`.

**Compiled 2026-08-07 from run logs that already existed.** No CI run was triggered to produce
this document and nothing was pushed for it. Every figure below was read out of
`gh run view <id> --log` for two runs that had already completed, and each is quoted verbatim
with the run it came from. Where a claim could only be made by inference it is not made; §4
lists what these logs do **not** establish, at greater length than §2 lists what they do,
because that is the honest ratio.

---

## 1. Provenance of the two runs

| | Run **31198290691** | Run **31145546652** |
|---|---|---|
| Conclusion | **success** | **failure** |
| Event | `pull_request` (PR **#4**, OPEN) | `pull_request` (PR **#3**, since MERGED) |
| Head branch | `feature/SPEC-INPUT-001` | `fix/tui-rendering` |
| Head SHA | `b8b325932683c6c5580051e253c9734d06d331cc` | `ab96df028506fe01f4b3d53ee660cab1fd0e0a90` |
| Created | `2026-08-07T16:35:18Z` | `2026-08-07T03:50:11Z` |
| Updated | `2026-08-07T16:36:20Z` | `2026-08-07T03:51:15Z` |
| Wall clock | **1m02s** | **1m04s** |
| `test` job | ✓ **52s** (id 92931808212) | ✗ **44s** (id 92764098738) |
| `image` job | ✓ **42s** (id 92931808246) | ✓ **1m00s** (id 92764098657) |

`b8b3259` is an ancestor of the current `HEAD` (`7a277b4`, `feature/SPEC-KEYCHAIN-001`); the four
keychain commits sit on top of it. So the green run measured the tree **one commit below** the
work this branch adds, and §4 is mostly a consequence of that fact.

---

## 2. What the green run establishes — run 31198290691

### 2.1 Architecture, read from the log rather than inferred from `ubuntu-latest`

T3 requires this because it is *"the first execution of this codebase on x86_64; every prior
measurement was aarch64"* (`.moai/specs/SPEC-MEMORY-001/spec.md:160`). `runs-on: ubuntu-latest`
is a label, not a measurement — GitHub has shipped arm64 hosted runners under adjacent labels,
so the architecture has to be read out of the run. Four independent strings say x86_64, and
they are quoted exactly:

```
  pythonLocation: /opt/hostedtoolcache/Python/3.11.15/x64
```

```
Cache hit for: setup-python-Linux-x64-24.04-Ubuntu-python-3.11.15-pip-711a08fc1918b8ecfcf47c8928f88ff7137f131e69efdced24d3088e7f0b5b09
```

```
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
```

```
Image: ubuntu-24.04
```

The `x64` in the toolcache path and the `Linux-x64` in the setup-python cache key are the
action's own reading of the host. The strongest corroboration is independent of that action —
**the wheel filenames pip actually selected**, which encode the platform tag the resolver
matched:

```
Using cached numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (16.9 MB)
Using cached faiss_cpu-1.15.0-cp310-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (18.8 MB)
Using cached grpcio-1.83.0-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (7.1 MB)
Using cached pyarrow-25.0.0-cp311-cp311-manylinux_2_28_x86_64.whl (50.1 MB)
Using cached coverage-7.15.4-cp311-cp311-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (255 kB)
Using cached ruff-0.16.1-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (11.5 MB)
```

Every compiled wheel in the install carries `_x86_64`. **`aarch64` occurs zero times in either
run's log** (`grep -c aarch64` = 0 on both). The C extensions the suite runs on — numpy's,
faiss's, grpcio's, pyarrow's, coverage's tracer — are therefore x86_64 builds, not the arm64
builds every previous measurement in this project used.

This discharges R3's premise: the code has now executed on x86_64 and did not fail there. It
does **not** discharge R3's concern, which is about future architecture-adjacent defects; one
green run on one tree is evidence, not immunity.

`faiss_cpu-1.15.0-cp310-abi3-...x86_64` also confirms the surviving half of R2 empirically
rather than from PyPI metadata: the abi3 x86_64 wheel R2 depends on exists and was selected.
`milvus_lite-3.2.0-py3-none-any.whl` and `pymilvus-3.0.1-py3-none-any.whl` were pure-Python, as
F3 predicted — see §5 for the one number in that set that has moved.

### 2.2 The `test` job's gates

Preflight (E3, AC-3):

```
ok       rich
ok       ollama
ok       httpx
ok       pymilvus
ok       milvus_lite
preflight ok - all 5 imports resolved
```

Lint (S4, AC-4):

```
All checks passed!
```

Suite and per-file coverage gate:

```
Per-file coverage gate passed (memory.py >= 100%, recall.py >= 100%, vectorstore.py >= 85%, params.py >= 100%, settings.py >= 100%)
```

```
Name             Stmts   Miss  Cover   Missing
----------------------------------------------
memory.py          204      0   100%
params.py          134      0   100%
recall.py           71      0   100%
settings.py        142      0   100%
vectorstore.py     266      0   100%
----------------------------------------------
TOTAL              817      0   100%
Required test coverage of 85% reached. Total coverage: 100.00%
============================= 469 passed in 18.06s =============================
```

Count and skip assertion (AC-1):

```
collected=469 passed=469 skipped=0 failures=0 errors=0
OK 469 passed, 0 skipped (floor 469)
```

**`MIN_PASSED` in force on that ref: `469`.** Read from the ref itself
(`git show b8b3259:.github/workflows/ci.yml` line 289) and echoed by the runner's own command
group, which prints the heredoc it is about to execute:

```
MIN_PASSED = 469
```

The floor and the observed count were equal on that run. That is a coincidence of timing — the
floor had just been raised to the measured value — not a property of the gate, which is a
`<` comparison.

### 2.3 The `image` job

```
import smoke ok
```

```
ok       main.py  1d9e552db179c97395af1bed6eab01a683488852826af571340a56aadfe304f3
ok       tools.py  59fb28ada7acdc2a8ae56ef82061b2e96191631f97055908c62c4ce4c7e022ee
ok       memory.py  16f642c3ecefb83c9fd2798e3a3ce9978158ca45be3ea89e6fe7e53359e3c9e3
ok       recall.py  4b8d2c3dfee99eabdbdbcef08e6b660bcc5b3f7643120eb6d1055c7eef9a4ed1
ok       vectorstore.py  db9e327d8467d5b35a9cb20927994cffdb480dc83b750bcda9bd01a49f133bb0
ok       params.py  2ca63e5c22162c6b3c718a24c2ac95d2afc03d8ec0b0608463dcfc225f6e0fe9
ok       settings.py  16e8a4c0b5a9cd6c822e3e9e0a7fccf29fa54eea169f53e65c66bd6e7020956f
```

**Seven files, and seven is all the tree had at that ref.** `git show b8b3259:Dockerfile` line 34
copies exactly those seven; the `FILES=` list at that ref names exactly those seven. The two
agreed, so this run says nothing about the case where they do not — see §4.4.

---

## 3. The negative evidence — run 31145546652, recorded under AC-1

The green run above cannot show that the `test` job is *capable* of reporting red. This one can,
and that is the only reason it is in this document.

Architecture, same two strings, same conclusion:

```
  pythonLocation: /opt/hostedtoolcache/Python/3.11.15/x64
```

```
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
```

The failure was a genuine product assertion, not an infrastructure fault:

```
FAILED tests/test_main_integration.py::test_render_stream_highlights_code_lines_as_they_arrive - AssertionError: assert '\x1b[38;2;' in 'T \x1b[36m─...
```

```
======================== 1 failed, 297 passed in 14.60s ========================
```

The job went red and the run's conclusion was `failure`. **That is the whole of what this run
establishes**, and it belongs to AC-1's "the job reports the state of the suite" clause.

Three qualifications, each of which narrows it:

1. **The count assertion did not produce the red.** That step runs `if: always()` and it
   *passed*:

   ```
   collected=298 passed=297 skipped=0 failures=1 errors=0
   OK 297 passed, 0 skipped (floor 296)
   ```

   `MIN_PASSED` was `296` on that ref and 297 tests passed, so the floor was met and no test was
   skipped. The red came from `pytest`'s exit status in the preceding step. So this run shows
   the **job** fails on a real defect; it does **not** show that the `passed < MIN_PASSED` or
   `skipped != 0` branches have ever been observed firing on a runner.

2. **The coverage gate passed, and enumerated only three floors:**

   ```
   Per-file coverage gate passed (memory.py >= 100%, recall.py >= 100%, vectorstore.py >= 85%)
   ```

   That is the state of `PER_FILE_COVERAGE_TARGETS` on `fix/tui-rendering`, which predates
   `params.py`, `settings.py` and `keychain.py`. It is recorded here because it dates the run,
   not because three is the current number — it is now six.

3. **The `image` job PASSED on this run** (1m00s), with `import smoke ok` and five `ok` hash
   lines. **This run therefore discharges no part of T8.** T8(d) requires an edited `main.py`
   with no rebuild, observed failing the hash comparison; nothing here approximates that. Nor
   does it discharge T8(a), (b) or (c): the failure was an ordinary test assertion, not a
   deliberately broken gate.

---

## 4. What these two logs do NOT prove

This section is longer than §2 on purpose. A green history is the easiest evidence in the world
to over-read.

### 4.1 Nothing about `feature/SPEC-KEYCHAIN-001`

`ci.yml` triggers on `push: [main]`, `pull_request: [main]` and `workflow_dispatch`. This branch
has never been pushed to `main` and has no pull request open against it, so
`gh run list --branch feature/SPEC-KEYCHAIN-001` returns **nothing**. Confirmed 2026-08-07.

Everything in §4.2–§4.4 follows from that one fact.

### 4.2 Nothing about `MIN_PASSED = 544`

`ci.yml:316` on this branch reads `MIN_PASSED = 544`, raised from `541` in the same change as
this record — 541 against a measured suite of 544 would have let three tests stop being
COLLECTED without the floor noticing, which is verbatim the failure the floor exists to catch,
and which `ci.yml:267-269` records as having already happened once (296 against 298, and it
"went unnoticed" *because* a trailing floor is safe).

The observed floor on the green run was **469**, on a ref where neither 541 nor 544 existed.
**Neither figure has ever been evaluated by a runner.** Both were derived from a host
measurement — 544 read from the `tests` attribute of a real local `pytest-results.xml`, the same
artefact the step parses, on 2026-08-07 under Python 3.11.14. That is the correct provenance for
the number and it is still not a runner's. A locally-measured floor is exactly the kind of number
this SPEC exists to stop trusting on sight.

### 4.3 Nothing about `keychain.py`'s coverage floor

`conftest.py:204-212` now declares **six** floors. The green run's gate line enumerates **five**
and does not mention `keychain.py`, because `keychain.py` did not exist at `b8b3259`. Neither
the floor nor the `--cov=keychain.py` entry it depends on in `pytest.ini` has been exercised on
a runner. A missing `--cov=` entry fails through the `coverage unavailable` branch at
`conftest.py:227-229`, which is loud — but "loud when it fires" and "observed firing" are not
the same claim, and only the first is supported here.

### 4.4 Nothing about the eight-file COPY

`Dockerfile:43` now copies **eight** modules. The green run hash-checked **seven**, on a ref
whose COPY line named seven. The eight-file image has never been built by CI, its import smoke
has never run, and the hash comparison has never seen `keychain.py`.

This is also where the two lists silently diverged: `479d700` (2026-08-07T11:16:41-07:00) added
`keychain.py` to `Dockerfile:43` and not to `FILES=`, and no CI run has occurred on this branch
since — so the divergence was never going to be reported by a run. It was closed on 2026-08-07
by `tests/test_source_seam.py`, which parses both lists and asserts set equality, and by adding
`keychain.py` to `FILES=` and to the in-image import smoke. **That test was observed failing
against the seven-file list before the fix was made**, on both of its assertions.

### 4.5 Nothing about T5, T8, or the canary

- **T5** (cold vs. warm image build durations, as separate numbers) is untouched. The `image`
  job times above — 42s and 1m00s — are *whole-job* wall clock including checkout, buildx setup,
  the run, the smoke and the hash step, on a warm `type=gha` cache of unknown state. They are
  **not** the cold and warm build durations R1's demotion decision is supposed to be taken on,
  and must not be used as such.
- **T8** requires four deliberate breakages, each observed red. Neither run here is one.
  Runs exist on a `t8-gate-verification` branch (PR #2, since closed); **this document makes no
  claim about them**, having neither examined nor reproduced them.
- **AC-5** (the canary) is not touched by either run. Both are `CI`, not the canary workflow.
- **AC-6**'s concurrency behaviour is not observable in either log; both were single runs.

### 4.6 A green run is not evidence for an unexercised floor

Stated plainly because it is the failure mode this record exists to avoid: the pipeline has
never been red for a reason it was built to catch, and it has never run at all on the tree that
introduced the three items in §4.2–§4.4. AC-1 is discharged **for `b8b3259`** and for no other
ref.

---

## 5. One incidental observation, recorded rather than acted on

The green run resolved **`milvus_lite-3.2.0-py3-none-any.whl`**. `spec.md`'s authoring-time
baseline records **`milvus-lite 3.1.1`**. `requirements.txt:16` pins `pymilvus[milvus_lite]>=3.0.1`
— a floor, not a version — so the engine moved a minor release beneath it without any commit,
and the suite passed at 100% on the new one.

This is F3's drift class occurring in the ordinary `test` job rather than in the canary, which
is the job built to watch for it. It is recorded here as a measurement, not as a finding: the
`test` job restores a pip cache and does not use `--upgrade`, so this is not a clean resolution
and must not be mistaken for the T7 baseline. `pymilvus 3.0.1` and `numpy 2.4.6` matched the
baseline exactly.

---

## 6. Status after this record

| Task | Status |
|---|---|
| **T3** | **Partially discharged, for `b8b3259` only.** x86_64 confirmed from the log by four independent strings; suite green at 469 passed / 0 skipped; all floors then declared were met; `Per-file coverage gate passed` present verbatim. Not discharged for this branch, for `MIN_PASSED = 544`, for `keychain.py`'s floor, or for the eight-file COPY (§4). |
| **T5** | **Not started.** No cold/warm separation exists. |
| **T8** | **Not started here.** Run 31145546652 shows the `test` job reporting red on a genuine assertion failure and is recorded under AC-1; its `image` job passed. |
| **T9** | Still blocked on T5 and T8, per `plan.md` §2. Nothing in this document licenses writing it. |
