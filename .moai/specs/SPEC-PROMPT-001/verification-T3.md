# SPEC-PROMPT-001 — T3 measurement record

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. Acceptance criteria are in
> `acceptance.md`.

---

## STATUS: GATE DECIDED (M-b, UNCHANGED) — §1, §2, §3.1 and §3.6's Target cell complete; §3.2–§3.4, §3.6's two OWED cells and §4 NOT RUN

**Created 2026-08-08 (v1.0.0) with its structure in place and every result cell empty. Amended
2026-08-08 (v1.1.0) to write the gate rule and the trial counts into §1.1 and §1.2 BEFORE T2 ran.**
The V0 Target cell was then run on 2026-08-09; the remaining seven V0 cells on 2026-08-09/10,
completing the baseline at **220 trials**; V1 and V2 Target on 2026-08-10; **V3 Target on
2026-08-12**. **Total: 310 records across four arms.**

**THE GATE IS DECIDED AND THE OUTCOME IS M-b** (§5). `r2 = 7/30 = 23.3 %` against `r0 = 17/30 =
56.7 %`. The absolute clause required `(r0 − r2) ≥ 0.40` and it measured **0.3333**; V2 needed
`k2 ≤ 5` DIRECT trials in 30 and recorded **7**. Fisher rejects (`p = 0.008428`) and **that does not
matter**, because §1.1 requires both clauses. **`plan.md` T4's routing half does not proceed.**

> **V3 HAS NOW RUN AT THE TARGET CELL AND IT DOES NOT TOUCH THE VERDICT. IT OVERTURNS §3.1's
> INTERPRETATION.** `r3 = 12/30 = 40.0 %`, 95% Wilson **[24.6 %, 57.7 %]** — worse than V2 on the
> gated quantity, and clearing **neither** clause of §1.1 (`r0 − r3 = 0.1667`; Fisher
> `p = 0.150734`). **§5's outcome is unchanged and was not revisited.** What changed is §3.1's
> attribution: it concluded that the routing repair does nothing and the capability advertisement
> does everything, and **that conclusion is wrong** — see **§3.6**, which supersedes it and states
> the reason (two arms cannot separate a main effect from an interaction; V3 is the cell that
> completes the 2 × 2 and bears on it).

> **THE ORDERING IS NOT CORROBORATED BY GIT, AND IT NEVER CAN BE. READ §1.0 BEFORE READING THE
> GATE.** An earlier draft of this header claimed §1.1 and §1.2 "were committed while §2 was still
> empty". **That was false.** Nothing was committed. See §1.0 for the full disclosure and for what
> evidence does and does not exist.

| Section | State |
|---|---|
| §1.1 decision rule, §1.2 trial counts | **Written before T2 ran — but see §1.0: not git-corroborated** |
| §1.3 provenance | **RUN** — read back from the server, for all four arms; re-verified over all 310 records 2026-08-12 |
| §2.1 V0 Target, N=30 | **RUN** |
| §2.2 V0 off-example (N=20), §2.3 V0 tool-reachable (N=20), §2.4 V0 control set (5 × N=30) | **RUN** — the baseline is complete at 220 trials |
| §2.5 findings F1, F2, F3 from the completed baseline | **RUN** |
| §3.1 V1 and V2 Target, N=30 each | **RUN** |
| §3.2 off-example, §3.3 tool-reachable, §3.4 control set — under V1/V2 | **NOT RUN** |
| §3.5 code correctness | **NOT ASSESSED** — explicitly, on any of the **65** CODE trials in all four arms; the M-a/M-c split is deferred |
| §3.6 V3 — **Target cell, N=30** | **RUN 2026-08-12** — not a cell AC-GATE item 7 asked for, and the one that turned out to matter |
| §3.6 V3 — **tool-reachable (N=20) and control set (5 × N=30)** | **NOT RUN — STILL OWED.** These are the two cells AC-GATE item 7 actually names, and neither exists |
| §4 post-change regression | **NOT RUN, and not yet owed** — nothing has shipped |
| §5 gate outcome | **DECIDED: M-b — unchanged by V3, and not revisited** |

**What is still missing, named as not run rather than as not needed.** §3.2, §3.3 and §3.4 would
say *where* V2's effect came from and whether it cost anything on the control set; none of them can
change §5, because §1.1 decides the gate on the Target cell alone.

**§3.6 is now partly run, and the part that ran is not the part that was owed.** AC-GATE item 7
requires V3 at the **tool-reachable cell (N=20)** and across the **full control set (5 × N=30)**,
before any prompt text merges (S6). What was run instead is V3 at the **Target cell (N=30)**, which
item 7 does not ask for at all. That run is the most informative cell in the experiment — it is what
falsifies §3.1's attribution — and it **discharges neither of item 7's two obligations**. **R2's only
remaining defence is still unmeasured, and nothing may merge.**

**There are no placeholder figures in this document and there must never be** (`spec.md` N7). Every
unrun cell reads `—` and every unrun section carries its own not-run marker. A plausible-looking
number written here as an illustration would, on the second reading by the second person, be
indistinguishable from data. That is not a hypothetical failure mode: `SPEC-KEYCHAIN-001`'s HISTORY
records a launcher check that *"had been inspecting nothing, and would have passed against the one
form the SPEC forbids"* — a test that looked like evidence and was not.

### The precondition, and the correction to what v1.0.0 said about it

~~**`spec.md` §HISTORY records why this file is empty rather than merely unwritten.** Ollama is not
reachable from the host this SPEC was authored on. Measured 2026-08-08:~~

```
$ command -v ollama
(no output, rc 1)
$ ls /usr/local/bin/ollama /opt/homebrew/bin/ollama
ls: /usr/local/bin/ollama: No such file or directory
ls: /opt/homebrew/bin/ollama: No such file or directory
$ curl -s -m 3 -o /dev/null -w "http_code=%{http_code}\n" http://localhost:11434/api/tags
http_code=000
```

**SUPERSEDED at v1.1.0 — `spec.md` HISTORY A1.** *Every line of that transcript is still true today
and none of it means what v1.0.0 concluded.* There is no host `ollama`, and there is not supposed to
be: the model runs in the compose `ollama` sidecar. `localhost:11434` answers `000` because
**`docker-compose.yml:28` publishes no host port for that service, deliberately** — the line reads
*"Kept internal to the compose network — no host port exposure needed."* and the service declares no
`ports:` key at all. **v1.0.0 read a healthy system as a broken one**, and recorded the probe as
blocked when it was merely unreachable from a namespace nothing needed to reach it from.

Re-verified 2026-08-08, and this is what actually holds:

```
$ docker ps --format '{{.Names}}\t{{.Status}}\t{{.Image}}'
coderunner              Up 17 minutes               coderunner-ai:latest
coderunner-ollama       Up 17 minutes (healthy)     ollama/ollama:latest

$ docker exec coderunner-ollama ollama list
NAME                       ID              SIZE      MODIFIED
nomic-embed-text:latest    0a109f422b47    274 MB    4 days ago
llama3.1:8b                46e0c10c039e    4.9 GB    5 days ago
```

The probe therefore runs **inside the compose network**, reaching `http://ollama:11434` — which is
what `docker-compose.yml:77` already sets `OLLAMA_HOST` to for the `coderunner` service.

~~**Until §3 is filled, `plan.md` T4 has not been authorised to start** (`spec.md` S5).~~

**SUPERSEDED 2026-08-10 — §3.1 is filled and §5 records M-b.** `plan.md` **T4's routing half is not
authorised and will not become authorised**; the gate has been taken and it did not clear. What
remains open to T4 is the `tools.py` advertisement half, and S6 requires V3 (§3.6) to be measured
before any of it merges.

---

## 1. Provenance and the decision rule

### 1.0 A limitation of this record, disclosed before the rule it limits

**The claim this section replaces was false, and it was false in the one direction that flatters the
measurement.** Two places in this document — the STATUS header and the opening of §1.1 — stated that
§1.1 and §1.2 **"were committed"** before T2 ran. **Nothing was committed.** Verified 2026-08-09:

```
$ git show HEAD:.moai/specs/SPEC-PROMPT-001/verification-T3.md \
    | grep -cE 'r0|Fisher|0\.40|alpha|pre-regist'
0
$ git status --porcelain .moai/specs/SPEC-PROMPT-001/
 M .moai/specs/SPEC-PROMPT-001/acceptance.md
 M .moai/specs/SPEC-PROMPT-001/plan.md
 M .moai/specs/SPEC-PROMPT-001/spec.md
 M .moai/specs/SPEC-PROMPT-001/verification-T3.md
```

The committed v1.0.0 of this file has **no §1.1 and no §1.2 at all**; its gate was the superseded
*"refusal rate"* / `N ≥ 10` formulation that A4 and A5 replaced. The rule and the results it gates
therefore sit in **one uncommitted working tree**, and in git they are **indistinguishable from
having been written in a single pass after the numbers landed**.

**This limitation is permanent and no later commit can repair it.** Committing now produces one
commit containing both the rule and the data, which is exactly the artefact that would exist had the
rule been fitted to the data. `acceptance.md` AC-GATE item 5 originally required the ordering to be
*"checkable in `git log`"*; **it is not, it cannot become so for this SPEC, and that criterion has
been amended rather than quietly marked satisfied** — see `acceptance.md` AC-GATE item 5 and its
stated reason.

**What evidence does exist, offered as evidence and not as reassurance:**

| # | Evidence | Weight |
|---|---|---|
| 1 | **§1.1 and §1.2 reference no observed value.** The rule is written entirely in terms of `r0` and `r2` as unknowns; no figure from §2.1 appears in it, and no clause is shaped around 17/30 | Consistent with pre-registration; also consistent with careful post-hoc writing. **Weak** |
| 2 | **The threshold is non-trivial in both directions.** At `r0 = 17/30 = 0.567` the rule demands `r2 ≤ 5/30` — V2 must more than triple its compliance rate. A rule fitted to flatter the SPEC would not have set a bar this high; a rule fitted to be unreachable would not have left it attainable | **Moderate.** It is hard to fit this number to a preferred outcome when the outcome is still unmeasured |
| 3 | **The rule is non-degenerate, verified by computation** (independently re-derived 2026-08-09, `math.comb`, no library): across every `r2` satisfying the absolute clause (`k = 0…5` DIRECT in 30), the one-sided Fisher exact `p` runs from `<10⁻⁶` to **`0.00139`** — always far below `alpha = 0.05`. **The 0.40 absolute clause strictly dominates Fisher: Fisher never binds.** Meanwhile `k = 6…9` would clear Fisher (`p = 0.0036…0.034`) and are rejected by the absolute clause. So the rule is neither vacuous nor unsatisfiable, and its binding constraint is the one stated in plain numbers | **Moderate.** A degenerate rule is the usual signature of one written to fit; this one is not degenerate |
| 4 | `spec.md` §4 carries the identical rule and **never made the commit claim** — its wording has always been the accurate *"written into `verification-T3.md` §1 before T2 runs"* | Shows the overclaim was local to this file, not a consistent position |

**None of items 1–4 is a substitute for the git ordering, and this table does not claim otherwise.**
A reader who declines to credit the pre-registration on this evidence is reading correctly. The
honest summary is: **the rule was written before the run, and you have only this document's word for
it.**

### 1.1 The decision rule — written before T2 ran

**Written into this file before T2 executed a single trial** (`spec.md` HISTORY A4, `acceptance.md`
AC-GATE item 2a). **§1.0 records that this ordering is not corroborated by git and never can be.**
The rule is reproduced in `spec.md` §4 and the two must agree textually.

**Primary endpoint: the DIRECT rate on the Target cell, at N = 30 per arm.**

A trial is DIRECT iff `extract_last_python_block()` (`main.py:447`) returns falsy — the identical
predicate to the production branch at `main.py:1032` that produced the reported behaviour (E6).
Write `r0` for V0's Target DIRECT rate and `r2` for V2's.

> **Proceed (M-a or M-c) if and only if:**
>
> **`(r0 − r2) ≥ 0.40` absolute**  **AND**  **a one-sided Fisher exact test rejects at
> `alpha = 0.05`.**
>
> **Otherwise the outcome is M-b.**

Four properties of this rule, each of which is why a clause is in it:

| Property | Why |
|---|---|
| **The endpoint is machine-decided** | v1.0.0 gated on *"refusal rate"* while E6 defined only the DIRECT rate. **They are different quantities.** A refusal is a human-coded **subset** of DIRECT: a turn that routes DIRECT because the model chatted is not a refusal, and a reply carrying two fenced blocks classifies DIRECT (`findall()` → `['']`, falsy) while refusing nothing whatever. A gate with a human-coded endpoint is settled by argument after the numbers land |
| **It is pre-registered** | A threshold chosen once the numbers are visible is not a gate. This SPEC has a stated preference for M-a, and that preference would have done the choosing |
| **It is decided on ONE cell** | The Target cell alone. **No other cell may rescue an M-b** — not the off-example task, not the tool-reachable task, not a favourable control. Consequently **no multiplicity correction is applied and none is needed**, because no second test is permitted to bear on the decision |
| **Both clauses are required** | The absolute threshold alone lets a large-but-noisy difference through. Significance alone lets a 12pp difference through at N=30 and calls it a repair |

**Refusal rate is retained as a SECONDARY, human-coded overlay** — O3 supplies the verbatim replies
— **which is reported and decides nothing.** It distinguishes a model that declined from a model
that chatted, which matters to `SPEC-MODEL-001`. It does not matter to this gate.

**Every trial record carries `len(CODE_BLOCK_RE.findall(reply))`** (E7), so a two-fence reply is
distinguishable after the fact from a genuine refusal.

### 1.2 Trials per cell — fixed before the run

| Cell | N per arm | Why this N |
|---|---|---|
| **Target** | **30** | The gated cell. At N=10 per arm a two-proportion test has usable power only against a swing of roughly **50 percentage points** — so v1.0.0's `N ≥ 10` could have returned "no difference" for a repair that moved routing by 40pp, recording M-b on a measurement structurally unable to see M-a |
| **Off-example network** | **20** | Diagnostic, not gated. It separates a routing effect from an account-shaped one and needs to resolve a large difference, not a small one |
| **Tool-reachable** | **20** | Diagnostic. Its V0 expectation is **zero** (§2.3), and distinguishing zero from small does not need 30 |
| **Control**, per prompt | **30** | Its question is **non-inferiority**. By the rule of three, 0 failures in 10 trials bounds the true regression rate only at **30%**; 0 in 30 bounds it at **10%**. A control that cannot exclude a 30% regression is not a defence against R2 |

**If budget forces a cut, cut the NUMBER of control prompts — floor 3, one of each kind — and never
cut N below 20.** Three prompts at N=30 is a measurement; five at N=6 is a rumour.

### 1.3 Provenance — read back from the running server, never from configuration

**`docker-compose.yml:46` and `:78` are `${CODERUNNER_MODEL:-llama3.1:8b}` — a DEFAULT, not a pin.**
`main.py:71` reads the same variable. The file states an intention; only the running server states a
fact. Every row below is filled from `client.list()`, `client.show()` and the observed environment at
run time (S4).

**RUN.** Every value below was read back from the running server or from the trial records
themselves. Nothing here is copied from `docker-compose.yml`.

| | Value |
|---|---|
| Date of run — V0 Target | **2026-08-09, 05:11:11 → 05:38:59 UTC** (first and last trial timestamps) |
| Date of run — rest of the V0 baseline | **2026-08-09 21:19:56 → 2026-08-10 02:06:13 UTC**. Cell windows: off-example 21:19:56→21:27:34, tool-reachable 21:28:18→21:47:05, C1 21:47:20→21:51:23, C2 21:51:59→02:04:10 *(interrupted and resumed — see the note below)*, C3 01:13:15→01:22:42, C4 01:23:29→01:34:16, C5 01:34:30→02:06:13 |
| Date of run — V1 Target | **2026-08-10, 14:57:59 → 15:17:15 UTC**, 18.9 min of trial time |
| Date of run — V2 Target | **2026-08-10, 15:20:41 → 16:10:58 UTC**, 44.2 min of trial time |
| Date of run — V3 Target | **2026-08-12, 00:35:16 → 00:56:29 UTC**, 19.9 min of trial time |
| Model tag | **`llama3.1:8b`** *(from `client.list()`, **not** from compose)* |
| Model digest | **`46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`** |
| Parameter size | **8.0B** |
| Quantisation | **Q4_K_M** |
| Family / format | **llama / gguf** |
| Reached via | **compose `ollama` sidecar, observed `OLLAMA_HOST` = `http://ollama:11434`** |
| Ollama server version | **0.32.1** *(from `GET /api/version`)* |
| Ollama Python client version | **0.6.2** |
| Temperature / sampling | **Nothing is pinned, at either end.** The harness sets no `options=`, no temperature and no seed (N10) — it drives `main.stream_llm()` (`main.py:209-221`), which passes none, so production sampling is inherited **by construction**. The modelfile pins none either: `client.show()` reports a `parameters` block containing **only three stop sequences** — `stop "<\|start_header_id\|>"`, `stop "<\|end_header_id\|>"`, `stop "<\|eot_id\|>"`. No `temperature`, `top_p`, `top_k` or `seed` appears. The server default therefore applies, and **the stochasticity in §2.1 is production's own** |
| Harness commit | **Three values, and the differences are bookkeeping rather than drift.** V0 Target carries **`0ef5c869cbc7a3219eac0d33b7c14987f1d02450`**; **250 records** — the rest of the V0 baseline, all of V1 and all of V2 — carry **`510f468ad09bfb840c06d9f5f0096faa656ae985`**; **V3's 30** carry **`e99fb3cc6b951e8e127f5a83b30145389a6f6a94`**, because HEAD advanced again between the V2 and V3 sessions. `probe/` was uncommitted at every run |
| `main.py` commit the classifier was imported from | As above — HEAD, and **HEAD does not know whether the tree is dirty**, which is exactly why the row below exists |
| `main.py` sha256 — the anchor that HEAD cannot provide | **`ff5a488fec10b3fd47e69c165154eb4f72aeb3cc9acb5cdd510129a83f4d6421`**, identical across **all 310 records** — every V0 cell, every V1 trial, every V2 trial and every V3 trial — **and re-computed against the working-tree `main.py` on 2026-08-12, where it still matches byte for byte.** **`main.py` was unmodified throughout, across the baseline and all three variant arms.** That is what makes V0 a baseline and what discharges `acceptance.md` AC-GATE items 5 and 5a: the variant arms were driven by *strings built in the harness*, never by an edited product |
| Python | **3.11.15** *(probe image; the host `.venv` running the re-derivation is 3.11.14)* |
| Trials per cell (N) | **Every cell was run at the `spec.md` §4 / §1.2 N, with no shortfall anywhere.** V0: Target 30, off-example 20, tool-reachable 20, controls 5 × 30 = **220**. V1 Target 30, V2 Target 30, V3 Target 30. **Total 310 trials.** Every file carries trial indices `0…N−1` exactly once — checked by computation on all eleven files. No control prompt was dropped and no N was cut (AC-GATE item 6) |
| Host | macOS/arm64, Docker Desktop, **CPU-only** (Docker Desktop passes no Metal through to a Linux container). Per-trial wall clock over the 220-trial baseline: **1.5 s min / 19.1 s median / 153.4 s max**, 1.76 h of trial time. V1: 1.9 / 11.7 / 125.7 s. V2: 4.2 / 70.9 / 206.4 s. V3: 2.2 / 50.5 / 99.4 s — and V3 splits the same way V2 does, **DIRECT 2.2–19.6 s against CODE 34.6–99.4 s**, for the reason given in note 2 below |

**Every provenance field that matters is constant across all 310 records** — one model tag
(`llama3.1:8b`), one digest, one quantisation, one host (`http://ollama:11434`), one Ollama server
version, one `main.py` hash. That was checked by computation over the JSONL rather than assumed. The
only field that varies is `harness_commit`, for the stated and harmless reason above.

**The stored classifications were re-derived from the stored reply text across all 310 records on
2026-08-12**, by importing `main.extract_last_python_block` and `main.CODE_BLOCK_RE` and running
them over `reply`: **310 re-classified, 0 disagreements on `classification` and 0 on
`fence_matches`.** The V3 arm therefore rests on the production predicate as it stands today, on the
same footing §2 already established for the baseline.

**Two operational notes, recorded because they affect how the numbers should be read and not
because they change any of them.**

1. **The C2 cell was interrupted and resumed**, which is why its window spans four hours while its
   trial time is 13.6 minutes. Resumption is keyed on `(variant, task, trial_index)`, and the C2
   file was checked afterwards: indices **0–29 exactly once each**, no gaps and no duplicates. The
   same check passed on all ten cells.
2. **V2's per-trial wall clock is not comparable to V0's and must not be read as a slowdown in the
   product.** V2 routes CODE far more often, and a CODE reply is a whole generated program where a
   DIRECT reply is two sentences — V2's DIRECT trials ran 4–10 s and its CODE trials 25–206 s. Part
   of the spread is also the measurement rig: four orphaned probe containers from interrupted chunks
   were left competing for the same CPU-only sidecar mid-run, and were killed once noticed. **This
   affects latency only.** It cannot affect a classification, which is a function of the reply text
   alone.

**S4 applies to this table.** A result obtained against any other model, quantisation or host is a
result *about that model*. It may be recorded here, clearly labelled, and it does **not** discharge
the gate.

---

## 2. Baseline — V0, `SYSTEM_PROMPT` unmodified

**COMPLETE. All eight cells are run: 220 trials.** §2.1 Target N=30, §2.2 off-example N=20, §2.3
tool-reachable N=20, §2.4 five control prompts at N=30 each.

This is `plan.md` T2. It must be taken **before** any prompt text is written. A baseline taken after
an edit is not a baseline; `main.py` was unmodified throughout, verified by the sha256 in §1.3 being
constant across all 220 records.

Its purpose is to convert the reported refusal from an anecdote at `n=1` into a rate. **It did more
than that, and §2.5 is where the three findings it produced are written down.**

**Every figure in §2 was re-derived from the raw JSONL by computation, on 2026-08-10, by a reader
who did not take the running notes on trust** (N7). The classification field stored in each record
was additionally **re-computed from the stored reply text** by importing
`main.extract_last_python_block` inside the image: **220 records re-classified, 0 disagreements on
`classification` and 0 on `fence_matches`**. So the tables below rest on the production predicate as
it stands today, not on a field written at run time and believed afterwards.

### 2.0 The whole baseline in one table

| Cell | N | CODE | DIRECT | DIRECT rate | 95% Wilson | Fence traps | Correctly routed |
|---|---|---|---|---|---|---|---|
| **Target** | 30 | 13 | **17** | **56.7 %** | [39.2 %, 72.6 %] | **0** | 13/30 |
| **Off-example network** | 20 | 10 | 10 | 50.0 % | [29.9 %, 70.1 %] | **0** | 10/20 |
| **Tool-reachable** | 20 | 20 | 0 | 0.0 % | [0.0 %, 16.1 %] | **0** | **20/20** |
| **C1** conversational | 30 | 0 | 30 | 100.0 % | [88.6 %, 100.0 %] | **0** | **30/30** |
| **C2** conversational | 30 | 10 | 20 | 66.7 % | [48.8 %, 80.8 %] | **0** | 20/30 |
| **C3** opinion | 30 | 4 | 26 | 86.7 % | [70.3 %, 94.7 %] | **0** | 26/30 |
| **C4** general knowledge | 30 | 30 | **0** | **0.0 %** | [0.0 %, 11.4 %] | **0** | **0/30** |
| **C5** general knowledge | 30 | 16 | 14 | 46.7 % | [30.2 %, 63.9 %] | **0** | 14/30 |
| **CONTROL POOLED** | **150** | 60 | **90** | **60.0 %** | **[52.0 %, 67.5 %]** | **0** | **90/150** |

*"Correctly routed" is evaluated against each task's own `expect_direct` field, which the harness
fixes at `probe/tasks.py` and writes into every record: the three measurement cells expect **CODE**,
the five control cells expect **DIRECT**. It is not a second opinion about what the right answer
was — it is the answer the task was defined with, carried in the data.*

**Zero fence traps in 220 trials.** Every DIRECT trial in the entire baseline had
`fence_matches == 0` ~~and every CODE trial had exactly `1`~~. The two-block contamination E7 exists
to detect did not occur anywhere, so no DIRECT rate in this document is inflated by a reply that
emitted a block and was counted as though it had not. **That is a measured result, not an
assumption**, and it was the first thing checked because it moves the gated quantity.

