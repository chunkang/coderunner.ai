---
id: SPEC-MODEL-001
version: "1.0.0"
status: "draft"
created: "2026-08-19"
updated: "2026-08-19"
author: "Chun Kang"
priority: "MEDIUM"
---

## HISTORY

### v1.0.0 (2026-08-19) — Initial specification

**The edit is one line. What the edit invalidates is every behavioural number this project owns.**
`main.py:71` reads `MODEL_NAME = os.environ.get("CODERUNNER_MODEL", "llama3.1:8b")`, and
`docker-compose.yml:46` and `:78` carry the same default twice more. Replacing that string with a
Phi-3.5 tag takes seconds. **Every measured rate in `.moai/` was taken against `llama3.1:8b` and
none of them survives the swap** — not as wrong, but as *no longer about the shipped product*. This
SPEC exists because the config edit is trivial and the re-measurement is not, and because doing the
first without the second would leave the repository's README and its project documents asserting
behaviour it has never observed.

**Nothing about Phi-3.5 is verified here, and the reason is mechanical.** The Docker daemon on this
host is down — verified today, `docker info` returns *"Cannot connect to the Docker daemon at
unix:///Users/kurapa/.docker/run/docker.sock"* — and there is no host `ollama` binary
(`command -v ollama` finds nothing). The model runs in a compose sidecar which publishes no host
port. **So the Phi-3.5 tag string, its parameter count, its quantisation, its context window and its
on-disk size are all UNVERIFIED and none of them appears as a figure anywhere in this document.**
T1 exists to establish them, and §4's **U2** forbids any downstream figure T1 did not produce. The
repository contains **zero** occurrences of `phi-3` or `phi3` today, in any case, so there is no
prior claim to inherit and none to contradict.

**The central risk is stated once, here, and again at §2.5 where it has evidence attached.**
`SYSTEM_PROMPT` (`main.py:122-182`, verified today: 61 source lines, **2575 characters** after
`textwrap.dedent().strip()`, sha256 `8a896634a9f6…`) is not an instruction. It is a **multi-part
contract** — a routing decision between two named protocols (`main.py:126-129`), the CODE
protocol's ten rules (`main.py:131-167`), and a `# @param` declaration grammar with its own type
list and its own prohibition on a second fence (`main.py:158-166`), among others; §2.5 tabulates
five such parts and cites each one. Phi-3.5-mini is a substantially
smaller model than `llama3.1:8b`. **Smaller models generally hold multi-protocol contracts less
reliably, so T2 may measure the `SPEC-ILLUSTRATE-001` defect as WORSE under Phi-3.5, not better —
and that is a result this SPEC admits in advance rather than a failure of it** (§3.3, outcome
**P-c**). The same applies to the `@param` grammar, which `SPEC-INPUT-001` R1 already named as *"the
highest-probability failure in this SPEC, and the only one no unit test can detect"* against an 8B
model.

**One collision was found while writing this, and it is not this SPEC's to resolve.**
`SPEC-PROMPT-001` **S4** (`spec.md:893` on `feature/SPEC-PROMPT-001`) reads: *"**IF** a probe result
is obtained against any model, quantisation or host other than `llama3.1:8b` on the compose sidecar,
**THEN** it **shall** be labelled with what it was measured against and **shall not** be recorded as
satisfying the gate."* **Changing the default disqualifies, by that SPEC's own rule, every probe run
taken after the swap from ever discharging that SPEC's gate.** That SPEC still owes V3 at the
tool-reachable cell and a full control set before its prompt text merges. §5.2 states the ordering
consequence and declines to choose for it.

**Every `file.py:LINE` citation below was read out of the working tree today, at `ab08333`, before
it was written down.** That is not a formality: **17 of the 20 symbol-anchored `main.py` citations
in `README.md` are stale** by commit `7f3e1b3`'s own count, `.moai/project/tech.md:17` cites
`main.py:66` for the very constant this SPEC changes (it is at `:71`), and `memory.py:268`'s
docstring cites `main.py:52` for the same constant. **Three documents point at three different wrong
lines for one string.** None of those numbers was copied forward into this file.

**One figure I could not reproduce, disclosed rather than repeated.** `SPEC-ILLUSTRATE-001` §2.1 and
its **N1** state that `SYSTEM_PROMPT` is **2910 characters**, sha256 `ec8ef366856f…`, at `ab08333`.
This tree *is* `ab08333`, and I measured **2575 / `8a896634a9f6…`** after `dedent().strip()`, **2577
/ `d4a736094a7b…`** after `dedent()` alone, and **2773 / `c2f9d0922c5c…`** for the raw undedented
literal. **No convention I tried yields 2910.** I do not know which of us is wrong, so this document
cites only the figure it measured and flags the disagreement for whoever owns that SPEC. It matters
because `SPEC-ILLUSTRATE-001` **N1** pins the prompt by that hash, and a pin nobody can reproduce
does not pin anything.

---

# SPEC-MODEL-001 — Replace the default chat model, and re-measure what the replacement invalidates

**Title:** `llama3.1:8b` becomes Phi-3.5 at four declaration sites and in every document that states
a measured rate, and the deliverable is not the edit — it is the measurement that tells anyone
whether the product still behaves the way it is documented to

## 1. Scope statement

The product's default chat model is `llama3.1:8b`, declared at `main.py:71` and defaulted twice more
in `docker-compose.yml` (`:46` for the one-shot `model-pull` service, `:78` for the app service).
This SPEC replaces it with Phi-3.5 and **re-measures the behaviour that the replacement puts back
into question.**

**The measurement is the deliverable and the config edit is a rider on it.** The scope is
*"`SPEC-PROMPT-001`'s five control cells plus `SPEC-ILLUSTRATE-001`'s c4"* — and **c4 is one of
those five**, so the count is **five cells, not six**, run once each at N=30. §3.2 states that
plainly because the phrase invites double-counting. **150 trials, one model round trip apiece**; at
`llama3.1:8b`'s c4 median of **20.45 s** per trial (an *inherited* figure — `SPEC-ILLUSTRATE-001`
§2.1, re-derived there from the committed records, **not** re-derived here), that is hours of wall
clock and an unknown number under a model nobody has timed. The edit to `main.py:71` is one string.
**If this SPEC is summarised as "swap the model", the summary has dropped the whole of the work and
kept the whole of the risk.**

**This document is specification only.** No source file is edited by it, no model is pulled by it,
no probe is run by it, and no figure in it comes from a Phi-3.5 execution — because none has
occurred.

---

## 2. Verified environment

*Every line number in this section was read from the working tree at `ab08333` on 2026-08-19.
Nothing here is carried over from another document.*

### 2.1 Where the model name lives

