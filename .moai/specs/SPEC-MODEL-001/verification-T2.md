# SPEC-MODEL-001 — T1 provenance and T2 pre-registration

> **§1 and §2 were committed alone, containing no results, at `3999b80` — before
> the run.** §3 and §5 were added afterwards, at the commit that carries the data.
> The git history is the evidence that the gate in §2.3 was not chosen after
> seeing a number; `SPEC-PROMPT-001` v1.1.1 records what it cost to pre-register
> nothing, and that fix is available only in advance.
>
> **The gate resolved to P-c and the swap does not ship.** §5 has the reasoning.

---

## 1. T1 — the model, read from the server

*Measured 2026-08-21 via `docker exec coderunner-ollama`. Every figure below is
from command output, not from a model card.*

| Field | Value | Source |
|---|---|---|
| **Tag, exactly as `ollama list` prints column 1** | **`phi3.5:latest`** | `ollama list` |
| Ollama id | `61819fb370a3` | `ollama list` |
| On-disk size | **2.2 GB** | `ollama list` |
| Architecture | `phi3` | `ollama show` |
| Parameters | **3.8B** | `ollama show` |
| Quantisation | **Q4_0** | `ollama show` |
| Context length | **131072** | `ollama show` |
| Embedding length | 3072 | `ollama show` |
| Blob digest | `sha256-b5374915da534cb93df39f03bd4f2cd5a0c533df0d5e21957dc9556c260be9eb` | `ollama show --modelfile` |

**The `:latest` suffix is load-bearing and this is the whole reason T1 exists.**
`have_model()` (`coderunner:480-483` at the time of writing) matches whole lines
with `grep -qx` against `ollama list` output. `phi3.5` was the string *pulled*;
`phi3.5:latest` is the string *printed*. **A default spelled `phi3.5` would
therefore never match, and would re-pull 2.2 GB on every launch, forever,
silently** — the exact failure this project already took once on the embedding
model. T5(a) must carry `phi3.5:latest` byte-for-byte into `main.py`,
`docker-compose.yml:46`, `:78` and `coderunner:512`.

**Comparison with the incumbent**, both from the same `ollama list`:

| | `llama3.1:8b` | `phi3.5:latest` |
|---|---|---|
| Size | 4.9 GB | **2.2 GB** |
| Parameters | 8B | **3.8B** |
| Quantisation | Q4_K_M | Q4_0 |

---

## 2. T2 — pre-registered acceptance thresholds

**Registered before the run. Nothing below was chosen after seeing a number.**

### 2.1 What is measured