> **CORRECTION, 2026-08-12 — the struck clause above is false, found by re-deriving it rather than
> by reading it.** Recomputed over all **310** records: **`fence_matches == 2` occurs once**, at
> `v0-tool-reachable.jsonl` trial **#14**, and that trial is classified **CODE**. So "every CODE
> trial had exactly 1" was never true of the baseline.
>
> **What it does and does not affect, stated precisely because the two are easy to conflate.** It
> changes **no rate anywhere in this document.** The trial is correctly classified: its two blocks
> are a one-line comment followed by the real program, `findall()` returns both, and
> `extract_last_python_block()` takes the **last** — which is non-empty, hence CODE. The **trap** E7
> was written for is a DIRECT classification arising from `findall() → ['']`, and that remains
> **0 in 310** — every DIRECT trial in every cell of every arm has `fence_matches == 0`.
>
> **It is recorded because the sentence overstated what had been measured, in the direction that
> makes the instrument look cleaner than it is.** A two-block reply *did* occur; it simply did not
> misclassify. §2.3's cell counts (20 CODE, 0 DIRECT) and §3.1's identical sentence about the Target
> arms are both unaffected — across the **120** Target trials of all four arms, DIRECT-with-fences
> is **0** and CODE-with-`fence_matches != 1` is **0**, checked and not assumed.

### 2.1 Target task — the reported request, verbatim

Task prompt: `check my gmail for recent 7 days and let me know the interview opportunities`

**RUN — 2026-08-09, N=30, V0, `llama3.1:8b` Q4_K_M via the compose sidecar.**
Records: `.moai/specs/SPEC-PROMPT-001/probe-runs/v0-target.jsonl` (30 lines, trial indices 0–29
complete with no gaps).

| Metric | Value |
|---|---|
| Trials (N) | **30** |
| Routed CODE (a fenced block was produced) | **13** |
| Routed DIRECT (`extract_last_python_block()` falsy) | **17** |
| **DIRECT rate — `r0`, the gated quantity** | **56.7 %** (17/30) |
| 95% Wilson interval on the DIRECT rate | **[39.2 %, 72.6 %]** |
| Trials with `fence_matches > 0` **and** classified DIRECT (the two-block trap, E7) | **0** |
| DIRECT trials that were genuinely unfenced | **17 of 17** |
| Refusal rate *(secondary, human-coded overlay — decides nothing)* | **17/30 = 56.7 %**. Every one of the 17 DIRECT trials was read, and **every one is a refusal.** In this cell the secondary quantity happens to coincide exactly with the gated one |
| Distinct refusal phrasings observed | **17 of 17 open with a first-person declination** — *"I can't process that request"*, *"I can't provide direct access to your personal account"*, *"I cannot access your personal Gmail account"*, *"I'm not allowed to access your Gmail account"*, *"I can't assist with that request"*. **Closing offer of help: 8 of 17** under the stated rule below |

**The closing-phrase count, with its matching rule stated so it reproduces.** *Rule: whitespace-
normalise each DIRECT reply (`" ".join(reply.split())`), then test for the exact substring* `Is there
anything else I can help you with?` — **8 of 17**. Admitting the one-word variant *"something else"*
gives **9 of 17**; additionally admitting *"feel free to ask"* gives **11 of 17**. The three numbers
are reported together because the count depends entirely on which rule is chosen, and quoting one
without its rule is how an untraceable figure enters a document.

*An earlier draft of this row said "fourteen", which reconciles to none of these rules and was
traceable to no computation. It decided nothing — the row is marked as secondary — but by this
document's own N7 standard an unreproducible figure has no place in it regardless of what it
decides. Recorded rather than silently corrected.*

**The reported anecdote is now a rate, and it is not a rare event.** `r0 = 56.7 %`, and the 95%
Wilson interval excludes everything below 39%. The user's single observation was not bad luck: the
turn refuses more often than not.

**The classifier and the human coding agree exactly here, and that agreement is a fact about this
cell rather than a property of the design.** All 17 DIRECT trials are refusals and all 13 CODE
trials emitted a block; **zero** trials hit the two-fence trap. A4 kept the two quantities separate
precisely because they can diverge, and E7's counter is what proves they did not diverge this time
instead of assuming it.

### 2.1.1 The diagnosis, in the model's own words

**Two trials from this cell state the routing rule they applied, and they state opposite rules from
the same prompt.** This is `spec.md`'s central claim — three contradictory routing rules, resolved
by the model rather than by the prompt — arriving as verbatim evidence rather than as inference.

Trial **#8**, classified **DIRECT**:

> Since this task requires computation on data (your Gmail account) **which I don't have access
> to**, I'll follow the DIRECT protocol.
>
> **Answer:** I'm a code interpreter, not an email client or a service that can access your personal
> accounts. […]

Trial **#1**, classified **CODE**:

> Since this task requires computation on **live data provided by the user**, I will follow the CODE
> protocol. […] To accomplish this, we'll use the IMAP […] library to connect to the user's Gmail
> account and search for messages with keywords related to interviews. […]
>
>     import imaplib
>     import email
>
>     # @param email_password: str = "Your Gmail password"
>     # @param email_address: str = "Your Gmail address"

**Same prompt, same model, same turn shape, opposite resolutions — and #8 is quoting
`main.py:128-129`'s *"needs live data you don't have"* clause back as its justification.** That is
the clause D1 proposes to repair, named by the thing under measurement.

**Trial #1 also collapses part of the M-c question in advance.** When the model does take CODE it
reaches for `imaplib` **and** declares its inputs with `# @param … : str`, which is the grammar
`SPEC-KEYCHAIN-001` already sources from the host keychain. The shape the SPEC hoped for is
achievable by this model at this quantisation. **Whether that code actually works is still not
assessed** (§3.5) — reaching for `imaplib` is not the same as getting IMAP right, and a plaintext
`str` password where `secret` is the declared type for passwords (`main.py:165`) is already one
visible defect in it.

Verbatim replies for all 30 trials (O3) are in the JSONL named above.

### 2.2 Off-example network task

*A network-reachable task outside the three exampled domains at `main.py:146-153`, involving no
account and no credential. This cell isolates the routing repair from anything mail-shaped.*

Task prompt: `how many open issues does the cpython repository have on GitHub right now?`

**RUN — 2026-08-09, N=20, V0.** Records:
`.moai/specs/SPEC-PROMPT-001/probe-runs/v0-off-example.jsonl` (20 lines, indices 0–19, no gaps).

| Metric | Value |
|---|---|
| Trials (N) | **20** |
| Routed CODE | **10** |
| Routed DIRECT | **10** |
| DIRECT rate | **50.0 %** (10/20) |
| 95% Wilson on the DIRECT rate | **[29.9 %, 70.1 %]** |
| Fence traps | **0** |
| Correctly routed (`expect_direct = false`, so CODE is correct) | **10/20** |

**This cell involves no account, no credential and no mail.** It is a public, unauthenticated JSON
endpoint, and the prompt's own network permission at `main.py:143-145` covers it explicitly. It
still routes DIRECT half the time. **Whatever is happening at the Target cell is not exclusively
about Gmail**, which is the single most useful thing this cell had to say and the reason §2.5's F1
exists.

### 2.3 Tool-reachable task

*A task for which `web_search` is the natural instrument. This cell is `product.md` §6.1's actual
close condition (`spec.md` N8) — not the presence of a string in the prompt.*

Task prompt: `search the web and summarise the three main criticisms people have of the uv Python
package manager`

**RUN — 2026-08-09, N=20, V0.** Records:
`.moai/specs/SPEC-PROMPT-001/probe-runs/v0-tool-reachable.jsonl` (20 lines, indices 0–19, no gaps).

| Metric | Value |
|---|---|
| Trials (N) | **20** |
| Routed CODE | **20** |
| Routed DIRECT | **0** |
| DIRECT rate | **0.0 %** — 95% Wilson **[0.0 %, 16.1 %]** |
| Fence traps | **0** |
| Correctly routed | **20/20** |
| Emitted code that imports `tools` (`import tools` / `from tools`) | **0 / 20** |
| Emitted code that calls, or text that so much as mentions, `web_search` | **0 / 20** |
| The bare token `tools` anywhere in the reply | **0 / 20** |

**Expected at V0: zero. Measured at V0: zero, and the prediction is confirmed rather than assumed.**
`SYSTEM_PROMPT` contains no occurrence of `tools` or `web_search` (measured 2026-08-08, `spec.md`
§2.2), so the model had no channel through which to learn the name, and it did not invent one. The
same two probes were additionally run across **all 220 baseline records**: `0/220` and `0/220`.

**What the model reached for instead, which is the actual content of the finding** — see §2.5's F2.

### 2.4 Control set — must route DIRECT

*`spec.md` S2. `plan.md` R2. This is the only defence against the regression with the largest blast
radius in this SPEC, and it is measured at V0 so there is something to compare against.*

**RUN — 2026-08-09/10, all five prompts at N=30, V0. 150 trials, no prompt dropped and no N cut.**

| # | Control prompt | Kind | Trials (N) | Routed DIRECT | Rate | 95% Wilson | Traps |
|---|---|---|---|---|---|---|---|
| **C1** | `hey, how are you doing today?` | conversational | **30** | **30** | **100.0 %** | [88.6 %, 100.0 %] | 0 |
| **C2** | `what can you help me with?` | conversational | **30** | **20** | **66.7 %** | [48.8 %, 80.8 %] | 0 |
| **C3** | `what do you think of Python as a first programming language?` | opinion | **30** | **26** | **86.7 %** | [70.3 %, 94.7 %] | 0 |
| **C4** | `explain what a Python closure is, with a short example` | general knowledge | **30** | **0** | **0.0 %** | [0.0 %, 11.4 %] | 0 |
| **C5** | `who wrote the book "The Mythical Man-Month"?` | general knowledge | **30** | **14** | **46.7 %** | [30.2 %, 63.9 %] | 0 |
| | **POOLED** | | **150** | **90** | **60.0 %** | **[52.0 %, 67.5 %]** | **0** |

Records: `v0-c1-conversational.jsonl`, `v0-c2-conversational.jsonl`, `v0-c3-opinion.jsonl`,
`v0-c4-general-knowledge.jsonl`, `v0-c5-general-knowledge.jsonl` — 30 lines each, indices 0–29, no
gaps and no duplicates.

#### The control set does not behave the way a control set is assumed to behave

**Pooled control DIRECT is 60.0 %, not the ~100 % anyone would assume of prompts chosen precisely
because they must route DIRECT. Three of the five misroute at baseline** — C2 at 10/30, C4 at 30/30,
C5 at 16/30 — **and this is V0. Nothing has been changed. There is no prompt edit to blame.**

**This is the concrete justification for AC-CONTROL item 2's insistence on a before-measurement, and
it should be stated plainly rather than left as a lesson the reader might draw.** Suppose the control
set had been measured only *after* the prompt edit, which is the normal way this is done and the way
it would have been done here had T2 been cut for budget. The reading would have been:

> C2 regressed from 100 % to 67 %. C4 regressed from 100 % to 0 % — the product now writes and
> executes Python to answer "explain what a closure is". C5 regressed from 100 % to 47 %. **The
> routing repair caused a catastrophic regression across the control set and must be reverted.**

**Every clause of that paragraph would have been false**, and it would have been unfalsifiable,
because the only thing that could have contradicted it — the before-measurement — would not exist.
The SPEC would have blamed its own edit for behaviour that predates it, reverted a change on that
basis, and recorded a finding about a regression that never happened. `plan.md` R2 is the risk that
the edit makes the product eager; **what the baseline shows is that the product is already eager**,
and R2's real question is therefore *"did it get worse"* and never *"is it wrong now"*. Those are
different questions and only one of them is answerable without §2.4.

**What this costs the control set as an instrument, stated against its own interest.** A control at
60 % pooled has far less power to detect a small regression than one at 100 %: C2, C4 and C5 have
room to move in both directions and noise at N=30 is not small. **C1 remains a genuine floor** — 30/30
with a Wilson lower bound of 88.6 %, so a real regression there would be visible. **C4 has no
downward room at all**: it is already at 0 % and cannot regress, which means it is now useless as a
regression detector even though it is the most interesting prompt in the set. §4, when it is owed,
must compare rates rather than assert correctness, and must say this out loud.

**C4 was the sharpest prompt in the set and it is there on purpose.** It asks for *an example*, so
the model may well emit an illustrative fenced Python block — at which point the product does not
illustrate it, it **executes** it. That was written as a hypothesis before the run. **It is not a
hypothesis any more: C4 routed CODE 30 times out of 30.** See §2.5's F3, which records it as a
finding in its own right, because it is a live defect on `main` and it has nothing to do with this
SPEC.

---

## 2.5 Three findings from the completed baseline