| Site | Line | What it is |
|---|---|---|
| `main.py:71` | `MODEL_NAME = os.environ.get("CODERUNNER_MODEL", "llama3.1:8b")` | **The default.** Read at import |
| `docker-compose.yml:46` | `CODERUNNER_MODEL: ${CODERUNNER_MODEL:-llama3.1:8b}` | The one-shot `model-pull` service |
| `docker-compose.yml:78` | `CODERUNNER_MODEL: ${CODERUNNER_MODEL:-llama3.1:8b}` | The app service |
| `coderunner:512` | `local model="${CODERUNNER_MODEL:-llama3.1:8b}"` | The launcher's own fourth copy, used to decide whether to pull |
| `README.md:42` | `\| CODERUNNER_MODEL \| llama3.1:8b \| Ollama chat model tag \|` | User-facing default |
| `README.md:70` | `│  model: llama3.1:8b   host: http://ollama:11434 …` | A transcript of the banner |
| `conftest.py:52` | `CHAT_MODEL = "llama3.1:8b"` | **A test fixture, not a product default** — §2.6 |
| `tests/test_memory_command.py:123` | `chat_model="llama3.1:8b"` | A hard-coded fixture value |
| `.moai/project/tech.md:17`, `:219`, `:387` | prose and a citation table | **All three cite `main.py:66`** — stale by five lines |

**The launcher's copy at `coderunner:512` is a fourth declaration of one fact and it is the one that
decides whether 4.9 GB gets downloaded.** There is no single source of truth for the model tag in
this repository; there are four defaults that happen to agree, plus two test fixtures, plus a
README table, plus a README transcript. **A swap that misses one of them produces a product that
pulls one model and talks to another**, and the failure mode is a launcher that downloads
gigabytes on every start because `have_model()` never matches.

### 2.2 What consumes `MODEL_NAME`, and what each consumer does with it

| Consumer | Line | Consequence of the swap |
|---|---|---|
| `client.chat(model=MODEL_NAME, …)` | `main.py:217` | The actual inference call. This is the swap |
| `MemoryConfig.from_env(MODEL_NAME)` | `main.py:108` | The tag is threaded into memory config (`memory.py:281-286`) and stored on **every record** |
| Banner subtitle | `main.py:753` | Prints the tag. Correct after the swap, by construction |
| Troubleshooting panel | `main.py:1191` | Prints `3. Pull the model:  ollama pull {MODEL_NAME}`. Correct after the swap |
| Banner **wordmark** | `main.py:750` | `banner.append("— agentic Python interpreter powered by LLaMA", style="dim")` — **a hard-coded string no environment variable reaches** |

**`main.py:750` is the one the swap breaks silently and visibly at the same time.** After the edit,
the product prints *"powered by LLaMA"* directly above a subtitle reading the Phi-3.5 tag, on every
launch, forever. Nothing raises. **It is a false claim rendered in the first panel the user sees,
and it is the single most quotable line this SPEC touches.** `main.py` carries the literal `LLaMA`
on **6** lines — `:11` (the file header), `:750` (the wordmark), and `:1054`, `:1073`, `:1119`,
`:1314`, which are four *status labels* the user reads on every turn: `🔄 [LLaMA] Analyzing
request…`, `💬 [LLaMA] No code produced…`, `💬 [LLaMA] Final response streaming…`, and
`❌ [LLaMA] API error:`. `README.md` carries it on **5** lines: `:5`, `:69`, `:77`, `:101`, `:116`.

**Whether the status labels should say the model's name, say "model", or say nothing is a product
decision this SPEC raises and does not settle** (§3.5). What it does settle is that eleven strings
saying `LLaMA` cannot survive a swap to Phi-3.5 unexamined.

### 2.3 The memory eligibility filter, and what it does not gate

Verified today:

```
vectorstore.py:599    @staticmethod
vectorstore.py:600    def _eligibility_filter(embed_model: str, dim: int) -> str:
vectorstore.py:601        return f"embed_model == {_quote(embed_model)} and dim == {int(dim)}"
```

Called at `vectorstore.py:579` (inside `search()`, `:549`) and `vectorstore.py:677`.

**`chat_model` is stored and gates nothing.** It is a field in `_RECORD_FIELDS`
(`vectorstore.py:129`), it is declared in the collection schema at `VARCHAR(256)`
(`vectorstore.py:289`), it is written on insert (`vectorstore.py:408`) and read back into the record
(`vectorstore.py:730`) — and it appears in **no** filter expression anywhere in that file. The
eligibility predicate is `embed_model` and `dim`, and nothing else.

**The consequence is exact and it survives the swap.** The embedding model
(`nomic-embed-text:latest`, `README.md:48`) is a separate variable, is **not** touched by this SPEC,
and keeps dim 768. So on the day the chat model changes, **every record llama3.1:8b ever authored
remains eligible**, and `format_recall_block()` (`memory.py:383-391`) will render it under the
heading `PRIOR SUCCESSFUL SOLUTION — reference only` (`memory.py:362`) with the line *"Its actual
output was:"*, and `inject_recall()` (`memory.py:394-408`) will splice it in as a system message
ahead of the user's request whenever cosine similarity clears `DEFAULT_MIN_SIMILARITY = 0.65`
(`memory.py:74`).

**So a Phi-3.5 turn will be shown llama3.1:8b's work, labelled as a successful solution, and asked
to adapt it — and nothing in the product, the store or the transcript says which model wrote it.**
Whether that is a feature or a defect is the subject of §3.4, and this SPEC does not assume it is
either.

### 2.4 The launcher's tag matching, which is exact and unforgiving

```
coderunner:476-479   # `ollama list` prints FULLY-QUALIFIED tags and `grep -qx` is a whole-line exact
                     # match, so any tag passed here must carry its `:latest` suffix where it has one.
coderunner:480-483   have_model() { docker exec coderunner-ollama ollama list 2>/dev/null
                                    | awk 'NR>1 {print $1}' | grep -qx "$1"; }
```

`have_model()` is called at `coderunner:513` for the chat model and `coderunner:522` for the
embedding model. `grep -qx` is a **whole-line** match, which is exactly why
`CODERUNNER_EMBED_MODEL` defaults to `nomic-embed-text:latest` **with** the suffix
(`coderunner:521`): a bare name never matches a fully-qualified one, `have_model()` returns false
forever, and `pull_model()` (`coderunner:488-494`) re-downloads on **every single launch**.

**The same trap is now armed for the chat model, and today it is disarmed only by an accident of
naming.** `llama3.1:8b` carries an explicit `:8b` suffix, so it matches whatever `ollama list`
prints. **Whether the chosen Phi-3.5 tag does is unknown until T1 runs `ollama list` and reads the
first column.** If the tag is written one way in `main.py:71` and printed another way by the server,
the product silently re-pulls the model on every start, and the only symptom is a slow launch. That
is T5, and it is not hypothetical: the comment at `coderunner:476-479` exists because the project
has already been bitten once, on the embedding model, and `SPEC-MEMORY-001` §3.2 records it.

