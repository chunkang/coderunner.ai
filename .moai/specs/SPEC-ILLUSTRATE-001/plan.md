# SPEC-ILLUSTRATE-001 — Implementation Plan (v1.0.0)

> Requirements are in `spec.md`. Acceptance criteria are in `acceptance.md`. The measurement record is
> `verification-T2.md`, and it is **empty**.

## 0. Starting position

Everything needed to observe this defect exists; nothing needed to decide on a fix does.

| Present | Evidence |
|---|---|
| A measured rate for the defect — **CODE 30/30, DIRECT 0/30**, Wilson **[0.000, 0.114]** | `v0-c4-general-knowledge.jsonl`, 2026-08-10 (`spec.md` §2.2) |
| A behavioural instrument that can measure a prompt's effect at all | `probe/` on `feature/SPEC-PROMPT-001` — the project's first, and it is **not on `main`** |
| A candidate discriminator with a clean separation on every cell that exists | 30/30 vs 0/43 (`spec.md` §2.4) |
| A path from block to execution with no decision point in it | `main.py:1071-1074`, `:1108-1152` |
| A documented statement of the gap, in the product's own docs | `tech.md:553` — *"no AST inspection … Whatever the model emits between the fences is written to disk and run"* |

| Absent | Consequence |
|---|---|
| **A probe cell for `product.md` §5.4** — deterministic computation on user-supplied data | The discriminator's **false-positive rate is unmeasured**, and §5.4 blocks are closed and import-free exactly as c4's are. **This is the whole reason T1 exists and the reason T4 cannot start** |
| Any measurement of any control prompt under any variant but **V0** | Whether the defect survives the prompt `SPEC-PROMPT-001` ships is unknown (`spec.md` §5 item 1) |
| Any assessment of whether a generated block **runs**, let alone is correct | 30/30 parse. That is all (`spec.md` §5 item 2) |
| Any latency or token figure for the **second** round trip | The probe issues one `stream_llm()` call per trial and executes nothing. "Roughly double" is inferred from `structure.md:122-124` |

So this is not a "write the fix" plan. It is a **"build the one missing measurement, then decide"**
plan. **T2 is where the value is; T3 is the decision; T4 onward is the consequence of T3 and does not
exist until T3 has a number to be a consequence of.**

**One correction to make in passing:** `product.md` §5.5 (`product.md:212-217`) documents behaviour
that is measured at 0/30, and `README.md:109` repeats it. T7 owns the fix, and T7 is **not** blocked
on any measurement — the documented claim is already known to be false.

---

## 1. Task decomposition

Eight tasks. **None has been started.** T2, T3 and T6 require a model; T1 and T4–T8 do not.

