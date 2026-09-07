---
id: SPEC-SKILL-001
version: "1.1.1"
status: "draft"
created: "2026-09-05"
updated: "2026-09-05"
author: "Chun Kang"
priority: "MEDIUM"
---

## HISTORY

### v1.1.1 (2026-09-06) — U1 asked the instrument for something it cannot give

**Found while planning T1, before a line of it was written, which is the only cheap time to find
it.** v1.1.0's **U1** required the meter to *"attribute every counted token to exactly one source:
system prompt, conversation history, recall or skill block, feedback injection, or completion."*
**That is not obtainable.**

*(Verified 2026-09-06 against the installed client.)* `BaseGenerateResponse` carries a **single**
`prompt_eval_count` for the whole prompt and no per-message breakdown, and `ollama.Client` exposes
`chat`, `generate`, `embed`, `show`, `list`, `ps`, `pull`, `push`, `copy`, `delete` and the web
helpers — **no tokenize endpoint**. Decomposing that one number across five sources therefore needs
a tokeniser, and **N2** forbids exactly that, for the reason §3.1 gives: a tokeniser's vocabulary is
not the server's, so its numbers would be a different model's approximation of this model's cost.

**U1 and N2 contradicted each other, and U1 is the one that was wrong.** It was written as an
attribution rule without checking that the instrument could attribute.

**The fix splits the claim along the line that already exists in the SPEC — measured versus
observed.** Cost stays exactly measured, per round trip, from the server's own counts. Attribution
becomes a record of each component's **size in characters**, labelled a size and never called a
token count. No character count is presented as tokens anywhere, so N2 stands untouched.

**It is enough for the only job attribution had.** `plan.md` R2 needs to know *which component
dominates the prompt*, so that T3, T4 and T5 are ranked by the measurement rather than by whoever
implemented first. A share of characters ranks them. It does not need to be a token count to do
that, and calling it one would be the failure this SPEC exists to avoid.

### v1.1.0 (2026-09-05) — Reuse must be FASTER, not only cheaper

Scope amendment on the author's instruction: *"the skill reused should work faster."*

**v1.0.0 treated latency as a caveat and this entry promotes it to a goal.** The original text
carried the tokens/wall-clock distinction only as a warning — `plan.md` R1 said a token saving might
not move the clock, and `acceptance.md` item 7 required such a saving be labelled a context-budget
saving rather than speed. That framing was correct and incomplete: it protected the SPEC from
overclaiming and gave it no reason to optimise the thing the user actually wants.

**The instrument already reaches.** *(Verified 2026-09-05 against the installed client's response
type.)* Ollama reports **six** fields, not two: `prompt_eval_count` and `eval_count`, and alongside
them `total_duration`, `load_duration`, `prompt_eval_duration` and `eval_duration`. The same final
chunk carries both dimensions, so no second instrument is needed and §3.1's no-estimation rule
extends to latency unchanged.

**`load_duration` is why the decomposition matters rather than being tidy.** It is the model being
loaded into memory, and **nothing in this SPEC can reduce it**. On a cold container it dominates
every other term, so a before/after comparison that includes it measures whether the model happened
to be warm — which is not an optimisation, and would read as one. `prompt_eval_duration` is the term
a smaller prompt actually moves; `eval_duration` moves only by generating less; a skipped round trip
removes an entire `total_duration`. §3.6 states which task is expected to move which.

**This re-ranks Stage 1.** Under tokens alone, T3's distillation and T5's bounded history are the
obvious targets. Under latency, **T4 — dropping the redundant second round trip — is the largest
Stage 1 win**, because it removes a whole prompt evaluation rather than shortening one. The ranking
is still decided by T2's measurement (`plan.md` R2) and not by this paragraph.

**And it sharpens Stage 2 rather than changing its gate.** A replayed skill costs *zero* model
tokens and *zero* model latency; that is the whole prize, and it makes the pull toward amending C2
stronger. §3.5's gate and the security cost at §3.4 are unchanged, and are now the only thing
standing between an attractive number and an executable poisoned record.

### v1.0.0 (2026-09-05) — Initial specification

Written against a feature that already half-exists, which is the reason §2 comes before §3.

The request was *"implement a skill registry: save the previous successful prompt and its response
as a skill and reuse it, so we can minimize token usage."* **Storing a successful turn and reusing
it is shipped** — `SPEC-MEMORY-001` does exactly that, and has since it reached `completed`. What is
not shipped, and what this SPEC is actually about, is the last clause: **minimize**.

