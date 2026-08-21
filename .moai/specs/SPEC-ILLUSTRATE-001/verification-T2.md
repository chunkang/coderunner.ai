# SPEC-ILLUSTRATE-001 — T2 measurement record

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. Acceptance criteria are in
> `acceptance.md`.

---

## STATUS: NOT YET RUN

**Created 2026-08-12 with its structure in place and every result cell empty.** No probe has been
executed for this SPEC. The compute-only cell (`plan.md` T1) does not exist yet. Nothing in §2, §3,
§4 or §5 has been measured, and every results cell below reads `—`.

**There are no placeholder figures in this document and there must never be** (`spec.md` N6). A
plausible-looking number written here as an illustration would, on a second reading by a second
person, be indistinguishable from data. This project has the discipline written down twice already —
`SPEC-KEYCHAIN-001`'s HISTORY names what was not run *"as not run and not as not needed"*, and
`SPEC-PROMPT-001`'s own record states in its header that no run produced it.

**Two preconditions must be discharged before anything below is filled** (`plan.md` §2):

- **P1 — the harness.** `probe/` does **not** exist at `ab08333`. It lives on
  `feature/SPEC-PROMPT-001` (tip `01aa887`, published as `origin/feature/SPEC-PROMPT-001`), arriving
  at `2c6b494`. T1, T2 and T6 therefore run on that branch or on one carrying it. **Records written
  by this SPEC go to `.moai/specs/SPEC-ILLUSTRATE-001/probe-runs/` and never to
  `SPEC-PROMPT-001`'s directory** (`plan.md` §2.1, R8).
- **P2 — the model.** `llama3.1:8b` on the compose `ollama` sidecar, reached at
  `http://ollama:11434` from inside the compose network. No host port is published for that service,
  so a host-side run is not the same measurement and must not be recorded as one (`spec.md` S6).

**Section §0 must be read before §4 is quoted anywhere.**

---

## 0. What this record is not evidence about

Written before any figure exists, because these two misreadings are the natural summary sentences and
a summary is what survives (`acceptance.md` AC-BOUNDARY).

- **Nothing here is evidence about routing.** `SPEC-PROMPT-001`'s control-set DIRECT rate measures
  the **model's reply**. This SPEC changes what the product **does** with a reply. A c4 rate of 0/30
  can persist for ever while every criterion in `acceptance.md` passes.
- **A green `SPEC-PROMPT-001` AC-CONTROL is evidence about neither this defect nor its fix**, and a
  result in this file is evidence about neither that SPEC's gate nor its control set.
- **The one thing this SPEC does change about that reading** is what a c4 CODE classification
  *implies*: after Stage 2 it no longer implies a narration round trip or a memory write.
  `spec.md` §4.3 states this in full and it must not be restated loosely here.

---

## 1. The pre-registered rule

**THIS SECTION MUST BE COMPLETED AND COMMITTED ON ITS OWN, BEFORE ANY TRIAL IS RUN**
(`acceptance.md` AC-MEASURE item 6). A commit containing this rule **and no results** is the only
available demonstration that the threshold was not chosen after the numbers arrived.

**`SPEC-PROMPT-001` v1.1.1 records in full what it cost to be unable to demonstrate that ordering:**
its `verification-T3.md` claimed twice, in bold, that its pre-registration had been committed before
the run. It had not. The rule and the results it gated sat in one uncommitted working tree,
indistinguishable in git from having been written in a single pass after the numbers landed. The
document's own words: *the cheap fix is to commit the pre-registration on its own, before running
anything; it is unavailable only in retrospect.*

| | Value |
|---|---|
| Date the rule was committed | — |
| Commit containing the rule **and no results** | — |
| Illustration cell (c4) — firing rate required for the predicate to be considered useful | — |
| **Compute cell — maximum acceptable false-positive rate** | — |
| Statistical form (exact test, N, alpha, one- or two-sided) | — |
| Decision rule, stated so a machine could apply it | — |
| What outcome **I-b** requires (`plan.md` T3) | — |
| What outcome **I-c** requires | — |

**Three properties the rule must have, each of which is why a clause is in it:**

1. **It names no observed value.** Every figure in this document is `—` at the time the rule is
   written, and the rule must remain readable as a rule after they are filled.
2. **It is decidable on the compute cell.** The illustration side is already known — 30/30 in the
   V0 records (`spec.md` §2.2) — so a rule that can be satisfied by the illustration side alone
   decides nothing. **The false-positive rate is the quantity the decision rests on.**