**`--doctor` reports the embedding model's presence and does not report the chat model's.** Verified
at `coderunner:540-562`: the rows are os, docker binary, docker version, compose command, daemon
reachable, image present, ollama service, **`ollama models`** (a comma-joined dump of every tag the
server lists, `:551`), ollama volume, app volume, **`embed model … (present|MISSING)`** (`:556-558`,
and only when `CODERUNNER_MEMORY != 0`), and bootstrap log. **There is no chat-model presence row.**
A user whose chat model failed to pull sees its absence only by reading the raw `ollama models`
line and knowing what to look for. §3.5 proposes the row; T5 owns it.

### 2.5 Why the prompt is the risk, stated with the prompt's own structure

`SYSTEM_PROMPT` is `main.py:122-182`. Measured today: **61 source lines, 2575 characters** after
`textwrap.dedent().strip()`, sha256 `8a896634a9f6414dadd43f35e423e2be0681bd7d74f4d0de5682b703f044382d`,
containing exactly **2** backtick fences — one fenced block, which is the property
`tests/test_source_seam.py` asserts and which `SPEC-ILLUSTRATE-001` **N2** depends on.

| Part | Lines | What it asks the model to hold |
|---|---|---|
| The routing decision | `main.py:126-129` | Choose CODE or DIRECT from the *shape of the request*, before writing anything |
| CODE protocol | `main.py:131-167` | Restatement, a `Thought:` section, **exactly one** fenced block, ten sub-rules including three named URL patterns, a timeout, a User-Agent, no `input()`, and a stop instruction |
| The `@param` grammar | `main.py:158-166` | `# @param name: type = "prompt"` inside the same fence, four types, and *"Never emit a second fenced block for these"* |
| DIRECT protocol | `main.py:169-174` | Four rules, including *"If in doubt, prefer the CODE protocol"* |
| Post-execution behaviour | `main.py:176-180` | Two more contracts: narrate stdout under `Answer:`, and on failure diagnose then re-emit |

**That is five contracts in one string, and the largest model this project has measured already
fails one of them at a rate of 30 in 30.** `SPEC-ILLUSTRATE-001` §2.2 measured, 2026-08-10, against
`llama3.1:8b` Q4_K_M via the compose sidecar, on the prompt *"explain what a Python closure is, with
a short example"*: **CODE 30/30, DIRECT 0/30**, 95 % Wilson interval on the DIRECT rate
**[0.000, 0.114]**. The routing decision at `main.py:126-129` is not being made correctly by the
model that ships today.

**Phi-3.5-mini is a substantially smaller model.** This SPEC therefore records, before any run, that
**T2 may measure the illustration defect as worse under Phi-3.5** — and that the `@param` grammar,
which `SPEC-INPUT-001` R1 already flagged as *"routing through a 50-line system prompt competing for
an 8B model's attention"*, has **never been measured at any rate against any model** and may
degrade below usability without a single test failing. **A smaller model getting a long
multi-protocol contract wrong is the expected outcome, not the surprising one, and a SPEC that has
not written that down in advance will read its own measurement as a setback rather than as data.**

**One thing that is genuinely unknown in the other direction, and is named so it is not treated as
settled.** c4 is at 0/30 under llama3.1:8b. **A cell at zero cannot get worse** — that is
`SPEC-ILLUSTRATE-001` §4.2's arithmetic, computed with one-sided Fisher exact at N=30, and it holds
here unchanged. So on c4 specifically, T2 can only measure *the same* or *better*. **The four
remaining control cells are where a regression can be seen**, and their V0 rates under
`llama3.1:8b` were c1 30/30, c3 26/30, c2 20/30, c5 14/30 (re-derived by `SPEC-ILLUSTRATE-001`
§2.2/F1 from the committed records; **not re-derived by this SPEC**, and flagged as inherited).

### 2.6 What is *not* invalidated by the swap, checked rather than assumed

**The embedding model is a separate variable and this SPEC does not touch it.**
`CODERUNNER_EMBED_MODEL` defaults to `nomic-embed-text:latest` at `coderunner:521` and
`docker-compose.yml:87`, dim 768, and it is pulled by an **independent** `have_model()` check at
`coderunner:522` — deliberately not gated on the chat model's presence, for the reason recorded at
`coderunner:515-519` and in `tech.md:385-392`. Nothing in `_eligibility_filter()` changes. **Every
stored embedding remains valid, and no re-embedding is required by this SPEC.**

**`conftest.py:52`'s `CHAT_MODEL = "llama3.1:8b"` is a fixture and does not need to change.** It is
consumed by `tests/test_vectorstore.py:332` and `:749` and `tests/test_memory_recall_block.py:35` as
an arbitrary string that must round-trip through the store; `tests/test_memory_command.py:123`
hard-codes the same literal for the same reason. **These tests assert that a chat-model string
survives a write and a read, not that it is the product's default.** Changing them would be churn.
Leaving them is a small readability cost, recorded here so nobody "fixes" it as part of the swap and
then cannot explain the diff.

**No on-disk size figure for the chat model exists in this repository's documentation.** Checked:
`product.md:77-83`'s residue table records the image (273 MB → 754 MB) and the embedding model
(274 MB) and **says nothing about the chat model's weights**. The only figure that exists anywhere
is in `SPEC-PROMPT-001` `spec.md:713`, which recorded *"`llama3.1:8b`, ID `46e0c10c039e`, **4.9
GB**"* from `ollama list` on 2026-08-08. **So the swap invalidates no published size claim, and T1's
size reading has nothing to be compared against except that one line.** Recorded so that T1 does not
go hunting for a documentation defect that is not there.

### 2.7 The harness, and the one property that makes T2 possible

`probe/` is **not on this branch.** Verified: `git ls-files probe/` returns nothing; the only thing
present at that path is `probe/__pycache__/` holding **6 stale `.pyc` files** from a checkout of
another branch — the compiled remains of a harness whose source is absent. The source lives on
`feature/SPEC-PROMPT-001`, whose tip is `01aa887` and which is **published** (verified today:
`feature/SPEC-PROMPT-001` and `origin/feature/SPEC-PROMPT-001` are both
`01aa887cf33eab74b3b67955da584588701c9d16`).

| File | Lines |
|---|---|
| `probe/run_probe.py` | 339 |
| `probe/aggregate.py` | 211 |
| `probe/variants.py` | 184 |
| `probe/tasks.py` | 139 |
| `probe/classify.py` | 67 |
| `probe/__init__.py` | 22 |

Its records are 22 files under `.moai/specs/SPEC-PROMPT-001/probe-runs/` on that branch — 11 JSONL
cells and 11 progress logs. `tests/test_probe.py` exists only there.

**The property that decides T2's design: the harness reads the model from `main.py`, and reads the
truth back from the server.** `probe/run_probe.py:53` is `from main import MODEL_NAME, OLLAMA_HOST,
stream_llm`, and the argument parser (`run_probe.py:290-303`) offers `--variant`, `--task`, `--n`,
`--host` and `--resume-from` — **there is no `--model` flag.** `collect_provenance()`
(`run_probe.py:114-144`) then calls `client.list()` and `client.show(MODEL_NAME)` on the **running
server** and records `model_tag`, `model_digest`, `quantisation`, `model_format` and
`modelfile_parameters` onto every trial (`run_probe.py:210-216`).