*These are not commentary on the tables above. They are results the baseline produced that the SPEC
did not ask for, and two of the three are stronger evidence than the cell the SPEC was written
around. Each is stated with the computation that produced it.*

### F1 — The dose-response gradient: proximity to a worked example predicts correct routing

`SYSTEM_PROMPT:146-153` names three sites by way of example — **wttr.in**, the **Wikipedia REST
API**, and **DuckDuckGo HTML search**. Nothing in the prompt says these are the only permitted
targets; `:143-145` says the opposite, in general terms. Three measurement cells sit at three
distances from that example set, and they routed like this:

| Cell | What it asks for | Distance from the example set | N | Routed CODE | CODE rate | 95% Wilson on the CODE rate |
|---|---|---|---|---|---|---|
| **Tool-reachable** | a web search | **INSIDE it** — DuckDuckGo search is exampled verbatim at `:151-153` | 20 | **20** | **100.0 %** | [83.9 %, 100.0 %] |
| **Off-example network** | a live HTTP fetch of public JSON (GitHub API) | **OUTSIDE it, identical in kind** — no account, no credential, a public endpoint, exactly the sort of thing `:143-145` permits | 20 | **10** | **50.0 %** | [29.9 %, 70.1 %] |
| **Target** | a live fetch from Gmail | **FURTHEST OUT** — off-example *and* account-shaped | 30 | **13** | **43.3 %** | [27.4 %, 60.8 %] |

**One-sided Fisher exact, on the CODE rate, computed with `math.comb` and no library:**

| Comparison | p |
|---|---|
| Tool-reachable vs off-example | **0.000218** |
| Tool-reachable vs Target | **0.0000122** |
| Off-example vs Target | **0.431** — *not significant; these two are not distinguishable at these N* |

**What this establishes, and what it does not.** The gap between "inside the example set" and
"outside it" is large and significant. The gap between "outside it" and "outside it *and*
account-shaped" is **6.7 percentage points and indistinguishable from noise** — so the data support
a **two-level** effect (exampled vs not) more strongly than the smooth three-point gradient the
ordering suggests. **The monotone ordering is real; the claim that each step down is a separate
effect is not supported at N=20/20/30.** Stated that way because the ordered table invites the
stronger reading and the arithmetic does not license it.

**Why this is stronger evidence than the Target cell alone, which is the point.** `spec.md`'s central
claim is that the prompt's *effective* capability surface is its **example set** rather than its
**rules**. The Target cell on its own is consistent with that, and equally consistent with the model
simply refusing anything mail-shaped. The off-example cell is the one that separates them: **no
account, no credential, no mail, fully covered by the stated rule — and still 50 % DIRECT.** A rule
the model follows only when it has seen a worked instance of it is not functioning as a rule. That
is the diagnosis, measured, on a task with nothing to do with Gmail.

**And it is the finding that predicts §3.1's result.** If example proximity is what drives routing,
then a variant that *rewrites the rule* should do little and a variant that *adds worked examples*
should do the work. That is exactly what §3.1 measured, and F1 was written down before §3.1 was read.

### F2 — `tools.py` was reached for zero times in twenty, and this is `product.md` §6.1's rate

The tool-reachable cell is a task with **no canonical API**, where a general web search is the
natural instrument and `tools.py`'s `web_search()` is precisely the right tool. Over its 20 trials,
counted by regex over the verbatim replies:

| Probe | Count |
|---|---|
| `import tools` or `from tools` | **0 / 20** |
| the string `web_search`, anywhere in the reply, code or prose | **0 / 20** |
| the bare token `tools` | **0 / 20** |
| **DuckDuckGo, hand-rolled** | **19 / 20** |
| `requests` | **20 / 20** |
| BeautifulSoup / `bs4` | **20 / 20** |
| Wikipedia | 0 / 20 |
| wttr.in | 0 / 20 |

Across **all 220 baseline records**: `import tools`/`from tools` **0/220**, `web_search` **0/220**.

**`product.md` §6.1 calls `tools.py` "effectively dead code". This is the rate, and it is 0 %.** The
module is copied into every sandbox by `run_python()` on every single execution, and the model has
never been told it exists. In **19 of 20** trials it hand-rolled DuckDuckGo scraping instead —
fetching `duckduckgo.com/html/?q=`, parsing with BeautifulSoup, pulling `a.result__a` — which is not
a coincidence and not the model's own idea: **it is `SYSTEM_PROMPT:151-153`, followed to the letter.**
The prompt taught it to reimplement, by example, the exact function sitting unmentioned beside its
script.

**This closes nothing yet, and `spec.md` N8 is the reason to say so.** §6.1 is closed by a *measured*
rate at which the model actually reaches `web_search` **under the variant that advertises it** —
that is the V2 row of §3.3, and **§3.3 is NOT RUN**. What F2 establishes is the *denominator*: the
V0 rate is a measured zero rather than an assumed one, so any non-zero V2 figure will be a real
difference against a real baseline. **That is the half of AC-TOOLS item 4 this run discharges.**

### F3 — C4 routes CODE 30/30, and it is a live defect on `main` that this SPEC did not cause and must not fix

Control prompt **C4** is `explain what a Python closure is, with a short example`. It is a
general-knowledge request. A user typing it expects prose.

**It produced executable Python in 30 trials out of 30.** Every one of the 30 replies carried
`fence_matches == 1` and contained a `def` definition. DIRECT rate **0.0 %**, 95% Wilson
**[0.0 %, 11.4 %]**.

**What the product then does with that block, which is the finding.** `extract_last_python_block()`
cannot distinguish an **illustrative** fenced block from **code the model intends to be run** —
there is no such distinction in the reply, and there is no flag in the protocol carrying it. So the
production path at `main.py:1032` sees a block, and the product:

1. **writes the model's teaching example to disk**,
2. **spawns a subprocess and executes it**, and
3. **pays a second LLM round-trip** to narrate the stdout of a snippet that was never meant to run —

on a turn the user believed was a question. On this prompt that is merely wasteful and confusing.
On a prompt whose illustrative example happens to be destructive, it is not merely wasteful.

**This is pre-existing and independent, and both words are load-bearing.** It was measured under
**V0**, with `main.py` unmodified — sha256 `ff5a488f…`, constant across all 220 records. It has
nothing to do with Gmail, nothing to do with the routing contradiction at `:126-129`, and nothing to
do with `tools.py`. **It is not what this SPEC was written to fix, and it is not fixed here.**

**It deserves its own SPEC.** The question it raises — *how does a code interpreter tell an example
from an instruction?* — is a protocol design question, not a prompt-wording question. Candidate
directions exist (an explicit marker the model must emit for runnable blocks; a confirmation step
before execution on general-knowledge turns; a classifier that is not `findall()`), and choosing
between them is exactly the kind of decision that needs its own requirements, its own risks and its
own measurement. **Doing it as a rider on this SPEC would be the same mistake `spec.md` N6 already
refuses for the `_HTML_RESULT_RE` rewrite.**

**One consequence for this document, recorded so it is not discovered later.** C4 is now useless as
a regression detector for §4 (see §2.4): it sits at 0 % and cannot go lower. The control set's
ability to catch R2 rests mainly on **C1**, which is at 30/30 with a Wilson floor of 88.6 %.

---

## 3. Variants — V1, V2 and V3

**RUN at the Target cell — all four arms (§3.1, §3.6). §3.2, §3.3 and §3.4 are NOT RUN.** This is
`plan.md` T3 and T3b.

| Variant | Definition | When it runs |
|---|---|---|
| **V1** | V0 with the routing contradiction repaired (`spec.md` D1) — `main.py:126-129` amended so DIRECT means "no computation and no fetch would answer this" rather than "you do not already hold this data" | T3 — **RUN, N=30, Target** |
| **V2** | V1 plus the capability section (`spec.md` D2, D3), inserted **below** `main.py:166` (N3), naming the library set, network egress and `from tools import web_search`, each with a worked example — **indented and unfenced (N9)** | T3 — **RUN, N=30, Target** |
| **V3** | **V0 + the capability section, without the routing repair** (`spec.md` A5, S6) | **RUN, N=30, Target, 2026-08-12 (§3.6).** Its tool-reachable and control cells — the ones AC-GATE item 7 names — remain **NOT RUN** |

**The four arms form a complete 2 × 2 factorial, and that was verified against the variant strings
rather than inferred from their names.** Computed 2026-08-12 over `probe/variants.py`:

| | **no capability section** | **capability section** |
|---|---|---|
| **no routing repair** | **V0** | **V3** |
| **routing repair** | **V1** | **V2** |

The 19-line capability block added to V0 to make V3 is **byte-identical** to the block added to V1 to
make V2 (checked by unified diff), and the only difference between V3 and V2 is the **two routing
lines** — `V3 → V2` diffs to exactly the two lines out and the two lines in that §3.0 records. Both
V3 and V2 are 76 lines, 2 fences, `# @param city` at the same prompt-line as V0, max width 76, and
zero mail / keychain / environment-variable tokens. **This is why §3.6 can say anything about the two
components separately: it is a designed factorial, not four prompts that happen to differ.**

### 3.0 The variant text that was actually run, and two corrections made to the T1 drafts before running

**`probe/variants.py` held V1, V2 and V3 as harness drafts. They were reviewed against the SPEC
before the run rather than after it, and two of them did not comply.** Both were corrected first.
Recording this because a variant is the treatment: a reader who is told only the results is being
asked to trust that the thing measured was the thing specified.

**Correction 1 — V1 was not line-count-neutral, and N3's pin would have moved.** The draft replaced
two lines of `main.py:128-129` with **four**, which pushes the `@param` passage from `:158-166` down
to `:160-168`. `SPEC-KEYCHAIN-001` N2 already cites that passage **18 lines stale**, and N3 exists
to stop a third generation of the same drift.

The obvious repair — widen the substitution to cover the whole `:126-129` paragraph, four lines for
four — **is closed off by the test suite**: `tests/test_probe.py:237` asserts `V0[:200] in text` for
every variant, and V0's first 200 characters run into `main.py:127`. **The two constraints together
force the edit into `:128-129` and force it to fit in two lines.** It now does:

    V0  question is conversational, opinion, general knowledge, or needs live data
        you don't have), follow the DIRECT protocol.

    V1  question is conversational, opinion, or general knowledge, and neither a
        fetch nor a computation would answer it), follow the DIRECT protocol.

Verified by computation: **V1 and V0 are both 57 lines**, `# @param city` sits at prompt-line 38 in
V0, V1, V2 and V3 alike, and both new lines are within V0's own 76-column measure.

**What was traded away, stated against the result it may have produced.** The discarded draft closed
with *"Not holding the data yourself is NOT a reason to choose DIRECT: if the answer is reachable
over the network, or computable, that is CODE."* — a sentence that answers V0 trial #8 in its own
words. **It does not fit in two lines and it was cut.** What survives carries D1's semantics —
DIRECT is now **conjunctive** where V0's was disjunctive — but not its emphasis. **V1 as run is
therefore a weaker treatment than the draft, and §3.1 records that V1 had no measurable effect. Those
two facts are stated together deliberately: the weakening is a live alternative explanation for V1's
null result, and this document does not get to choose between them.**

> **PROMOTED 2026-08-12 — this disclosure is now load-bearing rather than a footnote, and §3.6 is
> why.** When it was written, it qualified a null result that the document was about to attribute to
> the routing repair being inert. **§3.6 removes the entitlement to that attribution**, and the
> question of how strong the routing repair actually was stops being a caveat and becomes the
> question. Two things follow, and neither is a conclusion:
>
> - The cut sentence is aimed **precisely** at the reasoning V0 trial #8 exhibited (§2.1.1), and
>   **V3 trial #1 exhibits that same reasoning again** — V3 retains the `:128-129` clause and the
>   model quotes it back (§3.6). The one arm where the model was observed citing the clause under
>   the capability section is the arm where the clause is still there.
> - The forcing constraint is still in place and still checkable: `tests/test_probe.py:237` asserts
>   `V0[:200] in text` for every variant, and N3 pins the `@param` line count. **A stronger V1
>   requires one of those two to move, or a two-line phrasing nobody has written yet.** That is a
>   concrete, bounded piece of work, not an aspiration — which is what makes it a better candidate
>   than the SPEC M-b nominally obliges (§5).

