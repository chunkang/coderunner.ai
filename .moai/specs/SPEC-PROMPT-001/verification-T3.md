# SPEC-PROMPT-001 — T3 measurement record

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. Acceptance criteria are in
> `acceptance.md`.

---

## STATUS: NOT YET RUN

**Created 2026-08-08 with its structure in place and every result cell empty.** No probe has been
executed. No model has been queried. Nothing in §2, §3, §4 or §5 has been measured.

**There are no placeholder figures in this document and there must never be** (`spec.md` N7). Every
results cell reads `—` and every section carries its own not-run marker. A plausible-looking number
written here as an illustration would, on the second reading by the second person, be
indistinguishable from data. That is not a hypothetical failure mode: `SPEC-KEYCHAIN-001`'s HISTORY
records a launcher check that *"had been inspecting nothing, and would have passed against the one
form the SPEC forbids"* — a test that looked like evidence and was not.

**`spec.md` §HISTORY records why this file is empty rather than merely unwritten.** Ollama is not
reachable from the host this SPEC was authored on. Measured 2026-08-08:

```
$ command -v ollama
(no output, rc 1)
$ ls /usr/local/bin/ollama /opt/homebrew/bin/ollama
ls: /usr/local/bin/ollama: No such file or directory
ls: /opt/homebrew/bin/ollama: No such file or directory
$ curl -s -m 3 -o /dev/null -w "http_code=%{http_code}\n" http://localhost:11434/api/tags
http_code=000
```

So the probe cannot be run from where the SPEC was written, and running it is a task with a stated
precondition (`plan.md` §1), not something an implementer discovers.

**Until §2 and §3 are filled, `plan.md` T4 has not been authorised to start** (`spec.md` S5).

---

## 1. Provenance — what was measured, and against what

*Not yet run. Every cell below is to be filled from the run itself, not from configuration files.*

| | Value |
|---|---|
| Date of run | — |
| Model tag | — *(expected `llama3.1:8b`, `docker-compose.yml:46`, `:78` — but record what the run reports, not what compose declares)* |
| Model digest | — |
| Quantisation | — |
| Reached via | — *(compose `ollama` sidecar at `http://ollama:11434`, or a named host)* |
| Ollama version | — |
| Temperature / sampling | — *(record it; the whole reason N ≥ 10 exists is that this is not zero)* |
| Harness commit | — |
| `main.py` commit the classifier was imported from | — |
| Trials per cell (N) | — |

**S4 applies to this table.** A result obtained against any other model, quantisation or host is a
result *about that model*. It may be recorded here, clearly labelled, and it does **not** discharge
the gate.

---

## 2. Baseline — V0, `SYSTEM_PROMPT` unmodified

*Not yet run.*

This is `plan.md` T2. It must be taken **before** any prompt text is written. A baseline taken after
an edit is not a baseline, and `acceptance.md` **AC-GATE** item 5 makes the `git log` ordering
checkable.

Its purpose is to convert the reported refusal from an anecdote at `n=1` into a rate.

### 2.1 Target task — the reported request, verbatim

Task prompt: `check my gmail for recent 7 days and let me know the interview opportunities`

| Metric | Value |
|---|---|
| Trials (N) | — |
| Routed CODE (a fenced block was produced) | — |
| Routed DIRECT (`extract_last_python_block()` falsy) | — |
| Refusal rate | — |
| Distinct refusal phrasings observed | — |

Verbatim replies (O3): *not yet collected.*

### 2.2 Off-example network task

*A network-reachable task outside the three exampled domains at `main.py:146-153`, involving no
account and no credential. This cell isolates the routing repair from anything mail-shaped.*

Task prompt: — *(to be fixed at T1 and recorded here verbatim, so V1 and V2 use the identical
string)*

| Metric | Value |
|---|---|
| Trials (N) | — |
| Routed CODE | — |
| Routed DIRECT | — |

### 2.3 Tool-reachable task

*A task for which `web_search` is the natural instrument. This cell is `product.md` §6.1's actual
close condition (`spec.md` N8) — not the presence of a string in the prompt.*

Task prompt: —

| Metric | Value |
|---|---|
| Trials (N) | — |
| Routed CODE | — |
| Emitted code that imports `tools` | — |
| Emitted code that calls `web_search` | — |

**Expected at V0: zero.** `SYSTEM_PROMPT` contains no occurrence of `tools` or `web_search`
(measured 2026-08-08, `spec.md` §2.2), so the model has no channel through which to learn the name.
**If this cell is non-zero at V0, that is a finding and it changes the SPEC** — it would mean the
model reaches for a module it was never told about, and §6.1's premise would need re-examining.

### 2.4 Control set — must route DIRECT

*`spec.md` S2. `plan.md` R2. This is the only defence against the regression with the largest blast
radius in this SPEC, and it is measured at V0 so there is something to compare against.*

| Control prompt | Kind | Trials (N) | Routed DIRECT | Rate |
|---|---|---|---|---|
| — | conversational | — | — | — |
| — | opinion | — | — | — |
| — | general knowledge | — | — | — |

---

## 3. Variants — V1 and V2

*Not yet run.* This is `plan.md` T3.

