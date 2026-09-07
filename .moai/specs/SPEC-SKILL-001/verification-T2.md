# SPEC-SKILL-001 — T2 measurement record

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. Acceptance criteria are in
> `acceptance.md`.

---

## STATUS: NOT YET RUN

**Created 2026-09-07 with its structure in place, its rule fixed, and every result cell empty.** No
turn has been measured for this SPEC. §1 below is complete; §2, §3, §4 and §5 read `—` throughout,
and this file is committed **on its own, containing no results**, before the first trial.

**There are no placeholder figures in this document and there must never be** (`spec.md` N2, N6). A
plausible-looking number written here as an illustration would, on a second reading by a second
person, be indistinguishable from data. This project has the discipline written down three times
already: `SPEC-KEYCHAIN-001`'s HISTORY names what was not run *"as not run and not as not needed"*;
`SPEC-PROMPT-001`'s record states in its header that no run produced it; and `product.md` §5.5 is a
retraction of a claim that was asserted rather than measured.

**Two preconditions must be discharged before anything below is filled** (`plan.md` §2.2):

- **P1 — the meter.** `meter.py` exists and is gated at 100 % (SPEC-SKILL-001 T1, merged as PR #16).
  **But no call site passes it a `Receipt` yet:** `main.py:1076` and `:1139` still call
  `prime_stream(stream_llm(client, …))` with two arguments. **T2-b is the wiring, and until it lands
  no turn produces a number for this file.** That is deliberate — T1 built the instrument and stopped
  before connecting it, so that the baseline could not be contaminated by a half-wired one.
- **P2 — the model.** `llama3.1:8b` on the compose `ollama` sidecar, reached at
  `http://ollama:11434` from inside the compose network. No host port is published for that service
  (`docker-compose.yml:21`), so a host-side run is **not the same measurement** and must not be
  recorded as one. Verified 2026-09-07: Docker is up, the sidecar is **not**.

---

## 0. What this record is not evidence about

Written before any figure exists, because these misreadings are the natural summary sentences and a
summary is what survives.

- **Nothing here is evidence that the skill registry works.** It measures what a turn costs and how
  long it takes, at the current tree, before any optimisation. It is a denominator, not a result.
- **Nothing here is evidence about answer quality.** A cheaper turn that answers worse is not
  measured by anything in this file. `acceptance.md` AC-GROUND is where that constraint lives, and it
  is a separate criterion with a separate gate.
- **Nothing here transfers across models.** Every figure is `llama3.1:8b`'s. `SPEC-MODEL-001`
  measured Phi-3.5 at a 131,072 context against llama's, and token costs are not comparable across
  them (`plan.md` R5). Every row carries the server's own model readback for this reason.
- **A token figure is not a latency figure.** `spec.md` U4 forbids a claim in one dimension from
  implying the other, and §1 sets the two targets separately because they may disagree.

---

## 1. The pre-registered rule

**THIS SECTION IS COMPLETE AND THIS FILE IS COMMITTED CONTAINING NO RESULTS** (`acceptance.md`
Scenario 5). A commit carrying this rule and no numbers is the only available demonstration that the
thresholds were not chosen after the numbers arrived.

**`SPEC-PROMPT-001` v1.1.1 records in full what it cost to be unable to demonstrate that ordering:**
its `verification-T3.md` claimed twice, in bold, that its pre-registration had been committed before
the run. It had not. The rule and the results it gated sat in one uncommitted working tree,
indistinguishable in git from having been written in a single pass after the numbers landed. The
document's own words: *the cheap fix is to commit the pre-registration on its own, before running
anything; it is unavailable only in retrospect.*

### 1.1 Stage 1 targets

| | Value |
|---|---|
| Date the rule was committed | **2026-09-07** |
| Commit containing the rule **and no results** | *(this commit)* |
| **Cost target** — reduction in prompt tokens per successful turn | **≥ 25 %** |
| **Latency target** — reduction in wall-clock per successful turn, **excluding `load_duration`** | **≥ 15 %** |
| Baseline | The median over N = 30 turns per task shape, at the tree this file is committed against |
| Statistical form | Median difference, N = 30 per shape, two-sided 95 % bootstrap confidence interval on the difference |
| Decision rule | Stage 1 **meets** a target when the median reduction is at or above its threshold **and** the 95 % interval on the difference **excludes zero**. Each target is decided **independently** |

**Why the two thresholds differ, recorded before either is measured.** The recall block alone can add
up to ~8 KB to a prompt (`memory.py:49-52`) against a system prompt of roughly 4 KB, so a quarter off
the token cost is a reachable target for a change that shortens what is sent. Latency is set lower
because **Ollama reuses a cached prompt prefix within a session**, so a size reduction may be absorbed
before it reaches the clock (`spec.md` §5 item 4). Setting them equal would have made one of them a
prediction rather than a target.

**`load_duration` is excluded and reported separately** (`spec.md` U5, N6). It is the model being
loaded into memory, nothing in this SPEC can reduce it, and on a cold container it dominates every
other term — so a comparison including it would measure whether the model happened to be warm.

### 1.2 The Stage 2 gate

| | Value |
|---|---|
| **Maximum acceptable false-reuse rate** | **0 observed in N = 30** |
| What a false reuse is | A retrieved record that is **wrong for the current task** — one whose stored solution, if replayed, would answer a different question than the one asked |
| Statistical form | Exact count at N = 30, one-sided. 0/30 carries a 95 % Wilson interval of **[0.000, 0.114]** |
| Decision rule | **S-a** requires **zero** observed false reuses **and** Stage 1 having missed at least one of its two targets. **Any** observed false reuse is **S-b** |

**Why the bar is zero and not a percentage.** Under C2 a false reuse costs prompt noise and the model
adapts or ignores it. Under replay it costs the user a **wrong answer, silently, with an
`Execution OK` panel over it** — the failure mode `product.md` §6.15 already documents for a
different cause. A threshold that tolerates one in thirty is a threshold that accepts that outcome
roughly once per thirty turns, and this SPEC is not willing to pre-register that.

**What 0/30 does and does not establish is stated at §6 item 2, and it is not what the number looks
like.**

### 1.3 Outcomes, admitted in advance

| | Outcome | Condition | What happens |
|---|---|---|---|
| **S-a** | Proceed | Zero false reuses at N = 30, **and** Stage 1 missed at least one target | T6 drafts the C2 amendment quoting the measured rate |
| **S-b** | Do not ship | Any false reuse observed | **Stage 2 does not ship.** C2 stands. Delivered value is the meter plus Stage 1 |
| **S-c** | Do not attempt | Stage 1 met **both** targets | Stage 2 is **not attempted**. A security-relevant constraint is not amended for a saving already banked |

**Three properties this rule has, each of which is why a clause is in it:**

1. **It names no observed value.** Every figure below §1 is `—` at the time this is written, and the
   rule must remain readable as a rule after they are filled.
2. **Each target is decided independently.** `spec.md` U4 forbids a claim in one dimension implying
   the other, so a rule that combined them into one pass/fail would launder exactly the confusion the
   requirement exists to prevent.
3. **It admits failure in advance.** S-b and S-c are outcomes, not excuses written later.

---

## 2. Provenance — what was measured, and against what

| | Value |
|---|---|
| Date of run | — |
| Tree measured (`main` sha) | — |
| Model tag, exactly as the server read it back | — |
| Quantisation | — |
| Context window | — |
| Host / architecture | — |
| Sidecar reachable at | — |
| Meter version (`meter.py` sha) | — |

*A rate without the model that produced it is not a measurement (`SPEC-MODEL-001` U3). The model tag
is the **server's own readback**, not the configured value.*

---

## 3. Baseline — per turn, at the current tree

### 3.1 Cost, by round trip (`spec.md` U1)

| Task shape | N | Round trip | `prompt_eval_count` median | `eval_count` median | Unmeasured |
|---|---|---|---|---|---|
| — | — | code | — | — | — |
| — | — | grounded | — | — | — |

### 3.2 Latency, by round trip, with `load_duration` broken out (`spec.md` U5)

| Task shape | Round trip | `total_duration` median | `load_duration` median | `prompt_eval_duration` median | `eval_duration` median |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

### 3.3 Component sizes, in **characters** (`spec.md` U6)

*These are sizes and not token counts. Per-message token attribution is not obtainable — the server
reports one `prompt_eval_count` for the whole prompt and exposes no tokenize endpoint (v1.1.1).*

| Component | Median size (characters) | Share of prompt |
|---|---|---|
| System prompt | — | — |
| Conversation history | — | — |
| Recall / skill block | — | — |
| Feedback injection | — | — |
| **Dominant component** | — | — |

**§3.3's last row is what selects between T3, T4 and T5** (`plan.md` R2). It is taken before any of
them is built, precisely so the answer is not chosen by whoever implemented first.

### 3.4 The illustration defect's share (`spec.md` O2)

| | Value |
|---|---|
| Turns in the sample matching the "explain X" shape | — |
| Their second-round-trip cost | — |

*Reported separately because that cost belongs to `SPEC-ILLUSTRATE-001` and two SPECs cannot both
bank the same saving.*

---

## 4. After Stage 1 (T3, T4, T5)

| Change | Cost reduction | 95 % interval | Latency reduction (excl. load) | 95 % interval | Target met? |
|---|---|---|---|---|---|
| T3 skill rendering | — | — | — | — | — |
| T4 second round trip removed | — | — | — | — | — |
| T5 bounded history | — | — | — | — | — |
| **Combined** | — | — | — | — | — |

---

## 5. Outcome

| | Value |
|---|---|
| Stage 1 cost target (≥ 25 %) | — |
| Stage 1 latency target (≥ 15 %) | — |
| False reuses observed at N = 30 | — |
| **Gate resolved to** | — |
| Reasoning | — |

---

## 6. What this record will NOT prove, however it comes out

Written now, so that it is not written later by whoever wants the result to mean more.

1. **It will not prove the skill registry is worth having.** It measures cost and time. Whether a
   shorter prompt produces an equally good answer is `acceptance.md` AC-GROUND's question, and
   nothing here answers it.

2. **0/30 does not establish a false-reuse rate below 2 %, and §1.2's threshold must not be read as
   if it did.** Zero observed in thirty carries a 95 % Wilson interval of **[0.000, 0.114]** — the
   true rate could be as high as **11 %** and still produce this result. What 0/30 establishes is
   that the rate is not *large*. The threshold is written as an exact count rather than a percentage
   for exactly this reason: *"zero in thirty"* is a statement about what was seen, and *"under 2 %"*
   would have been a claim the sample cannot support. **If Stage 2 ever ships, this paragraph is the
   one that says what its evidence was worth.**

3. **It will not distinguish a cost saving from a speed saving without saying so.** If the two
   disagree, §5 records both and names which target was met. A single headline number would hide
   precisely the finding `spec.md` §5 item 4 exists to anticipate.

4. **It will not transfer to another model, another host, or a warm cache.** Every figure is one
   model on one machine, and `load_duration` is excluded rather than absent.
