---
id: SPEC-PROMPT-001
version: "1.1.2"
status: "draft"
created: "2026-08-08"
updated: "2026-08-12"
author: "Chun Kang"
priority: "HIGH"
---

## HISTORY

### v1.1.2 (2026-08-12) — V3 ran, the gate did not move, and a causal conclusion this SPEC published is withdrawn

**The gate is untouched. The outcome is still M-b, on the same rule, with the same numbers, and §5
was not revisited.** `r2 = 7/30` against `r0 = 17/30`; the absolute clause required 0.40 and measured
**0.3333**. V3 measured `r3 = 12/30 = 40.0 %` — **worse than V2** — and clears neither clause
(`r0 − r3 = 0.1667`; Fisher `p = 0.150734`). Nothing about §1.1 or §4's rule changed, and no
threshold was reinterpreted after the fact.

**What changed is a conclusion, and it is the kind this SPEC exists to get right.**
`verification-T3.md` §3.1 concluded — in bold, with a `p`-value beside it — that **"the routing
repair does nothing; the capability advertisement does everything"**. **That conclusion is
withdrawn.** It is struck through in place at §3.1, marked superseded by the new §3.6, and the reason
is stated there rather than the text being replaced:

**With only V0, V1 and V2 there is no arm in which the capability section appears without the routing
repair.** "The capability section is the active ingredient" and "the two only work in combination"
are then **observationally identical** — they predict the same 17/30, 19/30, 7/30. **Two arms cannot
separate a main effect from an interaction.** V3 is the third arm, and it does not reproduce V2: the
capability section alone recovers **16.7 of V2's 33.3 percentage points** and misses significance.

**The four arms are a complete 2 × 2 factorial** — verified against `probe/variants.py`, not inferred
from names: the 19-line capability block added to V0 to make V3 is **byte-identical** to the block
added to V1 to make V2, and `V3 → V2` diffs to exactly the two routing lines.

| arm | composition | N | DIRECT | rate | 95% Wilson | traps | Fisher vs V0 |
|---|---|---|---|---|---|---|---|
| **V0** | baseline | 30 | 17 | 0.5667 | [0.392, 0.726] | 0 | — |
| **V1** | routing repair only | 30 | 19 | 0.6333 | [0.455, 0.781] | 0 | **0.785215** — null, wrong direction |
| **V2** | repair + capability | 30 | 7 | 0.2333 | [0.118, 0.409] | 0 | **0.008428** — rejects |
| **V3** | capability only | 30 | 12 | 0.4000 | [0.246, 0.577] | 0 | **0.150734** — null |

**Neither component alone clears significance against V0; only the combination does.** That is exact
and it is the strongest supported statement about the two components.

**What was NOT written, and the arithmetic that forbade it — recorded because the temptation ran the
other way.** It would have been natural to replace the withdrawn claim with *"the effect is an
interaction, not a main effect"*. **The data do not license that either**, and writing it would
repeat the same error in the opposite direction — treating "significant vs not significant" as itself
a significant difference. Computed over the 120 Target trials:

- **The pooled main effect of the capability section is large and significant**: 19/60 = 0.3167
  against 36/60 = 0.6000, Fisher one-sided **`p = 0.001601`**. The pooled routing effect is null
  (`p = 0.357115`). **"No main effect" is contradicted outright.**
- **Super-additivity is present as a point estimate only**: additive prediction for `r2` is 0.4667
  against 0.2333 observed, an excess of **0.2333**.
- **It is not established**: Woolf/Wald on the ratio of odds ratios gives **`p = 0.1718`**; a
  200 000-draw permutation test on the interaction contrast gives **`p = 0.2743`**. The 95 % interval
  on the ratio of ORs is **[0.075, 1.59]** — consistent with strong synergy and with mild antagonism.

**So the honest statement is narrower than either single-factor story**, and `verification-T3.md`
§3.6.3 states it as a list of what is and is not established. **V3 sits between V0 and V2 and is
separated from neither at N=30.** It removes the entitlement to the strong claim; it does not confer
a replacement one.

**Three consequences that are not editorial:**

- **AC-GATE item 7 is NOT discharged.** Item 7 requires V3 at the **tool-reachable cell (N=20)** and
  across the **full control set (5 × N=30)**. What ran is V3 at the **Target cell (N=30)**, which item
  7 does not name. **Both required cells remain unrun, R2's only remaining defence is unmeasured, and
  nothing may merge** (S6).
- **AC-GATE item 4's obligation to open `SPEC-MODEL-001` stands, and the evidence argues against its
  premise.** Under V2 the model complies on **23 of 30** Target trials — 76.7 % — and prompt text has
  a significant pooled main effect. **This M-b was produced by a threshold miss, not by model
  refusal, and item 4 as written did not anticipate that distinction**; it has one branch for both
  states of the world. `verification-T3.md` §5.1 records the tension, declines to resolve it, and
  names it as a decision the SPEC author owes — to be taken here in HISTORY rather than by quietly
  not opening the SPEC.
- **§3.0's disclosure that V1 as run was a weaker treatment than drafted is promoted from footnote to
  load-bearing.** The cut sentence — *"Not holding the data yourself is NOT a reason to choose
  DIRECT…"* — belongs to the very component whose contribution was mis-attributed, and **V3 trial #1
  quotes the `:128-129` clause back exactly as V0 trial #8 did**, in the one variant arm that retains
  it. A stronger V1 requires `tests/test_probe.py:237`'s `V0[:200] in text` or N3's pin to move, or a
  two-line phrasing nobody has written. **That is a candidate for where to look next, not a result**,
  and any re-run needs its own pre-registration committed before it starts.

**The design lesson, recorded as evidence rather than as satisfaction.** **V3 existed only because
`plan.md` T3b noticed that under M-b the shipped prompt would be `V0 + capability` — a string none of
V0, V1 or V2 is — and added a cell for a branch the SPEC expected not to take.** `verification-T3.md`
called it *"a formality"*. **That contingency cell became the most informative cell in the
experiment**, and without it this SPEC would have shipped a single-factor causal attribution its own
data never supported. **The generalisable form: measure the configuration you would actually ship,
not only the two ends of your hypothesis.**

**Two further corrections found by re-deriving figures rather than reading them** (N7):

- **`verification-T3.md` §2.0's claim that "every CODE trial had exactly `1`" fence match is false.**
  Recomputed over all 310 records, `fence_matches == 2` occurs once — `v0-tool-reachable.jsonl` #14 —
  correctly classified CODE, because `extract_last_python_block()` takes the **last** block and it is
  non-empty. **It changes no rate.** The trap E7 was written for — a DIRECT classification from
  `findall() → ['']` — remains **0 in 310**. Struck through in place with the measurement beside it,
  because the sentence overstated what had been checked in the direction that flatters the
  instrument.
- **The unassessed-CODE count is 65 across four arms, not 60.** 13 + 11 + 23 + 18, counted from the
  JSONL. **Code correctness is still NOT assessed on any trial of any arm**, and the M-a/M-c split
  stays deferred to `SPEC-ACCOUNT-001` A1.

**Provenance, re-verified rather than carried forward.** 310 records; `main.py` sha256
`ff5a488f…` **identical across all of them and still matching the working-tree file**; one model tag,
one digest, one quantisation, one host, one Ollama version. All 310 stored classifications were
**re-derived from the stored reply text** by importing `main.extract_last_python_block` —
**0 disagreements on `classification`, 0 on `fence_matches`**. `harness_commit` now takes three
values, the third being V3's, for the same harmless reason as the second.

**Not changed:** no requirement, no threshold, no acceptance criterion, no gate outcome. **§4's rule
is untouched and §5's verdict was not revisited, softened or relitigated.**

### v1.1.1 (2026-08-09) — A false claim about this SPEC's own evidence, withdrawn

**`verification-T3.md` claimed twice, in bold, that the pre-registration "was committed" before T2
ran. It was not. Nothing was committed.** Found by quality review, verified independently before
being acted on:

```
$ git show HEAD:.moai/specs/SPEC-PROMPT-001/verification-T3.md \
    | grep -cE 'r0|Fisher|0\.40|alpha|pre-regist'
0
$ git status --porcelain .moai/specs/SPEC-PROMPT-001/
 M acceptance.md    M plan.md    M spec.md    M verification-T3.md
```

The committed v1.0.0 of that file has **no §1.1 and no §1.2 at all** — its gate was the superseded
*"refusal rate"* / `N ≥ 10` formulation. So the rule and the results it gates sit in **one
uncommitted working tree**, indistinguishable in git from having been written in a single pass after
the numbers landed.

**This is the worst class of error this SPEC could contain, and the reason is structural rather than
moral.** A5's whole argument for pre-registration is that *"a threshold chosen after the numbers
arrive is not a gate"*. A false claim that the threshold was committed first does not merely
overstate the evidence — **it manufactures the exact property whose absence would invalidate the
gate.** It is also the one error that this SPEC's own N7 discipline was least likely to catch, because
N7 polices *figures*, and this was a claim about *process*.