Three measurements shaped the design and two of them chose it outright.

- **M1 — solution memory increases prompt size; it does not reduce it.** `_RECALL_TEMPLATE`
  (`memory.py:361`) renders a preamble, the prior task, the approach that worked, the full script
  and its stdout. The truncation caps at `memory.py:49-52` bound those at 2,000 / 1,000 / 4,000 /
  1,000 characters respectively, so a single injected record adds **up to ~8 KB to the prompt**, per
  turn, on top of the system prompt and the whole conversation. The feature trades tokens for
  first-attempt success. On this SPEC's stated goal it currently points the wrong way, and that is
  not a defect in it — it is what it was specified to do.

- **M2 — the move that would actually save tokens is forbidden today, deliberately.**
  `SPEC-MEMORY-001` **C2** (`spec.md:269`): *"Reuse is few-shot prompt injection. The retrieved
  solution enters the prompt as context; the model still reasons and may adapt. **Stored code is
  never replayed and the LLM is never skipped.**"* It is restated as an Unwanted behaviour
  (`spec.md:406`) and again as out of scope (`spec.md:433`). Skipping the model is where the large
  saving is. **This SPEC does not route around that constraint and does not quietly reinterpret it.**
  §3.5 stages the work so that Stage 1 lives entirely inside C2, and Stage 2 proposes amending it —
  as an amendment, gated on a measurement, with the amendment's cost stated.

- **M3 — there is no token accounting anywhere in the product, so "minimize" currently has no
  baseline.** *(Measured 2026-09-05 by grepping `main.py`, `memory.py`, `recall.py` and
  `vectorstore.py` for `token`, `tiktoken`, `num_ctx` and `context_window`.)* Every hit is unrelated:
  string parsing in `memory.py:116-119` and stream chunks in `main.py:408-409`. **There is no meter.**
  A SPEC that claims a reduction it cannot measure is the failure this project has already had to
  correct twice — `product.md` §5.5 was false for as long as it was written, and
  `SPEC-PROMPT-001` v1.1.1 records what it cost to be unable to demonstrate a pre-registration
  ordering. T1 is therefore the meter, and it lands before any optimisation does.

**One finding turned the meter from an approximation into a measurement.** The `ollama` client's
response type carries **`prompt_eval_count`** and **`eval_count`** — the server's own token counts
for the prompt and the completion. `stream_llm()` (`main.py:209-221`) discards them: it reads
`chunk.get("message", {}).get("content", "")` and yields only non-empty content, so the final chunk
and every count on it are thrown away. Surfacing that chunk is a small change at a clean seam, and
it means **no figure in this SPEC has to be estimated from character counts**. §3.1 makes exactness
a requirement rather than a convenience.

---

## 1. Problem statement

CodeRunner pays tokens on every turn and counts none of them.

Four costs are known and none is measured:

| Cost | Mechanism | Evidence |
|---|---|---|
| **Unbounded conversation history** | `Conversation.messages` is append-only — `system()`, `user()` and `assistant()` (`main.py:195-201`) each append and nothing anywhere trims, windows or summarises. Every turn re-sends the entire history, and every failed attempt injects a full stderr+stdout dump first | `product.md` §6.6 |
| **Two round trips per successful turn** | `main.py:1058` produces the code; `main.py:1121` sends **`conv.messages` entire** for a second pass that narrates a value already rendered on screen | `product.md` §4 feature 15 |
| **Recall injection** | Up to ~8 KB added to attempt 1 | `memory.py:361`, `:49-52` (M1) |
| **The illustration defect** | An "explain X" turn executes an illustration and pays the second round trip to narrate a result nobody asked for. Measured **30/30** | `product.md` §6.15 |

The user's request names the second and third of those and proposes a mechanism — a *skill* — for
attacking them. This SPEC accepts the mechanism, adds the instrument the claim requires, and is
explicit that the largest saving sits behind a constraint that another SPEC owns.

---

## 2. What already exists, stated so this SPEC is not a duplicate

Written first and at length, because the honest summary of the request is *"most of this ships"* and
a SPEC that does not say so invites a second implementation of a working feature.

`SPEC-MEMORY-001` (status `completed`) already:

- persists task, reasoning, executed script and real stdout on every **successful** turn, with a
  768-dimension embedding of the task (`product.md` §4 feature 16);
- retrieves the single most similar past task above a `0.65` cosine floor and injects it as one
  ephemeral `system` message before the user's message, on attempt 1 only (feature 17);
- deduplicates by task hash, truncates each field, prunes oldest-first at 100,000 records;
- degrades to exactly one status line on any fault (feature 20).