**Two consequences, and both are load-bearing.**

**First, T2 can measure the swap before the swap is committed.** `main.py:71` reads
`CODERUNNER_MODEL` from the environment, compose passes it through (`docker-compose.yml:78`), and
the probe inherits it. So exporting the variable is sufficient to run the whole of T2 against
Phi-3.5 with the repository still on its old default. **The config edit does not have to precede the
measurement, and the measurement is worth more if it does not** — a run that fails can then be
abandoned without a revert.

**Second, the provenance cannot lie about which model produced a record.** `SPEC-PROMPT-001`
`spec.md:721-726` states the principle in its own words: *"compose declares an intention; only the
running server can report the fact."* This is why T1's figures come out of the probe's own
provenance block rather than out of a README.

**`probe/classify.py` imports `CODE_BLOCK_RE` and `extract_last_python_block` from `main`** and
`tests/test_probe.py` asserts by AST that it holds no copy of the fence regex. Porting `probe/` to
this branch must preserve that; a harness with its own copy of the predicate measures fiction
(`SPEC-PROMPT-001` R7).

---

## 3. Design decisions

### 3.1 D1 — The measurement is the deliverable; the edit is a rider on it

**Recommendation.** T2 is the unit of work. `main.py:71`, `docker-compose.yml:46` and `:78` are
edited **as part of** T2, after its run has produced numbers, not before it as a separate task.

The reason is that the alternative has a specific and familiar failure: the one-line edit lands, it
is obviously correct, it is merged, and the six-cell measurement becomes a follow-up that never
happens. **The repository would then be shipping a model against which no cell has ever been run,
while five documents assert rates measured against a different one.** That is worse than the status
quo, because the documents would be confidently wrong rather than merely out of date.

**The cost of D1, stated rather than hidden:** it makes a trivial change expensive. Someone who
wants Phi-3.5 today can have it with `CODERUNNER_MODEL=…` and no edit at all — the variable is
supported at `main.py:71`, `docker-compose.yml:78` and `coderunner:512`. **What this SPEC governs is
changing the *default*, which is a claim about what the product is, and a claim needs evidence.**

### 3.2 D2 — Six cells, and the sixth is the fifth

**Recommendation.** T2 measures **`SPEC-PROMPT-001`'s five control cells at N=30 each**, at V0.
`SPEC-ILLUSTRATE-001`'s c4 **is** one of those five — it is `c4_general_knowledge`,
`probe/tasks.py`'s *"explain what a Python closure is, with a short example"*, `n=30`,
`expect_direct=True`. **The two SPECs name the same cell and this SPEC runs it once**, reporting it
under both headings.

Saying "five cells plus c4" and running six would produce a spurious sixth column and, worse, two
rates for one prompt that a later reader would try to reconcile. **The five control cells at V0,
N=30, are the whole of T2's routing measurement**, and c4's row carries a note that it is also
`SPEC-ILLUSTRATE-001`'s measurement cell.

**Why V0 and not the variant `SPEC-PROMPT-001` may ship.** V0 is the prompt string in the tree at
`main.py:122-182` today. It is the only string this SPEC's numbers can be compared against, because
it is the string every prior control-cell number was taken against. **Measuring a new model against
a new prompt simultaneously would produce a number that is about neither.** §5.2 records the
ordering hazard that follows.

### 3.3 D3 — The three outcomes of T2, all admitted before the run

**Recommendation.** T2's verdict is recorded as exactly one of three, and all three are legitimate.

| | Outcome | What it means | What happens next |
|---|---|---|---|
| **P-a** | Phi-3.5 meets the pre-registered thresholds on all five control cells | The swap is defensible on measured evidence | T4 records both figures side by side; the edit merges |
| **P-b** | Phi-3.5 is materially better on the cells that had headroom | The swap is an improvement and can be described as one, **with the cells and counts that support it** | As P-a, plus the improvement is stated per-cell and never as a general claim about the model |
| **P-c** | **Phi-3.5 is materially worse — on routing, on the illustration defect, or on the `@param` grammar** | **The swap does not merge as specified.** The measurement is the deliverable and it delivered | Record it in `verification-T2.md` §5, leave the default at `llama3.1:8b`, and T4's documentation work is then a correction of nothing |

**P-c is the outcome this SPEC is most likely to reach and it is not a failure.** A smaller model
holding a five-part contract less reliably is the prior, not the surprise. **A SPEC that measures
its own preferred change out of contention has done the measurement correctly**, and this project
has a precedent for saying so plainly: `SPEC-PROMPT-001`'s V2 arm moved its target cell
significantly and still **missed** its pre-registered threshold and returned **M-b**.

**The corollary, which is where this rule earns its keep.** If T2 returns P-c, the temptation is to
soften the thresholds and call it P-a. That is why **the thresholds are pre-registered in
`verification-T2.md` §1 and committed on their own, before the run starts** (`acceptance.md`
**AC-MEASURE** item 1). A threshold chosen after the numbers arrive is not a gate; it is a
description.

### 3.4 D4 — The memory-eligibility question is a decision, and this SPEC declines to prejudge it

**§2.3 established the mechanism: `chat_model` is stored and gates nothing, so llama-authored
records stay eligible for injection into a Phi-3.5 turn.** Three options exist. **All three are
admitted in advance and each needs a test.** This SPEC does not recommend one, because the choice
turns on T2's numbers and on a value judgement about silent capability loss that is not this
document's to make.

| | Option | The cost it accepts |
|---|---|---|
| **M-a** | **Leave cross-model reuse as-is.** `_eligibility_filter()` is untouched | A Phi-3.5 turn is shown llama3.1:8b's script under `PRIOR SUCCESSFUL SOLUTION — reference only` with no indication of provenance. Whether an 8B model's Python is a good few-shot for a smaller one is **unmeasured and unmeasurable from inside the product** |
| **M-b** | **Add `chat_model` to the eligibility filter** (`vectorstore.py:601`) | **Every existing user's store goes dark on switch day.** Not partially — the filter is a conjunction, and no record in any existing store carries the new tag. `/memory` will report records that exist and never match. **This is a silent capability loss with no error, no warning and no migration**, and it is the option most likely to be chosen for looking principled |
| **M-c** | **Keep reuse, but name the authoring model inside the injected block** — one line in `_RECALL_TEMPLATE` (`memory.py:361-380`), rendered from `record.chat_model`, which is already read back at `vectorstore.py:730` | The prompt gets longer, on a smaller model, in a turn that is already carrying a 2575-character system prompt plus the recall block. **§2.5's whole argument applies to this addition too** |

