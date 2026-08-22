# SPEC-MODEL-001 — Acceptance Criteria (v1.0.0)

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. The measurement record is
> `verification-T2.md`, and it **does not exist yet**.

**Status at authoring: none of these criteria has been observed.** Nothing has been pulled, nothing
has been run, nothing has been edited. The Docker daemon on this host is down and there is no host
`ollama` binary, so **no Phi-3.5 figure of any kind exists in this directory** — not a tag, not a
parameter count, not a rate. AC-TAG through AC-PROMPT-UNTOUCHED are **specified, not verified**.

One theme runs through all six: **a criterion that can only be satisfied is not a criterion.** Each
is written so that a plausible-looking outcome can fail it. That matters more here than usual,
because this SPEC has a stated preference — it would like Phi-3.5 to work — and §2.5 of `spec.md`
argues, before any run, that **the likeliest outcome is that it works worse**. A criterion set that
cannot record "the smaller model holds the contract badly" is a criterion set that will not notice.

---

## AC-TAG — every Phi-3.5 figure came out of a command, and the command is named

**Covers:** U2, U3, S1, E1, O2

**Given** a candidate Phi-3.5 model and the compose `ollama` sidecar running

**When** T1 establishes the model empirically

**Then**

- `ollama pull` and `ollama list` have been executed against the sidecar
  (`docker exec coderunner-ollama ollama list`), and **the tag is recorded exactly as column 1 of
  `ollama list` prints it** — the full byte string, not an abbreviation of it (E1);
- the **parameter count**, **quantisation level**, **context window** and **on-disk size** are each
  recorded with the command that produced them and the date;
- `verification-T2.md` §1 states, for each figure, whether it came from `ollama list`, from
  `ollama show`, or from the probe's own provenance readback (`probe/run_probe.py:114-144`).

**And** no document, comment, config file or commit message in this SPEC names a Phi-3.5 tag,
parameter count, quantisation, context window or size that T1 did not produce (S1, U2).

**And** the tag recorded here is the byte string that appears at **all four** declaration sites —
`main.py:71`, `docker-compose.yml:46`, `docker-compose.yml:78`, `coderunner:512` — with no
per-site variation (U1).

### Why the exact byte string is the load-bearing clause

`have_model()` (`coderunner:480-483`) pipes `ollama list` through `awk 'NR>1 {print $1}'` into
`grep -qx`, which is a **whole-line** match. The comment directly above it
(`coderunner:476-479`) records what this cost the project once already: *"A bare
`nomic-embed-text` would never match and would re-pull 274 MB on every single launch."*

**A tag that differs from the server's by one byte produces a launcher that re-downloads the model
every time, and the only symptom is a slow start.** Nothing raises, nothing logs, and `--doctor`
does not currently have a chat-model row to reveal it (`coderunner:540-562`). **This is the failure
mode that a code review cannot catch, because the string looks right.**

### How each clause is observed

| Clause | How |
|---|---|
| Tag as printed | The raw `ollama list` output is pasted into `verification-T2.md` §1, not paraphrased |
| Parameters, quantisation, context, size | `ollama show` output, pasted; size cross-checked against the probe's provenance readback where they overlap |
| Same string at four sites | `git grep -n` for the tag returns exactly the expected sites and no others |
| No unproduced figure anywhere | Read the three documents and the diff. **The absence of a figure is the pass condition, and it is easy to fail by being helpful** |

---

## AC-MEASURE — the thresholds were written before the numbers, and the numbers are all reported

**Covers:** U2, U3, U6, E2, E3, E4, S3, S4, N5, N6, N7

**This is the criterion the SPEC exists to satisfy.**

