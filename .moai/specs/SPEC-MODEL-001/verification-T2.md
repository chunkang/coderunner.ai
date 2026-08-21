# SPEC-MODEL-001 — T1 provenance and T2 pre-registration

> **This file is committed containing no results.** §2 onward are empty and stay
> empty until the run that fills them has happened. `SPEC-PROMPT-001` v1.1.1
> records what it cost to pre-register nothing, and that fix is available only in
> advance.

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

*Empty. Filled by the run.*

---

## 4. T6 — post-change verification

*Empty. Not reached unless T3 resolves to P-a or P-b.*

---

## 5. The decision

*Empty. Filled after §3 exists.*
