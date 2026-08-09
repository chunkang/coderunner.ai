# SPEC-PROMPT-001 — Acceptance criteria (v1.1.1)

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. The measurement record is
> `verification-T3.md`.

> **v1.1.1 (2026-08-09).** **AC-GATE item 5 amended** — its `git log` form is permanently
> unsatisfiable for this SPEC, because the pre-registration and the results were never committed
> separately. Replaced by a check carried inside the trial records, with the reason stated beside it.
> Item 2a's ordering half moved to item 5. See `spec.md` HISTORY v1.1.1 and `verification-T3.md`
> §1.0.
>
> **v1.1.0 (2026-08-08).** Four of `spec.md` HISTORY's five corrections reach this file. **A4**
> replaces AC-GATE's endpoint: the gate is decided on the machine-coded **DIRECT** rate against a
> **pre-registered** rule, and refusal rate becomes a reported secondary. **A5** adds AC-GATE item 7
> (V3 under M-b) and raises every N. **A3** adds AC-N2 item 7 (unfenced prompt material, N9).
> **A2** adds AC-VISIBLE items 6–8: `tools.py` is **not** gated and has **never** had a test, so
> "observed red before green" requires building the suite first. Nothing is deleted; superseded text
> is struck through with the reason it stopped holding.

Nine criteria. Three of them (**AC-MEASURE**, **AC-GATE**, **AC-CONTROL**) cannot be discharged by
reading code, because the thing under test is a model's behaviour. Those three are the reason this
SPEC exists in this shape, and they are stated first.

**A note on what "passing" means here.** Six of the nine are ordinary assertions. Three are
measurements, and a measurement passes by being **taken and recorded**, not by producing a
particular number. **AC-GATE** in particular passes when the outcome is correctly classified — an
honest **M-b** discharges it exactly as well as an M-a, and then stops the SPEC. A criterion that
can only pass one way is not a measurement; it is a wish.

---

## AC-MEASURE — the instrument exists, and it reports what the product does

**Covers:** U5, U6, E6, S4, S5, N7

| # | Criterion | How it is observed |
|---|---|---|
| 1 | The probe harness drives `llama3.1:8b` with a given `SYSTEM_PROMPT` variant and a given task prompt, N times, and records the variant, the task, the **verbatim reply** (O3) and the classification for every trial | Run it; inspect the per-trial records |
| 2 | **The classifier is the production predicate.** The harness imports `extract_last_python_block` from `main.py` and classifies a trial DIRECT iff it returns falsy. It does **not** carry its own copy of the regex | Read the import. Then mutate: point the harness at a private reimplementation and confirm the test suite notices, or if it cannot, record that as a known limit rather than claiming coverage |
| 3 | `verification-T3.md` §1 names the model tag, the digest if obtainable, and the host or compose service the probe reached — **read back from the running server (`client.list()`, `client.show()`, observed `OLLAMA_HOST`), never from `docker-compose.yml`** | Read §1. An unnamed model is S4's failure. *`docker-compose.yml:46` and `:78` are `${CODERUNNER_MODEL:-llama3.1:8b}` — a default, not a pin, so the file states an intention and only the server states a fact* |
| 3a | **The probe does not pin temperature, does not set a seed, and passes no `options=`** (N10) — it calls `main.stream_llm()`, which passes none, so production sampling is inherited by construction. The sampling it inherited is **recorded** | Read the harness for `options=`, `temperature`, `seed`. *A temperature-0 measurement measures a different distribution from the one that produced the reported refusal* |
| 4 | Every figure in §2–§4 carries the variant, the task cell and **N** | Read the tables |
| 5 | **No placeholder figures anywhere in `verification-T3.md`** — cells are empty and explicitly marked not-yet-run until a run fills them | Read the file before any run. Every results cell reads as unrun, and no cell contains a plausible-looking number |
| 6 | While §2–§4 are unrun, the file says so at the top, and T4 has not been started | Check the file header against the `main.py` diff |

**The failure this criterion is really guarding against** is a probe that is easier to satisfy than
the product. Item 2 is the whole criterion; the rest is bookkeeping around it.

---

## AC-GATE — the three-outcome classification is made, and it is honest

**Covers:** S1, `spec.md` §3.4