**The one thing this SPEC does assert about the choice.** **M-b's blast radius is larger than it
looks and must not be adopted casually.** It is the option that reads as correct — *records from a
different model are not comparable* — and its actual effect on switch day is that solution memory,
the subject of an entire prior SPEC, stops returning anything for every existing install, with the
only symptom being that recall never fires. `product.md` §4 item 20's one-line degradation
convention exists for exactly this class of event and **M-b as specified emits no line at all**,
because from the store's point of view nothing has gone wrong.

**Whichever option is chosen, T3 owns a test for it**, and the tests differ: M-a needs a test that
records with a foreign `chat_model` are still returned; M-b needs a test that they are not, plus
whatever user-visible line the project decides that loss deserves; M-c needs a test that the
rendered block names the authoring model and that a record written under the current model is not
mislabelled.

### 3.5 D5 — The launcher gets a chat-model row, and the wordmark is a product question

**Recommendation, split, because the two halves have very different weights.**

**The mechanical half is T5 and it is not optional.** `have_model()` (`coderunner:480-483`) matches
with `grep -qx`; T1 must record the tag **exactly as `ollama list` prints it in column 1**; and
`main.py:71`, `docker-compose.yml:46`, `:78` and `coderunner:512` must all carry that same string.
`--doctor` gains a chat-model presence row beside the embedding one (`coderunner:556-558` is the
shape to copy), because a diagnostic that reports the presence of the secondary model and not the
primary one is a diagnostic with a hole in it.

**The branding half is raised and not settled.** `main.py:750` says *"powered by LLaMA"* and four
status labels say `[LLaMA]`. After the swap all five are false. Three answers are available — name
the model dynamically from `MODEL_NAME`, use a neutral label such as `[Model]`, or hard-code the new
name — and **they differ in how much they cost the next swap**. This SPEC records that a decision is
required and that leaving it undecided ships a product whose first panel misstates what it runs on.
**It does not choose, because "what the status labels say" is a product-voice question and this
document has no evidence to bring to it.**

### 3.6 D6 — `probe/` is ported, not forked

**Recommendation.** T2 requires `probe/` on this branch. It is brought over from
`feature/SPEC-PROMPT-001` (`01aa887`) **unmodified**, and the rule from `SPEC-ILLUSTRATE-001` **D6**
is adopted verbatim: **additive only. No existing `Task` — its `id`, its `text`, its `kind`, its
`n` or its `expect_direct` — may change.** `probe/tasks.py`'s own banner requires byte-identical
task text across arms *"or the columns of that table are not comparable, which is the quiet way a
before/after measurement stops being one"*.

**This SPEC adds no cell.** It changes the model and holds everything else fixed, which is the only
way its numbers mean anything. **`SPEC-ILLUSTRATE-001` T1's compute-only cell is that SPEC's to
add**, and if it lands first, T2 inherits it and reports it as a sixth column labelled with where it
came from.

**T2's records go to `.moai/specs/SPEC-MODEL-001/probe-runs/`** and never to `SPEC-PROMPT-001`'s
directory. Two SPECs' evidence in one directory is one SPEC's evidence by the time anybody reads it.

---

## 4. EARS requirements

All five requirement types are represented.

### 4.1 Ubiquitous — always true

| # | Requirement |
|---|---|
| **U1** | The product **shall always** name one model tag, and every site that declares it **shall** declare the same string. Four declarations exist today (`main.py:71`, `docker-compose.yml:46`, `:78`, `coderunner:512`) and a swap that updates three of them produces a product that pulls one model and talks to another. |
| **U2** | Every figure this SPEC records about Phi-3.5 — tag, parameter count, quantisation, context window, on-disk size, and every rate — **shall always** be a figure a run produced, quoted with the command, the date and the trial count that produced it. **What was not run shall be named as not run, not as not needed.** Adopted from `SPEC-PROMPT-001` U6 and `SPEC-ILLUSTRATE-001` U5. |
| **U3** | Any measurement in this SPEC **shall always** carry the model tag, digest and quantisation read back from the **running server** (`probe/run_probe.py:114-144`), never from `docker-compose.yml`, `main.py:71` or any document. Compose declares an intention; only the server reports a fact. |
| **U4** | Documentation **shall always** present a Phi-3.5 rate **beside** the `llama3.1:8b` rate it supersedes, with both dates and both model tags. **A superseded measurement is still a measurement**, and a document that silently replaces one number with another destroys the only evidence that the swap changed anything. |
| **U5** | This SPEC **shall always** treat `SYSTEM_PROMPT` (`main.py:122-182`) as read-only. Changing the model and the prompt together produces a measurement about neither, and the string is `SPEC-PROMPT-001`'s contested surface with a measurement in flight against it. |
| **U6** | Any claim that Phi-3.5 is better or worse **shall always** be stated per-cell, with N, and **shall not** be generalised into a claim about the model. Five control prompts at N=30 measure five prompts. |

### 4.2 Event-driven — WHEN … THEN …

| # | Requirement |
|---|---|
| **E1** | **WHEN** the Phi-3.5 tag is established (T1), **THEN** it **shall** be recorded exactly as column 1 of `ollama list` prints it, and that byte string — not an abbreviation of it — **shall** be what `main.py:71`, `docker-compose.yml:46`, `docker-compose.yml:78` and `coderunner:512` carry. `have_model()` (`coderunner:480-483`) matches with `grep -qx`, which is a whole-line match. |
| **E2** | **WHEN** T2's run begins, **THEN** the pre-registered acceptance thresholds **shall** already exist in `verification-T2.md` §1 in a commit that contains **no results**. A threshold written after the numbers arrive is a description of them. |
| **E3** | **WHEN** a control cell is measured under Phi-3.5, **THEN** its record **shall** state the prompt string it was measured against — V0's, identified by the sha256 of `SYSTEM_PROMPT` at run time — so that a later comparison cannot silently span two prompts. |
| **E4** | **WHEN** T2 reports a rate, **THEN** it **shall** report the `llama3.1:8b` rate for the same cell alongside it, at the same N, with the date each was taken. |
| **E5** | **WHEN** the memory-eligibility decision (T3) is taken, **THEN** the chosen option **shall** ship with a test that fails if the behaviour reverts, and the decision **shall** be recorded with the option letter (M-a, M-b or M-c) and the reason. |
| **E6** | **WHEN** option **M-b** is chosen, **THEN** the turn on which an existing store becomes ineligible **shall** emit exactly one status line saying so, in the shape of `product.md` §4 item 20's one-line degradation convention. A capability that disappears without a line is a capability that disappeared silently. |
| **E7** | **WHEN** the default model changes, **THEN** `README.md:42`, `README.md:70`, `.moai/project/product.md` §5.5, `.moai/project/tech.md:17` and `:219`, and `SPEC-ILLUSTRATE-001` §2.2 **shall** be amended in the same change, and the stale citations named at §5.4 **shall** be repointed in the same pass. |
| **E8** | **WHEN** `probe/` is ported to this branch, **THEN** `probe/classify.py` **shall** still import `CODE_BLOCK_RE` and `extract_last_python_block` from `main`, and `tests/test_probe.py`'s AST assertion **shall** still hold. A harness carrying its own copy of the product's predicate measures fiction. |
| **E9** | **WHEN** `--doctor` runs, **THEN** it **shall** report the chat model's tag and its presence, in the shape of the embedding-model row at `coderunner:556-558`. |

