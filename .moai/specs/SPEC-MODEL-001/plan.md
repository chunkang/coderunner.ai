# SPEC-MODEL-001 — Implementation Plan (v1.0.0)

> Requirements are in `spec.md`. Acceptance criteria are in `acceptance.md`. The measurement record
> is `verification-T2.md`, and it **does not exist yet**.

## 0. Starting position

**The edit is available today and the evidence for it is not.** That asymmetry is the whole shape of
this plan.

| Present | Evidence |
|---|---|
| A single environment variable that already switches the model without any edit | `main.py:71` reads `CODERUNNER_MODEL`; compose passes it through (`docker-compose.yml:78`); the launcher honours it (`coderunner:512`) |
| A behavioural instrument that reads the model back from the running server rather than from config | `probe/run_probe.py:53`, `:114-144`, `:210-216` — on `feature/SPEC-PROMPT-001`, tip `01aa887`, published |
| A baseline for all five control cells at V0, N=30, against `llama3.1:8b` | 11 JSONL cells under `.moai/specs/SPEC-PROMPT-001/probe-runs/` on that branch |
| A named, measured defect to watch for regression on | `SPEC-ILLUSTRATE-001` §2.2 — c4 at CODE 30/30, DIRECT 0/30, Wilson [0.000, 0.114] |
| A memory schema that already stores the authoring model | `vectorstore.py:129`, `:289`, `:408`, `:730` |

| Absent | Consequence |
|---|---|
| **Any verified fact about Phi-3.5.** The Docker daemon is down (`docker info` fails) and there is no host `ollama` binary | **The tag itself is unknown.** Nothing downstream may cite a figure, and T5's `grep -qx` match cannot be reasoned about until the tag is read from `ollama list`. **T1 exists for this alone** |
| **`probe/` on this branch.** `git ls-files probe/` returns nothing; only 6 stale `.pyc` files sit in `probe/__pycache__/` | T2 cannot run until the harness is ported (T2a) |
| Any measurement of the `@param` grammar (`main.py:158-166`) under **any** model | The riskiest surface of the swap has no instrument, and `SPEC-INPUT-001` R1 already said no unit test can detect its failure |
| Any token count, anywhere | `elapsed_sec` (`probe/run_probe.py:196`, `:208`) covers **one** round trip of at least two. "A smaller model will be faster" cannot be demonstrated end-to-end today |
| A chat-model row in `--doctor` | `coderunner:540-562` reports the **embedding** model's presence and not the chat model's |

**So this is not a "change the default" plan. It is a "measure what the default change costs, then
change it" plan.** T2 is where the value is; T1 is what makes T2 quotable; T3, T4 and T5 are the
consequences that a one-line edit leaves behind and that nobody notices until a user does.

---

## 1. Task decomposition

Five tasks and one prerequisite. **None has been started.** T1 and T2 require a running Ollama; T3,
T4 and T5 do not.

