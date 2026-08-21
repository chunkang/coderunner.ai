---
id: SPEC-ILLUSTRATE-001
version: "1.0.0"
status: "draft"
created: "2026-08-12"
updated: "2026-08-12"
author: "Chun Kang"
priority: "MEDIUM"
---

## HISTORY

### v1.0.0 (2026-08-12) — Initial specification

**This defect was found by a control set — by the prompts whose entire job was to prove that a change
had *not* broken anything.** `SPEC-PROMPT-001` measured five control prompts at V0 before touching
`SYSTEM_PROMPT`, and one of them came back at **0 DIRECT in 30 trials**. Nothing caused it. It is the
baseline. The edit that control set exists to police had not been written yet, and the defect it
found has nothing to do with the Gmail request that motivated that SPEC.

**The measurement, taken 2026-08-10, `llama3.1:8b` via the compose sidecar.** Task text, verbatim:
*"explain what a Python closure is, with a short example"*. **CODE 30/30. DIRECT 0/30.** 95 % Wilson
interval on the DIRECT rate **[0.000, 0.114]**; by the rule of three, 0 in 30 bounds the true rate at
**10 %**. `fence_matches == 1` in **all thirty**, so **this is not the two-block trap**
(`tests/test_source_seam.py:533-548`) — the model emitted exactly one fenced block each time and the
extractor returned it. `def ` appears in **30/30** extracted blocks; `print(` in **30/30**.

**The model is not confused about what it is doing.** Trial #0 opens:

> \*\*Code Protocol\*\*
>
> 1. One-line task restatement.
> > Explain what a Python closure is.
>
> 2. A "Thought:" section explaining the plan.
>
> A closure in Python is a function that remembers its surrounding scope…

It announces the CODE protocol for a request to explain a concept, and then explains the concept in
prose — measured today, **30/30 replies carry a prose explanation outside the fence** (median **80.5
words**, minimum 48) and **30/30 of those prose sections contain both "closure" and "scope"**. The
answer the user asked for is already on the screen before anything runs.

**The defect specified here is what the product then does with that block, and it is not the
routing.** `extract_last_python_block()` (`main.py:447-449`) is a regex. It cannot distinguish an
**illustrative** fenced block from one meant to be run, because the distinction is not in the block —
it is in the request. So `agentic_turn()` writes the illustration to a temp directory
(`main.py:497-501`), spawns a subprocess under `python -I` (`main.py:514-521`), renders an execution
panel (`main.py:1108`), pays a **second LLM round trip** to narrate a result the user did not ask for
(`main.py:1119-1127`), and — the consequence nobody has named before — **captures the illustration
into the solution-memory store as a successful solution** (`main.py:1143-1152`), from which
`format_recall_block()` (`memory.py:383-391`) will later re-inject it, under the heading **"PRIOR
SUCCESSFUL SOLUTION"** with the words *"Its actual output was:"*, into a future turn that asks a
similar question. **The defect feeds itself.**

**No exception, no diagnostic, no log line — `main.py` imports no logging module at all (measured:
zero occurrences of `logging` in 1340 lines).** The turn is not silent; it is *unremarkable*. The
user sees `⚙️ [System] Running generated Python code…`, an `Execution OK` panel and
`📊 [System] Execution successful`, which is byte-for-byte what a correct computation turn looks
like. **That is worse than an error**, because there is nothing for a bug report to quote.

**Three findings shaped this document, and two of them changed it.**

- **F1 — the failure is graded, not binary, and c4 is its extreme.** *(Re-derived 2026-08-12 from the
  committed V0 records.)* DIRECT rate across the five control prompts: **c1 30/30**, **c3 26/30**,
  **c2 20/30**, **c5 14/30**, **c4 0/30**. A general-knowledge question about a *book*
  (c5, *"who wrote the book 'The Mythical Man-Month'?"*) routes CODE 16 times in 30; a
  general-knowledge question that asks for *an example* routes CODE every time. **The word "example"
  in the request is the strongest predictor in the set**, and it is the one word an explanation
  request is most likely to contain.

- **F2 — c4 is dead as a regression detector, and this is arithmetic rather than opinion.**
  *(Computed 2026-08-12 with `math.comb`, one-sided Fisher exact at `alpha = 0.05`, N=30 per arm.)*
  A cell at **0/30** cannot reject at **any** post-change count: there is no observation that makes
  it worse. `SPEC-PROMPT-001`'s **AC-CONTROL** is the only defence in that SPEC against its
  highest-blast-radius risk (**R2**), and one of its five cells cannot signal harm. The minimum
  regression each remaining cell **can** distinguish from noise is **c1 16.7 pp**, **c3 23.3 pp**,
  **c2 26.7 pp**, **c5 26.7 pp**. **c1 carries that defence largely alone**, and c1 is the one prompt
  in the set that nobody would mistake for a code request. §4.2.

- **F3 — the hazard was written down before it was measured, in the file that produced the
  measurement.** `probe/tasks.py`'s comment on c4 (branch `feature/SPEC-PROMPT-001`) reads: *"It asks
  for an EXAMPLE, so the model may well emit an illustrative fenced Python block — at which point the
  product does not illustrate it, it EXECUTES it."* The prompt was chosen **because** the author
  suspected this. Thirty trials later the suspicion is a rate. This is the same shape as
  `SPEC-CI-001` §5.1 — *an invariant stated in a comment, and violated anyway* — with the
  difference that here the comment was a **prediction** and the measurement **confirmed** it. It is
  cited as provenance, not as authority: a comment is not evidence, and 0/30 is.

**On the identifier.** The working name was `SPEC-DIRECT-001` and the branch is
`feature/SPEC-DIRECT-001`. **It is renamed here to `SPEC-ILLUSTRATE-001`, and the reason is that
`DIRECT` names the thing this SPEC declines to own.** DIRECT is (a) a protocol in `SYSTEM_PROMPT`
(`main.py:169-174`) and (b) `SPEC-PROMPT-001`'s **measured classification of a reply**, on which its
pre-registered gate is decided. A SPEC called `DIRECT` reads as *"make the model take DIRECT more
often"* — which is a prompt change, which is `SPEC-PROMPT-001`'s contested surface, which is the one
intervention §3.1 rejects on measured evidence, and which pulls against that SPEC's target in the
same string. `ILLUSTRATE` names the class of block the product cannot recognise. It stays accurate
under every candidate fix in §3, including the ones that never touch routing at all.

**The rename costs one command today and more later:** `git branch -m feature/SPEC-DIRECT-001
feature/SPEC-ILLUSTRATE-001`. Verified 2026-08-12: **there is no `origin/feature/SPEC-DIRECT-001`**,
so nothing has been published under the old name and no reference to it exists outside this working
tree. Reverting the decision costs one `git mv` of this directory and the `id:` field in four
frontmatter blocks. Like `SPEC-PROMPT-001`'s pre-registration commit, **it is cheap only before it is
needed.**

**Nothing here has been run by this SPEC.** `verification-T2.md` is created with this document,
structurally complete and **empty of results**, and it says so in its first line. Every figure in
this file is either a re-derivation over `SPEC-PROMPT-001`'s committed V0 records (method and
provenance at §2.1) or a fact read out of the tree at `ab08333`.

---

# SPEC-ILLUSTRATE-001 — An illustrative code block is executed as if it were an answer