### 4.3 State-driven — IF/WHILE … THEN …

| # | Requirement |
|---|---|
| **S1** | **IF** T1 has not established the tag empirically from `ollama pull` and `ollama list`, **THEN** no document, comment or config file in this SPEC **shall** name a Phi-3.5 tag, parameter count, quantisation, context window or size. There is no such figure today and inventing one is the failure mode U2 exists for. |
| **S2** | **IF** T2 returns outcome **P-c** (§3.3), **THEN** the default **shall** remain `llama3.1:8b`, the result **shall** be recorded in full, and T4's documentation work **shall not** describe a swap that did not happen. |
| **S3** | **IF** a T2 cell is measured against a model, quantisation or host other than the one recorded in that run's provenance block, **THEN** the result **shall** be labelled with what it was measured against and **shall not** discharge any criterion. Adopted from `SPEC-PROMPT-001` **S4**. |
| **S4** | **IF** `SPEC-PROMPT-001` has not merged its prompt change, **THEN** T2's verdict **shall** state the `SYSTEM_PROMPT` sha256 it was taken against and **shall** be recorded as provisional with respect to that SPEC. A verdict taken against a string about to be replaced is a verdict about the past. |
| **S5** | **WHILE** `verification-T2.md` contains no results, this SPEC **shall** remain `draft`, the file **shall** state in its first line that it has not been run, and T4 **shall not** write a Phi-3.5 rate into any document. |
| **S6** | **IF** the Phi-3.5 tag as printed by `ollama list` differs by one byte from the tag configured, **THEN** the launcher re-pulls the model on every launch and the only symptom is a slow start. T5 **shall** verify the match by observation — a successful second launch that pulls nothing — and not by inspection. |
| **S7** | **WHILE** both this branch and `feature/SPEC-ILLUSTRATE-001` are unmerged, T4's edit targets **shall** be resolved against whichever branch merges first (§5.1) and **shall not** be taken from line numbers recorded in either document without re-reading the file. |

### 4.4 Unwanted — shall not

| # | Requirement |
|---|---|
| **N1** | `SYSTEM_PROMPT` **shall not** be modified by this SPEC — not one character of `main.py:122-182`, whose sha256 is `8a896634a9f6…` as measured today. Changing the model and the prompt in one change produces a measurement about neither. |
| **N2** | No document **shall** replace an `llama3.1:8b` figure with a Phi-3.5 figure. Both stand, both dated, both labelled with their model (U4). |
| **N3** | The embedding model **shall not** be changed, re-pulled, or re-embedded by this SPEC. `CODERUNNER_EMBED_MODEL` is a separate variable (`coderunner:521`, `docker-compose.yml:87`), dim 768 is unchanged, and `_eligibility_filter()`'s `embed_model` and `dim` clauses are untouched by every option in §3.4. |
| **N4** | Option **M-b** **shall not** be adopted without recording, in the same change, that every existing store becomes empty of eligible records on switch day, and without the status line **E6** requires. It is a silent capability loss and it **shall not** ship silently. |
| **N5** | No existing `Task` in `probe/tasks.py` **shall** be renamed, re-worded, re-sized or removed, and no record file under `SPEC-PROMPT-001`'s `probe-runs/` **shall** be modified, rewritten or re-scored. That SPEC's evidence is not this SPEC's to edit. |
| **N6** | `verification-T2.md` **shall not** contain placeholder figures, illustrative numbers or example tables populated with plausible values. Empty cells, explicitly marked not-yet-run. Adopted verbatim from `SPEC-ILLUSTRATE-001` N6. |
| **N7** | This SPEC **shall not** claim that Phi-3.5 fixes, mitigates or improves the `SPEC-ILLUSTRATE-001` illustration defect unless T2 measured a change in c4's rate, at N=30, and reported it with its confidence interval. **c4 is at 0/30 and a cell at zero cannot get worse**, so any movement is upward and must be quantified rather than asserted. |
| **N8** | The swap **shall not** be merged with `main.py:750`'s *"powered by LLaMA"* wordmark and the four `[LLaMA]` status labels (`main.py:1054`, `:1073`, `:1119`, `:1314`) left unexamined. Whether they change is D5's open question; that they are looked at is not optional. |
| **N9** | No figure from this SPEC **shall** be recorded as discharging any `SPEC-PROMPT-001` criterion. That SPEC's **S4** (`spec.md:893`) forbids it explicitly, and §5.2 records what follows. |
| **N10** | `conftest.py:52`'s `CHAT_MODEL` fixture and `tests/test_memory_command.py:123`'s literal **shall not** be changed as part of the swap. They assert that an arbitrary chat-model string round-trips through the store, not that it is the product's default (§2.6). |

### 4.5 Optional — where possible

| # | Requirement |
|---|---|
| **O1** | **Where possible**, T2 **should** record `elapsed_sec` distributions per cell alongside the rates. The field already exists (`probe/run_probe.py:196`, written at `:208`), it costs nothing, and a smaller model's latency is one of the few things a swap is expected to improve — **which makes it the one improvement this project could actually demonstrate.** |
| **O2** | **Where possible**, T1 **should** record `modelfile_parameters` and `model_format` from the provenance readback (`probe/run_probe.py:141-144`), not merely the tag and quantisation, so that a later reader can tell whether a temperature or context setting differed. |
| **O3** | **Where possible**, `--doctor` **should** report the chat model's on-disk size as `ollama list` gives it, since the row already shells out to that command (`coderunner:551`) and the figure is the one users ask for before a first launch. |
| **O4** | **Where possible**, the four `[LLaMA]` status labels **should** be derived from a single constant rather than repeated as four literals, so that the next model swap is one edit rather than four. Recorded as optional because it is a refactor with no measurable behaviour, and D5's product question comes first. |
| **O5** | **Where** option **M-c** is chosen, the authoring model **should** be rendered from `record.chat_model`, which is already read back at `vectorstore.py:730` and requires no schema change (`vectorstore.py:289` already declares the field at `VARCHAR(256)`). |

---

## 5. Hazards this SPEC inherits rather than creates

### 5.1 The merge-order hazard — T4's edit targets depend on which branch lands first

**This branch is cut from `main`, and `main` does not carry `SPEC-ILLUSTRATE-001`'s documentation
corrections.** Verified today: `git log --oneline main..feature/SPEC-ILLUSTRATE-001` returns **9
unmerged commits**, six of which are documentation corrections to the exact files T4 must amend —
`394cca7`, `afba32e`, `ceb5898`, `209d3fb`, `b78ce02`, `7f3e1b3`.

**The consequence is that T4's targets differ, by file, by section and by line, depending on merge
order.** Measured on both branches today:

| Target | On `main` (this branch) | On `feature/SPEC-ILLUSTRATE-001` |
|---|---|---|
| `README.md` length | 228 lines | 330 lines |
| `CODERUNNER_MODEL` table row | `README.md:42` | `README.md:48` |
| Banner transcript | `README.md:69-70` | `README.md:82-83` |
| The measured 0/30 narrative | **does not exist** | `README.md:124`, with a full transcript at `:129-162` citing `llama3.1:8b` twice |
| `product.md` §5.5 | `:212-217`, titled *"Conversational / explanatory questions"*, asserting DIRECT fires | `:212`, retitled *"— the DIRECT protocol does not fire"*, carrying **CODE 30/30, DIRECT 0/30** and the model tag |
| `product.md` §6.15 | **does not exist** — the file ends its limitations at §6.14 (`:423`) | `:473`, *"Illustrative code is executed, narrated and stored as a solution"* |

**On this branch, `product.md` §5.5 states behaviour measured false and there is no §6.15 to amend.
On the other branch, both carry `llama3.1:8b` figures that T4 must place a Phi-3.5 figure beside.**
These are not the same job. **T4 must re-read its target files at the moment it runs**, which is
**S7**, and must not take line numbers from this table — including from this table — without
re-reading. The table is a description of a hazard, not a work order.

**The recommendation, offered and not imposed: let `feature/SPEC-ILLUSTRATE-001` merge first.** Its
six commits are corrections of claims that are already false, they are blocked on nothing, and
merging them first means T4 amends one set of accurate sentences rather than correcting a false one
and adding a figure to it in the same edit. **If this branch merges first, T4 owes the ILLUSTRATE
branch a rebase conflict in five files, and the conflict will be in prose.**

### 5.2 `SPEC-PROMPT-001`'s S4 disqualifies every post-swap run from its gate

Quoted in full at the HISTORY block. The mechanism is simple and there is no way around it: **that
SPEC's gate is defined over `llama3.1:8b`, and this SPEC changes what the default is.** After the
swap, anyone running `probe/` without setting `CODERUNNER_MODEL` back is measuring Phi-3.5 and, by
**S4**, producing a result that *"shall not be recorded as satisfying the gate."*

`SPEC-PROMPT-001` still owes V3 at the tool-reachable cell (N=20) and the full control set
(5 × N=30) before its prompt text merges. **Those runs are cheaper before this SPEC merges than
after**, because after, they require an explicit environment override that someone must remember and
that nothing enforces.

**This SPEC states the finding and declines to fix it.** The remedy is an amendment to
`SPEC-PROMPT-001` — either it re-scopes **S4** to the model recorded in each run's provenance, or it
completes its outstanding runs first. **Both are that SPEC's author's call, in that SPEC's HISTORY,
with whatever re-run it implies.** Flag it the day T2 is scheduled, not the day it reports.

### 5.3 What is not known

Named as not known, and not as not needed.

1. **Everything about Phi-3.5.** Tag, parameters, quantisation, context window, on-disk size,
   licence, and every behavioural rate. **Unverified, because the Docker daemon is down and there is
   no host `ollama` binary.** T1 exists for the first five; T2 for the rates.

2. **Whether the `@param` grammar (`main.py:158-166`) survives the swap. Unmeasured — and it was
   never measured under `llama3.1:8b` either.** `SPEC-INPUT-001` R1 named this as the highest-
   probability failure with no unit test able to detect it, and T9 of that SPEC's manual check is
   the only instrument that has ever existed for it. **No probe cell in any arm asks for a
   parameterised turn.** A smaller model may stop emitting the declaration syntax entirely, and the
   observable would be a script that hard-codes a placeholder and runs — which looks like success.

3. **Whether an `llama3.1:8b`-authored record is a useful few-shot for Phi-3.5.** §3.4's whole
   question. **It cannot be measured from inside the product**, which has no telemetry and will not
   be given any, and no probe cell exercises the recall path at all.

4. **Latency.** The probe's `elapsed_sec` (`probe/run_probe.py:196`, `:208`) covers **one** round
   trip; a successful CODE turn costs at least two (`main.py:1113-1127` is the second). **No token
   count exists in any probe record or anywhere in `main.py`** — checked: no `eval_count`,
   `prompt_eval` or `total_duration` field is read from the Ollama response. So "a smaller model
   will be faster" is a reasonable expectation and **not** a thing this project can currently
   demonstrate end-to-end.

5. **Whether Phi-3.5's replies are *correct*.** Nobody in this project has assessed correctness on
   any trial of any model. `SPEC-PROMPT-001` v1.1.2 records 65 unassessed CODE trials and defers the
   question. T2 measures **routing**, which is a different and much cheaper thing, and **shall not**
   be reported as if it were quality.

6. **`SPEC-ILLUSTRATE-001`'s prompt hash.** Disclosed in HISTORY: its 2910-character / `ec8ef366856f…`
   figure is not reproducible at this tree under three conventions, and this SPEC uses its own
   measurement. **Which of the two is right is unresolved**, and it matters because that SPEC's N1
   pins the prompt by that hash.

### 5.4 Stale citations found while writing this, recorded so they need no re-derivation

Each was verified against the file in the working tree at `ab08333` today.

| Cites | Correct | Where |
|---|---|---|
| `main.py:66` for `MODEL_NAME` | `main.py:71` | `.moai/project/tech.md:17`, `:219` |
| `coderunner:206` for the launcher's model default | `coderunner:512` | `.moai/project/tech.md:17`, `:219` |
| `docker-compose.yml:71` (and `:39`) for the model env | `docker-compose.yml:78` (and `:46`) | `.moai/project/tech.md:17`, `:219` |
| `coderunner:174-177` for `have_model()` | `coderunner:480-483` | `.moai/project/tech.md:224`, `:390-391`; `docker-compose.yml:81` cites `coderunner:176` |
| `coderunner:209-213` for the independent-pull comment | `coderunner:515-519` | `.moai/project/tech.md:390` |
| `docker-compose.yml:80` for the embed model | `docker-compose.yml:87` | `.moai/project/tech.md:19` |
| `main.py:52` for `MODEL_NAME` | `main.py:71` | `memory.py:268` (docstring) |
| `main.py:138-143` for the DIRECT protocol | `main.py:169-174` | `.moai/project/product.md:214` |
| `main.py:480-482` for the no-code branch | `main.py:1071-1074` | `.moai/project/product.md:216` |
| `main.py:1032` for the same branch | `main.py:1072` | `probe/classify.py` docstring, on `feature/SPEC-PROMPT-001` |

**T4 owns the first seven, because they are citations to the string this SPEC changes and leaving
them stale would make the swap unauditable.** The rest are recorded so the next reader does not
trust them.

---

## 6. In scope

1. **`verification-T2.md`** — structure and pre-registered thresholds committed first, figures only
   from runs (U2, N6, E2).
2. **T1's empirical establishment of the Phi-3.5 tag** via `ollama pull` and `ollama list`,
   recording tag, parameters, quantisation, context window and on-disk size (S1, E1).
