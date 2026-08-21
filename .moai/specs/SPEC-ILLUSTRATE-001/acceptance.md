# SPEC-ILLUSTRATE-001 — Acceptance Criteria (v1.0.0)

> Requirements are in `spec.md`. Implementation detail is in `plan.md`. The measurement record is
> `verification-T2.md`.

**Status at authoring:** **none of these criteria has been observed.** Nothing has been implemented,
nothing has been run, and `verification-T2.md` is empty by design. AC-PREDICATE through AC-FLOOR are
**specified, not verified**. T2, T3 and T6 discharge the measured ones; T4–T8 discharge the rest.

A single theme runs through AC-MEASURE, AC-SUPPRESS and AC-BOUNDARY: **a criterion that can only be
satisfied is not a criterion.** Each of those three is written so that a plausible-looking outcome
can fail it — because the defect this SPEC addresses was found by a control set, and the reason a
control set found it is that one of its cells was allowed to come back at zero and be believed.

---

## AC-PREDICATE — the discriminator is structural, gated, and fails closed

**Covers:** U1, E1, E4, S1, N3, N4, N9

**Given** a fenced block extracted by `extract_last_python_block()` (`main.py:447-449`)

**When** the illustration predicate is evaluated on it

**Then**

- the verdict is derived from an **`ast` parse** of the block and from nothing else — no substring
  search, no regex over source text, no model call, no network (E4);
- the predicate is **true** iff the block parses, contains **no** `Import`/`ImportFrom` node, and
  every loaded `Name` is either bound within the block or a Python builtin;
- the module holding it imports **nothing outside the standard library** and **no first-party
  module**, asserted in `tests/test_source_seam.py` alongside the existing stdlib-only assertions;
- the module is registered in **both** `pytest.ini`'s `--cov` list **and** `conftest.py`'s
  `PER_FILE_COVERAGE_TARGETS`, at a **100 %** floor, and appears in the `Dockerfile` `COPY` line and
  in every file list `tests/test_source_seam.py` asserts set equality over.

**And** the predicate returns **false** — never true, never an exception reaching the turn — when the
block does not parse, when it exceeds any internal bound the implementation sets, or when it contains
a node the implementation does not recognise (S1, N4).

**And** no branch of the predicate consults a list of module names, function names or constructs
considered dangerous (N9).

**And** `main.py` contains **no** part of the decision: it calls the predicate, holds the result in
one value, and branches on it (N3).

### Why "fails closed" is the load-bearing clause

**Measured 2026-08-12 over the committed V0 records: 3 of the 103 CODE-classified blocks do not
parse** — one each in c5, target and tool-reachable. Today such a block is written to disk, executed,
fails inside the child, and enters the retry loop (`main.py:1155-1167`). That is the existing
handling and it is correct.

A predicate that fired on an unparseable block would change behaviour **precisely when its own
analysis had failed**, and the observable would be a turn that quietly declined to narrate a
computation that had crashed. The failure would be invisible, would occur about 3 % of the time on
this corpus, and would be attributed to the model.

### How each clause is observed

| Clause | How |
|---|---|
| `ast`-only, no regex, no client | **AST assertion in `tests/test_source_seam.py`**, in the style of the existing `probe/classify.py` check — not a grep, which would also match a comment |
| stdlib-only, no first-party import | the existing stdlib-only source-seam assertion, extended by one module name |
| 100 % floor, registered in both places | `pytest.ini` and `conftest.py` read together; the session **fails** if only one carries it |
| in the image | `tests/test_source_seam.py`'s set-equality assertion over the `Dockerfile` `COPY` line and the CI file lists |
| fails closed | a unit test per branch, including a deliberately unparseable block |
| no decision in `main.py` | review, plus the absence of any new conditional expression in `main.py` beyond the single branch |

---

## AC-MEASURE — the false-positive rate is measured before anything is suppressed

**Covers:** U6, S2, E5, E6, N6, N7