**Title:** The turn cannot tell a fenced block written to *show* from one written to *compute*, so it
runs, narrates and remembers the illustration — and this document specifies the discrimination, the
measurement that must precede it, and the boundary against `SPEC-PROMPT-001`

## 1. Scope statement

On a turn where the user asks for an explanation, the model emits one fenced Python block as part of
the explanation. The product executes it, pays a second model round trip to narrate its output, and
writes it to the solution-memory store as a solved task. **Measured at 30 out of 30 trials on the
prompt `"explain what a Python closure is, with a short example"` (2026-08-10, `llama3.1:8b`).**

This SPEC specifies **what the product should do about a block it was not asked to run.** It does
**not** specify a change to `SYSTEM_PROMPT` and it does **not** try to move the routing — both are
`SPEC-PROMPT-001`'s surface, both pull against that SPEC's target in the same string, and §3.1 gives
the measured reason why a prompt-only intervention is the weakest option on this codebase's own
evidence.

**The first deliverable is not a fix. It is the measurement that any fix must be decided on** (§3.5,
T1–T2). The candidate discriminator has a **perfect separation on every cell that exists** and an
**unmeasured false-positive rate on the one cell that does not** — `product.md` §5.4, *deterministic
computation on user-supplied data*, which has no probe cell in any arm. Shipping a suppression rule
without that cell would be `SPEC-PROMPT-001` U5's prohibition committed one layer down: an
unfalsifiable change to behaviour nobody can observe.

**This document is specification only.** No source file is edited by it, no prompt text is written by
it, and no measurement is run by it.

---

## 2. Verified environment

### 2.1 The measurement, where it lives, and how to reach it

**The records are not on this branch.** They are committed on `feature/SPEC-PROMPT-001`, whose tip is
`01aa887` and which is **published** — verified 2026-08-12, `feature/SPEC-PROMPT-001` and
`origin/feature/SPEC-PROMPT-001` are both `01aa887cf33eab74b3b67955da584588701c9d16`. Reading them
requires no checkout and no merge:

| To get | Command |
|---|---|
| The c4 records (30 JSON lines) | `git show feature/SPEC-PROMPT-001:.moai/specs/SPEC-PROMPT-001/probe-runs/v0-c4-general-knowledge.jsonl` |
| Its progress log | `git show feature/SPEC-PROMPT-001:.moai/specs/SPEC-PROMPT-001/probe-runs/v0-c4-general-knowledge.progress.log` |
| All eleven cells | `git ls-tree -r --name-only feature/SPEC-PROMPT-001 -- .moai/specs/SPEC-PROMPT-001/probe-runs/` |
| The harness that produced them | `git show feature/SPEC-PROMPT-001:probe/run_probe.py` (and `classify.py`, `tasks.py`, `variants.py`) |
| From a clone without that branch | `git fetch origin feature/SPEC-PROMPT-001` first |

**`probe/` does not exist at `ab08333`.** It arrived on `2c6b494` on that branch and has never been
merged to `main`. Any run this SPEC requires (T2) therefore happens **on that branch or on a branch
that carries it**, and §3.6 states the rule for touching it.

**Provenance, read out of the records rather than out of configuration** — identical on all 30 c4
rows:

| Field | Value |
|---|---|
| `model_tag` | `llama3.1:8b` |
| `model_digest` | `46e0c10c039e…` |
| `quantisation` | `Q4_K_M` |
| `host` | `http://ollama:11434` (the compose sidecar; `docker-compose.yml` publishes no host port) |
| `ollama_server_version` | `0.32.1` |
| `harness_commit` / `main_commit` | `510f468` |
| `main_sha256` | `ff5a488f…` |
| Timestamps | `2026-08-10T01:23:29Z` … `2026-08-10T01:34:16Z` |
| `elapsed_sec` | median **20.45**, mean **23.00**, min **12.54**, max **45.58**, total **690.1** |

**`main_sha256` is not this tree's.** `ab08333`'s `main.py` is `a359773…`. The difference is
**40 inserted lines and nothing else** — verified with `git diff -U0 510f468 ab08333 -- main.py`: two
hunks, `+40 −0`, both after `main.py:705`, both the `SPEC-BANNER-001` wordmark. **Everything this
SPEC cites below line 705 has the same number in both trees**, and everything above it is offset by
exactly 40, which is why `SPEC-PROMPT-001` cites `main.py:1031-1034` for the branch this document
cites as `main.py:1071-1074`. Two things were checked rather than assumed:

- **`SYSTEM_PROMPT` is byte-identical** between `510f468` and `ab08333` — 2910 characters,
  sha256 `ec8ef366856f…` in both. The measurement was taken against the prompt this tree ships.
- **`CODE_BLOCK_RE` and `extract_last_python_block()` are byte-identical** in both. The classifier
  that produced these numbers is the predicate in the current product.

**Method for every re-derived figure in §2.2 and §2.4.** The stored `reply` field was re-parsed with
`ast` from the standard library; classification was re-derived from the fence pattern and compared
against the stored `classification` and `fence_matches` fields across **all 310 records of all
eleven cells**: **0 disagreements on either field.** No model was called; nothing was executed.
**One disclosure**: this re-derivation used a *transcribed copy* of `CODE_BLOCK_RE`'s pattern rather
than importing `main`, which is exactly what `SPEC-PROMPT-001` R7 forbids in the harness. It is
tolerable here only because the 310-record agreement check is itself the test that the copy did not
drift, and it would **not** be tolerable in anything committed under `probe/`.

### 2.2 What the thirty replies contain

*Re-derived 2026-08-12 over `v0-c4-general-knowledge.jsonl`. N=30 unless stated.*

| Property of the reply or its extracted block | Count |
|---|---|
| Classified **CODE** | **30 / 30** |
| Classified **DIRECT** | **0 / 30** — 95 % Wilson **[0.000, 0.114]** |
| `fence_matches == 1` | **30 / 30** — **not** the `['']` two-block trap |
| Extracted block parses under `ast.parse` | **30 / 30** |
| Block contains `def ` | **30 / 30** |
| Block contains `print(` | **30 / 30** |
| Block contains **any** `import` / `from … import` | **0 / 30** |
| Block loads **any** name it does not itself bind (excluding builtins) | **0 / 30** |
| Block contains a network, file or subprocess token (`requests.`, `urllib`, `socket`, `http`, `imaplib`, `smtplib`, `open(`) | **0 / 30** |
| Every `print()` call takes **only literal** arguments | **0 / 30** |
| At least one `print()` call takes a **computed** argument | **30 / 30** |
| Block length | median **7.5** lines (min 7, max 16) |
| Prose outside the fence | median **80.5** words (min 48, max 155) |
| Prose outside the fence mentions "closure" **and** "scope" | **30 / 30** |
| Reply contains an `Answer:` heading | **19 / 30** — of which **11** appear *before* the fence |
| Reply contains the literal string "Code Protocol" | 2 / 30 |
| Reply contains "restatement" / "Thought" / "DIRECT protocol" | 10 / 30, 18 / 30, 8 / 30 |

**Two rows in that table are the whole of §3.3 and §3.4, and they point in opposite directions.**

*The row that kills a heuristic.* **"Does it `print` a literal?"** is a natural first guess at telling
an illustration from a computation, and it is **measured dead: 0 of 30.** These blocks build a
closure and print what it returns. An illustration of a language feature is *supposed* to compute
something; that is what makes it an illustration rather than a quotation.

