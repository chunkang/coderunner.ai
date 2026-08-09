---
id: SPEC-PROMPT-001
version: "1.0.0"
status: "draft"
created: "2026-08-08"
updated: "2026-08-08"
author: "Chun Kang"
priority: "HIGH"
---

## HISTORY

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

**Not measured, and named as not measured.** No probe has been run. Ollama is not reachable from
the host this SPEC was written on — `command -v ollama` fails, there is no binary at
`/usr/local/bin/ollama` or `/opt/homebrew/bin/ollama`, and `localhost:11434` returns
`http_code=000` (measured 2026-08-08). The probe must therefore run against the compose `ollama`
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

The bottom three rows are `tech.md` §8.7, and they are the reason T5 exists: **this SPEC promotes
`tools.py` from dead code to live code, and §6.1 and §8.7 are about the same module.** Fixing the
first without addressing the second ships a live helper whose failures are invisible.

### 2.6 The absence this SPEC is most exposed to

| Absent | Evidence |
|---|---|
| Any test for `main.py` | `structure.md:56` — *"There are zero tests for `main.py` and `tools.py`"* (the `tools.py` half is now false; the `main.py` half is not) |
| Any test of `SYSTEM_PROMPT`'s effect | none exists, and none can exist without a model in the loop |
| Any reachable Ollama on the authoring host | measured 2026-08-08: `command -v ollama` fails; no binary at `/usr/local/bin` or `/opt/homebrew/bin`; `localhost:11434` → `http_code=000` |
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

**Precondition, and it is a plan item rather than a discovery.** Ollama is not reachable from the
authoring host (§2.6). The probe runs against the compose `ollama` sidecar, which pins
`llama3.1:8b` (`docker-compose.yml:46`, `:78`). Any result obtained against a different model, a
different quantisation or a different host is a result about that model and must be labelled as
such.

**Shape.** Variants × task set × N trials, N ≥ 10 per cell because an 8B model at default
temperature is stochastic and a single trial measures nothing.

| Variant | Prompt |
|---|---|
| **V0** | `SYSTEM_PROMPT` exactly as it is today. This is the baseline and it converts the reported anecdote into a rate |
| **V1** | V0 with the routing contradiction repaired (D1) |
| **V2** | V1 with the capability section added, naming `tools.py` (D2, D3) |

| Task set | Purpose |
|---|---|
| **Target** | The reported Gmail request, verbatim |
| **Off-example network** | A network task outside `:146-153`'s three domains, with no account or credential involved — isolates the routing repair from anything account-shaped |
| **Tool-reachable** | A task `web_search` is the natural instrument for — measures whether the advertisement is acted on, which is §6.1's actual close condition |
| **Control** | Conversational, opinion, and general-knowledge prompts that **must** stay DIRECT (D5) |

**Gate:** if V2's Target refusal rate is not materially better than V0's, the outcome is **M-b**,
T4 does not proceed on the account-access half, and `SPEC-MODEL-001` is opened. §6 S1.

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

`tools.py` **is** gated. The T5 change to its error handling carries a test like any other change to
a gated module, and `MIN_PASSED` (`.github/workflows/ci.yml:316`, currently **544**) rises to a
count read from a real `junitxml` run — **measured, never computed from an expected delta**. That
discipline is `SPEC-KEYCHAIN-001`'s and it is adopted here explicitly (E5).

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

### 6.3 State-driven — IF/WHILE … THEN …

| # | Requirement |
|---|---|
| **S1** | **IF** variant V2's Target refusal rate is not materially better than baseline V0's, **THEN** the refusal is safety-training-driven (**M-b**), the account-access half of this work **shall not** proceed as a prompt-design SPEC, `SPEC-ACCOUNT-001` **shall** remain gated closed, and `SPEC-MODEL-001` **shall** be opened. |
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
   egress and `from tools import web_search`, each with a worked example.
2. **The probe harness.** Variants × task set × control set × N trials, classifying by
   `extract_last_python_block()` (E6). Committed and re-runnable (O1).
3. **`verification-T3.md`** — structure now, figures only from runs (U6, N7).
4. **`tools.py`** — make instant-answer failure visible (E3). `tools.py:90-91` only; the regex is
   untouched (N6).
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
| Requirements | this file, §6 (U1–U6, E1–E6, S1–S5, N1–N8, O1–O4) |
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
| U5, U6, E6, S4, S5, N7 | **AC-MEASURE** |
| S1, §3.4 | **AC-GATE** |
| U2, E1 | **AC-ROUTE** |
| U1, U3, E2, N4, N8 | **AC-TOOLS** |
| S2, D5 | **AC-CONTROL** |
| U4, N1, N2, N3, E4 | **AC-N2** |
| E3, S3, N6 | **AC-VISIBLE** |
| E5, §7 item 7 | **AC-FLOOR** |
| §7 item 6 | **AC-DOCS** |