| # | Criterion | How it is observed |
|---|---|---|
| 1 | A **compute-only cell** in the shape of `product.md` §5.4 exists in `probe/tasks.py`, expects **CODE**, and is measured at **V0**, **N = 30** | Read the harness fixtures and `verification-T2.md` §2. The cell is named in the diff |
| 2 | The cell is **adversarial**: its correct block is self-contained and import-free, so the predicate *could* fire on it. A cell whose correct block imports something measures nothing | Read the task text and the recorded blocks. **This is the criterion most likely to be satisfied on paper and violated in substance** (`plan.md` §3.1) |
| 3 | The added cell is **purely additive** — every pre-existing `Task`'s `id`, `text`, `kind`, `n` and `expect_direct` is byte-identical, and no record file under `SPEC-PROMPT-001`'s `probe-runs/` is modified, rewritten or re-scored | `git diff` on `probe/tasks.py` shows exactly one added entry; `git status` shows no modification under that directory (N7) |
| 4 | **c4 is re-measured** at N = 30 under the prompt string current at run time, and `verification-T2.md` **states which string that was** — V0's, or `SPEC-PROMPT-001`'s shipped text | Read `verification-T2.md` §2 and §3. A rate without its prompt string is not comparable to the 0/30 in `spec.md` §2.2 (E6) |
| 5 | The predicate's behaviour is reported with **both** halves of its separation: the rate at which it fires on the illustration cell **and** the rate at which it fires on the compute cell | `verification-T2.md` §4. A one-sided figure fails this criterion outright (U6) |
| 6 | The **acceptable false-positive rate was written into `verification-T2.md` §1 and committed on its own, before the run started** | `git log` on `verification-T2.md` shows a commit containing the rule and **no results**. *`SPEC-PROMPT-001` v1.1.1 records in full what it cost to be unable to demonstrate this ordering; the fix costs one commit and is unavailable in retrospect* |
| 7 | **No placeholder figures anywhere.** Every unrun cell reads `—` | Read `verification-T2.md` (N6) |
| 8 | The outcome is recorded as **I-a**, **I-b** or **I-c** (`plan.md` T3), including when it is I-b | `verification-T2.md` §5 |

**Why item 6 is here rather than in the plan.** A threshold chosen after the numbers arrive is not a
gate. This SPEC has a stated preference — it would like the predicate to work — and a preference is
exactly the thing that does the choosing when the rule is written afterwards. The one demonstration
available is a commit containing the rule and nothing else.

**Why item 8 admits I-b explicitly.** The predicate is a candidate with **one** measured half
(30/30 on illustrations; 0/43 on cells that cannot be done without the network). The half that
decides whether it is shippable has never been measured. **A criterion set that cannot record "the
discriminator does not work" is a criterion set that will not notice.**

---

## AC-SUPPRESS — the expensive half is skipped, the answer is not

**Covers:** U2, E2, E3, S4, N8, N10

**Given** a turn in which the predicate fires on the extracted block

**When** the turn completes

**Then**

- the execution panel is rendered exactly as it is today (`main.py:1108`) — **the user's screen loses
  nothing** (S4);
- **no second LLM round trip is issued** (`main.py:1113-1127` is not reached);
- **`_capture_turn()` is not called** (`main.py:1143-1152` is not reached), and the solution-memory
  store gains **no** record for that turn;
- **exactly one** status line is emitted saying the narration was skipped and why — one line for the
  turn, not one per skipped step (E3, U2);
- the block **is executed** (N8).

**And** on a turn where the predicate does **not** fire, every byte of behaviour is what it is today:
same panel, same feedback splice, same `Answer` stream, same capture.

**And** no turn asks the user whether to execute (N10).

### The assertion is on the calls, not on the effects

**Assert that the narration round trip and `_capture_turn()` are not *called*.** An effect-based
assertion — "the store has no new record", "no `Answer` panel appeared" — passes under
implementations that call them and discard the result, and it passes for the wrong reason when the
store is unavailable or the client is a stub.

`SPEC-KEYCHAIN-001` measured this distinction rather than argued it: AC-POLICY was verified by
mutation, and under the mutation **the output was still redacted**, so an effect-based assertion
would have passed. The assertion on the call was the only thing that caught it. The same shape
applies here, and for the same reason.

### Why execution is not suppressed at this stage

| | Predicate wrongly fires, **narration** suppressed | Predicate wrongly fires, **execution** suppressed |
|---|---|---|
| The code | runs | does not run |
| stdout | on screen in the execution panel | never exists |
| The user's answer | present, unglossed | **absent** |
| Recovery | read the panel | re-ask the question |

With the false-positive rate unmeasured (AC-MEASURE), only the left-hand column is defensible. **The
cost side is not symmetric either:** the narration is a full model round trip — c4's *first* round
trip alone ran a median of **20.45 s** (N=30, 2026-08-10) — while the subprocess is milliseconds and
its temp directory is removed in a `finally` (`main.py:537-538`). The capture is the only part of the
defect that survives the session and feeds itself back through `format_recall_block()`
(`memory.py:383-391`).

**Suppressing execution is Stage 3 and it is out of scope for this version** (`spec.md` §9 item 5).

---

## AC-PROMPT-UNTOUCHED — `SYSTEM_PROMPT` is unchanged, and a test says so

**Covers:** U3, N1, N2

**Given** any commit produced under this SPEC

**When** `main.py` is read

**Then**