**The storage layer needs nothing from this SPEC.** A "skill" as requested is a `SolutionRecord`
plus a rendering decision, and §3.2 defines the difference precisely rather than inventing a second
store.

---

## 3. Design decisions

### 3.1 D1 — The meter reads the server's own numbers, and never estimates

**Recommendation.** Both dimensions are derived from the final streamed chunk and from nothing else:
**cost** from `prompt_eval_count` and `eval_count`, **latency** from `total_duration`,
`load_duration`, `prompt_eval_duration` and `eval_duration`.

**Why one instrument and not two.** They arrive on the same chunk. A separate wall-clock timer around
the call would measure the client's rendering and the terminal's scroll as well as the server's work,
and the difference between those two numbers is exactly the size of the claim this SPEC makes.

**Why not a tokeniser.** Adding `tiktoken` would introduce a dependency whose vocabulary is not the
one the server used, so its numbers would be a different model's approximation of this model's cost —
precise-looking and wrong in a way no test would catch. The server already reports what it charged.

**Why this is a requirement and not a preference.** A reduction claim is this SPEC's only deliverable
of consequence. `product.md` §5.5 records what it costs to assert a behaviour rather than measure it;
`structure.md` §6 records what it costs to leave a stale document standing. An estimated figure
presented in a table beside measured ones is indistinguishable from data on a second reading.

**What happens when the numbers are absent.** Some servers and some client versions may omit them.
**A turn whose counts or durations are absent is recorded as unmeasured** (§4, S1) and contributes to
no rate. Cost is never back-filled from character counts, and latency is never back-filled from a
client-side timer.

### 3.2 D2 — A skill is a *rendering*, not a second store

**Recommendation.** A skill is a distilled form of an existing `SolutionRecord`, produced at
injection time. No new collection, no new volume, no schema migration.

**Why.** `vectorstore.py`'s collection already carries every field a skill needs, and §6.4 of
`tech.md` records what the schema costs to change: `task_hash` is the primary key, `seq` is carried
forward by hand through `upsert()`, and `meta` is persisted because the collection cannot be
enumerated. A second store would double that surface to hold data the first one already has.