| # | Task | Artefact | Depends on |
|---|---|---|---|
| **T1** | **Establish the Phi-3.5 tag empirically.** `ollama pull <candidate>` then `ollama list`, inside the compose sidecar (`docker exec coderunner-ollama ollama list`), and `ollama show` for the details. Record, from output and not from a web page: the tag **exactly as column 1 prints it**, the parameter count, the quantisation level, the context window, and the on-disk size. **Nothing downstream may cite a figure T1 did not produce** (`spec.md` U2, S1). The tag string is the deliverable that T5 depends on, because `have_model()` matches whole lines with `grep -qx` (`coderunner:480-483`) and a tag that differs by one byte re-pulls the model on every launch, forever, silently. | `verification-T2.md` §1 (provenance) | — |
| **T2a** | **Port `probe/` to this branch, unmodified.** Six files from `feature/SPEC-PROMPT-001` (`01aa887`): `run_probe.py` (339), `aggregate.py` (211), `variants.py` (184), `tasks.py` (139), `classify.py` (67), `__init__.py` (22), plus `tests/test_probe.py`. **Additive only** — no existing `Task`'s `id`, `text`, `kind`, `n` or `expect_direct` changes by one byte (`spec.md` N5, D6). `probe/classify.py` must still import `CODE_BLOCK_RE` and `extract_last_python_block` from `main`, and `tests/test_probe.py`'s AST assertion that it holds no copy of the fence regex must still pass (`spec.md` E8). Delete the 6 orphaned `.pyc` files in `probe/__pycache__/` in the same change, or the first import will be answered by a stale bytecode cache. | `probe/`, `tests/test_probe.py` | — |
| **T2** | **Run the measurement. This is the deliverable.** `SPEC-PROMPT-001`'s **five control cells** at **V0**, **N=30 each**, under Phi-3.5. c4 (*"explain what a Python closure is, with a short example"*) **is one of the five** and is also `SPEC-ILLUSTRATE-001`'s measurement cell; it is run **once** and reported under both headings (`spec.md` D2). **Pre-register the acceptance thresholds in `verification-T2.md` §1 and commit that file, containing no results, before the run starts** (`spec.md` E2; `acceptance.md` AC-MEASURE item 1). Record every cell's Phi-3.5 rate **beside** the `llama3.1:8b` rate at the same N and date (`spec.md` E4, U4). Every record carries the server's own model readback, so the provenance cannot be misreported (`spec.md` U3). **The run may be executed with `CODERUNNER_MODEL` exported and the repository still on its old default** — §2.2 explains why that ordering is preferred. The config edit to `main.py:71`, `docker-compose.yml:46`, `:78` and `coderunner:512` lands **as part of this task**, after its numbers exist (`spec.md` D1). | `verification-T2.md`, `probe-runs/`, `main.py`, `docker-compose.yml`, `coderunner` | T1, T2a |
| **T3** | **Decide the memory-eligibility question, and test whichever answer is chosen.** `_eligibility_filter()` (`vectorstore.py:601`) gates on `embed_model` and `dim` and **not** on `chat_model`, so llama-authored records stay eligible for injection into a Phi-3.5 turn under `PRIOR SUCCESSFUL SOLUTION — reference only` (`memory.py:362`, `:383-391`). Three options, **all admitted in advance** (`spec.md` §3.4): **M-a** leave cross-model reuse as-is; **M-b** add `chat_model` to the filter, **accepting that every existing user's store goes dark on switch day — a silent capability loss with no error and no migration**; **M-c** keep reuse but name the authoring model inside the injected block, rendered from `record.chat_model` (already read back at `vectorstore.py:730`). Each needs a **different** test, and the test is the deliverable, not the opinion. M-b additionally needs the one-line degradation notice `spec.md` E6 requires. | `vectorstore.py` or `memory.py`, `tests/` | T2 (for the numbers), but decidable independently |
| **T4** | **Amend the documents the swap falsifies.** `README.md`, `.moai/project/product.md` §5.5 and §6.15, `.moai/project/tech.md`, and `SPEC-ILLUSTRATE-001` §2.2. **Each states a measured rate, and the Phi-3.5 figure goes BESIDE the `llama3.1:8b` figure, not instead of it — a superseded measurement is still a measurement** (`spec.md` U4, N2). Repoint the seven stale citations to the string this SPEC changes (`spec.md` §5.4): `tech.md:17`/`:219`'s three, `tech.md:224`/`:390-391`'s two, `tech.md:19`'s one, and `memory.py:268`'s docstring. **Edit targets differ by merge order** (§2.1 below, `spec.md` §5.1, S7) — re-read every target file at the moment of editing and take no line number from any document, including this one. | `README.md`, `product.md`, `tech.md`, `SPEC-ILLUSTRATE-001/spec.md`, `memory.py` | T2 = P-a or P-b |
| **T5** | **Launcher and compose.** Three things. (a) **The pull path**: `coderunner:512`'s default and `docker-compose.yml:46`'s `model-pull` service carry the T1 tag byte-for-byte. (b) **`have_model()` tag matching** (`coderunner:480-483`): verify by observation — launch twice and confirm the second launch pulls **nothing** — and not by inspection (`spec.md` S6). The comment at `coderunner:476-479` exists because this project was already bitten once by exactly this, on the embedding model. (c) **`--doctor` reporting**: add a chat-model presence row in the shape of the embedding row at `coderunner:556-558`; today `--doctor` (`coderunner:540-562`) reports the secondary model's presence and not the primary one's. And decide the branding question `spec.md` D5 raises: `main.py:750`'s *"powered by LLaMA"* wordmark and four `[LLaMA]` status labels (`:1054`, `:1073`, `:1119`, `:1314`) are false after the swap (`spec.md` N8). | `coderunner`, `docker-compose.yml`, `main.py` | T1 |