- `SYSTEM_PROMPT` (`main.py:122-182`) is **byte-identical** to its state at `ab08333`: **2910
  characters**, sha256 **`ec8ef366856f…`** — the same value it has at `510f468`, which is the tree
  the 0/30 measurement was taken against;
- `prompt.count("```") == 2` still holds (`tests/test_source_seam.py:547`);
- the `@param` passage (`main.py:158-166`) is semantically unchanged, satisfying `SPEC-KEYCHAIN-001`
  N2 without this SPEC having to re-cite it;
- no design in this SPEC requires the model to emit a second fenced block or any reply shape making
  `CODE_BLOCK_RE.findall()` return more than one match (N2, `spec.md` §3.2).

**And** the assertion is **executable**, not a review note: a source-seam test asserting the hash, so
that an edit made under time pressure fails CI rather than being noticed at review.

### Why a hash and not a substring

A substring assertion passes when text is **added**, and added text is exactly the intervention this
SPEC forbids — one sentence about illustrations is the cheapest-looking fix in the document and the
one §3.1 rejects on measured evidence. It is also the change that would confound
`SPEC-PROMPT-001`'s in-flight measurement **without anyone noticing for weeks**, because a prompt
edit has no error message, no log line and no test of its own.

**The hash is stated as a literal here deliberately, and it is the only literal in this document that
also lives in a test.** It is a *pin on an unchanged thing*, not a threshold: it never moves under
this SPEC, so the two copies cannot drift while the SPEC is in force. If a later SPEC legitimately
edits the prompt — `SPEC-PROMPT-001` will — that SPEC updates the test and this criterion is
superseded rather than silently violated.

---

## AC-BOUNDARY — nobody can read this fix as a routing improvement

**Covers:** U4, N5, `spec.md` §4.3

| # | Criterion | How it is observed |
|---|---|---|
| 1 | No document produced under this SPEC claims the routing defect is fixed, mitigated or improved | Read `product.md`, `README.md`, `tech.md`, `structure.md` and any commit message. The model routes **exactly** as it did |
| 2 | `verification-T2.md` states that a control-set DIRECT rate is evidence about **neither** this defect **nor** its fix | Read `verification-T2.md` §0 |
| 3 | The `product.md` §6 limitation, while it stands, distinguishes what changed (what the product **does** with a block) from what did not (what the model **produces**) | Read the section |
| 4 | `SPEC-PROMPT-001`'s AC-CONTROL is **not** cited anywhere as evidence for or against this SPEC | Read the documents |
| 5 | The finding that **c4 cannot fail AC-CONTROL at any post-change count** is recorded where `SPEC-PROMPT-001`'s author will see it, and **no remedy is applied to that SPEC by this one** | `spec.md` §4.2; the amendment is that SPEC's to make |

### The two misreadings this criterion exists to prevent

- **"AC-CONTROL is green, so explanations no longer execute."** AC-CONTROL measures the **model's
  reply**. After Stage 2, c4 can be 0/30 CODE for ever and no illustration will be narrated or
  captured. The rate does not move by one trial.
- **"This SPEC improved the DIRECT rate."** It cannot. `classify()` is a function of the reply text
  alone, and this SPEC changes no text the model sees.

**The reason to write both down is that they are the natural summary sentences**, and a summary is
what survives into the next SPEC's §0.

---

## AC-DOCS — the corrections landed, including the one that predates this SPEC

**Covers:** `spec.md` §8 item 8, E7

| # | Criterion | How it is observed |
|---|---|---|
| 1 | **`product.md` §5.5 (`product.md:212-217`) no longer states that "explain X" questions take the DIRECT protocol without qualification.** It records the measured rate — **0 DIRECT in 30 trials, 2026-08-10, `llama3.1:8b`** — with its provenance and the branch its records live on | Read the section. **This correction is owed whether or not any fix ships** (`plan.md` T7) |
| 2 | **`README.md:109`** — *"the model skips the code protocol and answers directly"* — is corrected in the same change | Read the line. A README is read by people who will never open a SPEC |
| 3 | `product.md` §6 carries one limitation, in the §6.1 style, for as long as the defect is live; when Stage 2 lands it is amended in the §6.2 style for a resolved finding — **amended, not deleted** | Read the section |
| 4 | `tech.md:553`'s *"No static screening of generated code"* row is repointed (`main.py:218-220` → `:447-449`) and, after T5, states what the predicate screens and what it does not. **The row is not deleted** — the predicate is a cost control, not a security boundary (`spec.md` N9) | Read the row |
| 5 | `structure.md` §3.1's turn-flow diagram shows the branch, and its citations are repointed (`agentic_turn()` `main.py:322-379` → `:990`; the extract at `:334` → `:1071`) | Read the diagram |
| 6 | The stale citations found but **not** fixed are listed with their corrections, so the next reader does not trust them and needs no re-derivation | `plan.md` §5 |