| Variant | Definition |
|---|---|
| **V1** | V0 with the routing contradiction repaired (`spec.md` D1) — `main.py:126-129` amended so DIRECT means "no computation and no fetch would answer this" rather than "you do not already hold this data" |
| **V2** | V1 plus the capability section (`spec.md` D2, D3), inserted **below** `main.py:166` (N3), naming the library set, network egress and `from tools import web_search`, each with a worked example |

### 3.1 Target task

| | V0 | V1 | V2 |
|---|---|---|---|
| Trials (N) | — | — | — |
| Routed CODE | — | — | — |
| Refusal rate | — | — | — |

### 3.2 Off-example network task

| | V0 | V1 | V2 |
|---|---|---|---|
| Trials (N) | — | — | — |
| Routed CODE | — | — | — |

**Read this table against §3.1.** If the off-example task improves and the Target does not, the
residue is account-specific and belongs to `SPEC-ACCOUNT-001`. If neither improves, the routing
repair did not work, and recording that is the point of taking the measurement.

### 3.3 Tool-reachable task

| | V0 | V1 | V2 |
|---|---|---|---|
| Trials (N) | — | — | — |
| Imports `tools` | — | — | — |
| Calls `web_search` | — | — | — |

**The V2 row of this table is what closes `product.md` §6.1** (`spec.md` N8, `acceptance.md`
AC-TOOLS item 4). Nothing else does.

### 3.4 Control set

| Control prompt | V0 DIRECT rate | V1 | V2 |
|---|---|---|---|
| — | — | — | — |
| — | — | — | — |
| — | — | — | — |

### 3.5 Code correctness, where assessed

*This is what separates **M-a** from **M-c**. A trial that produced a fenced block is not a success
unless the code was also assessed.*

| Task | Variant | Trials producing code | Code assessed? | Code that ran successfully |
|---|---|---|---|---|
| Target | V2 | — | — | — |
| Off-example network | V2 | — | — | — |
| Tool-reachable | V2 | — | — | — |

**If correctness was not assessed at T3, say so here explicitly and defer the M-a/M-c distinction to
`SPEC-ACCOUNT-001` A1** (`acceptance.md` AC-GATE item 3). Leaving this section blank without that
sentence is the failure the criterion names.

---

## 4. Post-change regression — the shipped prompt

*Not yet run.* This is `plan.md` T6, and it runs **after** `main.py` is amended, against whatever
actually shipped.

| Control prompt | Kind | V0 DIRECT rate | Shipped DIRECT rate | N (V0) | N (shipped) | Worse? |
|---|---|---|---|---|---|---|
| — | conversational | — | — | — | — | — |
| — | opinion | — | — | — | — | — |
| — | general knowledge | — | — | — | — | — |

**If any row is worse, it is recorded here with its numbers and either resolved or accepted in
writing** (`acceptance.md` AC-CONTROL item 5). It is not rounded away, and it is not attributed to
noise without stating N.

**If the control set ran at a smaller N than the target set, both Ns are above and the difference is
stated in words**, because a control measured at N=3 against a target measured at N=20 is not a
control.

---

## 5. Gate outcome

*Not yet determined.*

**Record exactly one of the following, with the numbers from §3.1 and §3.5 that support it. Do not
record "pass", "fail", "improved" or "works"** (`acceptance.md` AC-GATE items 1 and 2).

| Outcome | Meaning | Consequence |
|---|---|---|
| **M-a** | Refusal was a routing artefact. V2 complies at a materially better rate than V0, and the emitted code works | `plan.md` T4 proceeds. `SPEC-ACCOUNT-001` proceeds as a prompt-design SPEC |
| **M-b** | Refusal is safety-training-driven. V2's Target refusal rate is **not** materially better than V0's | `plan.md` T4's routing half does **not** proceed. `SPEC-ACCOUNT-001` stays gated closed. Open `SPEC-MODEL-001`. `spec.md` S1 |
| **M-c** | The model complies but writes code that does not work | T4 proceeds. `SPEC-ACCOUNT-001` A1 inherits a narrowed question: the constraint is neither prompt wording nor model choice, but that IMAP is fiddly. D1 of that SPEC is decided against this |

**Outcome:** —

**Supporting figures:** —

**Classified by:** —

**Date:** —

---

## 6. What these runs do NOT establish

*To be written after the runs, and expected to be longer than §2–§4 combined — that is the honest
ratio, and it is the ratio `SPEC-CI-001/verification-T3.md` set for this repository.*

Candidates known in advance, listed so they are not forgotten once numbers exist:

- **A rate is not a guarantee.** N trials at default temperature bound a probability; they do not
  establish that the model will never refuse. Nothing measured here makes a claim about any single
  future turn.
- **One model, one quantisation, one host.** Nothing here generalises to a different
  `CODERUNNER_MODEL`, and users may set one (`docker-compose.yml:78`).
- **The task prompts are the ones chosen at T1.** A phrasing the probe did not try is a phrasing the
  probe says nothing about, and the reported defect arrived through a phrasing nobody predicted.
- **The classifier observes routing, not quality.** Except where §3.5 is filled, a fenced block is
  counted as compliance regardless of whether the code would have worked.
- **The control set is three prompts.** It is a smoke test for R2, not a characterisation of
  conversational routing.
- **Nothing here measures token cost** unless O4 was taken up, and the added prompt text is paid for
  on every turn of every session.