### 1.1 Dependencies and critical path

| Task | Blocks | Blocked by | Needs a model? | Needs `probe/`? |
|---|---|---|---|---|
| T1 | T2, T5 | — | **yes** | no |
| T2a | T2 | — | no | it *is* `probe/` |
| **T2** | T3, T4 | T1, T2a | **yes** | **yes** |
| T3 | — | T2 (soft) | no | no |
| T4 | — | T2 = P-a/P-b | no | no |
| T5 | — | T1 | **yes** (to verify (b)) | no |

```
T1 ──┬── T2 ──┬── T3
     │        └── T4        (only under P-a / P-b)
T2a ─┘
T1 ────── T5
```

**Critical path: T1 → T2 → T4.**

**T2 is a gate, not a milestone.** Under outcome **P-c** — Phi-3.5 measurably worse on routing, on
the illustration defect, or on the `@param` grammar — the path stops there. The default stays
`llama3.1:8b`, T4 has nothing to amend because nothing changed, and the SPEC's delivered value is
`verification-T2.md` plus whatever T3 and T5 are worth on their own. **That is a smaller thing than
was hoped for and a real one.**

**T2a and T5 are the only tasks that deliver something under every outcome.** T2a puts the project's
only behavioural instrument on a second branch, where it stops being one SPEC's private property.
T5's `--doctor` row and `have_model()` verification are correct regardless of which model wins.

### 1.2 Priority

| Priority | Tasks | Rationale |
|---|---|---|
| **High** | T1, T2a, T2 | The one measurement that does not exist is the one every other decision needs. Without it the swap is an unfalsifiable change to behaviour nobody can observe |
| **High** | T5 (b) and (c) | `have_model()` mismatch is a silent multi-gigabyte re-download on every launch, and `--doctor`'s missing row is what would let a user diagnose it. Both are correct work under every outcome |
| **Medium** | T3 | Real user-visible consequence, and M-b's blast radius makes getting it wrong expensive. Not on the critical path |
| **Medium** | T4 | Only reachable under P-a/P-b, and the merge-order hazard means doing it early costs more than doing it late |
| **Low** | T5's branding half, `spec.md` O1–O5 | Necessary for the work to hold; nothing depends on them |