**Correction 2 — V2's capability section landed at column 0, which is not the shape N9 requires.**
`textwrap.dedent()` had stripped the intended indentation off the block. V0's own ladder is
**bullets at column 3, continuations at 5, worked examples at 7** (`- Available libraries:` at 3,
`path), do NOT call input().` at 5, `# @param city:` at 7). The draft's bullets landed at **0** —
the column of `CODE protocol:` and `DIRECT protocol (no code needed):` — so two new **top-level
sections** would have appeared wedged between the `Rules:` list and `4. Stop after the fenced
block.`, inside numbered item 3. N9 requires added examples to be *"indented and unfenced, in the
shape of the existing examples at `main.py:146-153` and `main.py:162-163`"*, and column 0 is not that
shape. Fixed with `textwrap.indent(..., "   ")`, whose default predicate leaves blank lines blank;
re-measured at **3 / 5 / 7 / 11**, matching V0 exactly, with zero trailing whitespace introduced.

**Everything else the review checked, and passed:**

| Check | V0 | V1 | V2 | V3 |
|---|---|---|---|---|
| Backtick fences (N9; `tests/test_source_seam.py:547` pins exactly 2) | 2 | **2** | **2** | **2** |
| Line count | 57 | **57** | 76 | 76 |
| `# @param city` at prompt-line | 38 | **38** | **38** | **38** |
| Mail tokens — `imap`, `gmail`, `mail`, `smtp`, `inbox`, case-insensitive | 0 | **0** | **0** | **0** |
| `keychain` / `keyring` (N2) | 0 | **0** | **0** | **0** |
| `os.environ` / `getenv` / "environment variable" (N1) | 0 | **0** | **0** | **0** |
| The `@param` passage, byte-for-byte against V0 (N2) | — | **identical** | **identical** | **identical** |
| Capability section inserted **below** the `@param` passage (N3) | — | n/a | **yes** | **yes** |
| Max line width | 76 | **76** | **76** | **76** |

**The zero-mail-tokens row is load-bearing for the gate's validity and not a tidiness check.** If V2
named mail, an M-a would no longer distinguish *"the routing repair worked"* from *"we explicitly
told it about mail"*, and the SPEC's question would have been answered by assuming its answer. V2
contains no mail token of any kind; its two worked examples are a `uv` web search and the CPython
issue count.

### 3.1 Target task

**RUN — all four arms at N=30.** Records: `v0-target.jsonl`, `v1-target.jsonl`, `v2-target.jsonl`,
`v3-target.jsonl` (30 lines each, indices 0–29, no gaps and no duplicates). **V3's column was added
2026-08-12; every figure in the table was re-derived from the JSONL in the same pass, and every V0,
V1 and V2 figure reproduced unchanged.**

| | V0 | V1 | V2 | **V3** |
|---|---|---|---|---|
| Composition | baseline | routing repair only | repair + capability | **capability only** |
| Trials (N) | **30** | **30** | **30** | **30** |
| Routed CODE | **13** | **11** | **23** | **18** |
| Routed DIRECT | **17** | **19** | **7** | **12** |
| **DIRECT rate (gated)** | **56.7 %** — this is `r0` | **63.3 %** — `r1` | **23.3 %** — this is `r2` | **40.0 %** — `r3` |
| 95% Wilson | **[39.2 %, 72.6 %]** | **[45.5 %, 78.1 %]** | **[11.8 %, 40.9 %]** | **[24.6 %, 57.7 %]** |
| **Fence traps** (DIRECT with `fence_matches > 0`) | **0** | **0** | **0** | **0** |
| DIRECT trials genuinely unfenced | **17 of 17** | **19 of 19** | **7 of 7** | **12 of 12** |

**The fence-trap row is zero in all four arms and that was checked, not assumed.** Across all 120
Target trials, every DIRECT reply had `fence_matches == 0` and every CODE reply had exactly `1`. **No
DIRECT rate in this table is inflated by a two-block reply that refused nothing** (E7,
`acceptance.md` AC-GATE item 2c). Had even one V2 trial been a trap, `r2` would be wrong in the
direction that flatters the SPEC.

#### The comparisons, computed

*Fisher exact throughout, one-sided in the direction of fewer DIRECT trials, `math.comb`, no
library. Re-derived 2026-08-12.*

| Comparison | Difference | One-sided Fisher exact `p` |
|---|---|---|
| **V0 → V2 — THE GATED COMPARISON** | `r0 − r2` = 0.5667 − 0.2333 = **0.3333** | **0.008428** |
| V0 → V1 *(reported, decides nothing)* | `r0 − r1` = **−0.0667** *(V1 is worse)* | **0.785215** |
| **V0 → V3** *(reported, decides nothing)* | `r0 − r3` = 0.5667 − 0.4000 = **0.1667** | **0.150734** |
| V1 → V2 *(reported, decides nothing)* | `r1 − r2` = **0.4000** | **0.001878** |
| **V3 → V2** *(reported, decides nothing)* | `r3 − r2` = **0.1667** | **0.133418** |
| **V1 → V3** *(reported, decides nothing)* | `r1 − r3` = **0.2333** | **0.060227** |

#### V1 did nothing, and that is the most informative row in the table

**V1 is the routing repair on its own — `spec.md` D1, the SPEC's central proposed fix — and it moved
the DIRECT rate from 17/30 to 19/30, in the wrong direction, at `p = 0.785`.** There is no effect
here to interpret; 19 versus 17 at N=30 is noise, and the honest statement is that **V1 is
indistinguishable from V0 on this cell.**

**The verbatim replies say why, and they are more informative than the counts.** V0 trial #8 justified
its refusal by *quoting the prompt*: "Since this task requires computation on data (your Gmail
account) **which I don't have access to**, I'll follow the DIRECT protocol" — the `:128-129` clause,
read back. **Under V1 that clause no longer exists.** All 19 V1 DIRECT replies were read. **Not one
of them cites a routing rule at all** — not the removed clause (0/19), not the new wording (0/19).
They are flat capability declinations:

> #0 — "I cannot access or check your email. Is there anything else I can help you with?"
>
> #9 — "I can't fulfill requests related to accessing or managing private user accounts."
>
> #26 — "I can't fulfill that request. I'm just an AI, I don't have access to your personal data or
> email accounts."

**17 of the 19 open with a first-person declination.** Removing the clause removed the model's stated
*justification* and left the *behaviour* untouched. **That is the signature of a disposition that is
not coming from the prompt** — which is precisely what M-b means, and it is why §5 does not read as a
narrow miss on an arbitrary threshold.

#### ~~What moved was the capability section, not the routing repair~~ — SUPERSEDED by §3.6

> **SUPERSEDED 2026-08-12 by §3.6. The heading and the two paragraphs below are kept verbatim,
> because they were the honest reading of a two-arm comparison and erasing them would destroy the
> record of why the wrong conclusion was reasonable** (the discipline `spec.md` HISTORY v1.1.0
> established). **They are wrong, and §3.6 states the reason: with only V0, V1 and V2 in hand there
> is no arm in which the capability section appears without the routing repair, so "the capability
> section is the active ingredient" and "the two only work together" predict the identical three
> numbers. Two arms cannot distinguish a main effect from an interaction. V3 is the cell that
> completes the 2 × 2, and V3 does not reproduce V2.**
>
> **`r3 = 12/30 = 40.0 %`.** The capability section on its own recovers **16.7 of the 33.3
> percentage points** V2 recovered against V0, and it misses significance (`p = 0.150734`).
> **Read §3.6 before relying on anything in the two paragraphs below.**

~~V1 → V2 is **40 percentage points at `p = 0.0019`**, and V2 is the only arm that moved. **The active
ingredient in this SPEC's proposed change is the part that advertises what the sandbox can do, not
the part that rewrites the routing rule** — which is exactly what §2.5's F1 predicted from the
baseline alone, before §3.1 was read: a model whose effective capability surface is its example set
responds to examples and ignores rules.~~

~~**This has a direct and unwelcome consequence, and §3.6 is where it lands.** Under M-b the routing
repair does not ship but the advertisement still can — and the advertisement is the half that
demonstrably works. **What would ship is `V0 + capability`, which is V3, and V3 has not been
measured.** §3.6 was written as a formality against an outcome nobody expected. It is now the most
important unrun cell in this document.~~

**What survives of it, and it is not nothing.** The V1 → V2 comparison is still 40 points at
`p = 0.001878`, and V1 alone is still null in the wrong direction. **What does not survive is the
attribution** — the inference from those two facts to "the capability half does the work and the
routing half does none of it". §2.5's F1 predicted that inference and F1's own warning applies to it
in turn: *"the monotone ordering is real; the claim that each step down is a separate effect is not
supported"*. The same caution was owed here and was not taken.

**What `r0 = 0.567` implied for the pre-registered rule, and what actually happened.** §1.1 requires
`(r0 − r2) ≥ 0.40` **and** significance. With `r0 = 0.567`, V2 had to land at **`r2 ≤ 0.167`** — no
more than **5** DIRECT trials in 30. **It recorded 7.** The bar was demanding and reachable, which is
what a gate should be; it was missed by **two trials**, and §5 says what that does and does not mean.

### 3.2 Off-example network task

**V0 IS RUN (§2.2). V1 AND V2 ARE NOT RUN.**

| | V0 | V1 | V2 |
|---|---|---|---|
| Trials (N) | **20** | — *(planned 20)* | — *(planned 20)* |
| Routed CODE | **10** | — | — |
| Routed DIRECT | **10** | — | — |
| DIRECT rate | **50.0 %** | — | — |

**Read this table against §3.1.** If the off-example task improves and the Target does not, the
residue is account-specific and belongs to `SPEC-ACCOUNT-001`. If neither improves, the routing
repair did not work, and recording that is the point of taking the measurement.

**Why this cell was not run, named as a gap rather than as a decision that needed no reason.** §1.1
decides the gate on the Target cell alone, and **no other cell may rescue an M-b** — so running this
one could not have changed §5, and the run was scoped to the gated comparison. **What is lost is
diagnosis, not verdict.** With §3.1 recording that V1 did nothing and V2 did the work, the V1 and V2
columns here would say whether V2's 40-point swing is a general re-opening of network tasks or
something narrower, and that question is now open. It belongs with §3.6, which is owed anyway.

### 3.3 Tool-reachable task

**V0 IS RUN (§2.3). V1 AND V2 ARE NOT RUN.**

| | V0 | V1 | V2 |
|---|---|---|---|
| Trials (N) | **20** | — *(planned 20)* | — *(planned 20)* |
| Routed CODE | **20** | — | — |
| Imports `tools` | **0** | — | — |
| Calls `web_search` | **0** | — | — |

**The V2 row of this table is what closes `product.md` §6.1** (`spec.md` N8, `acceptance.md`
AC-TOOLS item 4). Nothing else does. **It is empty, so §6.1 is not closed by this run**, and no
sentence anywhere in this document may be read as closing it. What §2.5's F2 supplies is the
**denominator** — a measured `0/20`, and `0/220` across the whole baseline — so that a future V2 or
V3 figure is a difference against something real.

**One observation from the Target cell, offered as a lead and explicitly not as this cell's answer.**
The same two probes were run over §3.1's **120** Target trials, where a general web search is *not*
the natural instrument and `tools.py` is *not* the right tool for the job:

| | V0 | V1 | V2 | **V3** |
|---|---|---|---|---|
| `import tools` / `from tools`, on the **Target** task | 0/30 | 0/30 | **1/30** | **0/30** |
| `web_search` mentioned, on the **Target** task | 0/30 | 0/30 | **2/30** | **0/30** |
| the bare token `tools`, on the **Target** task | 0/30 | 0/30 | **1/30** | **0/30** |

**One trial and two trials. That is not a rate and it does not close §6.1** — it is the wrong task
for the question, and `n=1` is what this SPEC exists to stop being persuaded by. It is recorded only
because it is the first evidence in the repository that the advertisement is read at all.

**V3 returns zero on all three probes, and that is a genuinely awkward row rather than a tidy one.**
V3 carries the **byte-identical** capability section — the same `from tools import web_search` line,
the same worked example — and on this task it produced **0/30** where V2 produced 1/30 and 2/30.
**Nothing may be concluded from that.** Three counts of 0, 1 and 2 out of 30 are not distinguishable
from one another at any N this document possesses, and the honest reading is that **the Target task
is the wrong instrument for this question in every arm.** It is recorded because omitting the V3
column from a table whose other columns are already published would be selecting the columns that
tell the better story. **§3.3's V2 and V3 rows — on the tool-reachable cell, at N=20 — remain the
only things that close `product.md` §6.1, and both are still unrun.**

### 3.4 Control set

**V0 IS RUN (§2.4). V1 AND V2 ARE NOT RUN.**