*The row that offers one.* **No block imports anything, and no block references any name it does not
define.** These thirty scripts are hermetically closed. §2.4 gives the other side of that
separation.

### 2.3 What the product does with such a block, by line

Read at `ab08333`. Nothing in this path is conditional on anything about the block except its
existence.

| Step | Site | Note |
|---|---|---|
| Extract the last fenced block | `main.py:1071` (`extract_last_python_block`, defined `:447-449`) | A regex. `tech.md:553` already says this in as many words: *"no AST inspection, no import allowlist, no denylist, no length cap, and no user confirmation step. Whatever the model emits between the fences is written to disk and run"* |
| The only branch that avoids execution | `main.py:1072-1074` | Taken **iff** the extractor returns falsy. There is no other way out |
| Parse `# @param` declarations, collect values | `main.py:1086-1087` | 0 of 30 c4 blocks declare one, so nothing prompts and no capture policy is engaged |
| Write to a temp dir, copy `tools.py`, run under `python -I` | `main.py:497-521` (`run_python`, `:473`) | Full network egress and the memory volume are reachable from the child (`tech.md` §7.2) |
| Render the execution panel | `main.py:1108` (`show_exec_result`, `:678`) | Indistinguishable from a legitimate computation turn |
| **Second LLM round trip** — feed stdout back as a synthetic *user* message and stream an `Answer` | `main.py:1113-1127` | `structure.md:122-124`: *"a successful execution costs **two** LLM round trips per attempt"* |
| **Capture into solution memory** | `main.py:1143-1152` → `_capture_turn` `:805-844` | Stores task, thought, **code** and **stdout**. Never reached on the DIRECT path, which returns at `:1074` |
| On failure instead: retry | `main.py:1155-1167`, loop at `:1038`, `MAX_RETRIES` `:73` (default **3**) | A *failing* illustration costs up to **three** thought round trips, not two |

**The cost of the defect is therefore at least one extra model round trip and at most three, plus one
subprocess and one persistent write.** The doubling figure is a **floor**, not a bound, and it is
reasoned from this table rather than measured: **the probe issues exactly one `stream_llm()` call per
trial and never executes anything**, so the second round trip has no recorded latency anywhere in
this project. `verification-T2.md` §3 is where that number goes when it exists.

**The persistent write is the part with a tail.** `format_recall_block()` (`memory.py:383-391`)
renders a stored record under the heading `PRIOR SUCCESSFUL SOLUTION — reference only` with the line
`Its actual output was:` and injects it as a system message before the user's next request
(`inject_recall`, `memory.py:394-408`, called at `main.py:1046-1050`) whenever cosine similarity
clears `DEFAULT_MIN_SIMILARITY = 0.65` (`memory.py:74`). **A second "explain X" question is exactly
the shape that clears it.** The product then shows the model its own illustration, labelled as a
solved task with real output, and asks it to adapt it. Nothing in the store distinguishes an
illustration from a solution, because at the moment of writing nothing in the product did.

### 2.4 The candidate discriminator, and both sides of its separation

*Re-derived 2026-08-12. The predicate: the block parses; it contains no `Import`/`ImportFrom` node;
and every loaded `Name` is either bound inside the block (assignment, `def`, `class`, argument,
comprehension target, import alias, `global`/`nonlocal`) or a builtin.*

| Cell | Task text | CODE trials | Predicate fires |
|---|---|---|---|
| **c4** general knowledge | *explain what a Python closure is, with a short example* | 30 | **30** |
| c2 conversational | *what can you help me with?* | 10 | 7 |
| c3 opinion | *what do you think of Python as a first programming language?* | 4 | 3 |
| c5 general knowledge | *who wrote the book "The Mythical Man-Month"?* | 16 | 2 |
| c1 conversational | *hey, how are you doing today?* | 0 | — |
| **target** | *check my gmail for recent 7 days…* | 13 | **0** |
| **off-example network** | *how many open issues does the cpython repository have…* | 10 | **0** |
| **tool-reachable** | *search the web and summarise the three main criticisms…* | 20 | **0** |

**42 of the 60 CODE-classified control trials; 0 of the 43 CODE-classified measurement-cell trials.**

**And that separation proves less than it looks, which is why §3.5 stages the fix behind a
measurement rather than shipping it.** The three cells at zero are zero because those tasks
**cannot** be done without the network — `imaplib` appears in 10 of 13 target blocks, `requests` in
19 of 20 tool-reachable blocks. The predicate is separating *network-bound* from *self-contained*,
and it is being read as separating *computation* from *illustration*. Those two partitions coincide
across every cell that exists **because no cell exists for the case where they differ**:

> **`product.md` §5.4 — "Deterministic computation on user-supplied data" — has no probe cell in any
> arm, at any N, under any variant.** *"Arithmetic, parsing, text transforms, and date math"*
> (`product.md:205-210`) produce blocks that import nothing and reference nothing external. **They
> are indistinguishable from c4's thirty by this predicate, and they are the product's second
> documented use case.**

**The false-positive rate of the only viable discriminator is therefore unmeasured, and the cell that
would measure it is one entry in `probe/tasks.py`.** That is T1.

**Two lesser discriminators, measured and rejected here so they are not re-proposed:**

- **`Answer:` heading present in the reply** — 19/30 on c4 (63 %), but also 2/10 off-example, 2/20
  tool-reachable, 6/16 c5. It **misses 11 of the 30** it needs to catch and fires on cells it must
  not. Rejected on the numbers.
- **All `print()` arguments literal** — **0/30**. Rejected outright (§2.2).

**One boundary condition the predicate must state, because the corpus contains it.** Of the 103
V0 CODE-classified trials, **3 do not parse** (one each in c5, target, tool-reachable). A block that
does not parse is written to disk and executed anyway today, fails in the child, and enters the
retry loop. The predicate **shall not** fire on an unparseable block (N4): the existing handling is
correct for that case, and a predicate that changes behaviour when its own analysis fails is a
predicate that fails open in the dark.

### 2.5 Repository facts this SPEC stands on