| # | Criterion | How it is observed |
|---|---|---|
| 1 | `verification-T3.md` §5 records the outcome as exactly one of **M-a**, **M-b**, **M-c** — never as "pass", "fail", "improved" or "works" | Read §5 |
| 2 | ~~The classification cites the numbers that support it: V0 and V2 Target **refusal** rates, both with N~~ **RESTATED at v1.1.0 (A4).** The classification cites V0 and V2 Target **DIRECT** rates (E6), both at **N=30**, and applies the pre-registered rule textually: `(r0 − r2) ≥ 0.40` **AND** one-sided Fisher exact rejecting at `alpha = 0.05`. **Refusal rates are reported beside them and decide nothing** | Read §5 against §1's rule and §2/§3's tables. If §5 reasons about refusal rate to reach its outcome, the criterion fails |
| 2a | **The rule applied in §5 is textually the rule written in §1** | Diff §5's applied rule against §1.1's stated rule, word for word. *This half is fully checkable and remains so.* The **ordering** half is **not** — see item 5 as amended, and `verification-T3.md` §1.0 |
| 2b | **The gate is decided on the Target cell alone.** No other cell is cited in support of the outcome, and no multiplicity correction appears — because none is needed | Read §5. A sentence of the form "although the Target cell did not clear the threshold, the off-example cell…" is this criterion's failure, written out |
| 2c | **Every trial record carries its fence-match count** (E7), and §5 states how many DIRECT-classified Target trials had `fence_matches >= 2` | Read the JSONL and §5. *A two-fence reply classifies DIRECT while refusing nothing (`tests/test_source_seam.py:533-548`). Uncounted, it inflates the secondary refusal figure and contaminates the gated one* |
| 3 | **M-c is distinguishable from M-a in the record.** A trial that produced a fenced block is not counted as success unless the code was also assessed. If code correctness was not assessed at T3, §5 says so and defers the M-a/M-c distinction explicitly to `SPEC-ACCOUNT-001` A1 | Read §5. The absence of this sentence, where correctness was not assessed, is the failure |
| 4 | **IF the outcome is M-b:** T4's routing half is not started, `SPEC-ACCOUNT-001` remains gated closed, and `SPEC-MODEL-001` is opened | Check the `main.py` diff and the specs directory |
| 5 | The gate was evaluated **before** `SYSTEM_PROMPT` was amended for the routing repair | ~~`git log` ordering: the `verification-T3.md` §3 commit precedes the `main.py` routing commit~~ **AMENDED at v1.1.1 — see below.** Observe instead: `main.py`'s **sha256 recorded in every trial record** of the variant being gated matches the **pre-amendment** `main.py`. That is carried inside the data rather than alongside it, so it cannot be lost by how the work happens to be committed |
| 5a | **The V0 baseline was measured against an unmodified `main.py`** | `verification-T3.md` §1.3 records `main.py`'s sha256, and §2.1 records that it is **identical across all 30 records**. Re-compute it against the pre-amendment blob. *This is the substantive claim item 5 was reaching for, and unlike the git form it is checkable from the artefacts themselves* |
| 6 | **Every cell was run at the v1.1.0 N** — Target 30, off-example 20, tool-reachable 20, control 30 per prompt — **or the shortfall is stated in words with the number actually run** | Read §2–§4. *If budget forced a cut it must have been taken in the NUMBER of control prompts (floor 3, one of each kind), never in N below 20 (`spec.md` §4)* |
| 7 | **IF the outcome is M-b:** V3 (V0 + capability, `spec.md` A5) is measured at the tool-reachable cell (N=20) and across the full control set (5 × N=30), recorded in §3.6, **before any prompt text is merged** (S6) | Read §3.6 against the `main.py` diff's commit date. *Under M-b what ships is `V0 + capability` and V0, V1 and V2 are none of them that prompt. Shipping it unmeasured is the failure this item exists for* |

**Item 5 is the one that will be tempting to fudge.** Writing the prompt first and measuring
afterwards produces the same files in the same state and a completely different epistemic claim.

**Why item 5 was amended at v1.1.1, stated plainly rather than folded into the new wording.** The
original form — *"the ordering is checkable in `git log`"* — **was not satisfied for this SPEC's own
T1/T2 work, and it can never be satisfied retroactively.** The v1.1.0 amendments (including the gate
rule itself) and the V0 Target results were produced in **one uncommitted working tree**; committing
them now yields a single commit containing both, which is precisely the artefact that would exist
had the rule been fitted to the data. `verification-T3.md` §1.0 discloses this in full.

