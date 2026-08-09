# SPEC-PROMPT-001 — Implementation Plan (v1.0.0)

> Requirements are in `spec.md`. Acceptance criteria are in `acceptance.md`. The measurement record
> is `verification-T3.md`.

## 0. Starting position

The diff this SPEC produces is small: a repaired clause and a new section in one string literal, one
`except` block in `tools.py`, and documentation. The work is not the diff.

**The work is that this repository has never observed the effect of a prompt change and has no way
to.** `main.py` has zero tests (`structure.md:56`). `SYSTEM_PROMPT` has none and cannot have any
without a model in the loop. So the edit is trivial and the evidence that it did what it claims —
and did not do anything else — has to be built first. Eight of the nine tasks below exist for the
evidence.

| Present | Evidence |
|---|---|
| A prompt that already teaches by worked example, and a shape to copy | `main.py:146-153` |
| A production predicate that decides CODE vs DIRECT in one call | `extract_last_python_block()` `main.py:447`; the branch `main.py:1032-1034` |
| A module already copied into every sandbox, needing only to be named | `main.py:77`, `main.py:507`, `main.py:510` |
| A documented, ranked instance of this exact defect class | `product.md` §6.1; `structure.md` §5.3 |
| A pinned constraint with a re-checkable line range | `SPEC-KEYCHAIN-001` N2 (`spec.md:840`); resolved at `1d5fff1` |
| A model pinned by compose, so "which model" is not ambiguous | `docker-compose.yml:46`, `:78` — `llama3.1:8b` |
| A `tools.py` that is gated and tested, so T5 lands in a covered module | `structure.md:234` |
| Live CI asserting `skipped == 0` and a pass floor | `.github/workflows/ci.yml:316` (`MIN_PASSED = 544`) |
| An established discipline for naming what was not run | `SPEC-KEYCHAIN-001` HISTORY; `SPEC-CI-001/verification-T3.md` header |

| Absent, and this SPEC must supply it | Evidence |
|---|---|
| Any instrument that can observe a prompt's effect | none exists in the repository |
| Any baseline for current routing behaviour | the reported refusal is an anecdote, `n=1` |
| A reachable Ollama on the authoring host | measured 2026-08-08 — see §2 |

**Two things to be clear-eyed about before starting.**

**The riskiest change in this SPEC is the one that looks safest.** Repairing `main.py:128-129`
narrows DIRECT. Narrowing DIRECT is exactly what the reported defect needs and it is also how this
product becomes one that generates and executes Python to answer "what do you think of Python".
There is no test that would catch that, there is no user-visible error when it happens, and the
cost lands on **every** turn rather than on turns using a new feature. That is R2, and T6 exists for
it alone.

**The SPEC can be wrong in a way that no amount of care in the diff would prevent.** If
`llama3.1:8b` refuses account access from its own safety training, every word of D1 and D2 is
irrelevant to the reported defect — though the `tools.py` half still stands on its own. T3 is a
gate, placed before T4, precisely so that this is discovered by measurement rather than by shipping.

---

## 1. Preconditions

**Ollama is not reachable from the authoring host.** Measured 2026-08-08: `command -v ollama` fails;
there is no binary at `/usr/local/bin/ollama` or `/opt/homebrew/bin/ollama`; `localhost:11434`
returns `http_code=000`.

This is recorded as a **precondition of T1**, not as something for the implementer to discover.
Before T1 begins, one of the following must be true and must be stated in `verification-T3.md` §1:

- the compose `ollama` sidecar is up and serving `llama3.1:8b` (`docker-compose.yml:46`, `:78`),
  and the probe reaches it at `http://ollama:11434` from inside the compose network; **or**
- an Ollama serving `llama3.1:8b` is reachable on the host and the probe points at it, in which case
  the tag, digest and host are recorded, because a differently quantised `llama3.1:8b` is a
  different model for this purpose (S4).

**Anything else is not a valid probe run.** A result against a substitute model is a result about
that model; it may be recorded, clearly labelled, but it does not discharge the gate.

---

## 2. Task decomposition

Nine tasks. T1–T3 are the critical path and T3 is a gate.