| # | Task | Artefact | Depends on |
|---|---|---|---|
| **T1** | **Add the compute-only cell to `probe/tasks.py`.** One `Task`, `kind` general/compute, `n = 30`, `expect_direct = False`, in the shape of `product.md` §5.4 — arithmetic, parsing, a text transform or date math on data given **in the request**, so the correct block is self-contained and import-free **and must run**. Choose the prompt so that its block is the hardest possible case for the predicate, not the easiest: **a cell that the predicate passes trivially measures nothing.** **Additive only** — no existing `Task` changes by one byte (`spec.md` N7, D6), and the diff must show exactly one added entry. Add the per-trial predicate verdict field at the same time if O4 is taken. | `probe/tasks.py` (on a branch carrying `probe/`) | — |
| **T2** | **Run the measurement, and record it.** Three cells at **V0**, N=30 each: (a) the new compute cell; (b) **c4 re-measured** under the prompt string current at run time, labelled with which string that is (`spec.md` E6); (c) the predicate evaluated over both, reporting **both halves** of the separation (`spec.md` U6). Plus, at the cost of one field, O3: **do c4's blocks execute without raising, and what do they print?** Record every figure in `verification-T2.md`, and **nothing that a run did not produce** (`spec.md` N6). **Pre-register the acceptable false-positive rate in `verification-T2.md` §1 and commit that file on its own before the run starts** — `SPEC-PROMPT-001` v1.1.1 records what it cost not to, and that fix is available only in advance. | `verification-T2.md` | T1 |
| **T3** | **Decide, on T2's numbers, whether Stage 2 ships.** The gate is at `verification-T2.md` §1 and it is `acceptance.md` **AC-MEASURE**'s subject. Three outcomes, all admitted in advance: **I-a** the predicate separates well enough to gate on → Stage 2 proceeds; **I-b** the false-positive rate is too high → Stage 2 does **not** ship as specified and the SPEC's remaining value is §4's boundary and T7's documentation; **I-c** c4's rate under the shipped prompt has moved far enough that the premise has changed → re-open §2 before doing anything else. **I-b is a real outcome and not a failure of the SPEC**; a discriminator measured unusable is a result. | `verification-T2.md` §5 | T2 |
| **T4** | **The predicate, as a new gated leaf.** `ast`-only, stdlib-only, no first-party import, floored at **100 %**. Registered in **both** `pytest.ini`'s `--cov` list **and** `conftest.py`'s `PER_FILE_COVERAGE_TARGETS` — both or neither; one without the other makes the coverage report raise and the session fail, which is the right direction for that mistake. Added to the `Dockerfile` `COPY` line **and** to every file list `tests/test_source_seam.py` asserts set equality over. Behaviour on an unparseable block is **do not fire** (`spec.md` S1, N4), and that is a test, not a comment. | new module, `pytest.ini`, `conftest.py`, `Dockerfile`, `tests/` | **T3 = I-a** |
| **T5** | **The wiring, in `main.py`, and nothing else.** Evaluate the predicate once; carry the result as a value; branch at `main.py:1108-1152` to skip the narration round trip and the capture; emit exactly one status line (`spec.md` E1–E3, U2). **No decision logic in `main.py`** (`spec.md` N3) — if a change here would need a new test to be trusted, it is in the wrong file. The execution panel still renders (`spec.md` S4): no turn ends with less on screen than it does today. | `main.py` | T4 |
| **T6** | **Verify against the model, not against the unit tests.** Re-run T2's cells with the change in place and confirm: the predicate's firing rate on c4 is what T2 measured; **no turn in the compute cell lost its narration** beyond the pre-registered rate; the status line appears exactly once per firing turn; the store gained **no** record for a firing turn. A unit test proves the predicate; only this proves the product. | `verification-T2.md` §4 | T5 |
| **T7** | **Documentation, and it is not blocked on any of the above.** `product.md` §5.5 (`product.md:212-217`) is false today and is corrected today: the measured rate, its date, its provenance, in the style §6.2 uses for a closed finding and §6.1 for an open one. `README.md:109` carries the same claim and goes with it. `product.md` §6 gains one limitation while the defect is live. `tech.md:553`'s row is repointed (`main.py:218-220` → `:447-449`) and, after T5, amended to say what the predicate screens and what it does not — it is **not** deleted, because the predicate is not a security control (`spec.md` N9). `structure.md` §3.1's diagram gains the branch and its citations are repointed. | `product.md`, `README.md`, `tech.md`, `structure.md` | — for the §5.5/README half; T5 for the rest |
| **T8** | **Raise `MIN_PASSED`** (`.github/workflows/ci.yml:332`) to a count **read from a real `junitxml` run**, never computed from an expected delta. The literal lives in exactly one place and is cited by symbol everywhere else (`SPEC-CI-001` N5). | `.github/workflows/ci.yml` | T4, T5 |

### 1.1 Dependencies and critical path

```
T1 ── T2 ── T3 ──(I-a)── T4 ── T5 ── T6
                                  └── T8
T7 (documentation half) ──────────────── independent
```

**Critical path: T1 → T2 → T3 → T4 → T5 → T6.**

**T3 is a gate, not a milestone.** Under **I-b** the path stops there and T4, T5, T6 and T8 are never
started; the SPEC's delivered value is then `spec.md` §4, §5 and T7, which is a smaller thing than
was hoped for and a real one. Under **I-c** the path returns to `spec.md` §2.

**T7's first half depends on nothing.** `product.md` §5.5 asserts something measured false eight
weeks before this document; it does not become more false or less by waiting for a fix.

### 1.2 Priority