| Control prompt | N | V0 DIRECT rate | V1 | V2 |
|---|---|---|---|---|
| C1 conversational | 30 | **100.0 %** (30/30) | — | — |
| C2 conversational | 30 | **66.7 %** (20/30) | — | — |
| C3 opinion | 30 | **86.7 %** (26/30) | — | — |
| C4 general knowledge | 30 | **0.0 %** (0/30) | — | — |
| C5 general knowledge | 30 | **46.7 %** (14/30) | — | — |
| **POOLED** | **150** | **60.0 %** (90/150) | — | — |

**The V0 column is the thing R2 actually needed and it now exists** (`acceptance.md` AC-CONTROL item
2, discharged). The V1 and V2 columns are diagnostic and are **not** the regression check —
`acceptance.md` AC-CONTROL item 3 asks for the control set under the **shipped** prompt, which is §4,
and nothing has shipped. **Under M-b the prompt that would ship is V3, so the control column that
matters next is V3's, in §3.6.**

### 3.5 Code correctness, where assessed

*This is what separates **M-a** from **M-c**. A trial that produced a fenced block is not a success
unless the code was also assessed.*

| Task | Variant | Trials producing code | Code assessed? | Code that ran successfully |
|---|---|---|---|---|
| Target | V0 | **13** | **NO — not assessed** | — |
| Target | V1 | **11** | **NO — not assessed** | — |
| Target | V2 | **23** | **NO — not assessed** | — |
| Target | **V3** | **18** | **NO — not assessed** | — |
| Off-example network | V2 | — *(cell not run)* | — | — |
| Tool-reachable | V2 | — *(cell not run)* | — | — |
| Tool-reachable | **V3** | — *(cell not run)* | — | — |

**Stating it explicitly, because `acceptance.md` AC-GATE item 3 makes the absence of this sentence
the failure rather than the absence of the data: code correctness was NOT assessed for ANY arm of
the Target cell — not V0, not V1, not V2, and not V3.** All **65** CODE trials across the **four**
arms emitted a fenced block (13 + 11 + 23 + 18, counted from the JSONL); **not one of those blocks
was executed, and none was read line by line.** The M-a/M-c distinction is therefore **explicitly
deferred** to `SPEC-ACCOUNT-001` A1, as that criterion permits.

**V3 adds 18 unassessed CODE trials and does not reduce this gap by one trial.** It also sharpens
it: **§3.6 now turns on comparing CODE *rates* across four arms, and a CODE rate is a routing
measure in every one of them.** If V3's 18 blocks were systematically worse than V2's 23 — a thing
nobody has looked at — the ordering §3.6 reasons about on routing counts could differ from the
ordering on anything a user would call working. **Nothing in §3.6 depends on that being false, and
nothing in §3.6 establishes that it is.**

**What this does and does not cost, given that §5 records M-b.** AC-GATE item 3 forbids recording
the gate as a *pass* under an unassessed M-c — that is, it forbids claiming M-a when the code was
never checked. **§5 does not record a pass**, so that trap is not the one in front of this run.
**The residue is on the other side and it is real:** M-b is the finding that the refusal is *not* a
routing artefact, and it was reached entirely from routing counts. A reader is entitled to ask
whether V2's 23 CODE trials contained *working* code, because "the model complies but writes code
that does not work" is M-c and M-c is a **proceed** outcome. **The gate rule does not depend on that
answer** — §1.1's endpoint is the DIRECT rate and nothing else — but the *interpretation* in §5
would be sharper with it, and it is not available.

**M-c is a real outcome and it has not been collapsed into M-a anywhere in this document.** §5 is
M-b on the arithmetic of the DIRECT rate alone; neither M-a nor M-c was reached, so the split
between them never had to be made. **If a later run clears §1.1's threshold, the split becomes
mandatory before "proceed" may be written.**

**One partial observation carried forward from §2.1.1, still a lead and still not an assessment.**
The one V0 CODE reply read for §2.1.1 imported `imaplib` and declared its inputs as
`# @param email_password: str` — the right mechanism, with the wrong type: `main.py:165` makes
`secret` the declared type for passwords, and `str` is not masked when typed. Regex counts over the
four arms, offered as texture and **not** as a correctness measure:

| | V0 | V1 | V2 | **V3** |
|---|---|---|---|---|
| replies mentioning `imaplib` or `imap` *(case-insensitive)* | 11/30 | 4/30 | **16/30** | **12/30** |
| replies containing `# @param` | 12/30 | 10/30 | **23/30** | **16/30** |

**A regex is not a code review.** These counts say the model reaches for the IMAP library and the
`@param` grammar more often under V2; they say nothing whatever about whether any of it runs. **V3
sits between V0 and V2 on both rows, which is the same shape §3.6 finds on the gated quantity — and
it is worth exactly as little here, for the same reason: these are counts of tokens, not of working
programs.**

**One partial observation, offered as a lead and not as an assessment.** The one CODE reply read for
§2.1.1 imported `imaplib` and declared its inputs as `# @param email_password: str` — the right
mechanism, with the wrong type: `main.py:165` makes `secret` the declared type for passwords, and
`str` is not masked when typed. That is one visible defect in one trial, found while reading a reply
for a different purpose. **It is not a rate**, and nothing here licenses a claim about the other 12.

### 3.6 Variant V3 — RUN at the Target cell, and it overturns §3.1's attribution

**TARGET CELL: RUN — 2026-08-12, N=30.** Records:
`.moai/specs/SPEC-PROMPT-001/probe-runs/v3-target.jsonl` (30 lines, indices 0–29, no gaps, no
duplicates).
**TOOL-REACHABLE AND CONTROL CELLS: NOT RUN — STILL OWED.** `spec.md` A5 / S6, `plan.md` T3b,
`acceptance.md` AC-GATE item 7.

**Read this first, because the two halves of this section pull in opposite directions.** The cell
that ran is **not** a cell AC-GATE item 7 asked for. Item 7 names the tool-reachable cell (N=20) and
the full control set (5 × N=30); the Target cell appears nowhere in it. **So this section
simultaneously reports the most informative result in the experiment and discharges none of the
obligation it was written to discharge.**

#### 3.6.1 The result

| | V0 | V1 | V2 | **V3** |
|---|---|---|---|---|
| Composition | baseline | routing repair only | repair + capability | **capability only** |
| N | 30 | 30 | 30 | **30** |
| Routed CODE | 13 | 11 | 23 | **18** |
| Routed DIRECT | 17 | 19 | 7 | **12** |
| **DIRECT rate** | **0.5667** | **0.6333** | **0.2333** | **0.4000** |
| 95% Wilson | [39.2 %, 72.6 %] | [45.5 %, 78.1 %] | [11.8 %, 40.9 %] | **[24.6 %, 57.7 %]** |
| Fence traps | 0 | 0 | 0 | **0** |
| One-sided Fisher vs V0 | — | **0.785215** | **0.008428** | **0.150734** |

**`r0 − r3` = 0.5667 − 0.4000 = 0.1667**, against the 0.3333 V2 achieved. **V3 is worse than V2 on
the gated quantity and it does not compete.** It clears **neither** clause of §1.1: the absolute
clause needed 0.40 and measured 0.1667, and Fisher does not reject (`p = 0.150734`). Where V2's
interval **contained** the threshold value 16.7 % and made it a near miss, **V3's interval
[24.6 %, 57.7 %] excludes 16.7 % outright.** V3 is not a near miss; it is not close.

#### 3.6.2 §3.1's attribution was wrong, and this is the correction

**§3.1 concluded — and this document then repeated to its reader — that "the routing repair does
nothing; the capability advertisement does everything".** That conclusion is **withdrawn**. It is
struck through in place at §3.1 rather than removed, and the reason it was wrong is this:

**With only V0, V1 and V2, there is no arm in which the capability section appears without the
routing repair.** "The capability section is the active ingredient" and "the two components only
work in combination" are then **observationally identical hypotheses** — they predict the same
17/30, 19/30, 7/30. **Two arms cannot separate a main effect from an interaction.** The inference was
not merely unlucky; it was unavailable from the data that were used to make it, and §2.5's F1 had
already stated the general form of that caution one section earlier.

**V3 is the fourth arm — the one that completes the factorial and breaks the confound — and it does
not reproduce V2.** The capability section alone recovers **16.7 of V2's 33.3 percentage points**
against V0 — about half — and misses significance at `p = 0.150734`.

**The single-arm tests, laid out so the pattern is visible:**

| Arm | What it isolates | vs V0 | Fisher one-sided |
|---|---|---|---|
| **V1** | routing repair alone | **−0.0667** *(wrong direction)* | **0.785215** — null |
| **V3** | capability alone | **+0.1667** | **0.150734** — null |
| **V2** | both together | **+0.3333** | **0.008428** — rejects |

**Neither component on its own clears significance against V0. Only the combination does.** That is
a fact about which tests cleared, it is exact, and it is the strongest thing this experiment
supports about the two components.

#### 3.6.3 What must NOT be concluded from that, and the arithmetic that forbids it

**It is tempting to write "the effect is an interaction, not a main effect", and the numbers do not
license it.** Writing it would be the standard error of treating "significant" and "not significant"
as though the difference between them were itself significant — and it would repeat, in the opposite
direction, exactly the mistake §3.6.2 is correcting. Three computations, all from the 120 Target
trials:

**1. The pooled main effect of the capability section is large and significant.** Collapsing over the
routing factor — the 60 trials that carry the capability section (V2 + V3) against the 60 that do not
(V0 + V1):

| Factor | With | Without | Difference | Fisher one-sided | two-sided |
|---|---|---|---|---|---|
| **Capability section** | **19/60 = 0.3167** | **36/60 = 0.6000** | **0.2833** | **0.001601** | **0.003202** |
| **Routing repair** | 26/60 = 0.4333 | 29/60 = 0.4833 | 0.0500 | 0.357115 | 0.714231 |

**So there *is* a main effect of the capability section, and it is the single strongest signal in the
experiment.** "No main effect, pure interaction" is contradicted by the data outright. The routing
repair, pooled, remains null.

**2. There is super-additivity on the difference scale, and it is a point estimate only.** Predicting
`r2` from V0 plus the two single-factor effects gives `0.5667 + 0.0667 − 0.1667 = 0.4667`; the
observed `r2` is **0.2333**. The excess is **0.2333** — the combination beat additivity by 23.3
percentage points. The interaction contrast is **−0.2333** under either parameterisation,
`(r0 − r3) − (r1 − r2)` and `(r0 − r1) − (r3 − r2)`, as it must be.

**3. That super-additivity is NOT statistically established.** Tested two ways, both reported
whatever they said:

| Test | Statistic | Result |
|---|---|---|
| Woolf/Wald on the ratio of odds ratios | OR(capability given no repair) = **0.5098**; OR(capability given repair) = **0.1762**; ratio **0.3456**, ln = −1.0624, SE = 0.7775, z = −1.3664 | **two-sided `p = 0.1718`** — does not reject |
| Permutation on the interaction contrast, 200 000 draws, seed 20260812 | observed \|contrast\| = 0.2333 | **two-sided `p = 0.2743`** — does not reject |

**The 95 % interval on the ratio of odds ratios is [0.075, 1.59]** — consistent with a
thirteen-fold synergy and consistent with mild antagonism. **At N=30 per arm this experiment cannot
tell those apart**, which is the expected situation: an interaction contrast is a difference of
differences and carries roughly four times the variance of a main effect of the same size.

**Both directions of overclaim are therefore closed, and the honest statement is narrower than
either.** What is established:

- **The routing repair alone does nothing** (null, wrong direction, `p = 0.785215`). Twice measured
  now, once against V0 and once in the pooled margin.
- **The capability section alone does not reproduce V2** — it recovers about half of V2's gain and
  misses significance (`p = 0.150734`).
- **Only the combined arm cleared significance against V0.**
- **Adding the routing repair on top of the capability section moved the rate a further 16.7 points**
  (V3 → V2), at `p = 0.133418` — **not significant.**
- **Pooled, the capability section has a large significant main effect and the routing repair has
  none.**

What is **not** established, and must not be written anywhere in this SPEC on this evidence:

- **That the two components are jointly necessary.** V3 is not distinguishable from V2 either
  (`p = 0.133418`). **V3 sits between V0 and V2 and is separated from neither at N=30.** It cannot
  adjudicate; it can only remove the entitlement to the strong claim §3.1 made.
- **That the effect is an interaction rather than a main effect.** Both interaction tests fail to
  reject, and the pooled capability main effect is significant at `p = 0.001601`. **A model in which
  the capability section does most of the work and the routing repair contributes a little is
  entirely consistent with these 120 trials**, and so is a synergy model. The data do not choose.