| # | Task | Artefact | Depends on |
|---|---|---|---|
| **T1** | **Build the probe harness.** Drives one prompt variant against one task prompt, N times, against `llama3.1:8b`, and records per trial: the variant, the task, the verbatim reply (O3), and the classification. **Classify by the production predicate** — a trial is DIRECT iff `extract_last_python_block()` (`main.py:447`) returns falsy, which is the branch at `main.py:1032` that produced the reported behaviour (E6). Import the real function; do not reimplement the regex, or the probe can pass while the product fails. Carries the **control set** from the outset (D5) — it is not bolted on at T6. Committed and re-runnable (O1); `SPEC-ACCOUNT-001` A1 uses the same harness. | probe harness; `verification-T3.md` §1 | §1 preconditions |
| **T2** | **Measure the baseline, V0.** Current `SYSTEM_PROMPT`, unmodified. Target task = the reported Gmail request verbatim. Plus the off-example network task, the tool-reachable task, and the control set. N ≥ 10 per cell. **This is the task that turns the anecdote into a number**, and it must run before any prompt text is written — a baseline taken after an edit is not a baseline. Record verbatim into `verification-T3.md` §2. | `verification-T3.md` §2 | T1 |
| **T3** | **Measure V1 and V2, and decide the gate.** V1 = routing contradiction repaired (D1). V2 = V1 + capability section naming `tools.py` (D2, D3). Same task set, same N, same harness. Record into `verification-T3.md` §3 and the outcome into §5. **GATE (S1):** if V2's Target refusal rate is not materially better than V0's, the outcome is **M-b** — stop, do not start T4's routing half, open `SPEC-MODEL-001`. If the model complies but the emitted code does not work, the outcome is **M-c** — T4 still proceeds, and `SPEC-ACCOUNT-001` A1 inherits a known-narrowed question. Classify against **M-a / M-b / M-c**, never as pass/fail: a binary gate reports M-c as success and hands `SPEC-ACCOUNT-001` a false premise. | `verification-T3.md` §3, §5 | T2 |
| **T4** | **Amend `SYSTEM_PROMPT`.** Apply the variant T3 selected. Two edits: repair `main.py:126-129` so DIRECT means *"no computation and no fetch would answer this"* rather than *"you personally lack this data"* (D1); add the capability section **below `main.py:166`** (N3) naming the library set, network egress and `from tools import web_search`, **each with a worked example** (U3, N4). Do **not** touch the `@param` passage (N2). Do **not** mention `os.environ` or the keychain (N1, N2). **Re-cite `SPEC-KEYCHAIN-001` N2's line range in this same commit** (E4) — §6.4 and the §9 traceability row — because the citation is already 18 lines stale and a third generation makes `spec.md` §2.3's verification method unreproducible. | `main.py`; `SPEC-KEYCHAIN-001/spec.md` | **T3 gate** |
| **T5** | **`tools.py`: make instant-answer failure visible — and land this before T4 if the tasks are separated in time.** `tools.py:90-91` is `except Exception: pass`, so a DuckDuckGo markup change yields zero hits rather than an error and is indistinguishable from an outage (`tech.md` §8.7). Today that is theoretical because `tools.py` is dead code; T4 makes it live. **Do not touch `_HTML_RESULT_RE`** (N6) — the regex→`bs4` rewrite reverses the module's stdlib-only contract (`tools.py:6`, `tools.py:82`, rationale `main.py:510`) and is out of scope with its reason recorded. This task is the written form of S3's fix-or-accept: it fixes the invisible half and accepts the regex half in writing. | `tools.py`, `tests/` | — |
| **T6** | **Regression: re-run the control set against the shipped prompt.** Not a checklist line, a task with its own criterion (**AC-CONTROL**). Assert the DIRECT rate for conversational, opinion and general-knowledge prompts is no worse than V0's. **This is the only defence that exists against R2**, and R2's blast radius is every turn of every session rather than the users of a new feature. Record into `verification-T3.md` §4. | `verification-T3.md` §4 | T4 |
| **T7** | **Source-level assertions** — the ones that hold with no model in the loop and therefore run in CI. The `@param` passage is present and unaltered; `SYSTEM_PROMPT` contains `web_search`; `SYSTEM_PROMPT` contains no occurrence of `os.environ` or `keychain`. These are what stop a later edit silently breaching N1/N2, and they are cheap. Add tests for the T5 error path in the same file set. | `tests/` | T4, T5 |
| **T8** | **Raise the CI pass floor.** `MIN_PASSED = 544` at `.github/workflows/ci.yml:316` → the count **measured** from a real `junitxml` run, never computed from an expected delta (E5). `SPEC-KEYCHAIN-001`'s HISTORY records raising it 469 → 541 from a real run and says so explicitly; the same method here. | `.github/workflows/ci.yml` | T7 |
| **T9** | **Documentation, including the citation corrections.** `product.md` §6.1 → **RESOLVED**, in the style §6.2 already established, **quoting the measured rate at which the model reaches `web_search`** rather than asserting closure from the presence of a name in a string (N8); correct its `main.py:100-151` → `main.py:122-182`. `structure.md` §5.3 → resolved; correct `main.py:210-211` → `main.py:507`. `tech.md` §8.7 → what was fixed and what was not; correct `tools.py:91-92` → `:90-91` and `tools.py:95-96` → `:94-95`. | `product.md`, `structure.md`, `tech.md` | T3, T6 |

**Critical path:** §1 preconditions → T1 → T2 → **T3 (gate)** → T4 → T6 → T7 → T8 → T9.
T5 is independent of the gate and may land first; it **must** land no later than T4.

---

## 3. Risks