| Priority | Tasks | Rationale |
|---|---|---|
| **High** | T1, T2, T3 | The one measurement that does not exist is the one every other decision needs. Everything downstream is unfalsifiable without it, which is `SPEC-PROMPT-001` U5's prohibition arriving one layer down |
| **High** | T7 (the `product.md` §5.5 / `README.md:109` half) | A document that states the opposite of a measured behaviour is worse than one that says nothing, because it is trusted. It costs two paragraphs and no measurement |
| **Medium** | T4, T5, T6 | The fix. Real value — one model round trip and one persistent write per occurrence — but conditional on T3, and the defect has been live since before any of these SPECs |
| **Low** | T8, T7 (the rest) | Necessary for the work to hold; nothing depends on them |

**Final goal is T6.** Optional goal: `spec.md` O1–O4 — the `/memory` explanation, the latency
figure, the block-execution field, and the per-trial predicate verdict. O3 and O4 are nearly free
**if taken at T1/T2** and expensive to retrofit, which is the only reason they are named here at all.

---

## 2. Execution decision — what is delivered now, and what is not

**Nothing is implemented by this SPEC's authoring.** The four documents in this directory are the
deliverable. No source file is edited, no prompt text is written, no probe is run, and nothing is
committed by the act of writing them.

| Task | Requires a model? | Requires `probe/`? | Status |
|---|---|---|---|
| T1 | no | **yes** — a branch carrying `probe/` | not started |
| **T2** | **yes** — `llama3.1:8b` on the compose sidecar, ~30–90 min per cell at the observed rates | **yes** | **not started** |
| T3 | no | — | blocked on T2 |
| T4, T5 | no | no | blocked on T3 |
| **T6** | **yes** | **yes** | blocked on T5 |
| T7 | no | no | **deliverable now** (documentation half) |
| T8 | no | no | blocked on T4/T5 |

**Until T2 and T3 have run, this SPEC is specified, not decided.** Say so in any status report, and
do not describe the predicate as "the fix" — it is a candidate with one measured half.

### 2.1 Where the work happens, and the branch it happens on

`probe/` does not exist at `ab08333`. T1, T2 and T6 therefore run on `feature/SPEC-PROMPT-001` or on
a branch that carries it. That has one consequence worth stating before someone discovers it:
**T2's records will live next to `SPEC-PROMPT-001`'s**, under a directory that SPEC owns. They must
be written to **`.moai/specs/SPEC-ILLUSTRATE-001/probe-runs/`** and never to that SPEC's, and
`verification-T2.md` cites them by path. Two SPECs' evidence in one directory is one SPEC's evidence
by the time anybody reads it.

**And the branch this document sits on should be renamed before anything is pushed:**
`git branch -m feature/SPEC-DIRECT-001 feature/SPEC-ILLUSTRATE-001`. Verified 2026-08-12 —
there is no `origin/feature/SPEC-DIRECT-001`, so the rename costs one command today and a published
reference tomorrow (`spec.md` HISTORY).

---

## 3. Technical approach — the four decisions worth defending

### 3.1 The measurement comes first, and it measures the thing that could go wrong

The tempting order is: write the predicate, see it fire on c4's thirty, ship it. **That order tests
the half that already has an answer.** 30/30 is known. What is not known is what the predicate does
to a turn that genuinely needs to run — and that turn is `product.md` §5.4, the product's second
documented use case, with **no cell in any arm**.

So T1's cell is chosen adversarially: a computation whose correct block is **self-contained and
import-free**, because that is the block the predicate cannot distinguish from an illustration by
construction. *"Sum these fifteen numbers"*, *"how many days between these two dates"*, *"reverse the
words in this sentence"* — all closed, all import-free, all must run. If the predicate fires on those
at any material rate, **I-b** is the outcome and the design changes.

**Picking an easy cell to pass is the failure mode this task is most exposed to**, and it would be
invisible in the result: a green number from a cell that could not have been red.

### 3.2 The suppression starts at the narration, and the reason is the shape of the mistake

`spec.md` §3.5 argues it in full; the short form belongs here because it is the decision an
implementer will be tempted to reverse.