- **That the routing repair is inert.** Its simple effect in the presence of the capability section
  is +16.7 points. Non-significant is not zero, and §3.0's disclosure — that **V1 as run is a weaker
  treatment than the drafted one** — is a live alternative explanation for its null that this run
  still cannot exclude. **That disclosure is now load-bearing and is cross-referenced from §3.0.**

#### 3.6.4 The design lesson, recorded as evidence rather than as satisfaction

**V3 exists only because `plan.md`'s T3b noticed, before any variant ran, that under M-b the shipped
prompt would be `V0 + capability` — a string none of V0, V1 or V2 is — and added a cell for a branch
the SPEC had not taken and expected not to take.** §3.6 was written, in this file, as *"a formality
to avoid shipping an unmeasured string on an outcome nobody expected"*.

**That contingency cell turned out to be the most informative cell in the experiment.** It is the
only arm that breaks the confound between the two components, and without it this document would
have shipped a single-factor causal attribution that its own data never supported — stated in bold,
twice, with a `p`-value beside it.

**The generalisable form, and it is an argument about method rather than about this SPEC:** the cell
worth adding is **the configuration you would actually ship**, not only the configurations that sit
at the ends of your hypothesis. Here the two coincided by accident — the shippable prompt was also
the missing factorial cell — and the accident is what makes the point checkable rather than
rhetorical. **A SPEC that measures only its proposal and its baseline can be wrong about which half
of its proposal did the work, and will not find out.**

#### 3.6.5 The model's stated reasoning under V3, offered as texture and not as a rate

**All 12 V3 DIRECT replies were read.** **10 of 12** open with a first-person declination under the
stated rule *(whitespace-normalise, then match an opening* `I can't` / `I cannot` / `I'm not able` /
`I don't` / `Sorry, I` / `Unfortunately, I`*)* — the rule is stated because §2.1 records what happens
to a count whose rule is not.

**One reply is worth quoting, and one is not a rate.** V3 trial **#1**:

> **This task requires computation on data that I don't have access to.** Let's follow the DIRECT
> protocol.
>
> **Answer:** I'm not capable of checking your Gmail account directly, but I can suggest ways to
> find interview opportunities in general. […]

**That is V0 trial #8's justification, verbatim in substance** (§2.1.1) — the `main.py:128-129`
clause quoted back. **V3 retains that clause**; V1 and V2 do not. Counting citations of a routing
rule across the four arms' DIRECT replies: **V0 2/17, V1 0/19, V2 1/7, V3 1/12.**

**These counts settle nothing and are recorded so that they are not later mistaken for having
settled something.** 2, 0, 1 and 1 are not distinguishable at these denominators. What they are
consistent with — and only consistent with — is the reading §5 already gives: **removing the clause
removed the model's stated justification and left its behaviour alone.** The one novel observation
is that when the clause is put back **alongside** the capability section, the model quotes it again,
once.

#### 3.6.6 What is still owed, and it is the whole of AC-GATE item 7

**The Target cell does not discharge item 7 and must not be recorded as though it did.** Item 7
requires V3 at the tool-reachable cell and across the full control set, **before any prompt text is
merged** (S6). Both are unrun. The table below is unchanged from when it was written, because
**nothing in it has been measured.**

| Cell | N | V0 | V3 |
|---|---|---|---|
| Tool-reachable — imports `tools` | 20 | **0** | **— NOT RUN** |
| Tool-reachable — calls `web_search` | 20 | **0** | **— NOT RUN** |
| C1 conversational — DIRECT rate | 30 | **100.0 %** (30/30) | **— NOT RUN** |
| C2 conversational — DIRECT rate | 30 | **66.7 %** (20/30) | **— NOT RUN** |
| C3 opinion — DIRECT rate | 30 | **86.7 %** (26/30) | **— NOT RUN** |
| C4 general knowledge — DIRECT rate | 30 | **0.0 %** (0/30) | **— NOT RUN** |
| C5 general knowledge — DIRECT rate | 30 | **46.7 %** (14/30) | **— NOT RUN** |

**The two questions these cells exist to answer, both still open:**

1. **Does the advertisement reach `tools.py`?** Against a measured V0 denominator of `0/20` and
   `0/20` (§2.5 F2). This is `product.md` §6.1's close condition (`spec.md` N8). **§3.3's Target-cell
   row gives 0/30 under V3 — on the wrong task, and it closes nothing.**
2. **Does the advertisement, on its own, move the control set?** §2.4 shows the control set is
   already at 60 % pooled and that C4 is at 0/30 — so the product is **already** eager, and a change
   that makes network work more salient is a change in the direction the controls are already
   failing. **R2 is the highest-blast-radius risk in this SPEC and the V3 control set is its only
   remaining defence.** C1 (30/30, Wilson floor 88.6 %) is the row with the most power to detect a
   regression; C4 has none left.

**The Target result makes question 2 more pressing rather than less.** V3 moved the Target CODE rate
from 13/30 to 18/30 — the product writes and runs code more often under the prompt M-b permits to
ship. **On the Target cell that is the intended direction. On the control set it is precisely the
regression R2 names**, and no control trial has been run under V3.

**Nothing may merge before those cells exist** (S6, AC-GATE item 7).

---

## 4. Post-change regression — the shipped prompt

**NOT RUN, AND NOT YET OWED — nothing has shipped.** This is `plan.md` T6, and it runs **after**
`main.py` is amended, against whatever actually shipped. **Under M-b the routing repair is not
amended into `main.py` at all**, so if anything ships it is the `tools.py` advertisement alone, and
this table's "shipped" column will be **V3's** prompt (§3.6).

**The V0 column below is now filled**, which is the whole point of having measured it first — see
§2.4 for what would have happened had it not been.

| Control prompt | Kind | V0 DIRECT rate | Shipped DIRECT rate | N (V0) | N (shipped) | Worse? |
|---|---|---|---|---|---|---|
| C1 | conversational | **100.0 %** (30/30) | — | **30** | — | — |
| C2 | conversational | **66.7 %** (20/30) | — | **30** | — | — |
| C3 | opinion | **86.7 %** (26/30) | — | **30** | — | — |
| C4 | general knowledge | **0.0 %** (0/30) | — | **30** | — | — |
| C5 | general knowledge | **46.7 %** (14/30) | — | **30** | — | — |
| **POOLED** | | **60.0 %** (90/150) | — | **150** | — | — |

**A warning for whoever fills the right-hand column, because the left-hand column is not what its
label suggests.** These are not five prompts that route DIRECT reliably. Three of them misroute at
baseline. **"Worse?" must be read as a comparison of rates with N stated, never as a judgement about
whether the shipped behaviour is correct** — C4 is at 0 % under V0 and cannot get worse, and a
reader who skims this table without §2.4 will draw the opposite conclusion from every row.

**If any row is worse, it is recorded here with its numbers and either resolved or accepted in
writing** (`acceptance.md` AC-CONTROL item 5). It is not rounded away, and it is not attributed to
noise without stating N.

**If the control set ran at a smaller N than the target set, both Ns are above and the difference is
stated in words**, because a control measured at N=3 against a target measured at N=20 is not a
control.

---

## 5. Gate outcome

**DETERMINED 2026-08-10. The outcome is M-b.**

> **UNCHANGED BY V3, 2026-08-12 — and this note exists so that the absence of a change is recorded
> rather than assumed.** §1.1's rule was fixed in advance, it is decided on `r0` against `r2` at the
> Target cell alone, and **V3 is not `r2` and cannot enter the rule.** V2 remains the best arm at
> `r2 = 0.2333`; V3 measured `r3 = 0.4000` and is **worse**. Applied to V3 for completeness only,
> the rule fails **both** clauses (`r0 − r3 = 0.1667 < 0.40`; Fisher `p = 0.150734`), so no reading
> of V3 produces a proceed outcome either. **The verdict below was not revisited, not softened and
> not relitigated.** What §3.6 changes is the *interpretation*, and that is recorded separately at
> §5.1 so the two are not confused.

**Record exactly one of the following, with the numbers from §3.1 and §3.5 that support it. Do not
record "pass", "fail", "improved" or "works"** (`acceptance.md` AC-GATE items 1 and 2).

| Outcome | Meaning | Consequence |
|---|---|---|
| **M-a** | Refusal was a routing artefact. V2 clears §1.1's rule against V0, and the emitted code works | `plan.md` T4 proceeds. `SPEC-ACCOUNT-001` proceeds as a prompt-design SPEC |
| **M-b** | Refusal is safety-training-driven. V2 does **not** clear §1.1's rule | `plan.md` T4's routing half does **not** proceed. `SPEC-ACCOUNT-001` stays gated closed. Open `SPEC-MODEL-001`. **V3 becomes owed (§3.6, S6).** `spec.md` S1 |
| **M-c** | The model complies but writes code that does not work | T4 proceeds. `SPEC-ACCOUNT-001` A1 inherits a narrowed question: the constraint is neither prompt wording nor model choice, but that IMAP is fiddly. D1 of that SPEC is decided against this |

### Outcome: **M-b**

**The rule, applied textually as §1.1 states it** (`acceptance.md` AC-GATE item 2a — this paragraph
is the rule word for word, with the measured values substituted and nothing else changed):

> **Proceed (M-a or M-c) if and only if `(r0 − r2) ≥ 0.40` absolute AND a one-sided Fisher exact
> test rejects at `alpha = 0.05`. Otherwise the outcome is M-b.**

| Clause | Required | Measured | Met? |
|---|---|---|---|
| **Absolute** | `(r0 − r2) ≥ 0.40` | `0.5667 − 0.2333` = **0.3333** | **NO** |
| **Significance** | one-sided Fisher exact `p < 0.05` | **`p = 0.008428`** | YES |
| **Conjunction** — both are required | | one clause failed | **NOT MET → M-b** |

**Supporting figures, all at N=30 per arm** (§3.1): `r0` = **17/30 = 56.7 %**, 95% Wilson
**[39.2 %, 72.6 %]**. `r2` = **7/30 = 23.3 %**, 95% Wilson **[11.8 %, 40.9 %]**. **Fence traps: 0 in
V0, 0 in V2, 0 across all 90 Target trials** — no DIRECT classification in either arm came from a
two-block reply (E7, AC-GATE item 2c). Under §1.1's threshold V2 needed **`k2 ≤ 5`** DIRECT trials in
30; **it recorded 7.**

**The gate is decided on the Target cell alone, and it has been.** No other cell is cited in support
of this outcome. **No multiplicity correction appears because none is needed** — §1.1 permits no
second test to bear on the decision (AC-GATE item 2b). In particular, and stated explicitly because
it is the sentence AC-GATE item 2b exists to forbid: **the fact that V1→V2 moved 40 points at
`p = 0.0019` does not rescue this outcome, and neither would any result from §3.2, §3.3 or §3.4.**
Those comparisons are diagnostic. This gate is `r0` against `r2`, and it did not clear.

**Refusal rate is not cited in reaching this outcome** (A4, AC-GATE item 2). It is a secondary,
human-coded overlay and it decided nothing. For the record only: of V2's 7 DIRECT trials, **6 open
with a first-person declination** and 1 mis-cites the DIRECT protocol; of V1's 19, **17 do**.

**Code correctness was NOT assessed for any arm** (§3.5). This outcome rests entirely on routing
counts. **The M-a/M-c distinction was never reached and is deferred to `SPEC-ACCOUNT-001` A1**, as
AC-GATE item 3 permits. **This is not a "pass" recorded under an unassessed M-c** — no proceed
outcome is being recorded at all.

#### Why this is M-b on the evidence and not merely on the arithmetic

**It was missed by two trials, and that deserves saying plainly rather than being buried.** Had V2
returned 5 DIRECT instead of 7, this document would record a proceed outcome. A reader is entitled
to ask whether M-b here is an artefact of a threshold. **Three things say it is not.**

1. **V1 — the routing repair, alone, which is `spec.md` D1 and the SPEC's actual proposal — produced
   no effect at all.** 19/30 against 17/30, in the wrong direction, `p = 0.785`. **The change this
   SPEC exists to make does not move the number it exists to move.**