**What distillation means, and what it must not do.** The full script is up to 4,000 characters
(`memory.py:51`). A skill renders the *shape* of the solution — the task pattern and the minimal
script — rather than the transcript. It **must not** drop the `adapt or ignore` framing
(`memory.py`'s `ADAPT_OR_IGNORE_SENTENCE`) or the `Authored by:` line, both of which are load-bearing
for reasons another SPEC measured: the first is `SPEC-MEMORY-001` R3's false-positive guard, the
second is `SPEC-MODEL-001` T3 option M-c.

### 3.3 D3 — The second round trip is a cost, not a fixture

**Recommendation.** Where the executed script's stdout already *is* the answer, the grounded-answer
pass at `main.py:1121` is skipped and the stdout is rendered directly.

**Why this is the cheapest large saving inside C2.** That pass sends `conv.messages` entire — the
system prompt, the whole history, the thought, the code and the stdout — to produce a sentence
wrapping a value the user can already see in the `Execution OK` panel. It is a whole prompt
evaluation per successful turn.

**Why it is not free, and what gates it.** The grounded answer is `product.md`'s stated value
proposition: *"answers are produced only after real stdout is fed back"*. Skipping it changes what
the user reads. **Whether a turn's stdout is self-explanatory is a judgement, and this SPEC does not
assume it can be made structurally** — §5 item 2 records it as the open question, and T4 carries a
measurement rather than an assertion.

### 3.4 D4 — Staging, and the staging is the recommendation

**Stage 1 lives entirely inside C2.** Compressed skill rendering (D2), the second round trip (D3),
and bounded history. Nothing in Stage 1 replays stored code, and nothing skips the model.

**Stage 2 proposes amending C2.** Replay of a stored solution, or short-circuiting the model on a
near-exact match, is where the large saving is — a matched turn could cost **zero** model tokens
instead of two full round trips. It requires amending `SPEC-MEMORY-001` C2, which is a constraint
chosen deliberately and defended in three places in that document.

**The amendment's cost, stated in advance.** C2 is what bounds the blast radius of a poisoned
memory record. `tech.md` §7.2: *"stored content is only ever shown to the model as text, never
executed… A poisoned record can mislead the model's reasoning. It cannot itself run."* Generated
code runs as the same `runner` uid that owns the store (`product.md` §6.11), so a model-written
script can write fabricated records. **Under C2 those records can only mislead. Under a replay
design they can execute.** Stage 2 is not a token optimisation with a security footnote; it is a
security decision with a token benefit, and T6 states it that way or it does not ship.

### 3.5 D5 — Stage 2's gate is a measured false-reuse rate

**Recommendation.** Stage 2 is gated on the rate at which a retrieved record is *wrong for the
current task* — a false reuse. Under C2 a false reuse costs a little prompt noise and the model
adapts or ignores it. Under replay it costs the user a wrong answer, silently, with an
`Execution OK` panel over it.

Three outcomes, all admitted in advance and none a failure of the SPEC:

| | Outcome | What happens |
|---|---|---|
| **S-a** | The false-reuse rate is low enough against the pre-registered threshold | Stage 2 proceeds; C2's amendment is drafted against `SPEC-MEMORY-001` with the measured rate quoted |
| **S-b** | The rate exceeds the threshold | **Stage 2 does not ship.** C2 stands unamended, and this SPEC's delivered value is Stage 1 plus the meter — which is a real deliverable, not a consolation |
| **S-c** | Stage 1's measured saving already meets the target | Stage 2 is **not attempted**, because a security-relevant constraint is not worth amending for a saving already banked |

**S-b and S-c are real outcomes.** Following `SPEC-ILLUSTRATE-001` §3.5: a SPEC that measures its own
preferred design out of contention has done the measurement correctly.

### 3.6 D6 — Which task moves which term, stated before any of them is built

**Recommendation.** Every task declares, in advance, the term it expects to move. A task whose
measured effect lands on a different term than predicted is a finding to write down, not a number to
present.

| Term | What it is | What can move it |
|---|---|---|
| `load_duration` | The model being loaded into memory | **Nothing in this SPEC.** It must be reported and excluded from every comparison |
| `prompt_eval_duration` | Evaluating the prompt that was sent | T3 (a shorter skill block), T5 (a bounded history) |
| `eval_duration` | Generating the completion | Only generating less; no task here targets it directly |
| `total_duration`, whole round trip | All of the above for one call | **T4** removes one entirely; Stage 2 removes both |

**Why this table is a design decision and not a note.** Without it, a warm-cache run compared against
a cold one shows a large improvement that no change caused, and it would be reported in good faith.
`load_duration` is the term that produces that error, and it is reported separately for exactly that
reason.

**One property of the server defeats the naive reading of `prompt_eval_duration`.** Ollama reuses a
cached prompt prefix across calls within a session, so shortening a prompt whose prefix was already
cached can reduce `prompt_eval_count` while barely moving `prompt_eval_duration` — a real saving in
context budget that is not a saving in time. §5 item 5 records this as unknown until measured, and
`plan.md` R1 is the risk that names it.

---

---

## 4. Requirements (EARS)

### Ubiquitous

| | Requirement |
|---|---|
| **U1** | The system **shall** attribute each **round trip** to its purpose — the code pass or the grounded-answer pass — and record the server's counts against it. Per-message token attribution is **not** required and is not obtainable (v1.1.1). |
| **U6** | The system **shall** record the **size in characters** of each prompt component — system prompt, conversation history, recall or skill block, feedback injection — and **shall** label every such figure a size. A size **shall not** be presented as, converted to, or described as a token count. |
| **U2** | The meter **shall** be a first-party module holding no third-party import, gated at **100 %** in **both** `pytest.ini`'s `--cov` list **and** `conftest.py`'s `PER_FILE_COVERAGE_TARGETS` (`conftest.py:205`). |
| **U3** | Every reduction figure this SPEC publishes **shall** cite the run that produced it and the baseline it is measured against. |
| **U4** | Every claim of improvement **shall** state which dimension it is in — **cost** (tokens) or **latency** (wall-clock) — and **shall not** imply the other. A saving in one is not evidence of a saving in the other (§3.6). |
| **U5** | Every latency comparison **shall** report `load_duration` separately and **shall** exclude it, because no task in this SPEC can reduce it and including it measures whether the model happened to be warm. |

### Event-driven

| | Requirement |
|---|---|
| **E1** | **WHEN** a model round trip completes, **THEN** the system **shall** record the `prompt_eval_count`, `eval_count`, `total_duration`, `load_duration`, `prompt_eval_duration` and `eval_duration` the server reported for it. |
| **E2** | **WHEN** a turn ends, **THEN** the system **shall** record its total cost, its per-round-trip attribution (U1) and its per-component sizes (U6). |
| **E3** | **WHEN** a skill block is injected in place of a full record, **THEN** the system **shall** record both the rendered size and the size the full record would have had, so the saving is a difference between two observed values rather than a claim. |
| **E4** | **WHEN** a round trip is skipped, **THEN** the system **shall** record the skip, so a latency improvement is attributable to a removed call rather than inferred from a smaller total. |

### State-driven

| | Requirement |
|---|---|
| **S1** | **IF** the server reports no counts or no durations for a round trip, **THEN** the turn **shall** be recorded as **unmeasured** in that dimension and **shall not** contribute to any rate in it, and no estimate **shall** be substituted. |
| **S2** | **IF** the meter raises for any reason, **THEN** the turn **shall** proceed exactly as it does today, with at most one status line — the degradation contract solution memory already meets (`product.md` §4 feature 20). |

### Optional

| | Requirement |
|---|---|
| **O1** | **WHERE** a turn is captured into solution memory, the recorded token cost **should** be stored with it, so a later arm can report cost per record without re-deriving it. |
| **O2** | **WHERE** the illustration defect fires (`product.md` §6.15, measured 30/30), the meter **should** report its cost separately, because that is a token cost `SPEC-ILLUSTRATE-001` would remove and this SPEC would otherwise take credit for. |

### Unwanted

| | Requirement |
|---|---|
| **N1** | The system **shall not** replay stored code or skip the model at Stage 1. C2 holds until it is amended, and it is amended by an amendment, not by this SPEC's implementation. |
| **N2** | The meter **shall not** estimate a token count from characters, bytes or word counts, nor a latency from a client-side timer, under any circumstance, including when the server omits its numbers. |
| **N6** | A latency figure **shall not** be presented without `load_duration` stated, and a comparison **shall not** be drawn between a cold run and a warm one. |
| **N3** | Distillation **shall not** remove the `adapt or ignore` framing or the `Authored by:` line. Both were specified by measurements this SPEC did not take. |
| **N4** | This SPEC **shall not** modify `SPEC-MEMORY-001`'s collection schema, `memory.py`'s truncation caps, or the `0.65` similarity floor. Those are measured values belonging to another SPEC. |
| **N5** | No existing cell in `probe/tasks.py` **shall** be renamed, re-worded, re-sized or removed, and no existing record file **shall** be rewritten. |

---

## 5. What this SPEC does not know

Written now, so that it is not written later by whoever wants the result to mean more.

1. **Whether Stage 1 alone meets the target.** Unknown until T2 records a baseline and T3–T5 are
   measured against it. S-c exists precisely because it might.
2. **Whether "stdout is self-explanatory" is decidable structurally.** D3 skips the second round
   trip on that judgement, and the judgement may not survive contact with real turns. T4 measures it;
   it does not assume it.
3. **What a false reuse rate actually is.** No cell measures it today. `SPEC-MEMORY-001` measured
   that the Seoul→Busan pair scores 0.76 and unrelated pairs 0.30–0.40, which establishes that the
   floor separates *related* from *unrelated* — not that a related record is *correct* for the new
   task. Those are different questions and this corpus cannot tell them apart.
4. **Whether a shorter prompt is a faster prompt.** Ollama reuses a cached prompt prefix within a
   session, so shortening a prompt whose prefix was already cached may reduce `prompt_eval_count`
   while barely moving `prompt_eval_duration`. **The two dimensions can disagree, and this SPEC does
   not know by how much until T2 measures it.** If they disagree sharply, T4 and Stage 2 — which
   remove whole calls rather than shortening them — are the only tasks that deliver what was asked
   for, and T3 and T5 deliver context budget instead. That is a finding, not a failure.
5. **Whether the model's own token accounting is stable across model tags.** `SPEC-MODEL-001`
   measured Phi-3.5 at a 131,072 context against llama3.1:8b's; a baseline taken under one and
   quoted under the other is not a comparison.

---

## 6. Out of scope

1. **Amending `SPEC-MEMORY-001` C2.** T6 *proposes* it with a measured rate attached. The amendment
   is that SPEC's to accept.
2. **A second vector store, a schema change, or a migration** (N4, D2).
3. **Fixing the illustration defect.** `SPEC-ILLUSTRATE-001` owns it. O2 exists so this SPEC does
   not claim its saving.
4. **A context-window guard.** Bounding history (T5) reduces tokens; detecting that a session has
   exceeded the model's window is `product.md` §6.6's other half and is not attempted here.
5. **Pinning or lockfiles.** `tech.md` §8.5 owns reproducibility.