**`spec.md` §4 never made the claim.** Its wording has always been the accurate *"written into
`verification-T3.md` §1 **before T2 runs**"*. The overclaim was local to `verification-T3.md`, which
means it was not a considered position — it was a stronger sentence written where a weaker one
belonged, in the file with the most to gain from it. Both sites now carry §4's wording.

**What was done, and what deliberately was not:**

- Both false claims **replaced** with the accurate weaker wording. **T2 was not re-run** — the data
  are sound; it is the claim about them that was not.
- **`verification-T3.md` §1.0 added**, before the rule it qualifies, stating that the ordering is
  **not corroborated by git**, that the amendments and results were produced together, and that
  **this limitation is permanent and no later commit can repair it** — committing now yields one
  commit containing both, which is the artefact a fitted rule would also produce.
- **The circumstantial evidence recorded as evidence, with its weight**, not as reassurance: the
  rule names no observed value (**weak**); the threshold is non-trivial in both directions, demanding
  `r2 ≤ 5/30` against `r0 = 17/30` (**moderate**); and the rule is **non-degenerate** — re-derived
  2026-08-09 with `math.comb`, the 0.40 absolute clause **strictly dominates** Fisher, with
  `p ≤ 0.00139` across every `r2` that satisfies it, while `k = 6…9` clear Fisher and are rejected by
  the absolute clause (**moderate**). None of it substitutes for the git ordering and §1.0 says so.
- **`acceptance.md` AC-GATE item 5 amended**, because its `git log` form is now permanently
  unsatisfiable for this SPEC. It is replaced by a check carried **inside the data** — `main.py`'s
  sha256, recorded in all 30 trial records and constant across them — with the reason for the
  amendment written beside it. **Amended rather than deleted, and rather than quietly ticked:** a
  criterion that cannot be met is not evidence, and leaving it to be ticked converts an unmet
  requirement into a claim.

**Three lesser corrections in the same pass:**

- **`.gitignore:92`'s `*.log` was silently swallowing `probe-runs/*.progress.log`** — one of the two
  evidence artefacts. `git add` would have taken the JSONL and dropped the log **without saying so**,
  which is the same failure mode as a vacuous parser: the absence looks like a clean result. A
  negation rule now tracks probe-run logs, verified with `git check-ignore -v`.
- **An untraceable figure removed from §2.1.** *"Fourteen close with a variant of…"* reconciles to no
  definition: measured, the exact substring gives **8**, admitting *"something else"* gives **9**,
  admitting *"feel free to ask"* gives **11**. The matching rule is now stated and all three numbers
  reported. It decided nothing — but a document whose entire value is that its figures trace cannot
  carry one that does not.
- **Three stale not-run markers corrected**, all understating what had been run: §2's preamble said
  *"Not yet run"* while §2.1 was complete, and §5 said *"nothing has been run"* and *"§3.1 is empty"*
  when `r0` was in it.

**Not changed:** no requirement, no threshold, no figure, and no acceptance criterion other than
AC-GATE item 5. **The gate itself is untouched** — `(r0 − r2) ≥ 0.40` and one-sided Fisher at
`alpha = 0.05`, on the Target cell alone. What changed is the strength of the claim this SPEC makes
about **when** that rule was written.

**The cheap fix, named for whoever writes the next one:** commit the pre-registration **on its own,
before running anything**. It costs one commit and it is the only thing that would have made this
checkable. It is unavailable only in retrospect.

### v1.1.0 (2026-08-08) — Five corrections, taken before the instrument was built

**All five were found by re-verifying v1.0.0's own evidence rather than by reading it.** Four of them
correct a claim this SPEC made about the tree; the fifth closes a hole in the SPEC's own logic that
would have shipped an unmeasured prompt. None of them is deleted below — each is struck through,
marked superseded, and given the reason it stopped being true, in the discipline
`SPEC-KEYCHAIN-001` §2.4 and `SPEC-MEMORY-001` C6 established for this repository. **A measurement
that was correct when taken is not an error, and erasing it destroys the only record of why the
wrong conclusion was reasonable.**

**A1 — the Ollama precondition is falsified, and the half of it that survives is the important
half.** v1.0.0 recorded the probe as *blocked*: no host binary, `localhost:11434` → `http_code=000`,
therefore "the probe cannot be run from where the SPEC was written". **The two facts still hold and
the conclusion does not.** Re-verified 2026-08-08: the Docker daemon is running; `coderunner-ollama`
is **Up and healthy**; `docker exec coderunner-ollama ollama list` reports **`llama3.1:8b`
(`46e0c10c039e`, 4.9 GB)** and `nomic-embed-text:latest` (274 MB); `coderunner-ai:latest`
(`63b37a80bfb7`) is built and present. There is still no host `ollama` binary and `localhost:11434`
still returns `000` — **because `docker-compose.yml:28` publishes no port for the `ollama` service,
deliberately**, and says so: *"Kept internal to the compose network — no host port exposure
needed."* (v1.0.0's own draft of this note cited `:21`, which is the line reading `services:`; the
comment is at `:28`, verified by `sed`.) So `http_code=000` is not evidence of an absent model. It
is evidence of a **design decision working**, and v1.0.0 read a healthy system as a broken one. The
probe was never blocked; it was only unreachable from the one place nobody needed to reach it from.

**A2 — `tools.py` is not gated, and the SPEC's evidence for saying it was does not say it.**
v1.0.0's `plan.md` §0 listed *"a `tools.py` that is gated and tested, so T5 lands in a covered
module"*, citing `structure.md:234`. Verified 2026-08-08: `pytest.ini:57-62` carries `--cov` for
`memory`, `recall`, `vectorstore`, `params`, `settings`, `keychain` and **no `--cov=tools`**;
`conftest.py:205-212`'s `PER_FILE_COVERAGE_TARGETS` has **no `tools.py` entry**;
**`tests/test_tools.py` does not exist**. `structure.md:234` is a row in a table headed *"Why it is
testable in isolation"* — **an aspirational list of testing targets, not a record of coverage**.
Reading it as coverage is the same category error as reading a `COPY` line as proof of an import,
which `SPEC-KEYCHAIN-001` AC-IMAGE was written about. **T5 is therefore materially larger than
v1.0.0 stated**: it is the first test file `tools.py` has ever had, plus a two-edit gate
registration — `pytest.ini`'s `--cov=tools` **and** `conftest.py`'s target entry, **both or
neither**, because `pytest.ini:42-46` records that an entry without a matching `--cov` makes
`cov.report()` raise and fails the session.

**A3 — a fenced example in the new prompt section would fail CI, and would re-arm a trap this
repository has already measured.** `tests/test_source_seam.py:547` asserts
`prompt.count("```") == 2` — exactly one fenced block in the whole of `SYSTEM_PROMPT`. Any new
capability section written with fenced code blocks breaks that assertion outright. Worse, it raises
the odds of the failure recorded at `tests/test_source_seam.py:533-548`: with two fenced blocks in
the model's reply, the closing fence of the first pairs with the opening fence of the second,
`CODE_BLOCK_RE.findall()` returns `['']`, `extract_last_python_block()` returns the empty string,
and the turn **silently classifies DIRECT** — which is the exact branch this SPEC exists to stop
firing. So the SPEC would have been teaching, by example, the form that produces the defect. **New
prompt material is indented and unfenced** (N9), matching the existing examples at `main.py:146-153`
and `main.py:162-163`, neither of which uses a fence.

**A4 — the gate had no machine-decidable endpoint, and now it has one, pre-registered.** S1 and
**AC-GATE** decided the gate on *"refusal rate"*. E6 defines the classifier for the **DIRECT** rate.
**These are different quantities**: a refusal is a human-coded subset of DIRECT — a turn that routes
DIRECT because the model answered conversationally is not a refusal, and a reply with two fenced
blocks classifies DIRECT while refusing nothing at all. Deciding a gate on the human-coded quantity
while defining only the machine-coded one is how a gate becomes an argument. **Resolved: the gate is
decided on the DIRECT rate**, machine-decided by `extract_last_python_block()` returning falsy.
Refusal rate is retained as a **secondary, human-coded overlay** (O3 supplies the phrasings) that
**does not decide the gate**. The full decision rule — threshold, test, alpha, and the single cell
it is evaluated on — is **written into `verification-T3.md` §1 now, before T2 runs**, because a
threshold chosen after the numbers arrive is not a gate.

**A5 — the M-b branch would have shipped a variant no cell measures.** V2 is defined as V1 + the
capability section. Under M-b the routing repair (V1) does **not** ship, but the `tools.py`
advertisement still does — because advertising a helper has no safety component, which §3.4 already
says. What ships under M-b is therefore **`V0 + capability`**, and **no cell in the design measures
that prompt**. The SPEC would have shipped, on its own most-likely-adverse branch, the one variant
it never looked at. **Resolved: V3 = V0 + capability section**, a **conditional** variant run
**only** on the M-b branch, at the tool-reachable cell (N=20) and across the control set
(5 × N=30). It is recorded as a conditional obligation — work owed **if** M-b is reached, not work
to do now.