**Why item 1 is not conditional on the fix.** `product.md` §5.5 asserts the opposite of a measured
behaviour. It was written from the code path rather than from an observation, which is a reasonable
way to be wrong and not a reason to stay wrong. **A document that states the opposite of what happens
is worse than one that says nothing, because it is trusted** — and this repository has already paid
for that once, in `SPEC-CI-001`, where `tech.md:635` asserted that `.github/` did not exist while it
did.

---

## AC-FLOOR — the CI floor is a measurement

**Covers:** `spec.md` §8 item 7

**Given** tests added by T4 and T5

**When** `MIN_PASSED` (`.github/workflows/ci.yml:332`) is raised

**Then** the new value is **read from a real `junitxml` run**, not computed from an expected delta,
and the literal appears in **exactly one place** — cited by symbol everywhere else (`SPEC-CI-001`
N5).

**And** this criterion states no number, deliberately. `SPEC-CI-001` AC-1 previously restated the
floor inside the very sentence claiming it lived in one place, and the copy went stale within a day.

---

## Success criteria and quality gates

### Gates

| Gate | Enforced by | Threshold |
|---|---|---|
| Predicate coverage | `conftest.py`'s `PER_FILE_COVERAGE_TARGETS` + `pytest.ini` `--cov` | **100 %** on the new leaf, both edits or neither |
| Predicate fails closed | AC-PREDICATE | unparseable / unrecognised ⇒ **does not fire**, asserted per branch |
| False-positive rate | AC-MEASURE, `verification-T2.md` §1 | **pre-registered before the run**, and committed before the run |
| Prompt integrity | AC-PROMPT-UNTOUCHED | `SYSTEM_PROMPT` sha256 `ec8ef366856f…`, 2910 chars; `prompt.count("```") == 2` |
| Harness integrity | AC-MEASURE item 3 | existing `Task`s byte-identical; no record file touched |
| Suppression | AC-SUPPRESS | narration and capture **not called**; execution still happens; exactly one status line |
| Test count | `SPEC-CI-001` AC-1 | 0 skipped; pass count ≥ `MIN_PASSED`, cited by symbol (N5) |

### Verification status

| Criterion | Status | Discharged by |
|---|---|---|
| AC-PREDICATE | **not verified** — the module does not exist | T4 |
| AC-MEASURE | **not verified** — the cell does not exist and nothing has been run. `verification-T2.md` is empty | T1, T2, T3 |
| AC-SUPPRESS | **not verified** — no suppression is implemented | T5, T6 |
| AC-PROMPT-UNTOUCHED | **trivially true today and untested.** `SYSTEM_PROMPT` is unedited because nothing has been done; the assertion that would keep it that way does not exist | T4 |
| AC-BOUNDARY | **not verified** | T7 |
| AC-DOCS | **not verified.** `product.md` §5.5 and `README.md:109` are false as of 2026-08-12 | T7 |
| AC-FLOOR | **not verified** | T8 |

**The one status worth reading twice is AC-PROMPT-UNTOUCHED's.** It is satisfied today for the same
reason everything else is unsatisfied — nothing has happened. Ticking it on that basis would convert
"no work done" into "requirement met", which is the conversion `SPEC-PROMPT-001` v1.1.1 corrected in
AC-GATE item 5.

### Definition of done

1. The compute-only cell exists in `probe/tasks.py`, is **additive only**, and its adversarial
   character is defensible from the task text alone (AC-MEASURE items 1–3).
2. The acceptable false-positive rate was **committed before the run**, in a commit containing the
   rule and no results (AC-MEASURE item 6).
3. `verification-T2.md` carries **both halves** of the predicate's separation, c4's rate **with the
   prompt string it was measured against**, and an outcome recorded as I-a, I-b or I-c — **including
   when it is I-b** (AC-MEASURE items 4, 5, 8).
4. Every criterion above has been **observed**, not inferred from a green suite. `SPEC-KEYCHAIN-001`
   carries this item because three of its ten were never run; it is repeated here for the same
   reason.
5. AC-SUPPRESS's non-calls are asserted **by mutation at least once**: reinstate the narration call,
   or the capture call, behind the firing predicate and confirm exactly one test fails naming it.
   *A gate never observed failing is not known to be a gate.*
6. `product.md` §5.5 and `README.md:109` no longer assert the opposite of the measurement — **and
   this is done whether or not steps 1–5 happened.**
7. `SYSTEM_PROMPT`'s hash assertion is in the suite and has been observed failing once, against a
   deliberately added space.
8. What was **not** run is named as not run, in `verification-T2.md`, in the wording this project
   uses: *as not run, and not as not needed.*