| R | Risk | P | Impact | Mitigation |
|---|---|---|---|---|
| **R1** | **M-b — the model refuses regardless of prompt.** Safety training, not routing | Med | Total to the account-access motivation; the `tools.py` half survives | T3 gate before T4. `SPEC-MODEL-001` contingency. The gate is placed before wording effort precisely so this costs a measurement rather than a SPEC |
| **R2** | **A prompt change is global, and there is no regression net.** `main.py` has zero tests (`structure.md:56`). Narrowing DIRECT (D1) or advertising capability (D2) can over-trigger CODE on conversational turns. Every such turn costs a generation, a subprocess and a second round-trip — **on all traffic, not on users of a feature** | **Med** | **High, and silent** — there is no error, no log line, and no test. It presents as "the product got slower" | Control set is in T1 **from the start**, not appended at T6. T6 is a task with **AC-CONTROL** as its own criterion. S2 makes the pre-change rate the bar. This is the risk this SPEC is most likely to be judged on later and it is the one easiest to let become an aspiration |
| **R3** | **M-c — complies but writes code that does not work.** A binary gate reports this as success | Med | High — hands `SPEC-ACCOUNT-001` a false premise | T3 classifies against three outcomes, not two (`spec.md` §3.4). M-c is a first-class recorded result |
| **R4** | **Advertising `tools.py` promotes known-fragile code from dead to live.** §6.1 and §8.7 are the same module: one says it is unreachable, the other says it is broken | High | Med — a markup change yields zero hits and reads as an outage | T5 before T4. S3 forces fix-or-accept in writing. The regex stays, with its reason (N6) |
| **R5** | **N2 citation drift, third generation.** The range is already +18 lines. Inserting above the `@param` passage moves it again and breaks `spec.md` §2.3's `git show 1d5fff1` check | High | Low individually, corrosive cumulatively — it converts evidence back into assertion | N3 (insert below `main.py:166`) + E4 (re-cite same commit). Costs one line of diff |
| **R6** | **Prompt token cost is paid on every turn forever.** The prompt grows to fix a subset of traffic | High | Low–Med, and currently **unquantified** | Keep additions terse, in the existing register. O4 offers to measure it into `verification-T3.md` |
| **R7** | **The probe reimplements the classifier and diverges from production.** A probe with its own regex can pass while `main.py:1032` still fails | Low | High — the measurement becomes fiction | E6: import `extract_last_python_block` from `main.py`. Named in T1 |
| **R8** | **A run against the wrong model is recorded as if it discharged the gate.** `llama3.1:8b` exists at several quantisations; the authoring host has no Ollama at all | Med | High | §1 preconditions; S4. Tag, digest and host recorded in `verification-T3.md` §1 |
| **R9** | **`MIN_PASSED` raised from an expected delta rather than a run** | Med | Low, but it makes the floor a fiction | E5, T8. The method `SPEC-KEYCHAIN-001` used, stated again |
| **R10** | **§6.1 declared resolved because the prompt now contains the string `web_search`** | Med | Med — closes the repository's top-ranked finding on no evidence | N8: closure requires a **measured** rate at which the model reaches the helper. T9 depends on T3 and T6 for that reason |

---

## 4. Definition of done

Ten items. Each is a thing observed, not a thing believed.

1. Every acceptance criterion in `acceptance.md` has been **observed** passing, not reasoned to
   pass.
2. `verification-T3.md` §1 states the model tag, digest and host the probe ran against, and §2–§4
   contain figures produced by runs — with N per cell — and no figure that a run did not produce
   (U6, N7).
3. **The gate outcome in `verification-T3.md` §5 is recorded as M-a, M-b or M-c**, with the numbers
   that support the classification. Not "passed".
4. `git show 1d5fff1:main.py | sed -n '140,148p'` still prints the `@param` passage, and
   `SPEC-KEYCHAIN-001` §6.4 N2 and its §9 row cite the passage's **post-change** range, changed in
   the same commit as `main.py` (E4, AC-N2).
5. The control-set rate in `verification-T3.md` §4 is no worse than V0's (S2, AC-CONTROL). If it is
   worse, that is a finding to be recorded and resolved, not rounded away.
6. `tools.py`'s instant-answer failure is distinguishable from an empty result set, with a test that
   was observed red before it was green (AC-VISIBLE).
7. `MIN_PASSED` at `.github/workflows/ci.yml:316` was raised to a number read out of a real
   `junitxml` run and the run is identified (E5, AC-FLOOR).
8. `product.md` §6.1's resolution quotes a **measured** rate, not the presence of a string (N8).
9. All four citation corrections landed: `product.md` §6.1 `main.py:100-151` → `:122-182`;
   `structure.md` §5.3 `main.py:210-211` → `:507`; `tech.md` §8.7 `tools.py:91-92` → `:90-91` and
   `:95-96` → `:94-95`.
10. **Anything not run is named as not run and not as not needed**, in the SPEC's HISTORY, in the
    discipline `SPEC-KEYCHAIN-001` established. In particular: if the control set was measured at
    fewer trials than the target set, say so and say how many.