`SPEC-PROMPT-001`'s **five control cells** at **V0**, **N=30 each**, 150 trials
total, under `phi3.5:latest`. c4 (*"explain what a Python closure is, with a short
example"*) is one of the five and is also `SPEC-ILLUSTRATE-001`'s measurement
cell; it is run **once** and reported under both headings.

V0 is `SYSTEM_PROMPT` unmodified (`probe/variants.py:38`). The prompt is not
touched by this SPEC.

### 2.2 The baseline this is measured against

`llama3.1:8b`, 2026-08-10, N=30 per cell, recorded in
`.moai/specs/SPEC-PROMPT-001/probe-runs/v0-*.jsonl`. c4's figure — **CODE 30/30,
DIRECT 0/30**, 95 % Wilson **[0.000, 0.114]** — is the one this project has
documented most widely.

### 2.3 The gate

| Outcome | Condition | Consequence |
|---|---|---|
| **P-a** | Phi-3.5's DIRECT rate on the control cells is **no worse** than llama3.1:8b's, within overlapping 95 % Wilson intervals | The swap proceeds. T4 amends the documents, T5 carries the tag |
| **P-b** | Phi-3.5 is **measurably better** on routing — its DIRECT rate exceeds llama's with non-overlapping intervals on at least one cell | The swap proceeds, and `SPEC-ILLUSTRATE-001`'s premise is re-opened, because a prompt-only intervention that failed at 8B may not have failed for the reason assumed |
| **P-c** | Phi-3.5 is **measurably worse** on any control cell, or fails to emit a parseable fenced block where llama did | **The default stays `llama3.1:8b`.** T4 has nothing to amend. The SPEC's delivered value is this file, plus T2a, T3 and T5(c), which are already banked |

**P-c is a real outcome and not a failure of the SPEC**, per `SPEC-ILLUSTRATE-001`
I-b. A 3.8B model holding a two-protocol contract less reliably than an 8B one is
the single most likely result here and it is admitted in advance.

### 2.4 What would invalidate the run rather than decide it

- Any trial whose recorded `model_tag` is not `phi3.5:latest`. The probe records
  the server's own readback, so this is detectable rather than assumed.
- Fewer than 30 completed trials in any cell.
- A change to `SYSTEM_PROMPT`, `probe/tasks.py` or `probe/classify.py` between
  the baseline and this run. All three are unmodified; `tests/test_probe.py`
  gates the third.

---

## 3. Results

*Run completed 2026-08-21. 150/150 trials, `phi3.5:latest`, V0, five control cells
at N=30. **Valid on all four §2.4 criteria**: every trial's server readback is
`phi3.5:latest`, every trial is V0, every cell reached 30, and `SYSTEM_PROMPT`,
`probe/tasks.py` and `probe/classify.py` are unmodified.*

`.moai/specs/SPEC-MODEL-001/probe-runs/phi35-v0-controls.jsonl`

### 3.1 DIRECT rate, per cell, against the llama3.1:8b baseline

| Cell | `llama3.1:8b` (2026-08-10) | `phi3.5:latest` (2026-08-21) | Verdict |
|---|---|---|---|
| `c1_conversational` | **30/30 — 100.0 %** [88.6, 100.0] | 11/30 — 36.7 % [21.9, 54.5] | **worse, disjoint** |
| `c2_conversational` | 20/30 — 66.7 % [48.8, 80.8] | **27/30 — 90.0 %** [74.4, 96.5] | overlapping |
| `c3_opinion` | **26/30 — 86.7 %** [70.3, 94.7] | 5/30 — 16.7 % [7.3, 33.6] | **worse, disjoint** |
| `c4_general_knowledge` | 0/30 — 0.0 % [0.0, 11.4] | 0/30 — 0.0 % [0.0, 11.4] | overlapping |
| `c5_general_knowledge` | **14/30 — 46.7 %** [30.2, 63.9] | 1/30 — 3.3 % [0.6, 16.7] | **worse, disjoint** |

**Totals: Phi-3.5 44/150 (29.3 %) DIRECT; llama3.1:8b 90/150 (60.0 %).** All
intervals are 95 % Wilson.

### 3.2 The fence trap, which is new and is not in the DIRECT rate

| | `llama3.1:8b` | `phi3.5:latest` |
|---|---|---|
| Trials with `fence_matches > 1` | **0/30 on c4** | **17/150 overall, 13/30 on c4** |

Distribution: c4 13, c3 2, c1 1, c2 1. Fence counts across the run: 89 trials at
1, 44 at 0, **17 at 2**.

**This is a second, independent failure mode and it is worse than the rate
suggests.** `SPEC-ILLUSTRATE-001` §2.2 recorded `fence_matches == 1` in all thirty
llama trials and stated explicitly that its finding was *"not the two-block
trap"*. Under Phi-3.5, c4 hits that trap in **13 of 30**. Since
`extract_last_python_block()` (`main.py:447-449`) returns the **last** match, a
two-block reply runs whichever block came second — which is not chosen for being
runnable, only for being last.

### 3.3 Latency

Median `elapsed_sec` 11.67 s, over one round trip of the at-least-two a real turn
costs. No end-to-end figure exists; the probe executes nothing. **"A smaller model
will be faster" is not demonstrated by this run and is not claimed.**

---

## 4. T6 — post-change verification

**Not reached.** T6 verifies a change that §5 declines to make.

---

## 5. The decision

**P-c. The default stays `llama3.1:8b`.**

§2.3 registered P-c before the run as *"Phi-3.5 is measurably worse on any control
cell"*. **Three of five are worse with non-overlapping 95 % Wilson intervals** —
c1, c3 and c5 — and c3 is the starkest at 86.7 % → 16.7 %. The condition is met
three times over, and the fence-trap finding in §3.2 is an additional failure the
gate did not even ask about.

**T4 is therefore not reached.** There is nothing to amend, because nothing
changed: `main.py:71`, `docker-compose.yml:46`, `:78` and `coderunner:512` keep
`llama3.1:8b`. T5(a) and T5(b) are likewise not reached — there is no new tag to
carry. **T5(c) and T3 are already delivered and stand on their own**, as §1.1
predicted they would under every outcome.

### 5.1 What was banked regardless

| | Delivered |
|---|---|
| **T1** | `phi3.5:latest` fully characterised: 3.8B, Q4_0, 2.2 GB, 131072 context — and the `:latest` suffix trap identified before it could cost anything |
| **T2a** | `probe/` ported off one SPEC's private branch; the project's only behavioural instrument now lives where a second SPEC can use it |
| **T2** | This file. **A measured answer to a question that was previously a matter of opinion** |
| **T3** | M-c shipped: the recall block names its authoring model |
| **T5(c)** | `--doctor` reports the chat model's presence |

### 5.2 The finding that outlives this SPEC

**`c4` is 0/30 on both models.** The defect `SPEC-ILLUSTRATE-001` documents — an
"explain X" question answered by writing, executing, narrating and *storing* an
illustration — is identical under a different model family, a different parameter
count and a different quantisation. **It is not a llama3.1:8b quirk.**

That is direct evidence for `SPEC-ILLUSTRATE-001` D1, which argued the fix must be
product-side rather than prompt-side, and it was previously argued rather than
measured. It now has a second data point from a model that shares nothing with the
first but the prompt.

**And the fence trap makes the case stronger.** A structural screen that asks
whether a block is closed and import-free is unaffected by how many blocks the
model emitted; a prompt-side fix would have to teach two different model families
two different lessons.

### 5.3 What this run does not establish

- **Nothing about Phi-3.5's code quality.** The probe classifies routing and never
  executes a block. A model that routes worse may still write better Python; this
  run cannot see it.
- **Nothing about the `@param` grammar**, which `spec.md` §5 named as the riskiest
  surface of a swap and which still has no instrument.
- **Nothing about V1–V3.** Only V0 was run. Whether Phi-3.5 responds better to the
  repaired prompt variants is unmeasured, and is the obvious next question.