**N per cell rises from v1.0.0's `N ≥ 10` to Target 30 / off-example 20 / tool-reachable 20 /
control 30 per prompt, and the arithmetic is the reason.** At N=10 per arm a two-proportion test has
usable power only against a swing of roughly **50 percentage points** — so `N ≥ 10` could have
returned "no significant difference" for a repair that moved routing by 40pp, and the SPEC would
have recorded M-b on a measurement structurally unable to see M-a. The control side is worse,
because its question is **non-inferiority**: by the rule of three, observing 0 failures in 10 trials
bounds the true regression rate only at **30%**; at 30 trials it bounds it at **10%**. A control set
that cannot exclude a 30% regression is not a defence against R2, and R2's blast radius is every
turn of every session. **If budget forces a cut, cut the NUMBER of control prompts (floor 3), never
N below 20** — three prompts at N=30 is a measurement; five at N=6 is a rumour.

**What this amendment does not change.** No requirement was weakened, no acceptance criterion was
removed, and the three-outcome classification (M-a / M-b / M-c) stands exactly as written. The gate
is now harder to pass than v1.0.0's, not easier: it must clear a pre-registered absolute threshold
**and** a significance test, on one named cell, with no other cell permitted to rescue it.

**T1 and T2 (partial) landed under this version. What was measured, and what was not.**

The harness is built (`probe/`, `tests/test_probe.py`), and the **V0 Target cell has been run at
N=30**: **DIRECT rate `r0` = 56.7 % (17/30), 95% Wilson [39.2 %, 72.6 %]**, against `llama3.1:8b`
Q4_K_M, digest `46e0c10c039e…`, Ollama 0.32.1, on the compose sidecar. **Zero** trials hit the
two-fence trap, and all 17 DIRECT trials were read and are genuine refusals — so in this cell the
gated quantity and the secondary overlay coincide. Full record in `verification-T3.md` §1–§2.1.

**The anecdote is now a rate, and the rate is high.** The turn refuses more often than not, and the
interval excludes everything below 39%. `n=1` has become 30.

**The diagnosis was confirmed in the model's own words, which was not an anticipated outcome.**
Trial #8 routed DIRECT saying *"Since this task requires computation on data (your Gmail account)
**which I don't have access to**, I'll follow the DIRECT protocol"* — quoting `main.py:128-129` back
as its reason. Trial #1 routed CODE from the identical prompt saying *"Since this task requires
computation on **live data provided by the user**, I will follow the CODE protocol"*, and then wrote
`imaplib` with `# @param` declarations. **Same prompt, same model, same turn shape, opposite
resolutions of the same clause.** §2.1.1 records both verbatim. This is the contradiction in §2.1
observed rather than inferred, and it is the strongest evidence this SPEC has for D1.

**Named as not run, not as not needed:**

- **§2.2 off-example, §2.3 tool-reachable and §2.4 the control set — all V0, all NOT RUN.** 190
  trials at the observed rate is 3–4 hours; the gated cell was run first and the run then stopped.
  **The control baseline's absence is the most consequential of the three**: R2's only defence is a
  before/after comparison, and the "before" half does not yet exist.
- **Code correctness was NOT assessed** for any of the 13 CODE trials. The M-a/M-c distinction is
  explicitly deferred (`verification-T3.md` §3.5).
- **T3, T4 and everything downstream are untouched.** `main.py` is unmodified — verified by sha256,
  constant across all 30 records.
- **`MIN_PASSED` was NOT raised.** The suite goes 544 → 574 with `tests/test_probe.py`; E5 requires
  that floor to be raised from a measured `junitxml` run, and that is T8's work, not this one's.

### v1.0.0 (2026-08-08) — Initial specification

Written from a refusal. A user typed *"check my gmail for recent 7 days and let me know the
interview opportunities"* and the model answered, under the `Thought · attempt 1` panel
(`main.py:1021`):

> I can't help you with accessing your personal email account. Is there anything else I can assist
> you with?

That is a refusal to a legitimate request — a local single-user tool being asked to read its own
user's mailbox with that user's own credentials — and the product declined work it is capable of
doing. `imaplib` is in the image's standard library, `# @param NAME: secret = "…"` already collects
a password with `getpass`, and `SPEC-KEYCHAIN-001` already stores it so it is typed once. Every
part existed. Nothing connected them, because the only party who could connect them was never told
they existed.

**The obvious diagnosis is wrong, and the correct one is one measurement.** The obvious diagnosis
is *"`SYSTEM_PROMPT` under-advertises capability"*. The measured one is sharper and explains more:

**The prompt contains three mutually inconsistent routing rules, and what actually resolves them is
its example set rather than its statements.**

- `main.py:128-129` — *"needs live data you don't have"* → **DIRECT**
- `main.py:143-145` — *"Network access IS allowed for scraping when the answer requires external /
  live data"*
- `main.py:174` — *"If in doubt, prefer the CODE protocol with a web lookup."*

Three rules, and no rule that orders them. What disambiguates them in practice is the concrete
example set at `main.py:146-153`: `wttr.in`, the Wikipedia REST API, DuckDuckGo HTML search. Inside
that set the model takes CODE. Outside it, `:128-129` wins. Gmail is outside it, so the turn routed
to DIRECT, produced no fenced block, and `main.py:1032-1034` returned without executing anything:

```
code = extract_last_python_block(thought)
if not code:
    status("💬", "LLaMA", "No code produced — returning direct answer.", "yellow")
    return
```

**One grep supports the whole diagnosis and it explains two defects rather than one.** Counted
2026-08-08 across `main.py:122-182`, the entire `SYSTEM_PROMPT`:

| Token | Occurrences |
|---|---|
| `email` | **0** |
| `imap` | **0** |
| `account` | **0** |
| `gmail` | **0** |
| `mail` | **0** |
| `tools` | **0** |
| `web_search` | **0** |
| `credential` | **0** |
| `keychain` | **0** |
| `secret` | 2 |
| `password` | 1 |

The first five zeros are the refusal. **The sixth and seventh are `product.md` §6.1**, which this
project already wrote down and already ranked:

> `run_python()` copies `tools.py` into every sandbox and an inline comment names the intended usage
> — *"`from tools import web_search` resolves without PYTHONPATH"*. But `SYSTEM_PROMPT` **never
> mentions `tools.py` or `web_search`**. … The model has no way to discover the helper, so all 99
> lines of `tools.py` are effectively dead code. **This is the single most concrete disconnect in
> the codebase.**

`structure.md` §5.3 records the same finding independently. **The Gmail refusal is a second
instance of a defect class this repository has already documented, named, and ranked first.** That
is the argument for this SPEC's `HIGH` priority, and it is why the general fix is specified before
the specific feature: closing the routing contradiction and advertising the sandbox's real
capability surface **resolves §6.1 as a side effect**, and it may resolve the reported refusal
outright. `SPEC-ACCOUNT-001` exists to find out whether anything is left over.

**The load-bearing unknown is not addressed by any of the above, and this SPEC refuses to assume
it either way.** Does `llama3.1:8b` (`docker-compose.yml:46`, `:78`) comply once correctly
instructed, or does it refuse from its own safety training regardless of prompt wording? If the
latter, this is a model-selection problem and every hour spent on prompt wording is wasted. §4
makes that a **gate** (T3) placed before any prompt-wording effort, with **three** outcomes rather
than two — the third, *complies but writes code that does not work*, is the one that most changes
the downstream design and was not named in the brief that produced this SPEC.

**Not measured, and named as not measured.** No probe has been run. ~~Ollama is not reachable from
the host this SPEC was written on — `command -v ollama` fails, there is no binary at
`/usr/local/bin/ollama` or `/opt/homebrew/bin/ollama`, and `localhost:11434` returns
`http_code=000` (measured 2026-08-08).~~ **SUPERSEDED at v1.1.0 — see A1.** *Those three facts are
still true and they never meant what this paragraph concluded. `localhost:11434` returns `000`
because `docker-compose.yml:28` publishes no host port for the `ollama` service, deliberately. The
sidecar is Up and healthy and serves `llama3.1:8b` (`46e0c10c039e`) — re-verified 2026-08-08. The
probe was not blocked; it was unreachable only from the host namespace, which is where nothing needs
to reach it from.* The probe must therefore run against the compose `ollama`
sidecar, which is where `llama3.1:8b` actually lives. That is a **precondition of T1**, recorded
here so it is a plan item rather than a discovery. `verification-T3.md` exists with its structure
in place and its results empty.

**Two citation corrections found while writing this, recorded rather than swept.** `product.md`
§6.1 cites `SYSTEM_PROMPT (main.py:100-151)`; the prompt is `main.py:122-182`. `tech.md` §8.7 cites
`tools.py:91-92` for the swallowed exception and `tools.py:95-96` for the outer handler; measured,
they are `tools.py:90-91` and `tools.py:94-95`. Both fall inside this SPEC's scope and are fixed by
it (§7 item 6). `structure.md`'s tree and its `main.py:210-211` citation for the sandbox copy are
further behind — the copy is at `main.py:507` — and `SPEC-KEYCHAIN-001` §2.4 already records that
`structure.md` is several SPECs stale. This SPEC fixes §5.3 because it edits it and leaves the rest
(§8 item 6).