Suppressing **execution** is the intuitive fix and it is the one whose false positive is
unrecoverable: the user asked for a computation, the product decided it looked illustrative, and the
answer **never exists**. Suppressing **narration and capture** has a false positive that costs the
model's prose gloss on an output the user can already see in the execution panel.

The cost side is not symmetric either. The narration is a full model round trip — c4's *first* round
trip alone ran a median of **20.45 s** on this hardware — and the capture is the only part of the
defect that **outlives the session** and feeds itself back through `format_recall_block()`. The
subprocess is milliseconds and its temp directory is removed in a `finally` (`main.py:537-538`).

**Stage 2 removes the recurring cost and the compounding cost, and leaves the bounded one.** Stage 3
is available afterwards, on a measurement, and not before.

### 3.3 The predicate is a leaf, and `main.py` gets a branch

`SPEC-INPUT-001` §5.3's rule, which this project has held to through three SPECs: **`main.py` is
wiring, and every decision lives in a gated leaf.** The predicate is decision-shaped — it has
boundary conditions, a defined behaviour on unparseable input, and a false-positive rate people will
argue about — so it goes in a module with a **100 %** floor.

Registering it takes three edits, and this repository has already got the third one wrong once:
`pytest.ini`'s `--cov` list, `conftest.py`'s `PER_FILE_COVERAGE_TARGETS`, and the `Dockerfile` `COPY`
line. The first two fail loudly when mismatched. The third failed **silently** for `params.py` and
`settings.py` until `fc19a07`, and `SPEC-CI-001` §5.1 records `keychain.py` being added to that line
and not to the workflow's file list **within one day of a comment warning against exactly that**.
`tests/test_source_seam.py` now asserts set equality over those lists; T4 must satisfy it rather than
work around it.

### 3.4 The harness is borrowed, so it is left in the state it was found in

`probe/` and its 310 records are `SPEC-PROMPT-001`'s evidence and its gate rests on them. T1 adds one
cell and changes nothing else: no existing `Task` field, no record file, no classifier, no variant
string. `probe/tasks.py`'s own banner gives the reason — byte-identical task text across arms, *"or
the columns of that table are not comparable"*.

**A shared instrument is only shared while both parties can still trust its history.**

---

## 4. Risks and mitigations