**Final goal is T4** under P-a/P-b, and `verification-T2.md` §5 under P-c. **Optional goals:**
`spec.md` O1 (per-cell `elapsed_sec`, nearly free at T2 and expensive to retrofit), O2 (modelfile
parameters in the provenance), O3 (`--doctor` size row), O4 (one constant for four status labels),
O5 (M-c's rendering).

---

## 2. Execution decision — what is delivered now, and what is not

**Nothing is implemented by this SPEC's authoring.** The three documents in this directory are the
deliverable. No source file is edited, no model is pulled, no probe is run, and no Phi-3.5 figure
exists anywhere in them.

**Until T1 and T2 have run, this SPEC is specified, not decided.** Say so in any status report, and
do not describe Phi-3.5 as "the new default" — it is a candidate with **zero** measured cells.

### 2.1 Merge order decides T4's edit targets, and the difference is not cosmetic

**This branch is cut from `main`. `main` does not carry `SPEC-ILLUSTRATE-001`'s documentation
corrections.** Verified today: `git log --oneline main..feature/SPEC-ILLUSTRATE-001` returns **9
unmerged commits**, six of them documentation — `394cca7`, `afba32e`, `ceb5898`, `209d3fb`,
`b78ce02`, `7f3e1b3`.

`spec.md` §5.1 tabulates the difference. The short form: **on this branch `README.md` is 228 lines,
`product.md` §5.5 asserts that "Explain X" questions take the DIRECT protocol, and `product.md`
§6.15 does not exist. On `feature/SPEC-ILLUSTRATE-001` `README.md` is 330 lines, §5.5 has been
rewritten to record CODE 30/30 / DIRECT 0/30 against `llama3.1:8b`, and §6.15 exists at `:473`.**

**T4 is therefore a different job on each side.** On this branch it would have to correct a false
claim *and* add a Phi-3.5 figure in one edit; on the other it adds a second figure beside an
accurate one. **The recommendation is to let `feature/SPEC-ILLUSTRATE-001` merge first** — its six
commits are blocked on nothing and correct claims that are already false. If this branch merges
first, it owes that branch a conflict in five files, and the conflict will be in prose rather than
in code, which is the expensive kind.

**Either way, T4 re-reads its targets at the moment it edits them** (`spec.md` S7). Taking a line
number from this plan would be committing, one document down, exactly the defect §5.4 catalogues.

### 2.2 The run comes before the edit, and that is a deliberate ordering

`main.py:71` reads `CODERUNNER_MODEL` from the environment, compose passes it through
(`docker-compose.yml:78`), and `probe/run_probe.py:53` imports `MODEL_NAME` from `main`. The probe's
argument parser (`run_probe.py:290-303`) has `--variant`, `--task`, `--n`, `--host` and
`--resume-from` and **no `--model` flag**, so the environment variable is the only lever — and it is
sufficient.

**So the whole of T2 can be run against Phi-3.5 with the repository still declaring
`llama3.1:8b`.** Two reasons that ordering is preferred:

- **A run that returns P-c can be abandoned rather than reverted.** No commit to undo, no
  documentation half-edited, no branch to explain.
- **`collect_provenance()` (`run_probe.py:114-144`) reads the model back from the running server**
  and writes `model_tag`, `model_digest` and `quantisation` onto every trial (`:210-216`). The
  record says what actually answered, not what a config file intended. `SPEC-PROMPT-001`
  `spec.md:721-726` states the principle: *"compose declares an intention; only the running server
  can report the fact."*

### 2.3 Where T2's records live

**`.moai/specs/SPEC-MODEL-001/probe-runs/`**, and never `SPEC-PROMPT-001`'s directory. Two SPECs'
evidence in one directory is one SPEC's evidence by the time anybody reads it — which is
`SPEC-ILLUSTRATE-001` R8's lesson, adopted here before it costs anything.

---

## 3. Technical approach — the four decisions worth defending

### 3.1 One variable changes, and everything else is held fixed

The temptation, once a run is scheduled, is to bundle: take the new model **and** `SPEC-PROMPT-001`'s
V3 prompt **and** `SPEC-ILLUSTRATE-001`'s new compute cell, and get one big measurement. **That
measurement would be about none of them.**

So: the prompt is `SYSTEM_PROMPT` exactly as it stands at `main.py:122-182` (61 lines, 2575
characters, sha256 `8a896634a9f6…`, measured 2026-08-19), pinned by `spec.md` N1. No cell is added,
renamed, re-worded or re-sized (`spec.md` N5). The variant is V0. The embedding model is untouched
(`spec.md` N3), which also means no re-embedding and no dimension change.

**The only variable is the model, and that is what makes the five cells comparable to the eleven
record files already committed on `feature/SPEC-PROMPT-001`.**

### 3.2 The prompt is the risk, and the SPEC says so before the numbers arrive

`spec.md` §2.5 sets it out in full; the short form belongs here because it governs how T2's result
should be read.

`SYSTEM_PROMPT` is not an instruction — it is **five contracts in one string**: a routing decision
(`main.py:126-129`), CODE's ten sub-rules (`:131-167`), the `@param` grammar with its four types and
its no-second-fence prohibition (`:158-166`), DIRECT's four rules (`:169-174`), and two
post-execution behaviours (`:176-180`). **Phi-3.5-mini is substantially smaller than `llama3.1:8b`,
and the larger model already fails one of those contracts at 30 in 30.**

**T2 may therefore measure the illustration defect as worse under Phi-3.5, and the `@param` grammar
as unusable.** Both are outcome **P-c**, both are results, and neither is a failure of this SPEC.
The reason to write that down now is that a SPEC which has not admitted its likeliest outcome in
advance will read that outcome as a setback and start negotiating with its own thresholds.

**One asymmetry worth holding onto.** c4 is at 0/30 under `llama3.1:8b`, and a cell at zero cannot
get worse — `SPEC-ILLUSTRATE-001` §4.2's arithmetic, one-sided Fisher at N=30. So the regression
signal, if there is one, will appear in **c1, c2, c3 and c5**, whose `llama3.1:8b` V0 rates were
30/30, 20/30, 26/30 and 14/30 respectively (re-derived by that SPEC from the committed records;
**inherited here, not re-derived by this SPEC**).

### 3.3 The eligibility question is a product decision wearing a one-line diff

`vectorstore.py:601` is one f-string. Adding `and chat_model == …` to it is the smallest possible
change in this plan and has the largest user-visible consequence in it.

**M-b's cost is that the filter is a conjunction and no existing record carries the new tag**, so
every existing store returns nothing on switch day. Not degraded — empty. `/memory` will report
records that exist and never match, recall will never fire, and **nothing will raise**, because from
the store's point of view the query simply had no hits. `product.md` §4 item 20's one-line
degradation convention was written for exactly this class of event and M-b as stated emits no line.

**M-a's cost is unmeasurable from inside the product**, which has no telemetry and will not be given
any: whether an 8B model's Python is a good few-shot for a smaller one cannot be observed.

**M-c's cost is length** — one more line in an injected block, in a turn already carrying a
2575-character system prompt, on a smaller model. §3.2's argument applies to it too.

**This plan recommends none of them.** It requires that whichever is chosen ships with a test that
fails if the behaviour reverts, and that the option letter and the reason go into the record
(`spec.md` E5). A change to `vectorstore.py` lands in a module floored at 85 % (`conftest.py:208`);
a change to `memory.py` lands in one floored at 100 % (`conftest.py:206`). If the test count moves,
`MIN_PASSED` (`.github/workflows/ci.yml:332`, currently **573**) is raised from a **measured**
`junitxml` run and never from an expected delta (`SPEC-CI-001` N5).

### 3.4 The launcher's match is exact, so it is verified by observation

`have_model()` (`coderunner:480-483`) pipes `ollama list` through `awk 'NR>1 {print $1}'` into
`grep -qx`. **A whole-line match.** The embedding model's default carries `:latest`
(`coderunner:521`) for precisely this reason, and the comment above the function
(`coderunner:476-479`) records what it cost to learn: a bare tag never matches, `pull_model()` fires
on every launch, and 274 MB comes down each time.

`llama3.1:8b` matches today by the accident of carrying an explicit `:8b`. **Whether the Phi-3.5 tag
does is unknown until T1 reads column 1.** And the failure is invisible in code review — the string
looks right, the launcher works, it is merely slow. **So T5 verifies it the only way that can fail:
launch, then launch again, and confirm the second launch pulls nothing.**

The `--doctor` row is the other half of the same argument. `coderunner:540-562` reports `ollama
models` as a comma-joined dump and an explicit **embed model … (present|MISSING)** row at
`:556-558`. **There is no chat-model row.** A user whose primary model failed to pull can only find
out by reading the raw dump and knowing what to look for. One row, copied from the one below it.

---

## 4. Risks and mitigations

| # | Risk | Assessment | Mitigation |
|---|---|---|---|
| **R1** | **Phi-3.5 holds the five-part contract worse than `llama3.1:8b`**, and routing, the illustration defect or the `@param` grammar degrades | **The most likely single outcome.** A smaller model on a 2575-character multi-protocol prompt is the prior, not the surprise | **T2 exists for this**, and outcome **P-c** is admitted in advance (`spec.md` §3.3). Under P-c the default stays put and the measurement is the delivered value. **Do not renegotiate the thresholds after the numbers arrive** — they are committed first, alone, by `spec.md` E2 |
| **R2** | **The one-line edit merges and the six-cell measurement never happens.** The edit is obviously correct in isolation and takes seconds | Near-certain if T2 is scheduled as a follow-up rather than as the task the edit belongs to | `spec.md` **D1**: the config edit is a rider on T2 and lands inside it. **If someone needs Phi-3.5 before T2, they set `CODERUNNER_MODEL` and change nothing** — the variable already works at `main.py:71`, `docker-compose.yml:78` and `coderunner:512` |
| **R3** | **The Phi-3.5 tag does not match `ollama list`'s output** and the launcher re-pulls the model on every single launch | Live and unmeasurable until T1. This project has already been bitten by it once, on the embedding model (`coderunner:476-479`, `SPEC-MEMORY-001` §3.2) | T1 records the tag **as column 1 prints it**; `spec.md` E1 requires that byte string at all four declaration sites; **T5 verifies by launching twice**, not by reading the diff (`spec.md` S6) |
| **R4** | **`main.py:750` ships saying "powered by LLaMA" above a Phi-3.5 subtitle**, on every launch, in the first panel the user sees | Certain unless someone looks. It is a hard-coded string no environment variable reaches, and four `[LLaMA]` status labels sit behind it | `spec.md` **N8** makes examining them non-optional and **D5** records that the *answer* is a product-voice question this SPEC does not settle. O4 offers the cheap version: one constant instead of four literals |
| **R5** | **M-b is chosen because it reads as principled**, and every existing user's solution memory silently goes empty on switch day | Plausible, and the damage is invisible: no error, no warning, no migration, and recall simply never fires | `spec.md` **N4** forbids adopting M-b without recording the blast radius in the same change, and **E6** requires the one-line degradation notice. `acceptance.md` **AC-MEMORY** asserts both |
| **R6** | **A Phi-3.5 figure replaces an `llama3.1:8b` figure in a document**, and the evidence that the swap changed anything is destroyed by the edit that documents it | Near-certain in a documentation pass written by someone optimising for tidiness | `spec.md` **U4** and **N2**: both figures, both dates, both model tags, side by side. **A superseded measurement is still a measurement.** `acceptance.md` **AC-DOCS** asserts it per file |
| **R7** | **T4 edits the wrong lines** because `feature/SPEC-ILLUSTRATE-001` merged, or did not, and the targets moved | Mechanical and cheap to prevent exactly once. `README.md` is 228 lines here and 330 there; `product.md` §6.15 exists on one side and not the other | `spec.md` **S7** and §2.1: re-read every target at edit time, take no line number from any document. **Prefer merging `feature/SPEC-ILLUSTRATE-001` first** |
| **R8** | **A post-swap probe run is quietly used to discharge a `SPEC-PROMPT-001` criterion**, which that SPEC's **S4** (`spec.md:893`) forbids in terms | Real the moment the default changes, because after that the *default* invocation measures the wrong model | `spec.md` **N9** and §5.2. Flag it to that SPEC's author the day T2 is **scheduled**, not the day it reports — its outstanding runs (V3 tool-reachable at N=20, full control set at 5×N=30) are cheaper before this merges than after |
| **R9** | **`probe/` is forked rather than ported**, and a cell is "improved" during the copy | Plausible: the harness is being touched for the first time by someone who did not write it | `spec.md` **N5** and **D6**: additive only, byte-identical task text. `probe/classify.py` must still import the product's predicate from `main`, and `tests/test_probe.py`'s AST assertion is what catches a re-implementation (`spec.md` E8) |
| **R10** | **The stale `.pyc` files in `probe/__pycache__/` shadow the ported source** or, worse, are committed | Small, mechanical, and confusing out of all proportion to its size — 6 compiled modules from a branch whose source is not here | T2a deletes them in the same change that adds the source |
| **R11** | **The measurement is run and never recorded**, because a result that confirms expectations feels uninteresting | This project's most valuable finding to date — `SPEC-ILLUSTRATE-001`'s entire premise — came from a **control** cell that everyone expected to be uninteresting | `spec.md` U2/N6 and `acceptance.md` AC-MEASURE. Every cell gets a row, including the ones that moved by nothing |

---

## 5. Successor — `SPEC-EVOLVE-001`, recorded here and not written

**Recorded because it is what this SPEC's measurement floor is *for*, and not written because three
of its four objectives need probe capability that does not exist.**

The shape is an offline prompt optimiser: **the probe measures variant Vn, an optimiser proposes
Vn+1, repeat.** It **depends on SPEC-MODEL-001** — an optimiser needs a stable measurement floor,
and a floor taken against a model that is about to be replaced is not one. `SPEC-PROMPT-001` built
the instrument and measured four hand-written variants; `SPEC-EVOLVE-001` would close the loop.

**Four objectives were selected. One is measurable today and three are not.** The gap is recorded
honestly rather than deferred:

| Objective | Can the probe measure it today? | What is missing |
|---|---|---|
| **Protocol routing** — does the model pick CODE or DIRECT correctly? | **Yes.** This is exactly what `probe/classify.py` computes, using the product's own predicate, and what all 11 committed cells report | Nothing. This objective is fully instrumented |
| **First-attempt execution success** — does the emitted block run without raising? | **No.** **The probe deliberately executes nothing** — it issues one `stream_llm()` call per trial and stores the reply | An execution stage in the harness, with the sandboxing question that comes with running model-authored code inside a measurement loop. `SPEC-ILLUSTRATE-001` O3 asks for a cheap version of this (exit status and stdout for one cell) and it is still unbuilt |
| **Fewer round trips** — is the answer reached in fewer model calls? | **No.** `elapsed_sec` (`probe/run_probe.py:196`, `:208`) covers **one** round trip; a successful CODE turn costs at least two (`main.py:1113-1127`) and a failing one up to `MAX_RETRIES` (`main.py:73`, default 3) | **No latency or token field for anything past the first call exists anywhere in this project.** Checked: no `eval_count`, `prompt_eval` or `total_duration` is read from the Ollama response in `main.py` or in any probe module. The objective has no unit |
| **Answer correctness** — is the answer right? | **No.** Nobody in this project has assessed correctness on any trial of any model | A **graded task set with known answers**. None exists. `SPEC-PROMPT-001` v1.1.2 records 65 unassessed CODE trials and defers the question entirely |

**So three of four objectives are blocked on harness work that nobody has scoped, and an optimiser
built on the one that works would optimise routing alone.** That is not necessarily wrong — routing
is the surface both prior SPECs contest — but **an optimiser silently scored on one of its four
stated objectives is an optimiser whose results will be read as being about all four.** Whoever
writes `SPEC-EVOLVE-001` inherits that sentence.

---

## 6. Follow-up notes

- **`SPEC-PROMPT-001` needs to hear about S4 before T2 is scheduled**, not after it reports. Its
  outstanding runs are cheaper against the current default than against the next one, and the
  amendment it needs — re-scope S4 to each run's provenance readback, or finish the runs first — is
  its author's call.
- **`SPEC-ILLUSTRATE-001`'s prompt hash could not be reproduced.** That SPEC's §2.1 and N1 state
  2910 characters / sha256 `ec8ef366856f…` at `ab08333`; measured at that same commit today,
  `SYSTEM_PROMPT` is **2575 / `8a896634a9f6…`** after `dedent().strip()`, **2577 /
  `d4a736094a7b…`** after `dedent()` alone, and **2773 / `c2f9d0922c5c…`** raw. **No convention
  tried yields 2910.** It matters because that SPEC's N1 pins the prompt by that hash, and a pin
  nobody can reproduce pins nothing. Flagged for its author; not corrected here.
- **After T2a, `probe/` exists on two branches, and that is an improvement worth naming.** The
  project's only behavioural instrument currently lives on a single unmerged feature branch. Whoever
  owns the harness should consider whether it belongs on `main`, at which point every future model
  or prompt change inherits it instead of borrowing it.
- **The `@param` grammar has never been measured under any model** (`spec.md` §5.3 item 2), and this
  SPEC deliberately adds no cell for it (`spec.md` §7 item 5) because it holds the instrument fixed.
  **That is a real gap and this SPEC widens the consequences of it** by changing the model that has
  to satisfy it. Recorded so the next SPEC does not have to rediscover it.
- **If T2 returns P-c, write it down as a result and stop.** Leave the default at `llama3.1:8b`, keep
  T2a and T5, and record which cells moved and by how much. A SPEC that measures its own preferred
  change out of contention has done the measurement correctly.