---

# SPEC-PROMPT-001 — Capability advertisement and routing repair in `SYSTEM_PROMPT`

**Title:** Make the prompt's stated capability surface match the sandbox's actual one, by repairing
three contradictory routing rules and advertising `tools.py` — measured before and after, against
the model that has to act on it

## 1. Scope statement

`SYSTEM_PROMPT` (`main.py:122-182`) is the only channel through which the model learns what the
sandbox can do. It currently understates that surface in two ways which are the same defect:

1. Its routing rules contradict each other (`:128-129` vs `:143-145` vs `:174`), and the
   contradiction is settled in practice by the worked examples at `:146-153` rather than by any
   rule. Anything outside those three domains falls through to DIRECT.
2. It never names `tools.py` or `web_search`, although `run_python()` copies the module into every
   sandbox (`main.py:507`) and a comment beside that line states the intended usage
   (`main.py:510`).

This SPEC repairs (1), closes (2), and — because a prompt change is a **global** change to a
program that has **zero** tests for `main.py` (`structure.md:56`) — builds the instrument that
proves either claim. The instrument is the deliverable that outlasts the edit.

**No behaviour of the Python code changes** beyond one error-handling path in `tools.py` (§7 item
4), which is in scope only because this SPEC promotes that module from dead code to live code and
must not ship a live module with a known-invisible failure mode.

**This SPEC does not specify account access.** It may nonetheless fix the reported refusal, and
whether it does is measured in T3 and recorded in `verification-T3.md`. `SPEC-ACCOUNT-001` is gated
on that result.

---

## 2. Verified environment

Everything in §2 was measured on 2026-08-08 against the working tree at `b8b3259`+ (branch
`feature/SPEC-INPUT-001`), on macOS/arm64.

### 2.1 The prompt's own text, by line

| Anchor | Lines | Text (abridged) |
|---|---|---|
| `SYSTEM_PROMPT` assignment | `main.py:122` | `SYSTEM_PROMPT = textwrap.dedent(` |
| Prompt body | `main.py:124-181` | ends `).strip()` at `main.py:182` |
| **Routing rule** | `main.py:126-129` | *"If NO (the question is conversational, opinion, general knowledge, or **needs live data you don't have**), follow the DIRECT protocol."* |
| **Network rule** | `main.py:143-145` | *"Network access IS allowed for scraping when the answer requires external / live data (weather, news, stock prices, definitions, etc.)."* |
| **The example set** | `main.py:146-153` | `wttr.in`; `en.wikipedia.org/api/rest_v1/…`; `duckduckgo.com/html/?q=…` |
| Library list | `main.py:142` | *"Available libraries: stdlib, requests, beautifulsoup4 (bs4), lxml."* |
| **The `@param` passage** | `main.py:158-166` | pinned by `SPEC-KEYCHAIN-001` N2 — see §2.3 |
| DIRECT protocol | `main.py:169-174` | ends *"If in doubt, prefer the CODE protocol with a web lookup."* |

### 2.2 The token count, and why it is one measurement for two defects

Counted across `main.py:122-182` on 2026-08-08: `email` **0**, `imap` **0**, `account` **0**,
`gmail` **0**, `mail` **0**, `tools` **0**, `web_search` **0**, `credential` **0**, `keychain`
**0**. Only `secret` (2) and `password` (1) appear, and both are inside the `@param` passage.

The zeros for `tools` and `web_search` are `product.md` §6.1 and `structure.md` §5.3, stated as a
number. The zeros for the mail tokens are the reported refusal. **They are the same measurement**,
and that is the whole reason this SPEC is written as a general repair rather than as a Gmail fix.

### 2.3 The N2 constraint, resolved by line range rather than by reading

`SPEC-KEYCHAIN-001` N2 (`.moai/specs/SPEC-KEYCHAIN-001/spec.md:840`) reads:

> **N2** Generated code **shall not** be instructed or expected to read `os.environ`. The
> `SYSTEM_PROMPT` at `main.py:140-148` is **unchanged**: the model declares `# @param` and uses a
> bare name, and does not learn that a keychain exists.

Read loosely, that sentence forbids this SPEC entirely. It does not, and the difference is settled
by resolving the citation against the tree **as it stood when N2 was written** rather than against
the tree today.

**Verification method, stated so the next reader re-checks it rather than trusting it:**

```
git show 1d5fff1:main.py | sed -n '140,148p'
```

`1d5fff1` is the commit that added `.moai/specs/SPEC-KEYCHAIN-001/spec.md`. Run on 2026-08-08, that
command prints **exactly** the nine-line `@param` passage:

```
140      - If you need a value only the user has (a city, an API key, a file
141        path), do NOT call input(). Declare it as a comment INSIDE this same
142        python block, before first use, then just use the name:
143
144          # @param city: str = "Which city?"
145          print(city)
146
147        Types: str, int, float, secret. Use secret for keys and passwords —
148        it is masked when typed. Never emit a second fenced block for these.
```

Not the whole prompt. The nine lines that define the `@param` grammar. The `§9` traceability row of
that SPEC (`spec.md:932`) uses the identical range under *"Explicitly not amended"*, which is a
second, independent confirmation that the range was deliberate rather than approximate.

**Therefore N2 forbids exactly two things:**

1. Instructing generated code to read `os.environ`.
2. Altering the `@param` declaration passage, or revealing to the model that a host keychain
   exists.

**N2 does not pin** the routing rule at `:126-129`, the network rule at `:143-145`, the example set
at `:146-153`, the library list at `:142`, or the DIRECT protocol at `:169-174`. A passage added
elsewhere in `SYSTEM_PROMPT` leaves the pinned range semantically untouched and is **not** a
breach. This SPEC's N1 and N2 adopt both of N2's clauses verbatim so that the constraint is
enforced rather than merely respected.

**One second-order effect, named because it looks like a breach and is not.** Prompt text that
makes the model *more* likely to declare `# @param … : secret` causes *more* keychain sourcing.
That is `SPEC-KEYCHAIN-001` working as designed. N2 governs what the model is **told**, not how
often the mechanism it was already told about fires.

**The citation is already stale and this SPEC must not create a third generation.** The pinned
passage sits at `main.py:158-166` today — **+18 lines** since `1d5fff1`. `SPEC-KEYCHAIN-001` §2.4
devotes a section to exactly this failure in `tech.md`, so inheriting it silently here would be
indefensible. Two consequences, both requirements: new prompt material is inserted **below** the
`@param` passage (N3), and N2's range is re-cited to its post-change value **in the same commit**
(E4).

### 2.4 The turn mechanics that produced the observed output

| Fact | Evidence |
|---|---|
| Streamed reply is rendered in a panel titled `Thought · attempt {attempt}` | `main.py:1021` |
| The fenced block is extracted by regex, with no AST inspection | `main.py:447`, `main.py:1031` |
| **No fence → the turn returns without executing anything** | `main.py:1032-1034` |
| That branch prints `No code produced — returning direct answer.` in yellow | `main.py:1033` |
| Retry loop runs `MAX_RETRIES` attempts, but only on **execution failure** — a refusal is not a failure | `main.py:998`, `main.py:1032-1034` |

The last row matters: a refusal is not retried, because from the program's point of view nothing
went wrong. The user sees one panel and a yellow line.

### 2.5 `tools.py` as it stands

| Fact | Evidence |
|---|---|
| Module path resolved at import | `main.py:77` `TOOLS_MODULE = Path(__file__).with_name("tools.py")` |
| Copied into every sandbox workdir | `main.py:507` `shutil.copy2(TOOLS_MODULE, …)` |
| The comment naming the intended usage, which only a human ever reads | `main.py:510` |
| Public surface is one function | `tools.py:98` `__all__ = ["web_search"]` |
| HTML results parsed by regex, not by `bs4`, although `bs4` and `lxml` are installed | `tools.py:51-55`; `tech.md` §8.7 |
| **Instant-answer failure is swallowed** — a parse regression is indistinguishable from an outage | `tools.py:90-91` `except Exception: pass` |
| Outer handler returns a `search_error` dict rather than raising, so a caller that does not inspect `title` treats failure as a result | `tools.py:94-95` |
| **Not covered by any coverage gate, and never tested** — added at v1.1.0 (A2) | no `--cov=tools` in `pytest.ini:57-62`; no entry in `conftest.py:205-212`; no `tests/test_tools.py`. Verified 2026-08-08 |

The middle three rows are `tech.md` §8.7, and they are the reason T5 exists: **this SPEC promotes
`tools.py` from dead code to live code, and §6.1 and §8.7 are about the same module.** Fixing the
first without addressing the second ships a live helper whose failures are invisible.

**The last row is why T5 is a larger task than v1.0.0 costed it at**, and it compounds the rest
rather than sitting beside them: the module about to be promoted to the hot path has **no test at
all**, so there is nothing to regress against and nothing to observe the fix red first with. §5
states the three pieces of work that follow from it.

### 2.6 The absence this SPEC is most exposed to