| # | Criterion | How it is observed |
|---|---|---|
| **1** | **The acceptance thresholds were written into `verification-T2.md` §1 and committed on their own, in a commit containing no results, before the run started** | `git log --follow verification-T2.md` shows a first commit carrying the rule and **nothing else**. *This is unavailable in retrospect; it costs one commit in advance* |
| 2 | `SPEC-PROMPT-001`'s **five control cells** were measured at **V0**, **N=30 each**, under Phi-3.5 | `verification-T2.md` §2; the JSONL files under `.moai/specs/SPEC-MODEL-001/probe-runs/` |
| 3 | **c4 is run once and reported twice.** It is one of the five control cells *and* `SPEC-ILLUSTRATE-001`'s measurement cell; there is exactly one c4 rate and its row says so | A sixth c4 column, or two different rates for `"explain what a Python closure is, with a short example"`, **fails this criterion** (`spec.md` D2) |
| 4 | Every trial carries `model_tag`, `model_digest` and `quantisation` **read back from the running server**, not from configuration | Read any record. `probe/run_probe.py:114-144` writes them; `:210-216` attaches them (U3) |
| 5 | Each cell's Phi-3.5 rate is reported **beside** its `llama3.1:8b` rate, at the same N, with both dates and both model tags | `verification-T2.md` §3. A table with one rate per cell **fails** (E4, U4) |
| 6 | The `SYSTEM_PROMPT` sha256 at run time is recorded, and it is the V0 string | `verification-T2.md` §1. Measured 2026-08-19 as `8a896634a9f6…`; if it differs, the run spans two prompts and is not comparable (E3, S4) |
| 7 | **No existing `Task` changed.** `probe/tasks.py`'s entries are byte-identical to `feature/SPEC-PROMPT-001`'s, and no file under that SPEC's `probe-runs/` was modified, rewritten or re-scored | `git diff` against `01aa887` on `probe/tasks.py` is empty; `git status` shows nothing under that directory (N5) |
| 8 | **No placeholder figures anywhere.** Every unrun cell reads `—` | Read `verification-T2.md` (N6) |
| 9 | The outcome is recorded as **P-a**, **P-b** or **P-c** (`spec.md` §3.3), **including when it is P-c** | `verification-T2.md` §5 |
| 10 | Any claim that Phi-3.5 is better or worse is stated **per cell, with N**, and never generalised into a claim about the model | Read §3 and §5's prose. *"Phi-3.5 routes better"* fails; *"c5 moved from 14/30 to n/30, one-sided Fisher p = …"* passes (U6) |
| 11 | Any statement about c4 is quantified, not asserted. **c4 is at 0/30 under `llama3.1:8b` and a cell at zero cannot get worse**, so any movement is upward and needs its interval | `verification-T2.md` §4 (N7) |
| 12 | If any cell was measured against a model, quantisation or host other than the one in that run's provenance block, it is **labelled** and **discharges nothing** | Read the labels (S3, adopted from `SPEC-PROMPT-001` S4) |

### Why item 1 is a criterion and not a note

**A threshold chosen after the numbers arrive is not a gate; it is a description of the numbers.**
This SPEC would like the swap to succeed, and a preference is exactly the thing that does the
choosing when the rule is written afterwards. **The one demonstration available is a commit
containing the rule and nothing else**, and `SPEC-PROMPT-001` v1.1.1 records in full what it cost to
be unable to produce that commit.

### Why item 9 admits P-c explicitly

`SYSTEM_PROMPT` (`main.py:122-182`) is 2575 characters carrying five contracts, and the *larger*
model already fails one of them at 30 in 30. **A smaller model holding it worse is the prior, not
the surprise.** `SPEC-PROMPT-001`'s own V2 arm moved its target cell significantly and still missed
its pre-registered threshold and returned M-b; the precedent for recording an unwelcome result
plainly already exists in this project. **A criterion set that cannot record "the new model is
worse" will produce a swap that ships anyway.**

---

## The pre-registered measurement gate for T2

**This section is the content of `verification-T2.md` §1, stated here so that it exists in a
reviewable document before the run is scheduled. It is copied into that file and committed there,
alone, before the first trial.**

**Population.** `SPEC-PROMPT-001`'s five control cells — `c1_conversational`
(*"hey, how are you doing today?"*), `c2_conversational` (*"what can you help me with?"*),
`c3_opinion` (*"what do you think of Python as a first programming language?"*),
`c4_general_knowledge` (*"explain what a Python closure is, with a short example"*),
`c5_general_knowledge` (*"who wrote the book 'The Mythical Man-Month'?"*) — at **V0**, **N = 30
each**, task text byte-identical to `feature/SPEC-PROMPT-001` at `01aa887`.