| # | Risk | Assessment | Mitigation |
|---|---|---|---|
| **R1** | **The predicate's false-positive rate is unacceptable, and Stage 2 does not ship.** `product.md` §5.4 blocks are closed and import-free by construction, exactly as c4's are | **Live, and unmeasured.** It is the most likely single reason this SPEC does not deliver a fix | **T1/T2 exist for this and nothing else**, and **I-b** is admitted as an outcome in advance (T3). A discriminator measured unusable is a result recorded in `verification-T2.md`, not a failure to be argued away. Do not soften the cell to get a better number — §3.1 |
| **R2** | **The shipped prompt moves c4 and the premise changes under the SPEC.** V1/V2/V3 ran on the Target cell only; **no control prompt has been measured under any variant but V0** | Real. `SPEC-PROMPT-001` S6 already owes the full control set at V3 before it merges | T2 re-measures c4 under the string current at run time and **labels which string it was** (`spec.md` E6, S3). If S6's run happens first, consume it rather than duplicating it. **Outcome I-c** exists for this |
| **R3** | **The fix is read as fixing the routing.** A green control set, or a lower firing rate, gets reported as "explanations no longer execute" | Near-certain in a summary written by anyone who has not read §4.3 | `spec.md` **N5** and **U4** forbid the claim in the documentation as well as in the SPEC; `acceptance.md` **AC-BOUNDARY** asserts it. The rate does not move by one trial and the documents say so in plain words |
| **R4** | **The status line becomes noise.** One line per firing turn, on a product that already emits memory lines, param lines and execution lines | Moderate. `SPEC-MEMORY-001` faced the same trade and answered it with *at most one line per turn* | `spec.md` E3: exactly one line, per turn, naming the reason in the user's terms. **Not** a line per skipped step — a turn that skips narration *and* capture emits **one** |
| **R5** | **`SYSTEM_PROMPT` gets edited anyway**, by an implementer who finds it easier to add a sentence than a module | Plausible under time pressure, and it would confound `SPEC-PROMPT-001`'s in-flight measurement without anyone noticing for weeks | `spec.md` **N1**, and `acceptance.md` **AC-PROMPT-UNTOUCHED** asserts the prompt's sha256 (`ec8ef366856f…`, 2910 characters) in a source-seam test. An assertion, not an intention |
| **R6** | **Suppressing capture is discovered as a bug by a user.** "Why is this turn not in `/memory`?" | Certain over a long enough window, and it is the only user-visible loss Stage 2 causes | `spec.md` **O1**: `/memory` (or the status line itself) should say a turn was not captured and why. Recorded as optional because the status line already carries the reason at the moment it happens |
| **R7** | **The predicate drifts from the harness's copy of it.** If O4 records a per-trial verdict, the harness must call **the product's** predicate, not its own | The exact defect `SPEC-PROMPT-001` R7 exists for, and `probe/classify.py` is the pattern to copy — it imports from `main` and `tests/test_probe.py` asserts by AST that it holds no copy of the regex | The predicate lives in a leaf module, so the harness imports **that module**. Any harness-local re-implementation makes the measurement fiction |
| **R8** | **Two SPECs' probe records end up in one directory** and, six months on, nobody can say which SPEC's gate a file supports | Mechanical, and cheap to prevent exactly once | §2.1: T2's records go to `.moai/specs/SPEC-ILLUSTRATE-001/probe-runs/`, never to `SPEC-PROMPT-001`'s, and `verification-T2.md` cites them by full path |
| **R9** | **The measurement is run and never recorded**, because the numbers looked obvious | This SPEC's central figure exists **only** because somebody recorded a control-set baseline that everyone expected to be uninteresting | `spec.md` U5/N6 and `acceptance.md` AC-MEASURE. And the standing lesson from `SPEC-PROMPT-001` v1.1.2: *measure the configuration you would actually ship, not only the two ends of your hypothesis* |

---

## 5. Follow-up notes

- **`SPEC-PROMPT-001`'s control set needs an amendment and this SPEC must not write it.** c4 cannot
  fail AC-CONTROL at any post-change count (`spec.md` §4.2). Two remedies are set out there; the
  choice belongs to that SPEC's author, in that SPEC's HISTORY, with whatever re-run it implies. Flag
  it the day T2 reports.
- **`product.md` §5.4 has no probe cell and never did — and after T1 it will.** That is worth more
  than this SPEC: it is the first cell in the project measuring the product's *core* use case rather
  than a defect. Whoever owns the harness should consider whether the compute cell belongs in the
  standing control set permanently, at which point every future prompt edit inherits it.
- **The stale citations found while writing this document, recorded so they need no re-derivation.**
  Each was verified against the file at `ab08333`:

  | Cites | Correct | Where |
  |---|---|---|
  | `main.py:218-220` for `extract_last_python_block()` | `main.py:447-449` | `tech.md:553` (§7.2) |
  | `main.py:138-143` for the DIRECT protocol | `main.py:169-174` | `product.md:214` (§5.5) |
  | `main.py:480-482` for the no-code branch | `main.py:1072-1074` | `product.md:216-217` (§5.5) |
  | `main.py:322-379` for `agentic_turn()` | `main.py:990` | `structure.md:99` (§3.1), and the diagram's ten node labels below it |
  | `main.py:200-242` for `run_python()` | `main.py:473-538` | `structure.md:141` (§4) |
  | `main.py:100-151` for `SYSTEM_PROMPT` | `main.py:122-182` | `product.md:237` (§6.1) — already flagged by `SPEC-PROMPT-001` §7 item 6 |

  T7 owns the first three. The rest sit in `structure.md`, which is several SPECs behind and is
  explicitly not this SPEC's to rewrite (`spec.md` §9 item 8) — recorded here so the next reader does
  not trust them and so that fixing them costs no investigation.
- **If T3 returns I-b, write it down as a result and stop.** A SPEC that measures its own preferred
  design out of contention has done the measurement correctly, and this project has a precedent for
  saying so plainly rather than quietly not mentioning it.