**The criterion was amended rather than marked satisfied, and rather than deleted.** A criterion
that cannot be met is not evidence of anything, and leaving it in place to be quietly ticked is
worse than not having it: it converts an unmet requirement into a claim. What replaces it is
**checkable from the artefacts themselves** — `main.py`'s sha256 is recorded inside all 30 trial
records, so "the baseline was measured against an unmodified prompt" survives any commit topology.

**The residue, named:** the amended item verifies *what `main.py` was* when the data were taken. It
does **not** verify *when the decision rule was written*. That question now rests on
`verification-T3.md` §1.0's four items of circumstantial evidence and on nothing stronger. **A future
SPEC should commit the pre-registration on its own, before running anything** — that is the cheap
fix, and it is unavailable only in retrospect.

---

## AC-CONTROL — unrelated routing did not regress

**Covers:** S2, `spec.md` §3.5, `plan.md` R2

| # | Criterion | How it is observed |
|---|---|---|
| 1 | The control set contains at least one conversational prompt, at least one opinion prompt and at least one general-knowledge prompt, and all are expected to route DIRECT | Read the harness fixtures. **Asserted offline in `tests/test_probe.py`**, not checked by eye |
| 2 | The control set was measured under **V0**, before any prompt edit | `verification-T3.md` §2 contains control rows |
| 3 | The control set was measured again under the **shipped** prompt | `verification-T3.md` §4 |
| 4 | The shipped DIRECT rate on the control set is **no worse than V0's**, at the same N | Compare §4 with §2 |
| 4a | **N is 30 per control prompt** (v1.1.0, A5), or the shortfall is stated | Read §4. *By the rule of three, 0 failures in 10 trials bounds the true regression rate only at **30%**; 0 in 30 bounds it at **10%**. A control that cannot exclude a 30% regression is not a defence against R2, which is the highest-blast-radius risk in this SPEC* |
| 5 | **IF it is worse**, that is recorded as a finding with its numbers, and either resolved or explicitly accepted in writing. It is **not** rounded away, and it is not attributed to noise without stating N | Read §4 and the SPEC HISTORY |
| 6 | If the control set ran at a smaller N than the target set, §4 states both | Read §4 |

**Why this is a first-class criterion rather than a checklist line.** The regression it guards
against has no error message, no log line and no test. It presents as the product feeling slower and
more eager, on every turn, for every user — including everyone who never asks it about mail. It is
the highest-blast-radius risk in the SPEC and the only thing standing in front of it is this table.

---

## AC-ROUTE — the contradiction is gone

**Covers:** U2, E1

| # | Criterion | How it is observed |
|---|---|---|
| 1 | No clause in `SYSTEM_PROMPT` routes to DIRECT on a ground another clause permits under CODE. Specifically: the *"needs live data you don't have"* ground at `main.py:128-129` no longer contradicts the network permission at `:143-145` and the tie-break at `:174` | Read the three sites together, in order, as a single reading. If a reader has to decide which rule wins, the criterion fails |
| 2 | DIRECT is defined by the absence of an answering action, not by the model's present possession of data | Read the amended clause |
| 3 | Measured: V1's Target refusal rate is recorded against V0's | `verification-T3.md` §3 |
| 4 | Measured: the **off-example network task** — outside `wttr.in` / Wikipedia / DuckDuckGo, and involving no account or credential — routes to CODE at a rate recorded against V0 | `verification-T3.md` §3 |

**Item 4 is the one that isolates the routing repair from anything mail-shaped.** If the
off-example task improves and the Target does not, the residue is account-specific and belongs to
`SPEC-ACCOUNT-001`. If neither improves, the repair did not work and saying so is the point.

---

## AC-TOOLS — the helper is discoverable, and discovery is measured not asserted

**Covers:** U1, U3, E2, N4, N8