**Comparator.** The `llama3.1:8b` V0 rates for the same five cells, from the committed records under
`.moai/specs/SPEC-PROMPT-001/probe-runs/`. **These are inherited, not re-derived by this SPEC**, and
`verification-T2.md` §3 must re-read them from the JSONL rather than copying them from prose —
including from this document.

**Statistic.** DIRECT count out of 30 per cell, with a 95 % Wilson interval, and a one-sided Fisher
exact test against the `llama3.1:8b` count at the same N. `alpha = 0.05`.

**The gate, pre-registered:**

| # | Rule | Consequence |
|---|---|---|
| **G1** | **No control cell regresses significantly.** For each of c1, c2, c3, c5, a one-sided Fisher exact test of the Phi-3.5 DIRECT count against the `llama3.1:8b` count must **not** reject at `alpha = 0.05` in the direction of fewer DIRECT | Any cell that rejects → **P-c** |
| **G2** | **c4 is reported and not gated.** Its `llama3.1:8b` rate is 0/30 and cannot get worse, so it contributes no pass/fail signal. Its Phi-3.5 rate is recorded with its Wilson interval and read as information about `SPEC-ILLUSTRATE-001`, not as a criterion here | A c4 rate used to justify the swap fails **AC-MEASURE item 11** |
| **G3** | **The routing floor.** The Phi-3.5 pooled DIRECT rate across c1, c2, c3, c5 (out of 120) must be **at least** the `llama3.1:8b` pooled rate minus **10 percentage points**, computed from the records | Below that → **P-c**, regardless of per-cell significance |
| **G4** | **`P-b` requires evidence, not absence of harm.** To be recorded as an improvement, at least one cell must reject in the *favourable* direction at `alpha = 0.05`. "No cell got worse" is **P-a**, not P-b | Mislabelling P-a as P-b fails **AC-MEASURE item 10** |
| **G5** | **A run that does not complete N=30 on a cell does not report that cell.** Partial cells are recorded as partial, with their count, and discharge nothing | `run_probe.py`'s `--resume-from` exists for this; a truncated cell reported as a rate fails **AC-MEASURE item 8** |

**What the gate does not cover, stated so it is not read as covered.** The `@param` grammar
(`main.py:158-166`) has **no cell in any arm** and is therefore **ungated by G1–G5** — a Phi-3.5
model that stops emitting the declaration syntax entirely would pass this gate cleanly.
`SPEC-INPUT-001` R1 already named this as *"the highest-probability failure … and the only one no
unit test can detect."* **This SPEC adds no cell for it** (`spec.md` §7 item 5) and records the
exposure instead of pretending the gate closes it. Correctness of any reply is likewise ungated and
unassessed, here and everywhere else in this project.

---

## AC-MEMORY — the eligibility decision is taken deliberately, and its loss is not silent

**Covers:** E5, E6, N3, N4, O5

**Given** a solution-memory store containing records written under `llama3.1:8b`, and a product now
defaulting to Phi-3.5

**When** a turn retrieves from that store

**Then** exactly one of the following holds, it was chosen deliberately, and it is recorded by
letter with its reason (E5):

- **M-a** — llama-authored records remain eligible and are injected unchanged. A test asserts that a
  record whose `chat_model` differs from the running model **is** returned by `search()`;
- **M-b** — `_eligibility_filter()` (`vectorstore.py:601`) gains a `chat_model` clause. A test
  asserts such a record is **not** returned, **and** the change records, in the same commit, that
  **every existing store returns nothing on switch day**, **and** the turn emits exactly one status
  line in the shape of `product.md` §4 item 20's one-line degradation convention (N4, E6);
- **M-c** — reuse is kept and the injected block names the authoring model, rendered from
  `record.chat_model` (already read back at `vectorstore.py:730`, already declared
  `VARCHAR(256)` at `vectorstore.py:289`, so no schema change). A test asserts the rendered block
  contains the authoring model's tag and that a record written under the current model is not
  mislabelled (O5).