| Fact | Evidence |
|---|---|
| The extractor is a regex with no analysis of any kind | `main.py:444`, `:447-449` |
| The product already documents this as a missing control | `tech.md:553` (§7.2 row *"No static screening of generated code"*) — its citation `main.py:218-220` is **stale**; the function is at `:447-449` |
| `SYSTEM_PROMPT` contains **exactly one** fenced block, and a test asserts it | `tests/test_source_seam.py:547` (`prompt.count("```") == 2`) |
| A reply with **two** fenced blocks classifies DIRECT with an empty match and executes nothing, silently | `tests/test_source_seam.py:533-548`; measured 2026-08-06 |
| The `@param` passage is pinned against semantic change | `SPEC-KEYCHAIN-001` N2 (`spec.md:840`, `:932`); the passage is `main.py:158-166` at `ab08333` |
| New prompt material must be **indented and unfenced** | `SPEC-PROMPT-001` N9 |
| `main.py` is under no coverage floor; decisions belong in gated leaves | `pytest.ini`, `conftest.py`'s `PER_FILE_COVERAGE_TARGETS` (six entries); `SPEC-INPUT-001` §5.3 |
| `main.py` has no logging of any kind | measured 2026-08-12: **0** occurrences of `logging` in 1340 lines |
| The CI pass floor is a single symbol | `.github/workflows/ci.yml:332` (`MIN_PASSED = 573`) — cited by symbol, never by literal (`SPEC-CI-001` N5) |
| `product.md` §5.5 states the behaviour that is measured 0/30 | `product.md:212-217`; its citations `main.py:138-143` and `main.py:480-482` are both stale (now `:169-174` and `:1072-1074`) |
| `structure.md` §3.1's turn-flow diagram cites `main.py:322-379` for `agentic_turn()` | `structure.md:99-124`; the function is at `main.py:990`. `structure.md` is several SPECs behind (`SPEC-KEYCHAIN-001` §2.4) |
| `README.md:109` makes the same claim as `product.md` §5.5, in one sentence | *"For conversational questions that don't need computation ("explain X"), the model skips the code protocol and answers directly."* |

---

## 3. Design decisions

### 3.1 D1 — The fix is product-side. It does not touch `SYSTEM_PROMPT`

**Recommendation.** No prompt text is written by this SPEC. The discrimination happens in the
product, on the extracted block, after the model has spoken.

Three reasons, in descending order of how much they are worth.

**(a) Prompt-only intervention is measured weak on this codebase, by this codebase.**
`SPEC-PROMPT-001` ran a complete 2 × 2 factorial at N=30 per arm on its target cell:

| Arm | Composition | DIRECT | Rate | 95 % Wilson | Fisher vs V0 |
|---|---|---|---|---|---|
| V0 | baseline | 17/30 | 0.5667 | [0.392, 0.726] | — |
| V1 | routing repair only | 19/30 | 0.6333 | [0.455, 0.781] | **0.785215** — null, and in the wrong direction |
| V2 | repair + capability | 7/30 | 0.2333 | [0.118, 0.409] | **0.008428** — rejects |
| V3 | capability only | 12/30 | 0.4000 | [0.246, 0.577] | **0.150734** — null |

**Neither component alone clears significance against V0; only the combination does.** That is the
exact statement and it is the strongest one the data support. **It is not an interaction claim** —
pooled over the routing factor, the capability section has a **significant main effect** (19/60
against 36/60, one-sided Fisher **`p = 0.001601`**), while the interaction contrast does **not**
reach significance (200 000-draw permutation **`p = 0.2743`**; Woolf/Wald on the ratio of odds ratios
**`p = 0.1718`**, 95 % CI **[0.075, 1.59]**, consistent with strong synergy and with mild
antagonism). Prompt text **can** move this model. **A single wording change reliably enough to fix a
30/30 defect is not something this project has ever observed**, and V2 — the arm that did move
things — still **missed its pre-registered 0.40 absolute threshold** and returned **M-b**.

**(b) The two SPECs pull in opposite directions on one string.** §4.1.

**(c) A prompt edit here would owe a six-cell re-measurement and would confound the one in flight.**
`SPEC-PROMPT-001` U5 requires a before/after measurement for **any** prompt change, and its **S6**
already owes V3 at the tool-reachable cell (N=20) and the **full control set (5 × N=30)** before
anything merges. A second, independent editor of the same string turns both measurements into
measurements of an unknown compound.

**The cost of D1, stated rather than hidden:** a product-side fix cannot change what the model
*intends*. It can only change what the product *does* with what the model produced. The model will go
on announcing the CODE protocol for explanation requests, and `verification-T2.md` will go on
recording 0/30 or whatever it becomes. **This SPEC does not close the routing question. It removes
the consequence.**

### 3.2 D2 — Rejected: ask the model to mark illustrative blocks differently

**Rejected on measured evidence, not on taste.**

Any marking scheme that puts the illustration in a **differently-fenced block** produces a reply with
**two fences**, and that is the one reply shape this repository has already established as a silent
failure: `CODE_BLOCK_RE.findall()` returns `['']` — the closing delimiter of the first block pairs
with the opening delimiter of the second — the empty string is falsy, `if not code:` is **true**, and
the turn answers as though no code had been produced (`tests/test_source_seam.py:533-548`, measured
2026-08-06). It would "work", in the sense that nothing would execute. **It would work by walking
into the trap, and it would teach the model, by example, the exact output shape that springs it** —
which is `SPEC-PROMPT-001` **N9**'s second reason, verbatim.

A marker *inside* the single fence — a leading `# illustrative` comment, say — avoids the trap and is
then just (a) again: prompt wording, unenforceable, measured weak, and on the pinned string.

Recorded here rather than omitted, because it is the first idea everyone has.

### 3.3 D3 — Rejected: the two cheap heuristics

**`print()` with only literal arguments: 0 of 30.** Dead on arrival (§2.2).

**An `Answer:` heading in the reply: 19 of 30, with false positives in three other cells.** It is the
model's own DIRECT marker and it is not reliable enough to gate on (§2.4).

Both are recorded with their numbers so that the next reader spends no time on them.

### 3.4 D4 — The discriminator is structural: closed and import-free

**Recommendation.** *The block parses; it imports nothing; every name it loads it also binds, or that
name is a builtin.* Measured **30/30** on c4 and **0/43** across the three cells where execution is
genuinely required (§2.4).

**Why this predicate rather than a longer one.** It is computable with `ast` from the standard
library, it is stable under formatting, it has no denylist to maintain, and every clause of it is a
statement about *what the block needs from the world*, which is the closest observable proxy for *why
it was written*. A block that reaches for nothing outside itself cannot be fetching, checking or
retrieving anything; the only thing it can be doing is demonstrating.

**Why the predicate is not sufficient, and must not be treated as if it were.** §2.4's second half:
`product.md` §5.4 turns are closed and import-free too, and no cell measures them. **The predicate
separates self-contained from network-bound. It is being asked to separate illustration from
computation. Those are different partitions and this corpus cannot tell them apart.**

### 3.5 D5 — What firing means: take the *expensive and durable* half first

**Recommendation, staged, and the staging is the recommendation:**

| Stage | What happens | Gated on |
|---|---|---|
| **1** | Add a **compute-only control cell** to `probe/tasks.py` in the shape of `product.md` §5.4, and measure it at N=30 alongside a re-measurement of c4 under the **shipped** prompt | nothing — this is the first task (T1, T2) |
| **2** | When the predicate fires: **render the execution panel as today, then stop.** Skip the narration round trip (`main.py:1113-1127`) and skip the capture (`main.py:1143-1152`). Emit **one** status line saying the narration was skipped and why | Stage 1's false-positive rate, pre-registered before it is read (T3) |
| **3** | Promote the predicate to suppress the **execution** as well | Stage 2 in the tree, plus a false-positive rate low enough to have been pre-registered as acceptable |

**Why suppression starts at the narration and not at the execution — the argument that decides this
SPEC.** Consider what a **false positive** costs under each.

| | Predicate wrongly fires under **Stage 2** | Predicate wrongly fires under **Stage 3** |
|---|---|---|
| The code | runs | **does not run** |
| stdout | rendered in the execution panel, on screen | **never exists** |
| The user's answer | present, unglossed | **absent** |
| Recovery | read the panel | re-ask the question |

**Stage 2's failure mode is a degraded answer. Stage 3's is no answer.** With the false-positive rate
unmeasured, only one of those is a defensible thing to ship, and it is not the one that can silently
withhold a computation.

**And Stage 2 takes the expensive half.** The narration is a full model round trip — c4's *first*
round trip alone ran a median of **20.45 s** on this hardware — while the subprocess is milliseconds
and its cleanup is guaranteed (`main.py:537-538`). The capture is the half with a **tail**: it is the
only part of the defect that outlives the session, and it is the part that feeds the defect back to
the model (§2.3). **Stage 2 removes the whole of the cost that recurs and the whole of the cost that
compounds, and leaves only the part that is bounded by `EXEC_TIMEOUT_SEC` and deleted afterwards.**

**One line, not zero.** When the turn declines to narrate, it **says so** (E3). Silence here is
indistinguishable from the pre-fix product, and `SPEC-MEMORY-001`'s one-line degradation convention
(`product.md` §4 item 20) is the established shape for exactly this: a behaviour the user cannot
otherwise detect gets one line and no more.

**What Stage 2 does not claim.** It does not stop the product executing code the user did not ask
for. §5 item 1 says so plainly, and Stage 3 is the only thing that would, and Stage 3 is gated on a
measurement nobody has taken.

### 3.6 D6 — The harness is shared, so touching it needs a rule

`probe/` belongs to `SPEC-PROMPT-001` and its records are that SPEC's evidence. T1 adds a cell to
`probe/tasks.py`. The rule, stated once:

**Additive only. No existing `Task` — its `id`, its `text`, its `kind`, its `n` or its
`expect_direct` — may change.** `probe/tasks.py`'s own banner requires byte-identical task text
across arms *"or the columns of that table are not comparable, which is the quiet way a before/after
measurement stops being one"*. A new cell appended alongside them costs the existing records nothing
and makes every future arm carry it.

**And the new cell must be run at V0 before it is run at anything else**, for the same reason c4's V0
run is what made this SPEC possible.

---

## 4. The tension with `SPEC-PROMPT-001`

This section exists because the two SPECs want opposite things from one string, and because a reader
who takes either one on its own will draw a wrong conclusion about the other.

### 4.1 They pull in opposite directions

| | `SPEC-PROMPT-001` | `SPEC-ILLUSTRATE-001` |
|---|---|---|
| Target behaviour | The model should take **CODE more often** | The product should **execute less often** |
| Target cell | *check my gmail for recent 7 days…* — V0 DIRECT **0.5667**, wanted **lower** | *explain what a Python closure is…* — V0 DIRECT **0.0000**, wanted **higher** |
| Instrument | `SYSTEM_PROMPT` | `agentic_turn()` and the extracted block |
| Direction on the DIRECT rate | **down** | **up** |

**Both are correct about their own cell**, which is why this is a tension and not a disagreement. The
prompt's routing rule is one text governing both, and a wording that narrows DIRECT — which is
precisely `SPEC-PROMPT-001`'s D1 — is a wording that makes an explanation request more likely to
produce an executed block, which is this defect. `SPEC-PROMPT-001`'s **AC-CONTROL** names that risk
in its own words: *"a capability advertisement shall not convert this into a product that writes and
executes Python to answer 'how are you'"* (**S2**).

**D1 is the resolution.** By staying off the prompt entirely, this SPEC removes itself from the
contested string. The two can then proceed in parallel: one changes what the model is told, the other
changes what is done with what the model says.

### 4.2 c4 is dead as a regression detector, and that is `SPEC-PROMPT-001`'s problem

**AC-CONTROL item 4 requires the shipped DIRECT rate on each control prompt to be "no worse than
V0's, at the same N", and item 5 forbids attributing a drop to noise "without stating N". So the
question item 5 poses is: what drop can each cell actually distinguish from noise?**

*Computed 2026-08-12, one-sided Fisher exact, N=30 per arm, `alpha = 0.05`:*

| Cell | V0 DIRECT | Largest post-change count that still rejects | Minimum detectable regression |
|---|---|---|---|
| **c1** *hey, how are you doing today?* | 30/30 | 25/30 (`p = 0.02609`) | **16.7 pp** |
| **c3** *what do you think of Python…* | 26/30 | 19/30 (`p = 0.03581`) | **23.3 pp** |
| **c2** *what can you help me with?* | 20/30 | 12/30 (`p = 0.03460`) | **26.7 pp** |
| **c5** *who wrote the book…* | 14/30 | 6/30 (`p = 0.02695`) | **26.7 pp** |
| **c4** *explain what a Python closure is…* | **0/30** | **none, at any count** | **none — the cell cannot fail** |

**A cell at zero cannot get worse.** It will report non-inferiority forever, on any prompt, including
one that has made everything else dramatically worse. It is not a weak detector; **it is not a
detector**. And it is the cell nearest the boundary the prompt edit is moving, which is the one place
a control set most needed to be able to see.

**c1 carries R2's defence largely alone**, at 16.7 pp, and c1 is *"hey, how are you doing today?"* —
the prompt least like a code request in the entire set, and therefore the least sensitive to the
change being policed. **The control set is strongest where the risk is smallest.**

**This SPEC states the finding and declines to fix it**, because the remedy is a change to
`SPEC-PROMPT-001`'s own instrument and belongs in that SPEC's amendment, not as a rider here. Two
remedies are available and this document recommends neither over the other:

1. **Add a replacement general-knowledge control with headroom** — a question that asks for an
   explanation *without* asking for an example, which F1 suggests would sit well above zero — and
   accept that it measures a slightly different thing from c4.
2. **Retire c4 as a control and re-designate it as a measurement cell of this SPEC**, where 0/30 is
   the *finding* rather than a floor, and where a rate that moves is signal in either direction.

Option 2 has a property option 1 does not: **it stops one cell from being scored under a criterion it
cannot satisfy**, which is the same correction `SPEC-PROMPT-001` v1.1.1 made to AC-GATE item 5 —
*"a criterion that cannot be met is not evidence, and leaving it to be ticked converts an unmet
requirement into a claim."*

### 4.3 What this SPEC changes about that baseline, exactly

**The claim that any fix here forces a re-measurement of `SPEC-PROMPT-001`'s control baseline is
true of a prompt fix and false of D1's.** The distinction is worth stating precisely, because it is
the main practical benefit of D1 and the easiest thing to get wrong:

| | Changed by a **prompt** fix | Changed by **D1**'s product-side fix |
|---|---|---|
| The replies the model produces | **yes** — every control cell's V0 rate must be re-measured (5 × 30, plus the target) | **no** — the model sees an identical prompt and the probe records only replies |
| The DIRECT rate the probe computes | **yes** | **no** — `classify()` is a function of the reply text alone |
| The stored records' comparability | **broken** until re-run | **untouched** |
| **What a green AC-CONTROL means** | unchanged in meaning | **changed** — see below |

**The one thing D1 does change is the meaning, and it must be written down where AC-CONTROL is read.**
After Stage 2, a CODE classification at c4 no longer implies a narration round trip or a memory
write. AC-CONTROL's rate is still measuring the model's routing; but the *harm* AC-CONTROL was
written to detect — *"the product feeling slower and more eager, on every turn, for every user"* —
would be **partly mitigated at a layer AC-CONTROL cannot see.** Two misreadings become available and
both are forbidden by U4:

- **Reading a green AC-CONTROL as evidence this defect is fixed.** It is not; the rate is unchanged
  by construction.
- **Reading this SPEC's fix as an improvement in the DIRECT rate.** It is not; the model routes
  exactly as it did.

### 4.4 What is owed, and by whom

| Owed | Owner | Status |
|---|---|---|
| V3 at the tool-reachable cell (N=20) and the **full control set** (5 × N=30), before any prompt text merges | `SPEC-PROMPT-001` **S6** / AC-GATE item 7 | **not run** — and it is the run that would tell this SPEC whether c4's 0/30 survives the shipped prompt |
| A decision on c4's status as a control (§4.2) | `SPEC-PROMPT-001`, by amendment | not taken |
| The compute-only cell (§2.4, T1) | **this SPEC** | not run |
| c4 re-measured under the shipped prompt | **this SPEC** (T2), consuming S6's run if it happens first | not run |
| Whether an executed illustration is ever *wrong* rather than merely wasteful | nobody, today | §5 item 2 |

**The dependency runs one way only.** This SPEC needs to know what the shipped prompt does to c4;
`SPEC-PROMPT-001` needs nothing from this SPEC. So this SPEC is **downstream** and must not block
that one — but neither may it record its own Stage-2 verdict against a prompt that is about to
change (S3).

---

## 5. What is not known

Named as not known, and not as not needed.

1. **Whether the defect persists under the shipped prompt. Unmeasured.** V1, V2 and V3 ran on the
   **Target cell only** — verified 2026-08-12: `v1-target.jsonl`, `v2-target.jsonl`,
   `v3-target.jsonl` are the only non-V0 record files that exist. **No control prompt has been
   measured under any variant other than V0.** Under M-b what ships is `V0 + capability` (V3's
   string), and c4's rate under it is unknown. It could be 0/30 unchanged; it could be worse, since
   V3's capability section widens the sanctioned use of CODE. **This SPEC's central figure describes
   a prompt that may not be the one that ships.**

2. **Whether executing an illustration ever produces a WRONG answer, as opposed to a wasteful one.
   Nobody has assessed correctness on any CODE trial in this project.** `SPEC-PROMPT-001` v1.1.2
   records **65 unassessed CODE trials across four arms** and defers the M-a/M-c split to
   `SPEC-ACCOUNT-001` A1. For c4 specifically, **30/30 blocks parse and that is the entirety of what
   is known**: whether they *run*, what they print, and whether the narrated `Answer` that follows is
   consistent with the prose explanation that preceded it are all unmeasured. Two of these matter
   materially:
   - **If a block raises**, the turn does not cost two round trips; it costs up to three thought
     streams through the retry loop (`main.py:1038`, `MAX_RETRIES` `:73`), and the user watches the
     model "diagnose" an illustration that was never meant to run.
   - **If the narrated answer contradicts the prose answer**, the turn has produced two different
     answers to one question and shown both. Nobody has looked.

3. **The token cost is not measured anywhere.** No probe record carries a token count; `elapsed_sec`
   covers the first round trip only. "Roughly double" is a floor derived from `structure.md:122-124`
   and §2.3's table, not an observation.

4. **The false-positive rate of §3.4's predicate.** Unmeasured, because the cell does not exist
   (§2.4). This is the single most consequential unknown in the document and T1 exists for it alone.

5. **Nothing here generalises past `llama3.1:8b` `Q4_K_M` at digest `46e0c10c039e…`.** One model, one
   quantisation, one host, one day. `SPEC-PROMPT-001` S4's labelling rule applies unchanged.

6. **How often real users ask c4-shaped questions.** The product has no telemetry of any kind and
   will not be given any. The rate at which this defect is *encountered* is therefore unknowable from
   inside the product, and this SPEC's priority is set from the cost per occurrence and the
   persistence of the record, not from a frequency nobody can supply.

---

## 6. Where the code belongs

**The predicate is a new gated leaf, not a function in `main.py`.**

`main.py` is under no coverage floor (`pytest.ini`, `conftest.py`'s `PER_FILE_COVERAGE_TARGETS`), and
`SPEC-INPUT-001` §5.3 established the rule this project holds to: **`main.py` is wiring, and every
decision lives in a gated leaf.** "Is this block an illustration?" is the most decision-shaped thing
this SPEC contains — it has branches, boundary conditions, a defined behaviour on unparseable input,
and a false-positive rate that will be argued about. It belongs in a module with a floor, in the
company of `params.py`, `settings.py` and `keychain.py`.

**Registering a gated module takes two edits and forgetting one fails loudly** — the `--cov` target
list in `pytest.ini` and the floor in `conftest.py`'s `PER_FILE_COVERAGE_TARGETS`; a module in the
second but not the first makes the coverage report raise, which the hook records as
`coverage unavailable` and the session fails. **And a third edit, which this repository has already
got wrong once**: the new module must be added to the `COPY` line in the `Dockerfile`, or the SPEC
ships a module that is absent from the image that runs it (`SPEC-KEYCHAIN-001` §5; `SPEC-CI-001`
§5.1, where `keychain.py` was added to that line and not to the workflow's file list **within one
day** of a comment warning against exactly that). `tests/test_source_seam.py` asserts set equality
between those lists and is the gate that now catches it.

`main.py`'s share is the wiring at `main.py:1108-1152`: call the predicate, and branch on it. If a
change in `main.py` would need a new test to be trusted, it is in the wrong file.

---

## 7. EARS requirements

All five requirement types are represented.

### 7.1 Ubiquitous — always true

| # | Requirement |
|---|---|
| **U1** | The product **shall always** be able to state, for any turn that executed a block, **why** it executed it. Today the answer is *"because `extract_last_python_block()` returned something truthy"* (`main.py:1071-1072`), which is not a reason about the task; it is a fact about a regex. |
| **U2** | Any behaviour introduced by this SPEC **shall always** be visible in the transcript on the turn it occurs, in exactly one status line. A turn that silently does less is indistinguishable from the pre-fix product, and `product.md` §4 item 20's one-line convention is the established shape. |
| **U3** | This SPEC **shall always** treat `SYSTEM_PROMPT` as read-only. Not amended, not appended to, not reordered — including the `@param` passage pinned by `SPEC-KEYCHAIN-001` N2 and the single-fence property asserted at `tests/test_source_seam.py:547`. |
| **U4** | Documentation **shall always** state that this SPEC changes what the product **does** with a block and not what the model **produces**, and that a control-set DIRECT rate is therefore evidence about neither this defect nor its fix (§4.3). |
| **U5** | Every figure in `verification-T2.md` **shall always** be a figure a run produced, quoted with the cell, the variant and the trial count it came from. What was not run **shall** be named as not run, not as not needed. Adopted verbatim from `SPEC-PROMPT-001` U6. |
| **U6** | Any discriminator this SPEC ships **shall always** be reported with **both** halves of its separation — the rate at which it fires on illustrations **and** the rate at which it fires on computations that must run. A single-sided figure is an advertisement. |

### 7.2 Event-driven — WHEN … THEN …

| # | Requirement |
|---|---|
| **E1** | **WHEN** a fenced block is extracted from a reply, **THEN** the turn **shall** evaluate the illustration predicate (§3.4) on it **before** deciding what to do with it, and **shall** carry the outcome as an explicit value rather than re-deriving it at each use site. |
| **E2** | **WHEN** the predicate fires, **THEN** the turn **shall not** issue the narration round trip (`main.py:1113-1127`) and **shall not** call `_capture_turn()` (`main.py:1143-1152`). The execution panel (`main.py:1108`) **shall** still be rendered, so the user retains the output. |
| **E3** | **WHEN** the turn declines to narrate, **THEN** exactly **one** status line **shall** say so and name the reason in the user's terms — *"this looks like an illustration; showing it rather than answering from it"* — and **shall not** be emitted more than once per turn. |
| **E4** | **WHEN** the predicate is evaluated, **THEN** its result **shall** be derived from an `ast` parse of the block and from nothing else: no substring search, no regex over source text, no model call. A second parser is a second thing to drift. |
| **E5** | **WHEN** `probe/tasks.py` gains this SPEC's cell, **THEN** every existing `Task` **shall** be left byte-identical, and the new cell **shall** be measured at **V0** before it is measured under any other variant (D6). |
| **E6** | **WHEN** `verification-T2.md` records a rate for c4, **THEN** it **shall** record which prompt string produced it — V0's, or the string `SPEC-PROMPT-001` ships — and **shall not** compare rates across different prompt strings without saying so. |
| **E7** | **WHEN** any part of this SPEC is implemented, **THEN** `product.md` §5.5, `product.md` §6, `README.md:109`, and `tech.md`'s §7.2 *"No static screening"* row **shall** be corrected in the same change, and the stale citations named at §2.5 **shall** be repointed. |

### 7.3 State-driven — IF/WHILE … THEN …

| # | Requirement |
|---|---|
| **S1** | **IF** the extracted block does not parse under `ast.parse`, **THEN** the predicate **shall not** fire and the turn **shall** behave exactly as it does today. Measured: **3 of 103** V0 CODE-classified blocks do not parse; the retry loop is the existing handling and it is correct for that case. |
| **S2** | **IF** the compute-only cell (T1) has not been measured, **THEN** no suppression behaviour **shall** be merged. The predicate's false-positive rate is the only thing that makes Stage 2 defensible, and shipping first would be `SPEC-PROMPT-001` U5's prohibition committed one layer down. |
| **S3** | **IF** `SPEC-PROMPT-001` has not merged its prompt change, **THEN** this SPEC's Stage-2 verdict **shall** be recorded as provisional and **shall** state the prompt string it was measured against. A verdict taken against a string about to be replaced is a verdict about the past. |
| **S4** | **IF** the predicate fires, **THEN** the turn's outcome **shall** still be a rendered answer: the model's own prose reply plus the execution panel. **No turn shall end with less on screen than it does today.** |
| **S5** | **WHILE** `verification-T2.md` contains no results, this SPEC **shall** remain `draft`, the file **shall** state that it has not been run, and T4 onwards **shall not** start. |
| **S6** | **IF** a measurement in this SPEC is taken against any model, quantisation or host other than `llama3.1:8b` `Q4_K_M` on the compose sidecar, **THEN** it **shall** be labelled with what it was measured against and **shall not** be recorded as discharging any criterion. Adopted from `SPEC-PROMPT-001` S4. |

### 7.4 Unwanted — shall not

| # | Requirement |
|---|---|
| **N1** | `SYSTEM_PROMPT` **shall not** be modified by this SPEC — not one character, in any of its 2910 (sha256 `ec8ef366856f…`). The measured weakness of prompt-only intervention (§3.1) is the reason, and the collision with `SPEC-PROMPT-001` is the second reason. |
| **N2** | No design **shall** require the model to emit a second fenced block, a differently-fenced block, or any output shape that makes `CODE_BLOCK_RE.findall()` return more than one match. `tests/test_source_seam.py:533-548`; §3.2. |
| **N3** | The predicate **shall not** be implemented in `main.py`. §6. |
| **N4** | The predicate **shall not** fail open, fail silently, or change behaviour when its own analysis is inconclusive. Unparseable block, timeout, unexpected node type — **each means "do not fire"** (S1). |
| **N5** | This SPEC **shall not** claim the routing defect is fixed, mitigated, or improved. The model routes exactly as it did; §4.3's two forbidden misreadings are forbidden in the documentation as well as here. |
| **N6** | `verification-T2.md` **shall not** contain placeholder figures, illustrative numbers, or example tables populated with plausible values. Empty cells, explicitly marked not-yet-run. Adopted verbatim from `SPEC-PROMPT-001` N7. |
| **N7** | No existing cell in `probe/tasks.py` **shall** be renamed, re-worded, re-sized or removed, and no existing record file **shall** be rewritten, re-scored or appended to. `SPEC-PROMPT-001`'s evidence is not this SPEC's to edit. |
| **N8** | Execution **shall not** be suppressed at Stage 2. Suppressing it is Stage 3 and is gated on a measurement that does not exist; the failure mode of a false positive under suppression is **no answer**, and that is not a thing to ship on an unmeasured rate (§3.5). |
| **N9** | The predicate **shall not** grow a denylist of module names, function names or "dangerous" constructs. This is not a sandbox SPEC; `tech.md` §7.2's missing controls are out of scope (§9 item 4) and a half-built allowlist reads as a security boundary while being none. |
| **N10** | No turn **shall** ask the user whether to execute. A confirmation prompt converts a measured 30-in-30 nuisance into a keystroke on every code turn the product runs, and `SPEC-INPUT-001` U2's constraint on the child's stdin is not the only reason that is a bad trade. |

### 7.5 Optional — where possible

| # | Requirement |
|---|---|
| **O1** | **Where** the predicate fires, `/memory` or a comparable report **should** be able to say that a turn was not captured and why, since "why is this not in my history" is the question a suppressed capture creates. |
| **O2** | **Where** the second round trip's latency can be measured, it **should** be recorded in `verification-T2.md` §3, so that "roughly double" stops being an inference from `structure.md:122-124`. |
| **O3** | **Where** a c4 block is executed during T2, its exit status and stdout **should** be recorded, so that §5 item 2's first half — *do these blocks even run?* — stops being unknown for the cost of one extra field. Correctness of the narrated answer stays out of scope (§9 item 6). |
| **O4** | **Where** `probe/` gains this SPEC's cell, the harness **should** record the predicate's verdict per trial alongside `classification` and `fence_matches`, so that a future arm can report the predicate's behaviour without re-deriving it from stored text. One boolean per trial. |

---

## 8. In scope

1. **`verification-T2.md`** — structure now, figures only from runs (U5, N6).
2. **One new cell in `probe/tasks.py`** in the shape of `product.md` §5.4 — deterministic computation
   on user-supplied data, expecting **CODE** — measured at V0, N=30 (T1, T2, D6). **Additive only**
   (N7).
3. **A re-measurement of c4** at N=30 under the prompt string that is current when T2 runs, labelled
   with which string that is (E6).
4. **A new gated leaf module** holding the illustration predicate: `ast`-based, stdlib-only, floored
   at **100 %**, registered in **both** `pytest.ini` and `conftest.py`'s
   `PER_FILE_COVERAGE_TARGETS`, added to the `Dockerfile` `COPY` line and to the file lists
   `tests/test_source_seam.py` asserts set equality over (§6).
5. **Wiring in `main.py` only** — evaluate the predicate at `main.py:1071`-adjacent code, branch at
   `:1108-1152`, one status line (E1–E3). No decision logic (N3).
6. **Tests**: the predicate's boundary conditions, including the unparseable block (S1) and a
   `product.md` §5.4-shaped block that **must not** fire; a source-seam assertion that
   `SYSTEM_PROMPT` is unchanged by this SPEC (N1); an assertion that the capture call is not reached
   when the predicate fires.
7. **The CI floor** — raise `MIN_PASSED` (`.github/workflows/ci.yml:332`) to a count **measured**
   from a real `junitxml` run, never computed from an expected delta (`SPEC-PROMPT-001` E5,
   `SPEC-KEYCHAIN-001` HISTORY).
8. **Documentation, including the citation corrections this SPEC found** (E7):
   - **`product.md` §5.5 (`product.md:212-217`) is a documentation defect and this SPEC fixes it.**
     It states that *"'Explain X' style questions take the DIRECT protocol"*. **Measured 0/30.** The
     documented behaviour and the measured behaviour disagree, and the section is rewritten to say
     what happens, with the rate and its date, in the style `product.md` §6.2 established for a
     finding that has been resolved and §6.1 for one that has not. Its two stale citations
     (`main.py:138-143` → `:169-174`; `main.py:480-482` → `:1072-1074`) are repointed in the same
     pass.
   - **`README.md:109`** carries the same claim in one sentence and is corrected with it. A README
     is the one document read by people who will never read a SPEC.
   - **`product.md` §6** gains one limitation in the §6.1 style, recording that an illustrative block
     is executed, narrated and captured, with the measured rate — **for as long as that remains
     true**.
   - **`tech.md` §7.2's *"No static screening of generated code"* row (`tech.md:553`)** — its
     citation `main.py:218-220` is repointed to `:447-449`, and the row is amended to record what the
     predicate does and does not screen. It is **not** deleted: the predicate is not a security
     control (N9).
   - **`structure.md` §3.1 (`structure.md:99-124`)** — the turn-flow diagram gains the branch, and
     its citations are repointed (`agentic_turn()` `main.py:322-379` → `:990`; the extract at `:334`
     → `:1071`). The rest of `structure.md` stays as it is (§9 item 8).

## 9. Out of scope

1. **Any change to `SYSTEM_PROMPT`, and the routing question generally.** N1, §3.1. `SPEC-PROMPT-001`
   owns that string and has a measurement in flight against it.
2. **Making c4 route DIRECT.** That is the routing question by another name. This SPEC's success does
   not move c4's rate by one trial and §4.3 forbids claiming otherwise.
3. **Repairing `SPEC-PROMPT-001`'s control set.** §4.2 states the finding, quantifies it, and offers
   two remedies. Choosing one is an amendment to that SPEC, by its author, with its own re-run.
4. **Sandboxing.** `tech.md` §7.2's missing controls — no `seccomp`, no `cap_drop`, no `read_only`,
   no resource limits — are a different subject with a different threat model. The predicate is a
   *cost* control, not a security boundary, and N9 keeps it from pretending otherwise.
5. **Stage 3 (suppressing execution).** Named in §3.5 as the eventual target, gated on a
   false-positive rate nobody has measured. It is out of *this* version's scope, not out of the
   project's.
6. **Assessing whether generated code is correct.** Nobody in this project has done it on any trial;
   `SPEC-PROMPT-001` v1.1.2 records 65 unassessed CODE trials and defers the question to
   `SPEC-ACCOUNT-001` A1. O3 asks only whether c4's blocks *run*, which is a different and much
   cheaper question.
7. **A user confirmation step before execution.** N10.
8. **Rewriting `structure.md`.** It is several SPECs behind (`SPEC-KEYCHAIN-001` §2.4). This SPEC
   fixes §3.1 because it changes §3.1, and leaves the rest to whoever owns documentation — the same
   boundary `SPEC-PROMPT-001` §8 item 6 drew.
9. **Retry behaviour.** A failing illustration entering the retry loop is a consequence of the defect
   and not a separate one; if Stage 2 lands, the loop is unchanged and still runs on a block that
   raises. Changing `MAX_RETRIES` semantics is `product.md` §6.7's subject, not this one's.
10. **Telemetry of any kind.** §5 item 6. The frequency of this defect in real use will remain
    unknown, and that is a deliberate product property rather than a gap this SPEC may close.

---

## 10. Traceability

| Artefact | Location |
|---|---|
| Requirements | this file, §7 (U1–U6, E1–E7, S1–S6, N1–N10, O1–O4) |
| Design decisions with costs | this file, §3 (D1–D6) |
| The tension with `SPEC-PROMPT-001`, and what each SPEC owes | this file, §4 |
| What is not known | this file, §5 |
| The measurement record | `.moai/specs/SPEC-ILLUSTRATE-001/verification-T2.md` — **NOT YET RUN** |
| Task decomposition, critical path, risks | `.moai/specs/SPEC-ILLUSTRATE-001/plan.md` |
| Acceptance criteria | `.moai/specs/SPEC-ILLUSTRATE-001/acceptance.md` |
| The records this SPEC is built on | `feature/SPEC-PROMPT-001` (tip `01aa887`, published), `.moai/specs/SPEC-PROMPT-001/probe-runs/v0-c4-general-knowledge.jsonl` and the ten sibling cells — **not present at `ab08333`**; §2.1 gives the commands |
| The harness | `feature/SPEC-PROMPT-001`: `probe/run_probe.py`, `probe/classify.py`, `probe/tasks.py`, `probe/variants.py`; `tests/test_probe.py` |
| The prompt that produced the measurement | `main.py:122-182` — **byte-identical** at `510f468` and `ab08333`, sha256 `ec8ef366856f…` |
| The predicate that classifies a reply | `main.py:444`, `main.py:447-449` |
| The branch that avoids execution | `main.py:1072-1074` (`SPEC-PROMPT-001` cites `:1032`; §2.1 explains the 40-line offset) |
| The execution path | `main.py:473-538`; panel at `:678`, called `:1108` |
| The second round trip | `main.py:1113-1127`; `structure.md:122-124` |
| The capture, and the loop it closes | `main.py:1143-1152`, `_capture_turn` `:805-844`; `memory.py:361-380`, `:383-391`, `:394-408`; threshold `memory.py:74` |
| The two-fence trap that disqualifies D2 | `tests/test_source_seam.py:533-548`; the single-fence assertion at `:547` |
| The pinned prompt passage | `main.py:158-166`; `SPEC-KEYCHAIN-001` N2 (`spec.md:840`, `:932`); `SPEC-PROMPT-001` N3, N9 |
| The gate registration this SPEC's module must join | `pytest.ini`, `conftest.py`'s `PER_FILE_COVERAGE_TARGETS`, the `Dockerfile` `COPY` line, `tests/test_source_seam.py` |
| CI floor to be raised | `.github/workflows/ci.yml:332` (`MIN_PASSED = 573`) |
| Explicitly not amended | `SYSTEM_PROMPT` `main.py:122-182` (N1); existing cells and records under `probe/` (N7); `docker-compose.yml` |
| Documentation to be corrected | `product.md:212-217` (§5.5), `product.md` §6, `README.md:109`, `tech.md:553` (§7.2 row), `structure.md:99-124` (§3.1) |
| Project context | `.moai/project/product.md`, `.moai/project/structure.md`, `.moai/project/tech.md` |

| Requirement group | Primary acceptance criteria |
|---|---|
| U1, E1, E4, S1, N3, N4, N9 | **AC-PREDICATE** |
| U6, S2, E5, E6, N6, N7 | **AC-MEASURE** |
| U2, E2, E3, S4, N8, N10 | **AC-SUPPRESS** |
| U3, N1, N2 | **AC-PROMPT-UNTOUCHED** |
| U4, N5, §4.3 | **AC-BOUNDARY** |
| §8 item 8, E7 | **AC-DOCS** |
| §8 item 7 | **AC-FLOOR** |
