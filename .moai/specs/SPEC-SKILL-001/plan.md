# SPEC-SKILL-001 — Implementation plan

> Requirements are in `spec.md`. Acceptance criteria are in `acceptance.md`.

---

## 1. Shape of the work

Seven tasks, one prerequisite, and a gate in the middle. **None has been started.**

The prerequisite is not a task: **T2 cannot begin until T1's meter exists**, because the baseline
T2 records is the only thing every later figure is measured against. That ordering is the whole
plan. Reversing it produces optimisations with no denominator.

T1, T3, T4 and T5 need no model and no Docker. T2 and T6 need a running `ollama` sidecar and are
measured in hours, not minutes.

---

## 2. Tasks

| # | Task | Artefact | Depends on |
|---|---|---|---|
| **T1** | **The meter, as a new gated leaf.** A first-party module holding no third-party import, floored at **100 %**. Registered in **both** `pytest.ini`'s `--cov` list **and** `conftest.py`'s `PER_FILE_COVERAGE_TARGETS` (`conftest.py:205`) — **both or neither**; one without the other makes `cov.report(include=[...])` raise and fails the session, which is the right direction for that mistake. Added to the `Dockerfile` `COPY` line (`Dockerfile:43`) **and** to every file list `tests/test_source_seam.py` asserts set equality over, because that test exists precisely because `keychain.py` was added to one and not the other. `stream_llm()` (`main.py:209-221`) is amended to surface the final chunk's **six** fields — `prompt_eval_count`, `eval_count`, `total_duration`, `load_duration`, `prompt_eval_duration` and `eval_duration` — because cost and latency arrive together and a client-side timer would measure this process's rendering as well as the server's work (`spec.md` D1); **its docstring records that it "has never been" tested with a fake client, and this task changes that.** Behaviour when the counts are absent is **record as unmeasured** (`spec.md` S1, N2), and that is a test, not a comment. | new module, `pytest.ini`, `conftest.py`, `Dockerfile`, `main.py`, `tests/` | — |
| **T2** | **The baseline, pre-registered.** Record per-turn **cost and latency** across representative task shapes at the current tree, with the per-source breakdown `spec.md` U1 requires and `load_duration` reported separately so it can be excluded (`spec.md` U5). **The two dimensions are recorded side by side and pre-registered separately**, because a target met in one and missed in the other is a likely outcome and the record must be able to say so. **Pre-register the reduction target and the Stage 2 false-reuse threshold in `verification-T2.md` §1, and commit that file containing no results, before the first turn is run.** `SPEC-PROMPT-001` v1.1.1 records in full what it cost to be unable to demonstrate that ordering: its record claimed twice, in bold, that its pre-registration had been committed first. It had not. **That fix is available only in advance.** Every figure carries the model tag the server read back, because `SPEC-MODEL-001` established that a rate without its model is not a measurement. | `verification-T2.md`, `probe-runs/` | T1 |
| **T3** | **The skill rendering.** A distilled form of an existing `SolutionRecord`, produced at injection time — **no new store, no schema change** (`spec.md` D2, N4). Renders the task shape and the minimal script rather than the ≤4,000-character transcript (`memory.py:51`). **Keeps the `adapt or ignore` sentence and the `Authored by:` line** (`spec.md` N3): the first is `SPEC-MEMORY-001` R3's false-positive guard, the second is `SPEC-MODEL-001` T3 option M-c, and neither was measured by this SPEC. `spec.md` E3 requires recording **both** the rendered size and the size the full record would have had, so the saving is a difference between two observed values. | new rendering in `memory.py`, `tests/` | T2 |
| **T4** | **The second round trip.** `main.py:1121` sends `conv.messages` **entire** to narrate a value already rendered in the `Execution OK` panel. Skip it where the executed script's stdout already *is* the answer. **This changes what the user reads**, and `product.md`'s value proposition is that answers are grounded in real stdout — so the deliverable is not the skip but the **measurement of when it is safe** (`spec.md` §5 item 2). If the judgement cannot be made structurally, T4's honest outcome is "not shipped, and here is why", exactly as `spec.md` §3.5 admits for Stage 2. | `main.py`, `verification-T2.md` §3 | T2 |
| **T5** | **Bound the history.** `Conversation.messages` is append-only (`main.py:195-201`) and every failed attempt injects a full stderr+stdout dump first. Window or summarise it. **The retry loop reads history to diagnose**, so a window that drops the failure it is correcting turns the self-correction loop into a slower first attempt — the test is that a two-attempt turn still recovers, not that the message list got shorter. | `main.py`, `tests/` | T2 |
| **T6** | **Stage 2 — the C2 amendment, gated.** Replay or model short-circuit on a near-exact match. `spec.md` §3.5's gate decides: **S-a** proceeds, **S-b** does not ship, **S-c** is not attempted because Stage 1 already met the target. The deliverable is a **drafted amendment to `SPEC-MEMORY-001` C2 carrying the measured false-reuse rate** — not an implementation that assumes the amendment. It states the security cost in the terms `tech.md` §7.2 already uses: under C2 a poisoned record can mislead the model; under replay it can execute. | `verification-T2.md` §5, an amendment against `SPEC-MEMORY-001` | T3, T4, T5 measured |
| **T7** | **Raise `MIN_PASSED`** (`.github/workflows/ci.yml:367`, currently **617**) to a count **read from a real `--junitxml` run**, never computed from an expected delta. That file's own comment says *"raise it in the same change that adds the tests, or it silently stops guarding"*. | `.github/workflows/ci.yml` | T1, and again after T3–T5 |

