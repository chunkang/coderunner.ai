---
id: SPEC-SKILL-001
version: "1.0.0"
status: "draft"
created: "2026-09-05"
updated: "2026-09-05"
author: "Chun Kang"
priority: "MEDIUM"
---

## HISTORY

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

### 3.1 D1 — The meter reads the server's counts, and never estimates

**Recommendation.** Token accounting is derived from `prompt_eval_count` and `eval_count` on the
final streamed chunk, and from nothing else.

**Why not a tokeniser.** Adding `tiktoken` would introduce a dependency whose vocabulary is not the
one the server used, so its numbers would be a different model's approximation of this model's cost —
precise-looking and wrong in a way no test would catch. The server already reports what it charged.

**Why this is a requirement and not a preference.** A reduction claim is this SPEC's only deliverable
of consequence. `product.md` §5.5 records what it costs to assert a behaviour rather than measure it;
`structure.md` §6 records what it costs to leave a stale document standing. An estimated figure
presented in a table beside measured ones is indistinguishable from data on a second reading.

**What happens when the counts are absent.** Some servers and some client versions may omit them.
**A turn whose counts are absent is recorded as unmeasured** (§4, S1) and contributes to no rate. It
is never back-filled from character counts.

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

---

## 4. Requirements (EARS)

### Ubiquitous

| | Requirement |
|---|---|
| **U1** | The system **shall** attribute every counted token to exactly one source: system prompt, conversation history, recall or skill block, feedback injection, or completion. |
| **U2** | The meter **shall** be a first-party module holding no third-party import, gated at **100 %** in **both** `pytest.ini`'s `--cov` list **and** `conftest.py`'s `PER_FILE_COVERAGE_TARGETS` (`conftest.py:205`). |
| **U3** | Every reduction figure this SPEC publishes **shall** cite the run that produced it and the baseline it is measured against. |

### Event-driven

| | Requirement |
|---|---|
| **E1** | **WHEN** a model round trip completes, **THEN** the system **shall** record the `prompt_eval_count` and `eval_count` reported by the server for that round trip. |
| **E2** | **WHEN** a turn ends, **THEN** the system **shall** record its total cost and the per-source breakdown required by U1. |
| **E3** | **WHEN** a skill block is injected in place of a full record, **THEN** the system **shall** record both the rendered size and the size the full record would have had, so the saving is a difference between two observed values rather than a claim. |

### State-driven

| | Requirement |
|---|---|
| **S1** | **IF** the server reports no token counts for a round trip, **THEN** the turn **shall** be recorded as **unmeasured** and **shall not** contribute to any rate, and no estimate **shall** be substituted. |
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
| **N2** | The meter **shall not** estimate a token count from characters, bytes, or word counts, under any circumstance, including when the server omits its counts. |
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
4. **Whether the model's own token accounting is stable across model tags.** `SPEC-MODEL-001`
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