| # | Criterion | How it is observed |
|---|---|---|
| 1 | `SYSTEM_PROMPT` names `tools.py` and `from tools import web_search`, states its return shape and its stdlib-only guarantee | Read `main.py:122-182` |
| 2 | **Every capability stated in the new section carries a worked example**, in the shape of `main.py:146-153`. A stated capability with no example fails this criterion (U3, N4) | Read the section. Count statements; count examples |
| 3 | Measured: on the tool-reachable task, the model actually emits code that imports `tools` and calls `web_search`, at a rate recorded with N | `verification-T3.md` §3 |
| 4 | **`product.md` §6.1 is declared resolved only on the strength of item 3's measured rate.** The presence of the string `web_search` in `SYSTEM_PROMPT` does not close §6.1 (N8) | Read §6.1's resolution text. It quotes a rate and an N, or it fails |
| 5 | `structure.md` §5.3 is resolved on the same evidence, and its `main.py:210-211` citation is corrected to `main.py:507` | Read §5.3 |

**Item 4 exists because this is the easiest false claim in the SPEC.** §6.1 says the model "has no
way to discover the helper". Adding the name removes that specific sentence's truth without
establishing that discovery now happens. Those are different facts and only one of them closes the
finding.

---

## AC-N2 — the pinned constraint is intact, and its citation is still re-checkable

**Covers:** U4, N1, N2, N3, E4

| # | Criterion | How it is observed |
|---|---|---|
| 1 | `git show 1d5fff1:main.py \| sed -n '140,148p'` still prints the nine-line `@param` passage | Run it. This is `spec.md` §2.3's method and it must keep working, because it is the only thing that makes §2.3 evidence rather than assertion |
| 2 | The `@param` passage in the working tree is **semantically unchanged** — same grammar, same four types, same "never emit a second fenced block" | Diff the passage. Whitespace-only movement is acceptable; a word change is not |
| 3 | New prompt material is inserted **below** the passage (N3) | Read the diff's line numbers |
| 4 | `SYSTEM_PROMPT` contains **zero** occurrences of `os.environ` and **zero** of `keychain`, case-insensitive (N1, N2) | An assertion in the test suite, not a review note. `SPEC-KEYCHAIN-001`'s HISTORY records a check that had been "inspecting nothing" for exactly this reason |
| 5 | `SPEC-KEYCHAIN-001` §6.4 N2 **and** its §9 traceability row cite the passage's post-change range, changed in the **same commit** as `main.py` (E4) | `git show` the commit; both files present |
| 6 | The re-cited range is verified by resolving it against the post-change tree, not by arithmetic on the old one | Run `sed -n` on the new range and read what comes out |
| 7 | **New prompt material is indented and unfenced** (N9, added v1.1.0). `tests/test_source_seam.py:547`'s `prompt.count("```") == 2` is **green without having been modified** | Read the diff for both `main.py` and that test. *If the assertion was relaxed to accommodate the new section, that is a finding rather than a fix: it is the one regression net this prompt has, and the SPEC would have removed it in the act of relying on it* |
| 8 | The new examples copy the shape of `main.py:146-153` and `main.py:162-163` — both already indented and unfenced | Read them side by side. *Two reasons, both measured: item 7's assertion, and `tests/test_source_seam.py:533-548`, where a two-fence reply makes `CODE_BLOCK_RE.findall()` return `['']`, `extract_last_python_block()` return the empty string, and the turn classify **DIRECT** with no exception and no retry. A prompt that demonstrates the two-block form teaches the model the exact failure this SPEC exists to remove* |

**Item 5's "same commit" is not pedantry.** A citation corrected in a later commit is a window in
which the repository states something false about its own constraint, and the window closes only if
someone remembers.

---

## AC-VISIBLE — a `tools.py` failure is distinguishable from an empty result

**Covers:** E3, S3, N6