**And** in all three cases the `embed_model` and `dim` clauses of `_eligibility_filter()` are
unchanged, the embedding model is not re-pulled, and nothing is re-embedded (N3).

**And** if the test count changes, `MIN_PASSED` (`.github/workflows/ci.yml:332`, currently **573**)
is raised to a count **read from a real `junitxml` run**, never computed from an expected delta.

### Edge case: the empty store, which passes every option and tests nothing

**A test written against a fresh store cannot distinguish M-a from M-b**, because both return
nothing. The test that discriminates requires a store containing at least one record whose
`chat_model` is a **different** string from the running model's — which is precisely the fixture
`conftest.py:52` already provides, since `CHAT_MODEL = "llama3.1:8b"` is a fixture constant and not
the product default (`spec.md` N10). **The fixture that this SPEC deliberately does not change is
the fixture that makes T3's test possible.**

### Why M-b's clause is the longest one here

`_eligibility_filter()` builds a conjunction. Adding `chat_model == <new tag>` to it means **no
record in any existing store matches**, because none carries the new tag. The store is not degraded;
it is empty of eligible records. **`/memory` will keep reporting records that exist and never
match**, recall will never fire, and **nothing will raise** — from the store's point of view the
query simply had no hits. That is a capability disappearing with no error, no warning and no
migration path, and **M-b is the option most likely to be chosen for looking principled.**

---

## AC-DOCS — both figures stand, and no citation to the changed string is left stale

**Covers:** U1, U4, N2, E7, S7, `spec.md` §5.4

**Given** outcome **P-a** or **P-b**, and a Phi-3.5 rate produced by T2

**When** the documentation pass runs

**Then**

- **every document that states a measured rate carries the Phi-3.5 figure BESIDE the `llama3.1:8b`
  figure**, each labelled with its model tag, its N and its date. **A document in which a Phi-3.5
  number has replaced an `llama3.1:8b` number fails this criterion outright** (U4, N2);
- the four declaration sites — `main.py:71`, `docker-compose.yml:46`, `docker-compose.yml:78`,
  `coderunner:512` — and the two README statements of the default (`README.md:42`, `README.md:70`
  on this branch) carry the same byte string (U1);
- `.moai/project/product.md` §5.5, `.moai/project/tech.md`, and `SPEC-ILLUSTRATE-001` §2.2 are
  amended; `product.md` §6.15 is amended **where it exists** (E7);
- the seven stale citations to the changed string, catalogued at `spec.md` §5.4, are repointed in
  the same pass: `tech.md:17` and `:219`'s `main.py:66` → `:71`, `coderunner:206` → `:512`,
  `docker-compose.yml:71`/`:39` → `:78`/`:46`; `tech.md:224` and `:390-391`'s
  `coderunner:174-177` → `:480-483` and `coderunner:209-213` → `:517-521`; `tech.md:19`'s
  `docker-compose.yml:80` → `:87`; and `memory.py:268`'s `main.py:52` → `:71`.

**And** every line number used in the edit was **re-read from the target file at edit time**, not
taken from `spec.md`, `plan.md`, this file, or `SPEC-ILLUSTRATE-001` (S7).

### Edge case: the merge-order hazard, which changes what "the target" means

**This branch is cut from `main`, which does not carry `SPEC-ILLUSTRATE-001`'s six documentation
commits** (`394cca7`, `afba32e`, `ceb5898`, `209d3fb`, `b78ce02`, `7f3e1b3` — 9 commits unmerged in
total, verified 2026-08-19).

| | On this branch | On `feature/SPEC-ILLUSTRATE-001` |
|---|---|---|
| `README.md` | 228 lines; default at `:42`, banner at `:69-70`; **no measured-rate narrative** | 330 lines; default at `:48`, banner at `:82-83`; measured 0/30 narrative at `:124` with a transcript to `:162` |
| `product.md` §5.5 | `:212-217` — asserts DIRECT fires, which is **measured false** | `:212` — rewritten, carries CODE 30/30 / DIRECT 0/30 and the model tag |
| `product.md` §6.15 | **does not exist**; limitations end at §6.14 (`:423`) | `:473` — *"Illustrative code is executed, narrated and stored as a solution"* |