### 2.1 Dependency graph

```
T1 ──> T2 ──┬─> T3 ──┐
            ├─> T4 ──┼─> T6   (gated: S-a / S-b / S-c)
            └─> T5 ──┘
T1 ──> T7 (and again after T3-T5)
```

### 2.2 What needs what

| Task | Needs a model? | Needs Docker? | Status |
|---|---|---|---|
| T1 | no | no | not started |
| **T2** | **yes** — the sidecar, and hours | **yes** | **not started** |
| T3 | no | no | blocked on T2 |
| T4 | no (unit) / **yes** (the judgement) | for the measurement | blocked on T2 |
| T5 | no | no | blocked on T2 |
| **T6** | **yes** | **yes** | gated on `spec.md` §3.5 |
| T7 | no | no | after T1, and again after T3–T5 |

---

## 3. Risks

| | Risk | Likelihood and blast radius | Mitigation |
|---|---|---|---|
| **R1** | **The two dimensions disagree, and the SPEC reports the flattering one.** Ollama reuses a cached prompt prefix within a session, so shortening a prompt whose prefix was already cached reduces `prompt_eval_count` while barely moving `prompt_eval_duration`. **Since v1.1.0 the SPEC promises speed**, so a cost-only result now under-delivers against its own stated goal rather than merely being mislabelled. | **The most likely way this SPEC produces a confident wrong number**, and the amendment raised the stakes: it looks like a measurement because it is one; it is just not a measurement of what was asked for. | T2 records both dimensions in the same row with `load_duration` broken out; `spec.md` **U4** forbids a claim in one dimension from implying the other, and **U5** forbids a latency comparison that includes model-load time. If they disagree, `spec.md` §5 item 4 admits the consequence in advance: T4 and Stage 2 deliver speed, T3 and T5 deliver context budget, and that split is a finding to publish rather than a failure to bury. |
| **R2** | **Stage 1 is measured and the saving is small.** Distilling a ≤4 KB script out of a prompt that also carries an unbounded history may be a rounding error against the total. | Real, and S-c exists for the opposite case. If the history dominates, T5 is the whole SPEC and T3 is decoration. | T2's **per-source breakdown** (`spec.md` U1) is what decides which of T3/T4/T5 is worth doing. It is taken **before** any of them, precisely so the answer is not chosen by whoever implemented first. |
| **R3** | **T4 removes the product's stated value proposition to save tokens.** `product.md` §2.1: answers are *"grounded in a value that was actually computed, not predicted"*. Skipping the grounded pass makes the raw stdout the answer. | Moderate probability, high blast radius: the change is invisible in tests and obvious to a user, and the README makes the promise explicitly. | T4's deliverable is the **measurement of when the skip is safe**, not the skip. `acceptance.md` AC-GROUND requires that no turn ends with **less on screen** than it does today, which is the same constraint `SPEC-ILLUSTRATE-001` S4 imposed on its own suppression. |
| **R4** | **Stage 2 is implemented before its amendment is accepted.** The saving is large and the constraint is one sentence in another document; the temptation is to treat C2 as a formality. | Low probability, **the highest blast radius in this SPEC**. C2 is what stops a poisoned memory record from executing (`tech.md` §7.2), and generated code can write to the store (`product.md` §6.11). | `spec.md` **N1** makes it an Unwanted behaviour, and T6's artefact is an **amendment document**, not code. If T6 produces a diff to `main.py` before `SPEC-MEMORY-001` carries the amendment, that is the failure this row names. |
| **R5** | **The baseline is taken under one model and quoted under another.** `SPEC-MODEL-001` measured Phi-3.5 at a 131,072 context against llama3.1:8b's; token costs are not comparable across them. | Certain if unguarded, and it silently invalidates every percentage in the SPEC. | Every T2 row carries the server's own model readback, as `SPEC-MODEL-001` U3 already requires of `probe/`. A figure without one is not recorded. |
| **R6** | **The illustration defect's cost is credited to this SPEC.** 30/30 of "explain X" turns pay a second round trip for a narration nobody asked for (`product.md` §6.15). Removing it would cut tokens — and it belongs to `SPEC-ILLUSTRATE-001`. | Moderate, and it would overstate this SPEC's result by whatever share those turns hold. | `spec.md` **O2** requires the meter to report that cost **separately**. Two SPECs cannot both bank the same saving. |

---

| **R7** | **A warm run is compared against a cold one.** `load_duration` is the model being loaded into memory and can dominate every other term on a cold container — `tech.md` §6.4 already records cold-start figures differing materially from same-process ones for the vector store, for the same class of reason. | Certain if unguarded, and it produces a large improvement that no change caused, reported in good faith. | `spec.md` **U5** and **N6** make reporting `load_duration` separately and excluding it a requirement, and forbid a comparison drawn across that boundary. `acceptance.md` AC-LATENCY is the gate. |

---

## 4. Sequencing note

**T1 and T7 land together or the branch is knowingly red in between**, in the sense that
`MIN_PASSED` trails the real count and stops guarding. The same applies after T3–T5.

**The ranking of T3/T4/T5 is decided by T2, not by this document.** Under cost alone the obvious targets are T3 and T5; under latency the obvious target is **T4**, because it removes an entire round trip rather than shortening one (`spec.md` §3.6). Both readings are plausible before the measurement and only one survives it.

**T2's pre-registration commit contains no results.** It is committed on its own, before the first
trial, and that is the only available demonstration that the threshold was not chosen after the
numbers arrived.