2. **The removed clause was not what the model was relying on.** Under V0 the model quoted
   `:128-129` back as its justification (§2.1.1, trial #8). Under V1 that clause is gone and **all 19
   DIRECT replies decline anyway, none of them citing any routing rule** (§3.1). The justification
   changed; the behaviour did not. **That is what "safety-training-driven rather than prompt-driven"
   looks like in the data.**
3. ~~**What did move was the capability advertisement, not the routing rule** — V1→V2, 40 points. And
   §2.5's F1 predicted exactly that from the baseline, before §3.1 was read: this model follows
   worked examples, not rules.~~
   **AMENDED 2026-08-12 — see §3.6.** The single-factor attribution is withdrawn: V3 isolates the
   capability section and recovers only about half of V2's gain, at `p = 0.150734`. **What survives,
   and it is what item 3 needed for this outcome, is the part about V1:** the routing repair alone is
   null against V0 (`p = 0.785215`) and null in the pooled margin (`p = 0.357115`). **Item 3's role
   in §5 is to say that the SPEC's own proposed fix did not move the number, and V3 does not disturb
   that** — it disturbs only the further claim about what did.

**The honest residue, stated against the outcome.** V1 as run is a **weaker** treatment than the T1
draft — §3.0 records the sentence that was cut to satisfy N3's line-count pin, and it was the
sentence most directly aimed at the model's observed reasoning. **A stronger V1 might have measured
differently, and this run cannot exclude that.** ~~What it can say is that the *effect that did appear*
came from the half of the change that adds examples, which is not the half the routing hypothesis
predicts.~~ **AMENDED 2026-08-12:** what it can say is that **the effect that did appear required
both halves to be present**, and that no single-component arm reproduced it (§3.6). **The residue is
larger than this paragraph originally allowed**, because the cut sentence belongs to the very
component whose contribution the experiment turns out to have mis-attributed.

#### Consequences, which follow from M-b and are not optional

- **`plan.md` T4's routing half does not proceed.** `main.py:126-129` is not amended.
- **`SPEC-ACCOUNT-001` stays gated closed.**
- **`SPEC-MODEL-001` is opened** (AC-GATE item 4). **This obligation stands and the evidence argues
  against its premise — see §5.1, which does not resolve the tension and says whose decision it is.**
- **V3 becomes owed** (§3.6, S6, AC-GATE item 7). **PARTLY DISCHARGED 2026-08-12 — and not the part
  item 7 named.** V3's **Target** cell is run (§3.6, `r3 = 0.4000`); V3's **tool-reachable** cell and
  **control set** — the two item 7 actually requires — are **still unrun**. **Nothing may merge.**
- **`SPEC-EXAMPLE-EXEC-001`, or whatever it is named, is owed separately** for §2.5's F3. That is a
  pre-existing defect on `main`, independent of this SPEC, and it is not fixed here.

### 5.1 Interpretation note — what this M-b means, and what it does not

**ADDED 2026-08-12, after V3. This is interpretation and it is deliberately separated from the
verdict above, which is unchanged.** Nothing in this subsection may be read as revisiting §1.1's
rule or §5's outcome.

**M-b's label in §5's table is "refusal is safety-training-driven", and on this evidence that label
is doing more work than the measurement supports.** Stated plainly:

- **M-b here does NOT mean "prompt wording cannot fix this".** Under V2 the model routed CODE on
  **23 of 30** Target trials. **It complies 76.7 % of the time**, on the exact request that was
  reported as a refusal, purely because of prompt text. A disposition immovable by wording does not
  look like that.
- **M-b here does NOT mean "the model refuses regardless".** Prompt text moved the DIRECT rate from
  56.7 % to 23.3 %, and the pooled capability main effect is `p = 0.001601` (§3.6.3).
- **What M-b means, exactly:** the two changes tested, in the two wordings they were tested in,
  **did not reach the bar this SPEC set for itself in advance.** `(r0 − r2) = 0.3333` against a
  required 0.40; `k2 = 7` where `k2 ≤ 5` was needed. That is a threshold miss on a specific pair of
  treatments — **not a finding about the model's dispositions.**

**Which makes `SPEC-MODEL-001` the wrong SPEC to open on this evidence, and AC-GATE item 4 still
requires it.** The tension is real and it is recorded rather than resolved here:

- **The obligation:** AC-GATE item 4 says *"IF the outcome is M-b … `SPEC-MODEL-001` is opened"*. The
  outcome is M-b. **The obligation is live and this document does not waive it.**
- **The evidence against its premise:** `SPEC-MODEL-001` is a *change the model* SPEC. Its premise is
  that the constraint lies in the model rather than in the prompt. **Three measured facts point the
  other way** — 76.7 % compliance under V2; a significant pooled main effect of prompt text; and a
  gate missed **by two trials** on a threshold, not by a wall of refusals.
- **Why the criterion did not anticipate this:** **AC-GATE item 4 as written assumes an M-b produced
  by model refusal, and this M-b was produced by a threshold miss.** Those are different states of
  the world and the criterion has one branch for both. When it was written, the only imagined route
  to M-b was "the model declines whatever the prompt says" — the route actually taken was "the
  prompt moved the model a long way and the pre-registered bar was set further".
- **This document does not decide it.** Whether to open `SPEC-MODEL-001`, to amend AC-GATE item 4 to
  distinguish the two kinds of M-b, or both, **is a decision the SPEC author owes** — and it should
  be made in `spec.md`'s HISTORY under the same supersede-don't-rewrite discipline as every other
  amendment here, not by quietly not opening the SPEC. **A criterion that is silently skipped is
  worse than one that is amended in writing** (`acceptance.md` AC-GATE item 5's own reasoning,
  applied to item 4).

**What the numbers argue for instead, named concretely so it is a candidate and not a mood.** They
argue for a **stronger V2**, and there is a named candidate already in this record: the sentence cut
from the V1 draft to satisfy N3's line-count pin —

> *"Not holding the data yourself is NOT a reason to choose DIRECT: if the answer is reachable over
> the network, or computable, that is CODE."*

— which is aimed precisely at the reasoning V0 trial #8 exhibited and which **V3 trial #1 exhibited
again** (§3.6.5). **§3.0's disclosure that V1 as run was a weaker treatment than designed is
therefore load-bearing rather than a footnote, and it has been promoted in place.** The forcing
constraint is `tests/test_probe.py:237`'s `V0[:200] in text` acting together with N3's pin; a
stronger V1 needs one of those to move or a two-line phrasing nobody has yet written.

**Stated against its own interest, because this subsection is the one most likely to be quoted
selectively:** "a stronger V2 would clear the bar" is a **hypothesis, not a result.** V3 → V2 is
+16.7 points at `p = 0.133418` and does not establish that the routing half contributes anything at
all; §3.6.3 records that both interaction tests fail to reject. **The argument for a stronger V2 is
an argument about where to look next. It is not evidence, and re-running a treatment until it clears
a pre-registered bar is exactly what §1.1 exists to prevent** — any such run needs its own
pre-registration, written and committed before it starts (`spec.md` HISTORY v1.1.1's cheap fix,
still unavailable in retrospect and still available in prospect).

**Classified by:** the pre-registered rule at §1.1, applied by computation over
`v0-target.jsonl` and `v2-target.jsonl`. Fisher exact computed with `math.comb`, no library.

**Cross-checked against §1.0 item 3, which is the useful part of this line.** That item was written
**before** V2 ran, and it recorded — as evidence that the rule was non-degenerate — that
`k2 = 6…9` would clear Fisher at `p = 0.0036…0.034` while being **rejected by the absolute clause**.
The measured `k2 = 7` falls inside that stated band (`p = 0.008428`), and re-computing the endpoints
today reproduces them: `k2 = 6 → 0.003637`, `k2 = 9 → 0.033639`. **The outcome landed in a region
this document had already described in writing as an M-b**, which is the closest thing available
here to the pre-registration being checkable — and §1.0 is candid that it is not a substitute for
the git ordering that does not exist.

**Date:** **2026-08-10.**

---

## 6. What these runs do NOT establish

*This section is longer than §2–§4 combined. That is the honest ratio, and it is the ratio
`SPEC-CI-001/verification-T3.md` set for this repository.*

**Limits on the gate specifically — these are the ones that could change the outcome:**

- **M-b was missed by two trials.** `k2 = 7` where `k2 ≤ 5` was needed. At N=30 the difference
  between 5 and 7 is well inside sampling noise: `r2`'s 95% Wilson interval is
  **[11.8 %, 40.9 %]** and it **contains 16.7 %**, the threshold value. **This run does not
  establish that a true `r2` below the threshold is impossible; it establishes that the measured one
  was not.** A pre-registered rule is decided on the measurement, not on the interval, and that is
  the price of having a rule at all — but the interval is the honest description of what is known.
- **V1 as run was weaker than the T1 draft** (§3.0). The cut sentence was the one aimed most
  directly at the model's observed reasoning. **A stronger V1, and therefore a stronger V2, might
  have measured differently, and nothing here excludes it.** The trade was forced by N3's pin and
  `tests/test_probe.py:237` acting together, and it is recorded rather than absorbed.
- **One wording per variant.** V2 is one way of writing a capability section. A different phrasing,
  a different insertion point, or a different worked example is a different treatment, and this run
  says nothing about any of them. **"The capability section works" is not established; "this
  capability section moved this cell by 40 points" is.**
- **Code correctness was not assessed in any arm** (§3.5). **65** CODE trials across **four** arms,
  none executed, none read line by line. **M-b was reached from routing counts alone.**
- **The two components cannot be separated at these N, in either direction** (§3.6.3). V3 is
  distinguishable from neither V0 (`p = 0.150734`) nor V2 (`p = 0.133418`); both interaction tests
  fail to reject (Woolf/Wald `p = 0.1718`, permutation `p = 0.2743`) while the pooled capability main
  effect does reject (`p = 0.001601`). **The ratio-of-odds-ratios interval is [0.075, 1.59] —
  consistent with strong synergy and with mild antagonism.** This document has now made one
  single-factor attribution and withdrawn it; **it must not make the opposite one.**

**Limits on the baseline:**

- **Three of the five control prompts misroute at V0** (§2.4). The control set is a weaker
  instrument than its name implies, C4 has no downward room left at all, and R2's detection now
  rests mainly on C1.
- **F1's gradient is really two levels, not three** (§2.5). Off-example vs Target is `p = 0.431` —
  not distinguishable at N=20/30. The ordered table invites a stronger reading than the arithmetic
  supports.
- **F2 does not close `product.md` §6.1** (`spec.md` N8). It supplies the V0 denominator — a
  measured `0/20`, and `0/220` baseline-wide — and **§3.3's V2 row, which closes it, is not run.**
- **The intervals are wide.** `r0` [39.2 %, 72.6 %], `r1` [45.5 %, 78.1 %], `r2` [11.8 %, 40.9 %] at
  N=30. No point estimate in this document should be quoted without its interval.

**What is simply not run, listed so it is not mistaken for not needed:**

- **§3.2, §3.3 and §3.4** — off-example, tool-reachable and control cells under V1 and V2. These
  could not have changed §5 (§1.1 decides on the Target cell alone) but they are the diagnosis of
  *where* V2's effect came from, and that diagnosis does not exist.
- **§3.6's tool-reachable and control cells under V3** — **the two cells AC-GATE item 7 actually
  requires, and neither is run.** V3's Target cell was run instead; it is the most informative cell
  in the experiment and it discharges neither obligation. **R2's only remaining defence is
  unmeasured and nothing may merge** (S6).
- **§4** — not yet owed; nothing has shipped.

Candidates known in advance, and they still hold:

- **A rate is not a guarantee.** N trials at default temperature bound a probability; they do not
  establish that the model will never refuse. Nothing measured here makes a claim about any single
  future turn. Note in particular that **a clean 0/30 is not zero**: by the rule of three its 95%
  upper bound is about **11%**, which is roughly one turn in nine and is entirely consistent with a
  user having seen one refusal.
- **Routing is not correctness.** The classifier observes which protocol the model took, never
  whether the code it wrote would work. Except where §3.5 is filled, a fenced block is counted as
  compliance regardless.
- **One turn shape.** System message + one user message, no recall block, no conversation history —
  the first-turn shape (`spec.md` §2.4). A real session is not that, and the reported refusal came
  from a real session.
- **One model, one quantisation, one host.** Nothing here generalises to a different
  `CODERUNNER_MODEL`, and users may set one (`docker-compose.yml:78`).
- **One phrasing per cell.** A phrasing the probe did not try is a phrasing the probe says nothing
  about, and the reported defect arrived through a phrasing nobody predicted.
- **The control set is five prompts.** It is a smoke test for R2, not a characterisation of
  conversational routing.
- **Nothing here measures token cost** unless O4 was taken up, and the added prompt text is paid for
  on every turn of every session.