**So on one side T4 must correct a false claim and add a figure; on the other it adds a second
figure beside an accurate one. These are different jobs and the criterion is satisfied differently
by each.** The check is that the *result* carries both models' figures with both dates, whichever
side it was reached from. **A table of line numbers — including the one directly above — is a
description of a hazard and not a work order.**

---

## AC-LAUNCHER — the tag matches by observation, and `--doctor` can say so

**Covers:** U1, E1, E9, S6, N8, O3, O4

**Given** a machine with the Phi-3.5 model already pulled into `coderunner_ollama_data`

**When** `./coderunner` is launched a second time

**Then**

- **nothing is pulled.** `have_model()` (`coderunner:480-483`) returns true, `pull_model()`
  (`coderunner:488-494`) is not called, and no *"Pulling chat model …"* line appears;
- this is verified **by launching twice and observing**, not by reading the diff (S6). **The failure
  mode is a launcher that works and is merely slow, which is invisible to inspection** — and the
  comment at `coderunner:476-479` exists because this project already learned that once, on the
  embedding model;
- `docker-compose.yml:46`'s `model-pull` service and `coderunner:512`'s default carry the T1 tag
  byte-for-byte (U1, E1).

**And** `./coderunner --doctor` reports the **chat** model's tag and its presence, in the shape of
the embedding-model row at `coderunner:556-558`. Today's `--doctor` (`coderunner:540-562`) prints a
comma-joined `ollama models` dump at `:551` and an explicit `embed model … (present|MISSING)` row —
**and no chat-model row at all** (E9).

**And** the branding question is **answered, not skipped**: `main.py:750`'s hard-coded
*"— agentic Python interpreter powered by LLaMA"* and the four `[LLaMA]` status labels at
`main.py:1054`, `:1073`, `:1119` and `:1314` have each been examined and either changed or
deliberately kept, with the reason recorded (N8). **A merge that leaves the first panel of the
product claiming "powered by LLaMA" above a Phi-3.5 subtitle, without anyone having decided that,
fails this criterion.**

### Edge case: `CODERUNNER_MEMORY=0`

`--doctor`'s embedding row is inside a conditional (`coderunner:555-561`) and prints
`disabled (CODERUNNER_MEMORY=0)` when memory is off. **The chat-model row must not inherit that
conditional.** The chat model is required whether or not solution memory is enabled, and a
diagnostic that hides the primary model's status because a secondary feature was disabled is a
diagnostic that fails hardest exactly when it is most needed.

---

## AC-PROMPT-UNTOUCHED — one variable moved

**Covers:** N1, U5

**Given** the whole of this SPEC's implementation

**When** the diff is reviewed

**Then** `SYSTEM_PROMPT` (`main.py:122-182`) is **byte-identical** to its state at `ab08333` —
61 source lines, **2575 characters** after `textwrap.dedent().strip()`, sha256
`8a896634a9f6414dadd43f35e423e2be0681bd7d74f4d0de5682b703f044382d`, containing exactly **2**
backtick fences (measured 2026-08-19).

**And** no cell in `probe/tasks.py` was renamed, re-worded, re-sized or removed, and no record file
under `SPEC-PROMPT-001`'s `probe-runs/` was modified (N5).

**And** the embedding model, its tag, its dimension and the `embed_model`/`dim` clauses of
`_eligibility_filter()` are unchanged (N3).

### One disclosure attached to this criterion

`SPEC-ILLUSTRATE-001` §2.1 and its **N1** pin this same string at **2910 characters**, sha256
`ec8ef366856f…`, at this same commit. **Measured today at `ab08333`, no convention reproduces
that**: `dedent().strip()` gives 2575 / `8a896634a9f6…`, `dedent()` alone gives 2577 /
`d4a736094a7b…`, and the raw undedented literal gives 2773 / `c2f9d0922c5c…`.

**This criterion asserts the figure this SPEC measured and flags the disagreement rather than
silently picking a side.** It matters beyond bookkeeping: `SPEC-ILLUSTRATE-001` **N1** is enforced
by that hash, and **a pin nobody can reproduce does not pin anything.** Resolving it belongs to that
SPEC's author.