| Absent | Evidence |
|---|---|
| Any test for `main.py` | `structure.md:56` — *"There are zero tests for `main.py` and `tools.py`"* (the `tools.py` half is now false; the `main.py` half is not) |
| Any test of `SYSTEM_PROMPT`'s effect | none exists, and none can exist without a model in the loop |
| Any test for `tools.py`, and any coverage gate on it | **added at v1.1.0 (A2).** `pytest.ini:57-62` has no `--cov=tools`; `conftest.py:205-212` has no `tools.py` entry; `tests/test_tools.py` does not exist. Verified 2026-08-08 |
| ~~Any reachable Ollama on the authoring host~~ | ~~measured 2026-08-08: `command -v ollama` fails; no binary at `/usr/local/bin` or `/opt/homebrew/bin`; `localhost:11434` → `http_code=000`~~ **SUPERSEDED at v1.1.0 (A1)** — the host facts hold; the conclusion does not. `docker-compose.yml:28` publishes no port for `ollama` **by design**, and the sidecar is Up, healthy and serving `llama3.1:8b` (`46e0c10c039e`) |
| CI pass floor to be raised | `MIN_PASSED = 544` at `.github/workflows/ci.yml:316` |

**A prompt edit is a global behaviour change with no regression net.** That is R2 in `plan.md`, it
is the risk this SPEC is most likely to be judged on later, and S2 plus the control set in T1 exist
for it alone.

---

## 3. Design decisions

### 3.1 D1 — Repair the contradiction rather than adding a rule on top of it

**Recommendation.** `main.py:128-129`'s *"or needs live data you don't have"* is the clause that
routes an actionable, network-reachable task to DIRECT. It is repaired so that DIRECT means *"there
is no computation and no fetch that would answer this"* — not *"you personally lack this data right
now"*, which is true of every network task the prompt elsewhere encourages.

**Why repair and not append.** Adding a fourth rule to three that already disagree produces four
that disagree. The failure being fixed is a model resolving an ambiguity in the wrong direction;
more text on the same ambiguity is more surface for it to resolve wrongly.

**Cost.** DIRECT becomes narrower, and the model will take CODE on turns where DIRECT was correct
and cheaper — "what do you think of Python", "explain closures". Every such turn costs a code
generation, a subprocess and a second model round-trip. **This is the regression S2 and the control
set exist to bound**, and the SPEC does not proceed on an assumption that it is small.

### 3.2 D2 — Advertise by **example**, not by rule

**Recommendation.** Every capability the prompt states gains a worked example, in the shape the
prompt already uses at `:146-153`.

This falls directly out of §2.2 and the HISTORY diagnosis. The prompt's **effective** capability
surface is measured to be its example set: the three exampled domains are used, and the general
permission at `:143-145` is not generalised beyond them. `tools.py` is the extreme case — permitted
by nothing, exampled by nothing, named by nothing, and consequently dead for its entire existence.

**So the intervention most likely to work is the one this prompt already demonstrates works.** A
rule the model does not act on is the failure mode under repair, not a mitigation for it (N4).

