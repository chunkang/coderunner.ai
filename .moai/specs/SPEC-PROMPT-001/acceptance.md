# SPEC-PROMPT-001 — Acceptance criteria (v1.0.0)

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. The measurement record is
> `verification-T3.md`.

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
| 3 | `verification-T3.md` §1 names the model tag, the digest if obtainable, and the host or compose service the probe reached | Read §1. An unnamed model is S4's failure |
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
| 2 | The classification cites the numbers that support it: V0 and V2 Target refusal rates, both with N | Read §5 against §2 and §3 |
| 3 | **M-c is distinguishable from M-a in the record.** A trial that produced a fenced block is not counted as success unless the code was also assessed. If code correctness was not assessed at T3, §5 says so and defers the M-a/M-c distinction explicitly to `SPEC-ACCOUNT-001` A1 | Read §5. The absence of this sentence, where correctness was not assessed, is the failure |
| 4 | **IF the outcome is M-b:** T4's routing half is not started, `SPEC-ACCOUNT-001` remains gated closed, and `SPEC-MODEL-001` is opened | Check the `main.py` diff and the specs directory |
| 5 | The gate was evaluated **before** `SYSTEM_PROMPT` was amended for the routing repair | `git log` ordering: the `verification-T3.md` §3 commit precedes the `main.py` routing commit |

**Item 5 is the one that will be tempting to fudge.** Writing the prompt first and measuring
afterwards produces the same files in the same state and a completely different epistemic claim.
The ordering is checkable in `git log` and that is why it is a criterion.

---

## AC-CONTROL — unrelated routing did not regress

**Covers:** S2, `spec.md` §3.5, `plan.md` R2

| # | Criterion | How it is observed |
|---|---|---|
| 1 | The control set contains at least one conversational prompt, at least one opinion prompt and at least one general-knowledge prompt, and all are expected to route DIRECT | Read the harness fixtures |
| 2 | The control set was measured under **V0**, before any prompt edit | `verification-T3.md` §2 contains control rows |
| 3 | The control set was measured again under the **shipped** prompt | `verification-T3.md` §4 |
| 4 | The shipped DIRECT rate on the control set is **no worse than V0's**, at the same N | Compare §4 with §2 |
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

**Item 5's "same commit" is not pedantry.** A citation corrected in a later commit is a window in
which the repository states something false about its own constraint, and the window closes only if
someone remembers.

---

## AC-VISIBLE — a `tools.py` failure is distinguishable from an empty result

**Covers:** E3, S3, N6

| # | Criterion | How it is observed |
|---|---|---|
| 1 | A `_ddg_instant()` failure — a JSON decode error, a network error — is distinguishable by the caller from "the query legitimately had no instant answer" | A test that induces each and asserts they differ |
| 2 | The test was observed **red before green** | Run it against the pre-change `tools.py:90-91` |
| 3 | `_HTML_RESULT_RE` (`tools.py:51-55`) is **unchanged** (N6) | Diff `tools.py` |
| 4 | The decision to leave the regex is recorded **in writing with its reason** — the stdlib-only contract at `tools.py:6` and `tools.py:82`, and the `-I`/`PYTHONPATH` rationale at `main.py:510` — in `spec.md` §8 item 2 and in `tech.md` §8.7 | Read both |
| 5 | `tech.md` §8.7's citations are corrected: `tools.py:91-92` → `:90-91`, `tools.py:95-96` → `:94-95` | Read §8.7 |

**Item 4 is S3 discharged.** S3 says fix-or-accept, in writing. Fixing half and staying silent on
the other half is the failure mode, and it is the one that reads as thoroughness.

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

See `plan.md` §4. Ten items, of which items 1, 3 and 5 are the ones most likely to be reported as
done without having been observed:

- item 1 — every criterion **observed**, not reasoned;
- item 3 — the gate recorded as **M-a / M-b / M-c**, not as "passed";
- item 5 — the control-set rate compared, and a regression recorded rather than rounded away.

`SPEC-KEYCHAIN-001`'s HISTORY names three of its own ten as never run. That is the standard this
SPEC is held to: not that everything was run, but that what was not run is named as not run.