| # | Criterion | How it is observed |
|---|---|---|
| 1 | A `_ddg_instant()` failure — a JSON decode error, a network error — is distinguishable by the caller from "the query legitimately had no instant answer" | A test that induces each and asserts they differ |
| 2 | The test was observed **red before green** | Run it against the pre-change `tools.py:90-91`. **Note (v1.1.0, A2): there is no test file to run it from.** `tests/test_tools.py` does not exist, so "observed red" requires creating the suite first — see items 6–8 |
| 3 | `_HTML_RESULT_RE` (`tools.py:51-55`) is **unchanged** (N6) | Diff `tools.py` |
| 4 | The decision to leave the regex is recorded **in writing with its reason** — the stdlib-only contract at `tools.py:6` and `tools.py:82`, and the `-I`/`PYTHONPATH` rationale at `main.py:510` — in `spec.md` §8 item 2 and in `tech.md` §8.7 | Read both |
| 5 | `tech.md` §8.7's citations are corrected: `tools.py:91-92` → `:90-91`, `tools.py:95-96` → `:94-95` | Read §8.7 |
| 6 | **`tests/test_tools.py` exists.** It did not before this SPEC: verified 2026-08-08, `tests/` holds eleven `test_*.py` files and none of them is it | `ls tests/`. *`plan.md` §0 claimed `tools.py` was "gated and tested" on the strength of `structure.md:234`, which is a row in a table headed "Why it is **testable** in isolation" — an aspiration, not a coverage record* |
| 7 | **`tools.py` is registered in BOTH gate locations, or in neither**: `--cov=tools` in `pytest.ini`'s `addopts` **and** a `tools.py` floor in `conftest.py`'s `PER_FILE_COVERAGE_TARGETS` | Read both files in the same diff. *`pytest.ini:42-46` documents the loud half-landing: an entry without a `--cov` makes `cov.report(include=[...])` raise and fails the session. The **quiet** half-landing is the other one — a `--cov` with no entry measures the module and enforces **nothing**, and nothing fails at all* |
| 8 | The chosen floor is stated with its reason, in the style `conftest.py:184-195` established for every module added since — including what it would mean to lower it later | Read the comment beside the new entry |

**Item 4 is S3 discharged.** S3 says fix-or-accept, in writing. Fixing half and staying silent on
the other half is the failure mode, and it is the one that reads as thoroughness.

**Items 6–8 are the v1.1.0 correction (A2), and they change this criterion's size rather than its
meaning.** v1.0.0 read `tools.py` as an already-gated module receiving one `except`-block fix. It is
not gated, it has never had a test, and `structure.md:234` — the cited evidence — is a row in a
proposal. So item 2's "observed red before green" has nowhere to be observed from until item 6 is
done, and item 7 is the difference between a module that is measured and a module that is
**enforced**.

---

## AC-FLOOR — the CI floor is a measurement

**Covers:** E5, `spec.md` §7 item 7

| # | Criterion | How it is observed |
|---|---|---|
| 1 | `MIN_PASSED` at `.github/workflows/ci.yml:316` is raised from **544** to a count read out of a real `junitxml` run | The run is identified in the commit message or the SPEC HISTORY |
| 2 | The count was **not** computed as 544 plus an expected number of new tests | The identified run's own reported total matches |
| 3 | CI still asserts `skipped == 0` | Read the workflow |

---

## AC-DOCS — the corrections landed

**Covers:** `spec.md` §7 item 6

| # | Correction | From | To |
|---|---|---|---|
| 1 | `product.md` §6.1 `SYSTEM_PROMPT` citation | `main.py:100-151` | `main.py:122-182` |
| 2 | `structure.md` §5.3 sandbox-copy citation | `main.py:210-211` | `main.py:507` |
| 3 | `tech.md` §8.7 swallowed-exception citation | `tools.py:91-92` | `tools.py:90-91` |
| 4 | `tech.md` §8.7 outer-handler citation | `tools.py:95-96` | `tools.py:94-95` |

| # | Criterion | How it is observed |
|---|---|---|
| 5 | `product.md` §6.1 is marked resolved in the style §6.2 established — the finding is **kept rather than deleted**, with what it was and what closed it | Read §6.1 |
| 6 | Corrections found but **out of scope** are recorded rather than silently left: `structure.md`'s stale tree, its §5.1 claim that `main.py` imports no first-party module (contradicted at `main.py:49-51`), and its §6 claim that no test suite exists | `spec.md` §8 item 6, and `SPEC-KEYCHAIN-001` §2.4 which already records them |

---

## Definition of done

See `plan.md` §4. Ten items at v1.0.0, **thirteen at v1.1.0**, of which items 1, 3, 5 and the new 11
are the ones most likely to be reported as done without having been observed:

- item 1 — every criterion **observed**, not reasoned;
- item 3 — the gate recorded as **M-a / M-b / M-c**, not as "passed";
- item 5 — the control-set rate compared, and a regression recorded rather than rounded away;
- item 11 — the gate rule **written before the numbers existed**, and applied textually afterwards.

`SPEC-KEYCHAIN-001`'s HISTORY names three of its own ten as never run. That is the standard this
SPEC is held to: not that everything was run, but that what was not run is named as not run.