3. **T2's five-cell measurement** — `SPEC-PROMPT-001`'s five control cells at V0, N=30, of which c4
   is also `SPEC-ILLUSTRATE-001`'s cell — plus the port of `probe/` to this branch, unmodified
   (D2, D6, E8).
4. **The config edit**: `main.py:71`, `docker-compose.yml:46`, `docker-compose.yml:78`,
   `coderunner:512` — one string, four sites (U1).
5. **The memory-eligibility decision** (M-a, M-b or M-c) with its test (E5, N4).
6. **Documentation**: `README.md`, `.moai/project/product.md` §5.5 and (where it exists) §6.15,
   `.moai/project/tech.md`, and `SPEC-ILLUSTRATE-001` §2.2 — each with the Phi-3.5 figure **beside**
   the `llama3.1:8b` one (U4, N2, E7), plus the citation repointing at §5.4.
7. **Launcher and compose**: the pull path, `have_model()` tag matching, and a `--doctor` chat-model
   row (E9, S6).
8. **The CI floor** — `MIN_PASSED` (`.github/workflows/ci.yml:332`, currently **573**) raised to a
   count **measured** from a real `junitxml` run if T3's test adds tests, never computed from an
   expected delta (`SPEC-CI-001` N5).

## 7. Out of scope

1. **Any change to `SYSTEM_PROMPT`** (N1, U5). `SPEC-PROMPT-001` owns that string and has a
   measurement in flight against it.
2. **Any change to the embedding model** (N3). Separate variable, separate pull path, unaffected
   dimension.
3. **Fixing the `SPEC-ILLUSTRATE-001` illustration defect.** That SPEC owns it. This SPEC measures
   c4 under a new model and records what it finds (N7).
4. **Repairing `SPEC-PROMPT-001`'s S4 collision.** §5.2 states it; the amendment is that SPEC's.
5. **Adding a probe cell of any kind**, including the `@param` cell §5.3 item 2 says is missing.
   This SPEC holds the instrument fixed and changes exactly one variable.
6. **Assessing correctness of generated code** under either model (§5.3 item 5).
7. **A model-selection UI, a model registry, or multi-model support.** One default, one string.
8. **Rewriting `structure.md`.** It is several SPECs behind and this SPEC does not change what it
   describes.

---

## 8. Traceability

| Artefact | Location |
|---|---|
| Requirements | this file, §4 (U1–U6, E1–E9, S1–S7, N1–N10, O1–O5) |
| Design decisions with costs | this file, §3 (D1–D6) |
| The three T2 outcomes, admitted in advance | this file, §3.3 (P-a, P-b, P-c) |
| The three memory options, admitted in advance | this file, §3.4 (M-a, M-b, M-c) |
| Hazards inherited | this file, §5 |
| Task decomposition, critical path, risks, successor | `.moai/specs/SPEC-MODEL-001/plan.md` |
| Acceptance criteria and the pre-registered gate | `.moai/specs/SPEC-MODEL-001/acceptance.md` |
| The measurement record | `.moai/specs/SPEC-MODEL-001/verification-T2.md` — **NOT YET CREATED, NOT YET RUN** |
| T2's records, when they exist | `.moai/specs/SPEC-MODEL-001/probe-runs/` — never `SPEC-PROMPT-001`'s directory |
| The model default, four sites | `main.py:71`, `docker-compose.yml:46`, `docker-compose.yml:78`, `coderunner:512` |
| What consumes it | `main.py:108`, `:217`, `:753`, `:1191` |
| The wordmark and the four status labels | `main.py:750`; `main.py:1054`, `:1073`, `:1119`, `:1314` |
| The prompt this SPEC must not touch | `main.py:122-182` — 61 lines, 2575 chars, sha256 `8a896634a9f6…`, measured 2026-08-19 |
| The eligibility filter | `vectorstore.py:599-601`, called `:579` and `:677` |
| `chat_model`, stored and ungating | `vectorstore.py:129`, `:289`, `:408`, `:730`; `memory.py:274`, `:281-286` |
| The recall path this SPEC's §3.4 governs | `memory.py:361-380` (template), `:362` (heading), `:383-391`, `:394-408`, threshold `:74` |
| The launcher's tag matching | `coderunner:476-479` (comment), `:480-483` (`have_model`), `:487-493` (`pull_model`), `:512-513`, `:521-522` |
| `--doctor`, and the row it lacks | `coderunner:540-562`; `:551` (`ollama models`), `:556-558` (embed row) |
| The harness | `feature/SPEC-PROMPT-001` (tip `01aa887`, published): `probe/run_probe.py` (339), `aggregate.py` (211), `variants.py` (184), `tasks.py` (139), `classify.py` (67), `__init__.py` (22); `tests/test_probe.py` |
| The model readback that makes U3 enforceable | `probe/run_probe.py:53`, `:114-144`, `:210-216` |
| The records this SPEC's baseline comes from | `feature/SPEC-PROMPT-001`: `.moai/specs/SPEC-PROMPT-001/probe-runs/` — 11 JSONL cells, 11 progress logs |
| The `llama3.1:8b` baseline for c4 | `SPEC-ILLUSTRATE-001` §2.2: CODE 30/30, DIRECT 0/30, Wilson [0.000, 0.114], 2026-08-10 |
| The S4 collision | `feature/SPEC-PROMPT-001`: `.moai/specs/SPEC-PROMPT-001/spec.md:893`; the 4.9 GB / `46e0c10c039e` reading at `:713` |
| Test fixtures deliberately unchanged | `conftest.py:52`; `tests/test_memory_command.py:123`; consumers `tests/test_vectorstore.py:332`, `:749`, `tests/test_memory_recall_block.py:35` |
| Coverage gates a T3 change lands in | `pytest.ini:57-62`; `conftest.py:205-212` (`vectorstore.py` floored 85.0, `memory.py` 100.0) |
| CI floor | `.github/workflows/ci.yml:332` (`MIN_PASSED = 573`) |
| The unmerged branch T4 collides with | `feature/SPEC-ILLUSTRATE-001` — 9 commits ahead of `main`; the six documentation ones are `394cca7`, `afba32e`, `ceb5898`, `209d3fb`, `b78ce02`, `7f3e1b3` |
| Project context | `.moai/project/product.md`, `.moai/project/structure.md`, `.moai/project/tech.md` — **citations stale, §5.4** |

| Requirement group | Primary acceptance criterion |
|---|---|
| U2, U3, S1, E1, O2 | **AC-TAG** |
| U2, U3, U6, E2, E3, E4, S3, S4, N5, N6, N7 | **AC-MEASURE** |
| E5, E6, N3, N4, O5 | **AC-MEMORY** |
| U1, U4, N2, E7, S7, §5.4 | **AC-DOCS** |
| U1, E1, E9, S6, N8, O3, O4 | **AC-LAUNCHER** |
| N1, U5 | **AC-PROMPT-UNTOUCHED** |