3. **It admits I-b in advance.** A predicate measured unusable is a result. A rule with no losing
   branch is not a gate; it is a conversation held after the fact.

---

## 2. Provenance — what was measured, and against what

*Not yet run. Fill from the run itself, not from configuration files.* `docker-compose.yml` writes
the model tag as `${CODERUNNER_MODEL:-llama3.1:8b}` — a **default**, not a pin — so the compose file
states an intention and only the running server states a fact.

| | Value |
|---|---|
| Date of run | — |
| Model tag | — *(expected `llama3.1:8b`; record what the server reports)* |
| Model digest | — *(the V0 records carry `46e0c10c039e…`)* |
| Quantisation | — *(the V0 records carry `Q4_K_M`)* |
| Reached via | — *(expected `http://ollama:11434`)* |
| Ollama server version | — *(the V0 records carry `0.32.1`)* |
| Sampling | — *(inherited from `stream_llm()`, which passes no `options=`; **must not** be pinned)* |
| Harness commit | — |
| `main.py` sha256 under test | — |
| **`SYSTEM_PROMPT` sha256 under test** | — *(`ec8ef366856f…` is V0's, byte-identical at `510f468` and `ab08333`)* |
| Trials per cell (N) | — *(30)* |
| Records written to | — *(`.moai/specs/SPEC-ILLUSTRATE-001/probe-runs/…`)* |

**The prompt hash row is not decoration.** `spec.md` E6 requires every c4 rate to be labelled with
the string that produced it, because `SPEC-PROMPT-001` may ship a different one and a comparison
across two prompt strings is not a comparison.

### 2.1 The new cell

| | Value |
|---|---|
| Task id | — |
| Task text, verbatim | — |
| `kind` / `expect_direct` / `n` | — |
| **Why this text is adversarial for the predicate** | — *(the correct block must be self-contained and import-free, so the predicate **could** fire on it — `plan.md` §3.1)* |
| Diff shows exactly one added `Task`, no existing field touched | — *(`acceptance.md` AC-MEASURE item 3)* |

---

## 3. Cell results

*Not yet run.*

### 3.1 The illustration cell — c4, re-measured

Task prompt: `explain what a Python closure is, with a short example`

| Metric | V0 (2026-08-10, from `SPEC-PROMPT-001`'s records) | This run |
|---|---|---|
| Trials (N) | 30 | — |
| Classified DIRECT | **0** | — |
| Classified CODE | **30** | — |
| DIRECT rate | **0.0000**, 95 % Wilson [0.000, 0.114] | — |
| `fence_matches == 1` | **30 / 30** | — |
| **Prompt string** | **V0** (sha256 `ec8ef366856f…`) | — |
| Predicate fires | **30 / 30** *(re-derived 2026-08-12 from stored replies, not from a run)* | — |
| First-round-trip latency | median **20.45 s** (mean 23.00, min 12.54, max 45.58) | — |

**The V0 column is quoted from `spec.md` §2.2 and §2.4 and must not be recomputed here.** One copy of
a figure is one copy.

### 3.2 The compute cell — the measurement this SPEC exists to take

| Metric | Value |
|---|---|
| Trials (N) | — |
| Classified CODE (expected: nearly all) | — |
| Classified DIRECT (a routing failure of a different kind; record, do not act) | — |
| **Predicate fires — the false-positive count** | — |
| **False-positive rate, with its 95 % Wilson interval** | — |
| Blocks that import something (i.e. that the predicate could never fire on) | — |
| Blocks that are closed **and** import-free (i.e. the cases that decide this SPEC) | — |
| Verdict against §1's pre-registered threshold | — |

**If the second-to-last row is small, this cell did not test the predicate**, whatever the
false-positive rate says. A compute cell whose blocks all import something is a cell the predicate
passes by construction (`acceptance.md` AC-MEASURE item 2). Record that as a defect **in this
measurement**, not as a result about the predicate.

### 3.3 Do the illustrations even run? (O3)

*Not yet run. One extra field on the c4 cell; unknown today for every trial ever taken.*

| Metric | Value |
|---|---|
| Blocks that parse | **30 / 30** at V0 *(known)* |
| Blocks that **execute** with returncode 0 | — |
| Blocks that raise | — |
| Blocks that time out at `EXEC_TIMEOUT_SEC` | — |
| Distinct stdout shapes | — |

**Why this row matters to the cost claim.** A block that raises does not cost one extra round trip;
it costs up to **three** thought streams through the retry loop (`main.py:1038`, `MAX_RETRIES`
`main.py:73`), while the user watches the model diagnose an illustration that was never meant to run.
`spec.md` §2.3's "at least one, at most three" is derived from the code and is **not** measured, and
this row is what would settle it.

**What this row is still not.** It is **not** an assessment of correctness. Whether the narrated
answer agrees with the prose answer the model already gave is unmeasured, on this cell and on every
CODE trial in this project (`spec.md` §5 item 2, §9 item 6).

### 3.4 Second-round-trip cost (O2)

*Not yet run. No figure for this exists anywhere in the project.*

| Metric | Value |
|---|---|
| Narration round-trip latency, median / min / max | — |
| Turn latency with narration vs. without | — |
| Token counts, if the client exposes them | — |

**The probe as it stands cannot supply these**: `run_probe.py` issues exactly one `stream_llm()` call
per trial and executes nothing. Filling this section requires driving the product's turn, not the
probe's, and that is a harness change with its own justification.

---

## 4. After the change (T6)

*Not yet run, and not startable until §3 is complete and §5 records **I-a**.*

| Metric | Before | After |
|---|---|---|
| c4 — predicate fires | — | — |
| c4 — narration round trips issued | — | — *(expected **0** on firing turns)* |
| c4 — store records written | — | — *(expected **0** on firing turns)* |
| c4 — status lines per firing turn | — | — *(expected exactly **1**)* |
| Compute cell — turns that lost their narration | — | — |
| Compute cell — turns that lost their **answer** | — | — *(must be **0**: execution is not suppressed, `spec.md` N8)* |
| c4 — DIRECT rate | — | — *(**expected unchanged**; a change here would mean something else moved)* |

**The last row is a control on the change itself.** This SPEC edits no text the model sees. If the
DIRECT rate moves, either the prompt moved underneath the measurement or the two runs are not
comparable — and either way the rest of the table is unsafe to read.

---

## 5. Outcome

*Not yet decided. Nothing above has been run.*

| | Value |
|---|---|
| Outcome (**I-a** / **I-b** / **I-c**) | — |
| Decided against §1's rule, as written and committed on | — |
| Consequence for `plan.md` T4–T6, T8 | — |
| Consequence for `spec.md` §3.5 Stage 3 | — |

**The three outcomes, admitted in advance** (`plan.md` T3):

| | Outcome | What it means | What happens next |
|---|---|---|---|
| **I-a** | The predicate separates well enough to gate on | The premise holds | T4–T6 proceed; Stage 3 stays gated on a further measurement |
| **I-b** | The false-positive rate exceeds §1's threshold | **The discriminator is not usable as specified** | T4–T6 and T8 are **not** started. The SPEC's delivered value is `spec.md` §4, §5 and `plan.md` T7. Record it plainly — *a SPEC that measures its own preferred design out of contention has done the measurement correctly* |
| **I-c** | c4's rate has moved materially under the shipped prompt | The premise has changed | Re-open `spec.md` §2 before anything else; do not decide I-a/I-b on a superseded baseline |

---

## 6. What this record will NOT prove, however it comes out

Written now, so that it is not written later by whoever wants the result to mean more.

1. **Nothing about any model other than the one in §2.** One tag, one digest, one quantisation, one
   host (`spec.md` S6).
2. **Nothing about how often users hit this.** The product has no telemetry and will not be given
   any (`spec.md` §5 item 6). A firing rate is a rate **per c4-shaped turn**, not per session.
3. **Nothing about correctness.** §3.3 asks only whether blocks run. Whether an executed
   illustration ever produced a **wrong** answer is unmeasured here and everywhere — 65 unassessed
   CODE trials across `SPEC-PROMPT-001`'s four arms, with the M-a/M-c split deferred to
   `SPEC-ACCOUNT-001` A1.
4. **Nothing about `SPEC-PROMPT-001`'s gate.** That gate is decided on the Target cell alone, at
   N=30 per arm, by a rule pre-registered in that SPEC's own record. No cell here may bear on it, and
   no cell there may rescue an outcome here.
5. **Nothing about c4's fitness as a control prompt.** `spec.md` §4.2 shows by arithmetic that c4
   cannot fail `SPEC-PROMPT-001`'s AC-CONTROL at any post-change count. That finding is complete
   already and does not need this run; the remedy is that SPEC's to choose.
6. **Nothing about Stage 3.** Suppressing execution is gated on a false-positive rate low enough to
   have been pre-registered as acceptable **for withholding an answer**, which is a stricter
   threshold than §1's and is not written yet.