**The examples are indented and unfenced, and that is a hard constraint rather than a style note
(N9, added v1.1.0).** The shape at `main.py:146-153` — the very shape being copied — is already
indented and unfenced, as is the `@param` example at `main.py:162-163`. Writing the new ones with
fences breaks `tests/test_source_seam.py:547` (`prompt.count("```") == 2`) and, more seriously,
demonstrates by example the two-block form that makes `CODE_BLOCK_RE.findall()` return `['']` and
routes the turn silently to DIRECT (`tests/test_source_seam.py:533-548`). A prompt that teaches the
defect by example is worse than one that stays silent.

**Cost.** The prompt grows, and every added line is in the context of every turn of every session.
That is a real and permanent token cost paid on all traffic to fix a subset of it. Accepted, and
bounded by keeping each addition to the existing `printf`-terse register rather than prose.

### 3.3 D3 — Advertise `tools.py`, and fix its invisible failure first

**Recommendation.** The capability section names `from tools import web_search`, its return shape,
and its stdlib-only guarantee. In the **same** SPEC, `tools.py:90-91`'s `except Exception: pass`
is replaced by a path that makes the failure visible to the caller.

**Why they are one SPEC and not two.** Today `tools.py` is dead, so §8.7's fragility is
theoretical. The moment `SYSTEM_PROMPT` names it, that fragility is in the product's hot path.
Shipping the advertisement without the fix converts a documented latent defect into a live one, in
a module where a DuckDuckGo markup change already yields **zero hits rather than an error**
(`tech.md` §8.7). T5 precedes T4's advertisement in the plan for that reason.

**Explicitly out of scope: rewriting `_HTML_RESULT_RE` to use `bs4`.** §8.7 is right that `bs4` and
`lxml` are installed (`requirements.txt`) and that a regex over HTML is the wrong tool. But
`tools.py`'s own banner (`tools.py:6`) and `web_search`'s docstring (`tools.py:82`) both claim
**stdlib-only**, and `main.py:510` explains that `-I` strips `PYTHONPATH` — the module is
deliberately importable from a sandbox that may not resolve site-packages the way `/app` does.
Reversing that claim is a decision about the module's contract, not a rider on a prompt SPEC. §8
item 2 records it with its reason rather than omitting it.

### 3.4 D4 — Measure first, and admit three outcomes

**Recommendation.** T1–T3 run **before** T4 touches the prompt, and T3 is a **gate**.

The question the gate answers is not "did the wording improve". It is **which of three worlds we
are in**:

| | Outcome | What it means | What happens next |
|---|---|---|---|
| **M-a** | Refusal is a **routing** artefact. The model complies once the prompt sanctions the task | This SPEC's premise holds | Proceed. `SPEC-ACCOUNT-001` proceeds as a prompt-design SPEC |
| **M-b** | Refusal is **safety-training**. The model refuses even under a prompt that explicitly sanctions it | This SPEC's prompt half still stands (advertising `tools.py` has no safety component), but account access is a **model-selection** problem | `SPEC-ACCOUNT-001` does **not** proceed as specified. Open `SPEC-MODEL-001` |
| **M-c** | Model **complies but writes code that does not work** | Neither prompt wording nor model choice is the constraint — the constraint is that IMAP is fiddly and 8B models drop fiddly details | Prompt wording is done; the remaining work is a worked example or a helper, decided in `SPEC-ACCOUNT-001` A1 |

**M-c is given equal standing deliberately.** It was not named in the brief that produced this SPEC
and it is the outcome that most changes the downstream design. A binary gate — "complied / refused"
— would report M-c as success and hand `SPEC-ACCOUNT-001` a false premise.

**The classifier is the production predicate, not a human judgement.** A trial counts as DIRECT iff
`extract_last_python_block()` (`main.py:447`) returns falsy — which is literally the branch at
`main.py:1032` that produced the reported behaviour. The measurement's success criterion and the
defect's mechanism are then the same line of code, and the probe cannot pass while the product
fails.

### 3.5 D5 — The control set is part of the measurement, not a follow-up

**Recommendation.** Every probe run carries a set of prompts that **must** route DIRECT — a
conversational one, an opinion one, a general-knowledge one — and the same before/after table
reports them.

`main.py` has no tests. `SYSTEM_PROMPT` has none and can have none without a model. So the only
evidence that a prompt edit did not break unrelated routing is a measurement taken deliberately,
and a measurement nobody plans is a measurement nobody takes. It is task T6 with its own acceptance
criterion (**AC-CONTROL**), not a line in a checklist.

### 3.6 D6 — Insert below the `@param` passage

**Recommendation.** New prompt material goes **after** `main.py:166`.

Mechanical, and it is the difference between one stale citation and two. N2's range is already 18
lines out. Inserting above the passage moves it again and makes the next reader's
`git show 1d5fff1:main.py | sed -n '140,148p'` check land on unrelated text — at which point the
evidence in §2.3 stops being reproducible, which is the only thing that makes it evidence. Pairing
this with E4's same-commit re-citation costs one line of diff and preserves the check.

---

## 4. The measurement

`verification-T3.md` is created with this SPEC, structurally complete and **empty of results**. No
figure appears in it until a run produces that figure. Placeholder numbers are forbidden (N7): a
placeholder that survives into a later read is indistinguishable from data, and this repository has
already established the opposite discipline — `SPEC-KEYCHAIN-001`'s HISTORY names what was not run
*"as not run and not as not needed"*, and `SPEC-CI-001`'s `verification-T3.md` states in its own
header that no run was triggered to produce it.

**Precondition — SATISFIED at v1.1.0, and the reason the v1.0.0 text read otherwise is recorded
rather than deleted.** ~~Ollama is not reachable from the authoring host (§2.6).~~ Re-verified
2026-08-08: the compose `ollama` sidecar (`coderunner-ollama`) is **Up and healthy** and
`docker exec coderunner-ollama ollama list` reports **`llama3.1:8b`, ID `46e0c10c039e`, 4.9 GB**.
There is still no host `ollama` binary and `localhost:11434` still answers `http_code=000`, because
`docker-compose.yml:28` publishes **no host port** for that service on purpose. The probe runs
**inside the compose network**, at `http://ollama:11434`, which is the only place it was ever
supposed to run. Any result obtained against a different model, a
different quantisation or a different host is a result about that model and must be labelled as
such.

**The model tag is a compose DEFAULT, not a pin, and the probe must not read it from compose.**
`docker-compose.yml:46` and `:78` are `${CODERUNNER_MODEL:-llama3.1:8b}` — a host environment
variable with a fallback. `main.py:71` reads the same variable. So compose declares an *intention*;
only the running server can report the *fact*. The probe therefore records `client.list()` and
`client.show(MODEL_NAME)` at run time, plus the observed `OLLAMA_HOST`, and `verification-T3.md` §1
is filled from those rather than from the file. S4 is discharged by the readback, not by the YAML.

**Shape.** Variants × task set × N trials. ~~N ≥ 10 per cell because an 8B model at default
temperature is stochastic and a single trial measures nothing.~~ **SUPERSEDED at v1.1.0 — the
premise was right and the number was too small to act on it.**

| Cell | N per arm | Why this N |
|---|---|---|
| **Target** | **30** | It is the gated cell. At N=10 per arm a two-proportion test has usable power only against a swing of roughly **50 percentage points**, so `N ≥ 10` could return "no difference" for a repair that moved routing by 40pp — recording M-b on a measurement structurally unable to observe M-a |
| **Off-example network** | **20** | Diagnostic, not gated. It separates a routing effect from an account-shaped one; it needs to resolve a large difference, not a small one |
| **Tool-reachable** | **20** | Diagnostic, and its V0 expectation is **zero** (§4 below, `verification-T3.md` §2.3). Distinguishing zero from small does not need 30 |
| **Control**, per prompt | **30** | Its question is **non-inferiority**, which is the harder direction. By the rule of three, 0 failures in 10 trials bounds the true regression rate only at **30%**; 0 in 30 bounds it at **10%**. A control that cannot exclude a 30% regression is not a defence against R2 |

**If budget forces a cut, cut the NUMBER of control prompts — floor 3, keeping one of each kind —
and never cut N below 20.** Three prompts at N=30 is a measurement; five at N=6 is a rumour. This is
stated as a rule now so that the trade is made against a written constraint at 2 a.m. rather than
against fatigue.

| Variant | Prompt | When it runs |
|---|---|---|
| **V0** | `SYSTEM_PROMPT` exactly as it is today. This is the baseline and it converts the reported anecdote into a rate | Always (T2) |
| **V1** | V0 with the routing contradiction repaired (D1) | Always (T3) |
| **V2** | V1 with the capability section added, naming `tools.py` (D2, D3) | Always (T3) |
| **V3** | **V0 + the capability section, without the routing repair.** Added at v1.1.0 (A5) | **Conditional — only on the M-b branch** |

**Why V3 exists, and why it is conditional rather than routine.** Under **M-b** the routing repair
does not ship, but the `tools.py` advertisement still does — §3.4's M-b row already says the
`tools.py` half "has no safety component" and survives. What would then ship is **`V0 +
capability`**, and none of V0, V1 or V2 is that prompt. The SPEC would have shipped, on its own
most-likely-adverse branch, the one variant it never measured. So V3 is a **conditional obligation**:
if and only if §5 records M-b, V3 is run at the **tool-reachable cell (N=20)** and across the **full
control set (5 prompts × N=30)** before any prompt text is merged, and recorded in
`verification-T3.md` §3.6. It is **not** work to do now, and it is **not** part of the gate — the
gate is already decided by the time V3 becomes owed.

| Task set | Purpose |
|---|---|
| **Target** | The reported Gmail request, verbatim |
| **Off-example network** | A network task outside `:146-153`'s three domains, with no account or credential involved — isolates the routing repair from anything account-shaped |
| **Tool-reachable** | A task `web_search` is the natural instrument for — measures whether the advertisement is acted on, which is §6.1's actual close condition |
| **Control** | Conversational, opinion, and general-knowledge prompts that **must** stay DIRECT (D5) |

**Gate — restated at v1.1.0 so that it is decidable by a machine, and pre-registered so that it is
decidable before the numbers exist.** ~~If V2's Target **refusal rate** is not materially better
than V0's, the outcome is **M-b**.~~ **SUPERSEDED (A4).** *"Materially better" names no threshold,
and "refusal rate" is not the quantity E6 defines. A refusal is a **human-coded subset** of DIRECT:
a turn that routes DIRECT because the model chatted is not a refusal, and a reply carrying two
fenced blocks classifies DIRECT (`CODE_BLOCK_RE.findall()` → `['']`, falsy — measured at
`tests/test_source_seam.py:533-548`) while refusing nothing whatever. A gate whose endpoint is
human-coded and whose classifier is machine-coded is not a gate; it is a conversation held after the
fact.*

**The gate is decided on the DIRECT rate**, machine-decided by `extract_last_python_block()`
returning falsy (E6), on the **Target cell only**, at **N=30 per arm**. Writing `r0` for V0's Target
DIRECT rate and `r2` for V2's:

> **Proceed (M-a or M-c) if and only if `(r0 − r2) ≥ 0.40` absolute AND a one-sided Fisher exact
> test rejects at `alpha = 0.05`. Otherwise the outcome is M-b.**

Three properties of that rule, each of which is the reason a clause is in it:

- **It is pre-registered.** The full rule is written into `verification-T3.md` §1 **before T2 runs**.
  A threshold chosen after the numbers arrive is not a gate, and this SPEC has a stated preference
  for M-a that would do the choosing.
- **It is decided on ONE cell.** No other cell may rescue an M-b — not the off-example task, not the
  tool-reachable task, not a favourable control. Consequently **no multiplicity correction is
  applied, and none is needed**, because no second test is permitted to bear on the decision.
- **It requires both clauses.** The absolute threshold alone would let a large-but-noisy difference
  through; significance alone would let a 12pp difference through at N=30 and call it a repair.

**Refusal rate survives as a secondary, human-coded overlay** (O3 supplies the verbatim replies)
which is **reported and does not decide anything**. It is what distinguishes a model that declined
from a model that chatted, and that distinction matters for `SPEC-MODEL-001`; it does not matter for
the gate. §6 S1.

---

## 5. Where the code belongs

Almost nowhere, and that is the point.

`SYSTEM_PROMPT` is a module-level string literal in `main.py`, which is **not covered by any
coverage floor** (`pytest.ini:50-54`, `conftest.py:200-206`) — the convention `SPEC-INPUT-001` §5.3
established, where `main.py` holds wiring and every decision lives in a gated leaf. There is no leaf
to move a prompt into and inventing one would be worse than the problem.

So this SPEC's verification is **not** unit coverage. It is:

- the probe harness and its recorded table (`verification-T3.md`), which is the only instrument
  that can observe a prompt's effect at all;
- source-level assertions that hold without a model — the pinned `@param` passage is intact, the
  prompt names `web_search`, no prompt text mentions `os.environ` or a keychain. These are cheap,
  they run in CI, and they are what stops a later edit silently breaching N1/N2.

~~`tools.py` **is** gated. The T5 change to its error handling carries a test like any other change
to a gated module.~~ **SUPERSEDED at v1.1.0 (A2) — `tools.py` is not gated, and it has never had a
test.** Verified 2026-08-08, three independent ways:

| Claim | Evidence |
|---|---|
| No coverage instrumentation | `pytest.ini:57-62` lists `--cov` for `memory`, `recall`, `vectorstore`, `params`, `settings`, `keychain`. There is **no `--cov=tools`** |
| No per-file floor | `conftest.py:205-212`'s `PER_FILE_COVERAGE_TARGETS` holds six entries and **`tools.py` is not among them** |
| No test file | `tests/` holds eleven `test_*.py` files. **`tests/test_tools.py` does not exist** |

**The v1.0.0 claim traced to `structure.md:234`, which does not say what it was read as saying.**
That line is a row in a table headed *"Why it is testable in isolation"* — it names
`_ddg_instant()` / `_ddg_html()` / `web_search()` as **targets worth testing**, in a document
section that is a testing proposal. It is an **aspiration, not a record of coverage**. Reading it as
coverage is the same category error as reading a `Dockerfile` `COPY` line as proof that the import
works, which is precisely what `SPEC-KEYCHAIN-001`'s AC-IMAGE was written to stop.

**So T5's true size is larger than v1.0.0 stated**, and it is stated here so the estimate is not
made twice:

1. **`tests/test_tools.py` — the first test file `tools.py` has ever had.** Not "a test for the new
   error path" bolted onto an existing suite; the suite itself.
2. **Two-edit gate registration, both or neither.** `pytest.ini` gains `--cov=tools` **and**
   `conftest.py`'s `PER_FILE_COVERAGE_TARGETS` gains a `tools.py` floor. `pytest.ini:42-46` records
   what happens if only one lands: `cov.report(include=[...])` raises, conftest records *"coverage
   unavailable"*, and the session fails — loudly, which that comment calls "the right direction for
   this mistake to fail in". Landing only the `--cov` is the quieter mistake: the module is measured
   and nothing enforces a floor on it.
3. **A floor chosen and justified**, in the style `conftest.py:184-195` established for every module
   added since — including the sentence about what to do if it is ever lowered.

`MIN_PASSED` (`.github/workflows/ci.yml:316`, currently **544**) rises to a
count read from a real `junitxml` run — **measured, never computed from an expected delta**. That
discipline is `SPEC-KEYCHAIN-001`'s and it is adopted here explicitly (E5). **A2 makes that delta
materially larger than v1.0.0 anticipated**, which is another reason E5 forbids computing it.

---

## 6. EARS requirements

All five requirement types are represented.

### 6.1 Ubiquitous — always true

| # | Requirement |
|---|---|
| **U1** | `SYSTEM_PROMPT` **shall always** state the capability surface the sandbox actually provides — the installed library set, network egress, and `from tools import web_search`. `run_python()` copies `tools.py` into every sandbox (`main.py:507`) and the prompt is the model's only discovery channel; a capability named nowhere is a capability that does not exist (`product.md` §6.1, `structure.md` §5.3). |
| **U2** | The prompt's routing rules **shall always** be mutually consistent. No clause **shall** route a task to DIRECT on a ground that another clause explicitly permits under CODE. Measured contradiction: `main.py:128-129` against `main.py:143-145` and `main.py:174`. |
| **U3** | Every capability stated in `SYSTEM_PROMPT` **shall always** carry a worked example. The prompt's effective capability surface is measured to be its example set (`main.py:146-153`) rather than its rules; a rule the model does not act on is the defect under repair, not a fix for it. |
| **U4** | The `@param` passage — `main.py:140-148` as cited by `SPEC-KEYCHAIN-001` N2, `main.py:158-166` today — **shall always** remain semantically unchanged, and no prompt text **shall** instruct generated code to read `os.environ` or reveal that a host keychain exists. |
| **U5** | No prompt change **shall** be merged without a recorded before/after measurement against `llama3.1:8b`, covering both the target behaviour **and** an unchanged-behaviour control set. `main.py` has zero tests (`structure.md:56`); a prompt edit is otherwise unfalsifiable. |
| **U6** | Every figure in `verification-T3.md` **shall always** be a figure a run produced, quoted with the variant and trial count it came from. What was not run **shall** be named as not run, not as not needed. |

### 6.2 Event-driven — WHEN … THEN …

| # | Requirement |
|---|---|
| **E1** | **WHEN** a task requires data reachable over the network — including data behind credentials or identifiers the user can supply — **THEN** the model **shall** take the CODE protocol and declare any missing values with `# @param`, rather than routing to DIRECT on the ground that it does not already hold the data. |
| **E2** | **WHEN** a task benefits from general web search, **THEN** the model **shall** be able to reach `from tools import web_search`, which resolves without `PYTHONPATH` under `-I` (`main.py:507-510`). |
| **E3** | **WHEN** `tools.web_search()` fails to fetch or fails to parse, **THEN** that failure **shall** be distinguishable from an empty result set. Today `except Exception: pass` (`tools.py:90-91`) renders a parsing regression identical to an outage, and the outer handler (`tools.py:94-95`) returns a `search_error` dict a caller may treat as a result. |
| **E4** | **WHEN** `SYSTEM_PROMPT` is amended, **THEN** `SPEC-KEYCHAIN-001` N2's line citation **shall** be corrected to its post-change range **in the same commit**, in both that SPEC's §6.4 and its §9 traceability table. The range is already 18 lines stale; a second generation makes §2.3's verification method unreproducible. |
| **E5** | **WHEN** tests are added, **THEN** `MIN_PASSED` (`.github/workflows/ci.yml:316`, currently **544**) **shall** be raised to a count read from a real `junitxml` run, **measured and not computed** from an expected delta. |
| **E6** | **WHEN** the probe is run, **THEN** a trial **shall** be classified DIRECT iff `extract_last_python_block()` (`main.py:447`) returns falsy — the same predicate as the production branch at `main.py:1032`. |
| **E7** | **WHEN** a trial is recorded, **THEN** the record **shall** carry `len(CODE_BLOCK_RE.findall(reply))` alongside the classification. *A reply with **two** fenced blocks makes `findall()` return `['']` — falsy — so it classifies **DIRECT** while the model refused nothing at all (`tests/test_source_seam.py:533-548`). Without this field such a trial is indistinguishable from a refusal, silently inflating the secondary refusal rate and, worse, contaminating the DIRECT rate the gate is decided on. The field costs one integer per trial and it is the only way to tell a refusal apart from a formatting accident after the fact.* |

### 6.3 State-driven — IF/WHILE … THEN …

| # | Requirement |
|---|---|
| **S1** | ~~**IF** variant V2's Target **refusal rate** is not **materially better** than baseline V0's~~ — **RESTATED at v1.1.0 (A4)** — **IF** the pre-registered rule in `verification-T3.md` §1 is not satisfied on the Target cell — that is, **IF NOT** (`(r0 − r2) ≥ 0.40` absolute **AND** one-sided Fisher exact rejects at `alpha = 0.05`), where `r0` and `r2` are the **DIRECT rates** (E6) for V0 and V2 at **N=30 per arm** — **THEN** the refusal is safety-training-driven (**M-b**), the account-access half of this work **shall not** proceed as a prompt-design SPEC, `SPEC-ACCOUNT-001` **shall** remain gated closed, and `SPEC-MODEL-001` **shall** be opened. *Refusal rate is a human-coded subset of DIRECT and is reported alongside, but **shall not** decide this.* |
| **S6** | **IF** the gate outcome is **M-b**, **THEN** variant **V3** (V0 + capability section, A5) **shall** be measured at the tool-reachable cell (N=20) and across the full control set (5 × N=30), and recorded in `verification-T3.md` §3.6, **before** any prompt text is merged. Under M-b what ships is `V0 + capability`, and V0, V1 and V2 are none of them that prompt. |
| **S2** | **IF** a conversational, opinion, or general-knowledge prompt is given, **THEN** DIRECT **shall** still be selected at no worse than the measured pre-change rate. A capability advertisement **shall not** convert this into a product that writes and executes Python to answer "how are you". |
| **S3** | **IF** `tools.py` is advertised in `SYSTEM_PROMPT`, **THEN** its known fragility (`tech.md` §8.7 — regex HTML parsing, swallowed exceptions) is in the product's hot path and **shall** be either fixed or explicitly accepted **in writing**, in this SPEC, with its reason. Silence is not acceptance. |
| **S4** | **IF** a probe result is obtained against any model, quantisation or host other than `llama3.1:8b` on the compose sidecar, **THEN** it **shall** be labelled with what it was measured against and **shall not** be recorded as satisfying the gate. |
| **S5** | **WHILE** `verification-T3.md` contains no results, the file **shall** state that it has not been run, and T4 **shall not** be started. |

### 6.4 Unwanted — shall not

| # | Requirement |
|---|---|
| **N1** | Generated code **shall not** be instructed or expected to read `os.environ`. `SPEC-KEYCHAIN-001` N2, clause one, adopted verbatim. |
| **N2** | The `@param` passage **shall not** be altered semantically, and the host keychain **shall not** be mentioned in any prompt text. `SPEC-KEYCHAIN-001` N2, clause two, adopted verbatim. |
| **N3** | New prompt material **shall not** be inserted above the `@param` passage. Insertion point is below `main.py:166`. The N2 citation is already stale by 18 lines and a third generation destroys §2.3's reproducibility. |
| **N4** | The prompt **shall not** gain a stated capability without a worked example. This is U3 as a prohibition because it is the rule most likely to be traded away under length pressure, and trading it away rebuilds the exact defect. |
| **N5** | `docker-compose.yml` **shall not** be modified. Every variable there is written `${VAR:-default}`, so anything added is permanently set inside the container — `SPEC-INPUT-001` N7's trap. |
| **N6** | The regex-to-`bs4` rewrite of `_HTML_RESULT_RE` **shall not** be attempted here. It reverses `tools.py`'s stdlib-only contract (`tools.py:6`, `tools.py:82`, rationale at `main.py:510`) and that is a decision about the module, not a rider on a prompt change. §8 item 2. |
| **N7** | `verification-T3.md` **shall not** contain placeholder figures, illustrative numbers, or example tables populated with plausible values. Empty cells, explicitly marked not-yet-run. A placeholder that survives one read becomes data. |
| **N8** | No claim that `product.md` §6.1 is resolved **shall** be made on the strength of the prompt edit alone. §6.1 is closed by a **measured** rate at which the model actually reaches `web_search`, not by the presence of its name in a string. |
| **N9** | New prompt material **shall not** use fenced code blocks. Every added example **shall** be **indented and unfenced**, in the shape of the existing examples at `main.py:146-153` and `main.py:162-163`. *Two independent reasons, both measured. (1) `tests/test_source_seam.py:547` asserts `prompt.count("```") == 2` — exactly one fenced block in the entire `SYSTEM_PROMPT` — so a fenced addition fails CI outright. (2) `tests/test_source_seam.py:533-548` records that when a reply carries two fenced blocks the closing fence of the first pairs with the opening fence of the second, `CODE_BLOCK_RE.findall()` returns `['']`, `extract_last_python_block()` returns the empty string, `if not code:` is TRUE, and the turn **silently classifies DIRECT** — no exception, no retry. A prompt that demonstrates multi-fence output by example teaches the model the exact form that produces the defect this SPEC exists to remove.* |
| **N10** | The probe **shall not** pin `temperature`, **shall not** set a seed, and **shall not** pass an `options=` mapping. `main.py:209-221`'s `stream_llm()` passes no `options`, so production sampling is inherited by construction. *A temperature-0 measurement measures a different distribution from the one that produced the reported refusal, and would answer a question nobody asked. What the probe **shall** do instead is **record** the sampling parameters it inherited, from `client.show(MODEL_NAME)` at run time.* |

### 6.5 Optional — where possible

| # | Requirement |
|---|---|
| **O1** | **Where** possible, the probe harness **should** be retained as a committed, re-runnable artefact rather than a throwaway script. It is the project's first behavioural instrument of any kind, `SPEC-ACCOUNT-001` A1 needs the same one, and every future prompt edit inherits U5. |
| **O2** | **Where** further helpers are added to `tools.py`, they **should** be advertised in the same prompt section in the same change. Adding a helper without advertising it is the mechanism that produced §6.1. |
| **O3** | **Where** the probe records a refusal, it **should** store the model's verbatim reply. The reported refusal is a sentence; refusal *phrasing* is the only available signal for distinguishing M-a from M-b when rates are ambiguous. |
| **O4** | **Where** the token cost of the added prompt text can be measured, it **may** be recorded in `verification-T3.md`. The cost is paid on every turn of every session and is currently unquantified. |

---

## 7. In scope

1. **`main.py` — `SYSTEM_PROMPT` only.** Repair the routing contradiction at `main.py:126-129`
   (D1); add a capability section below `main.py:166` (D2, D3, N3) naming the library set, network
   egress and `from tools import web_search`, each with a worked example — **indented and unfenced
   (N9)**, so that `SYSTEM_PROMPT` still contains exactly one fenced block.
2. **The probe harness.** Variants × task set × control set × N trials, classifying by
   `extract_last_python_block()` (E6). Committed and re-runnable (O1).
3. **`verification-T3.md`** — structure now, figures only from runs (U6, N7).
4. **`tools.py`** — make instant-answer failure visible (E3). `tools.py:90-91` only; the regex is
   untouched (N6). **Plus, at v1.1.0 (A2): `tests/test_tools.py`, which does not exist today, and
   the two-edit gate registration — `--cov=tools` in `pytest.ini` AND a `tools.py` floor in
   `conftest.py`'s `PER_FILE_COVERAGE_TARGETS`, both or neither.** See §5.
5. **Source-level assertions** — the `@param` passage is intact, the prompt names `web_search`, no
   prompt text mentions `os.environ` or a keychain. These enforce N1/N2 without a model in the loop.
6. **Documentation, including the citation corrections this SPEC found:**
   - `product.md` §6.1 → **RESOLVED**, in the style §6.2 already established for a closed finding,
     with the measured rate rather than an assertion (N8). Its `main.py:100-151` citation for
     `SYSTEM_PROMPT` is corrected to `main.py:122-182`.
   - `structure.md` §5.3 → resolved; its `main.py:210-211` citation for the sandbox copy corrected
     to `main.py:507`.
   - `tech.md` §8.7 → note what was fixed and what was not; its `tools.py:91-92` and `tools.py:95-96`
     citations corrected to `tools.py:90-91` and `tools.py:94-95`.
   - `SPEC-KEYCHAIN-001` §6.4 N2 and §9 — re-cite the `@param` range (E4).
7. **`.github/workflows/ci.yml:316`** — `MIN_PASSED` raised from **544** to a measured count (E5).

## 8. Out of scope

1. **Account access, IMAP, and anything mail-shaped.** `SPEC-ACCOUNT-001`, gated on T3.
2. **Rewriting `_HTML_RESULT_RE` with `bs4` or `lxml`.** `tech.md` §8.7 is correct that the parser
   is wrong for the job. It is out here because `tools.py:6` and `tools.py:82` both claim
   stdlib-only and `main.py:510` explains why (`-I` strips `PYTHONPATH`; the module must import from
   a bare sandbox). Reversing that contract is its own decision with its own SPEC. Recorded with its
   reason rather than omitted (N6).
3. **Model selection and refusal handling.** `SPEC-MODEL-001`, opened only under outcome M-b.
4. **Trimming `SYSTEM_PROMPT` for token cost.** This SPEC makes it longer and O4 offers to measure
   that. Shortening it is a separate change that needs the same instrument and would confound this
   measurement if bundled.
5. **A coverage gate for `main.py`.** `SPEC-INPUT-001` §5.3 established that `main.py` is wiring and
   not floored. A string literal does not change that, and adding a floor to a 1300-line module is
   not a rider on a prompt edit.
6. **Rewriting `structure.md`.** `SPEC-KEYCHAIN-001` §2.4 records it as several SPECs behind — its
   tree omits five modules, its §5.1 claim that `main.py` imports no first-party module is
   contradicted at `main.py:49-51`, and its §6 claim that no test suite exists is now false by ten
   files. This SPEC fixes §5.3 because it edits §5.3, and leaves the rest to whoever owns
   documentation.
7. **Retry-on-refusal.** `main.py:998`'s loop retries execution failures; a refusal is not a
   failure and is not retried. Making it one is a plausible mitigation under M-b and therefore
   belongs to `SPEC-MODEL-001`, not here.
8. **Any change to `docker-compose.yml`** (N5).

---

## 9. Traceability

| Artefact | Location |
|---|---|
| Requirements | this file, §6 (U1–U6, E1–**E7**, S1–**S6**, N1–**N10**, O1–O4) |
| The five v1.1.0 corrections, with what superseded what | this file, HISTORY v1.1.0 (A1–A5) |
| The pre-registered gate rule | this file, §4; **normative copy** in `verification-T3.md` §1 |
| The ports decision that made `http_code=000` look like an outage | `docker-compose.yml:28` |
| The evidence that `tools.py` is ungated | `pytest.ini:57-62`; `conftest.py:205-212`; absence of `tests/test_tools.py` |
| The two-fence trap, measured | `tests/test_source_seam.py:533-548`; the one-fence assertion at `:547` |
| The sampling the probe inherits by construction | `main.py:209-221` (`stream_llm()` passes no `options=`) |
| The diagnosis — three contradictory rules resolved by example | this file, HISTORY and §2.1 |
| The one grep that explains two defects | this file, §2.2 |
| The N2 resolution and its re-checkable method | this file, §2.3 |
| The three measurement outcomes, M-a / M-b / M-c | this file, §3.4 |
| Design decisions with costs | this file, §3 (D1–D6) |
| Task decomposition, critical path, risks | `.moai/specs/SPEC-PROMPT-001/plan.md` |
| Acceptance criteria | `.moai/specs/SPEC-PROMPT-001/acceptance.md` |
| The measurement record | `.moai/specs/SPEC-PROMPT-001/verification-T3.md` |
| The gated downstream SPEC | `.moai/specs/SPEC-ACCOUNT-001/spec.md` |
| The constraint this SPEC works within | `.moai/specs/SPEC-KEYCHAIN-001/spec.md:840` (N2), `:932` (§9 row) |
| The defect class already documented | `product.md` §6.1; `structure.md` §5.3 |
| The prompt sites | `main.py:122-182`; `:126-129`, `:142`, `:143-145`, `:146-153`, `:158-166`, `:169-174` |
| The branch that produced the refusal | `main.py:1031-1034`; panel title `main.py:1021` |
| The sandbox copy and its human-only comment | `main.py:77`, `main.py:507`, `main.py:510` |
| The module being promoted from dead to live | `tools.py:77-98`; fragility at `tools.py:51-55`, `:90-91`, `:94-95` |
| CI floor to be raised | `.github/workflows/ci.yml:316` (`MIN_PASSED = 544`) |
| Explicitly not amended | `docker-compose.yml` (N5); the `@param` passage `main.py:158-166` (N2, N3); `_HTML_RESULT_RE` `tools.py:51-55` (N6) |
| Documentation to be corrected | `product.md` §6.1; `structure.md` §5.3; `tech.md` §8.7; `SPEC-KEYCHAIN-001` §6.4 and §9 |
| Project context | `.moai/project/product.md`, `.moai/project/structure.md`, `.moai/project/tech.md` |

| Requirement group | Primary acceptance criteria |
|---|---|
| U5, U6, E6, **E7**, S4, S5, N7, **N10** | **AC-MEASURE** |
| S1, **S6**, §3.4 | **AC-GATE** |
| U2, E1 | **AC-ROUTE** |
| U1, U3, E2, N4, N8, **N9** | **AC-TOOLS** |
| S2, D5 | **AC-CONTROL** |
| U4, N1, N2, N3, **N9**, E4 | **AC-N2** |
| E3, S3, N6 | **AC-VISIBLE** |
| E5, §7 item 7 | **AC-FLOOR** |
| §7 item 6 | **AC-DOCS** |
