---
id: SPEC-INPUT-001
version: "1.0.0"
status: "draft"
created: "2026-08-07"
updated: "2026-08-07"
author: "Chun Kang"
priority: "MEDIUM"
---

## HISTORY

### v1.0.0 (2026-08-07) — Initial specification

Written against a prohibition rather than a gap. `main.py:136` tells the model *"No `input()`, no
infinite loops. Deterministic and self-contained."* That line is usually read as a style
preference. It is not: it is load-bearing, and the measurements in §2 are what turn that from an
assertion into a fact. The feature specified here therefore does **not** relax the prohibition —
it adds the thing the prohibition leaves the model with nothing to do about.

Four measurements shaped the design, and two of them chose it outright.

- **M1 — `input()` in generated code fails on the host and would hang in the container.**
  *(Measured 2026-08-06 on this machine, by driving `run_python()`'s exact `subprocess.run`
  argument list against a script whose only statement is `input()`.)* Result on the host:
  `returncode 1`, stdout `'hi: '`, stderr `EOFError: EOF when reading a line`. The reason is one
  omission at `main.py:461-468`: `stdin` is **never passed**, so the child inherits the parent's.
  On the host under pytest that parent's stdin is closed or a pipe, hence `EOFError`. Inside the
  container it is the REPL's own TTY (`docker-compose.yml:67-68` set `stdin_open: true` and
  `tty: true`), so the child would **block on the user's terminal and eat their keystrokes** until
  `EXEC_TIMEOUT_SEC` expired — a 30-second freeze in which every character the user types is
  consumed by a script they cannot see. The prohibition at `main.py:136` is the thing standing
  between the product and that behaviour. **It stays.**

- **M2 — a separate `params` fence silently converts a CODE turn into a DIRECT turn.**
  *(Measured 2026-08-06 against the real `CODE_BLOCK_RE` at `main.py:414`.)* This retired the
  most obvious of the three syntax candidates. Given a response containing a ```` ```params ````
  block followed by a ```` ```python ```` block, `CODE_BLOCK_RE.findall()` returns **`['']`** —
  a single empty match, because the closing fence of the `params` block and the opening fence of
  the `python` block form a matching pair the regex accepts. `extract_last_python_block()`
  (`main.py:417-419`) therefore returns `''`, `if not code:` at `main.py:826` is **true for the
  empty string**, and the turn takes the "No code produced — returning direct answer" branch at
  `main.py:827-828`. The script is never executed and nothing anywhere reports an error. Reverse
  the block order and it works. **A syntax whose correctness depends on the ordering choices of an
  8B model is not a syntax.** Full result table at §3.1.

- **M3 — naive interpolation of a user-typed value is remote code execution against our own
  sandbox, and it is one line of code away.** *(Measured 2026-08-06.)* With
  `city = "Seoul"; import os; os.system("id"); x="`, a prelude built as `f'city = "{value}"'`
  executed `id` and printed **`uid=501(kurapa) gid=20(staff) …`** to stdout. The same value
  emitted through `repr()` arrived as a **39-character string** and did nothing. A value containing
  a newline does not even need a quote: `f'v = "{value}"'` where the value is `a\nimport os\n…`
  produces four statements out of one assignment. This is why §3.2 is a **HARD** requirement and
  why AC-INJ exists.

- **M4 — a prelude cannot be prepended blindly.** *(Measured 2026-08-06.)* A file whose first
  statement is an assignment and whose second is `from __future__ import annotations` fails with
  `SyntaxError: from __future__ imports must occur at the beginning of the file`. `SCRIPT_HEADER`
  (`main.py:422-431`) is comments only, so this hazard does not exist today and is **created** by
  this SPEC. Recorded as R4 in `plan.md` with a mitigation, not waved away.

One structural property was found rather than designed, and it is the single most important
sentence in this document: **`code` as captured into solution memory is the *extracted block*, not
the executed script.** `agentic_turn()` extracts at `main.py:825`, executes at `main.py:831`, and
captures at `main.py:860-869` — passing the same `code` object it extracted. If the prelude is
assembled inside `run_python()` and never merged back, an injected value is **structurally absent**
from the store, not merely filtered out of it. That property is free today and is destroyed by the
first refactor that "simplifies" the prelude into `code` before extraction. §4.4 N4 and AC-CAP
exist to nail it down.

---

# SPEC-INPUT-001 — Declared parameters for generated scripts

**Title:** Runtime values supplied by the user, declared by the model and injected as a
literal-safe prelude, with a user-chosen policy for what solution memory retains

## 1. Scope statement

Give the model a sanctioned way to obtain a value only the user has — a city, an API key, a file
path — without `input()`, without touching the child's stdin, and without any user-typed text ever
becoming executable source.

The model **declares** what it needs, inside the Python fence it already emits. CodeRunner prompts
the user for each declared value, once per turn. The values are emitted as Python literals into a
prelude prepended to the script at execution time. The generated code refers to them as ordinary
module-level names, which is what it would have done with `input()` and is the entire point:
nothing about the shape of the code the model writes has to change except that the value is
already there.

This SPEC also settles a question it cannot avoid raising: successful turns are captured into a
persistent, plaintext, generated-code-readable store (`tech.md` §7.2, `product.md` §6.11). A
feature that puts secrets into a turn therefore owes an answer about capture. That answer is a
**user-chosen, persisted setting**, and persisting it reverses a documented property of this
project (§5).

Nothing here weakens the sandbox. `main.py:136` keeps forbidding `input()`; §4.4 N1 restates it.

## 2. Verified environment

### 2.1 What `run_python()` does with stdin today (measured 2026-08-06)

`main.py:461-468`:

```
proc = subprocess.run(
    [sys.executable, "-I", script_path],
    capture_output=True, text=True, timeout=timeout, check=False, cwd=workdir,
)
```

`capture_output=True` sets `stdout` and `stderr` to pipes. It does **not** touch `stdin`. There is
no `stdin=` argument anywhere in the call, so the child inherits the parent's descriptor 0.

| Environment | Parent's fd 0 | `input()` in generated code |
|---|---|---|
| Host / pytest (**measured**) | closed or a pipe | `EOFError: EOF when reading a line`, rc **1**, stdout `'hi: '` |
| Container under `./coderunner` (**reasoned, not measured**) | the REPL's TTY (`docker-compose.yml:67-68`) | **blocks**, consuming the user's keystrokes, until `CODERUNNER_TIMEOUT` (default 30 s, `main.py:68`) |

The second row is marked as reasoning because it has not been driven end to end in a container.
It follows from descriptor inheritance and from compose allocating a TTY, and it is the worse of
the two outcomes: the host failure is loud and immediate, the container failure is a silent
30-second hijack of the user's terminal. **Neither is acceptable, which is why the prohibition is
not being relaxed.**

`-I` (isolated mode) is orthogonal here. It ignores `PYTHON*` environment variables and disables
the user site directory; it does not close stdin and does not filter non-`PYTHON*` environment
variables. That last point matters at §3.7.

### 2.2 Repository facts this SPEC stands on

| Fact | Evidence |
|---|---|
| The prohibition being amended | `main.py:136` |
| Code fence extraction | `CODE_BLOCK_RE` at `main.py:414`; `extract_last_python_block()` at `main.py:417-419` |
| Empty-string early return | `main.py:825-828` — `if not code:` is true for `''` |
| Script assembly | `main.py:447-448`, `SCRIPT_HEADER` at `main.py:422-431` |
| Retry loop | `main.py:792`, bound by `MAX_RETRIES` (`main.py:69`, default 3) |
| Retrieval-once-per-turn precedent | `main.py:762-764` — the comment states the principle this SPEC reuses for values |
| Code streamed as it arrives | `render_stream(..., highlight_code=True)` at `main.py:814-822` |
| Live regions are transient and TTY-gated | `processing()` at `main.py:562-596` |
| Result rendering | `show_exec_result()` at `main.py:625`, called at `main.py:833` |
| Feedback sent back to the model | success `main.py:838-842`; failure `main.py:878-884` |
| Capture site and its arguments | `main.py:860-869` → `_capture_turn()` `main.py:712-751` → `remember_success()` `main.py:736-738`, `recall.py:240-248` |
| readline prompt bracketing | `PROMPT` at `main.py:974`, with the reasoning at `main.py:960-973` |
| The prompt call itself | `_prompt_user()` at `main.py:977-981` |
| readline history is persisted to the volume | `_install_history()` `main.py:930-957`; `CODERUNNER_HISTORY` forced to `/home/runner/.coderunner/history` at `docker-compose.yml:107` |
| Command dispatch point in the REPL | `main.py:1013` (`/memory`), exit words at `main.py:1010` |
| Per-turn Ctrl+C recovery | `main.py:1022-1023` |
| The eleven environment variables | `main.py:66-71` and `main.py:87-96`; table at `tech.md` §4.1 |
| "no config file, no `.env`" | `tech.md:204-207` |
| The volume that survives `--rm` | `docker-compose.yml:75`, named `coderunner_app_data` at `docker-compose.yml:114-115` |
| Volume ownership trap | `Dockerfile:36-46`; `tech.md` §6.5 trap A (`tech.md:513`) |
| Memory store is plaintext and generated-code-reachable | `tech.md` §7.2 (`tech.md:555-590`), `product.md` §6.11 |
| One-line degradation convention | `product.md:138` (feature 20) |
| `memory.py` is stdlib-only, asserted twice by AST | `memory.py:12`; `tests/test_source_seam.py:106-114`; `tests/test_memory_primitives.py:24-47` |
| Per-file coverage floors | `conftest.py:187-192`; enforcement `conftest.py:195-225`; the `coverage unavailable` branch `conftest.py:206-209` |
| Which modules are measured at all | `pytest.ini:38-45` — `--cov=memory --cov=recall --cov=vectorstore` |
| CI pass floor | `MIN_PASSED = 296` at `.github/workflows/ci.yml:268` |

**One drift noted in passing, not fixed here.** `tech.md` §4.1 cites `main.py:65-95` for the
environment block; the constants are at `main.py:66-71` and `main.py:87-96` today, and
`tech.md` §4.1 gives `docker-compose.yml:100` for `CODERUNNER_HISTORY`, which is at
`docker-compose.yml:107`. Both are off by a few lines and neither changes any claim. Folded into
the documentation task (`plan.md` T9) rather than left to rot.

---

## 3. Design decisions

Six questions, each answered with a recommendation and the price of that recommendation.

### 3.1 D1 — Declaration syntax: a `# @param` comment **inside** the Python fence

**Recommendation.** The model declares each value as a comment line inside the fenced block it
already emits, before first use:

```
# @param city: str = "Which city?"
# @param api_key: secret = "OpenWeather API key"
```

Grammar, deliberately small enough that an 8B model can hit it every time:

```
# @param <name> : <type> = "<prompt text>"
         ^ident   ^one of: str | int | float | secret
```

`name` must match `[A-Za-z_][A-Za-z0-9_]*`; anything else is not a declaration. `secret` is a
*type* rather than a separate flag because one token is easier for a small model than two, and
because it makes the sensitive case impossible to express half-way.

**Why not the alternatives.** Both were tested against the real regex, and one of them is
disqualified by measurement rather than by taste (M2, 2026-08-06):

| Candidate | `CODE_BLOCK_RE.findall()` | `extract_last_python_block()` | Verdict |
|---|---|---|---|
| ```` ```params ```` block **before** the ```` ```python ```` block | `['']` | `''` | **Disqualified.** Empty string is falsy at `main.py:826`; the turn silently answers as if no code was produced |
| ```` ```params ```` block **after** the ```` ```python ```` block | `['print(city)\n']` | `'print(city)'` | Works — **by ordering luck only** |
| `# @param` comment inside the fence | `['# @param city: str = "Which city?"\nimport requests\nprint(city)\n']` | intact | **Chosen** |
| `PARAMS:` header line above the fence | `['print(city)\n']` | intact | Works; rejected below |

The header-line option is not broken; it is weaker. It lives outside the fence, so it is rendered
by `render_stream()` as prose rather than as highlighted code, it is not part of `code`, and it is
anchored to nothing the model already produces — it is a new free-form convention competing with
prose for an 8B model's attention. The comment form is anchored to something the model emits
constantly and correctly.

**What the choice costs, stated plainly.**

1. **The declarations live inside `code`.** They are streamed and syntax-highlighted like any
   other line (`main.py:814-822`), they are written into the temp script, and — being legal Python
   comments — they are *executed* as comments, which is to say harmlessly. That last property is
   the quiet benefit: if the parser fails to recognise a declaration, the script still **parses**.
   The failure is a `NameError` at runtime, which feeds the existing self-correction loop at
   `main.py:872-884`, rather than a `SyntaxError` before line one.
2. **They are captured into solution memory** (they are part of `code`), so a recalled record can
   carry a `# @param` line into a later turn where the model may re-emit it and re-prompt the user
   for something the new task does not need. This is a real annoyance with no clean fix at the
   store layer; the mitigation is that the user can decline a value (§3.4) and the turn proceeds
   with an empty string.
3. **`# @param` becomes reserved.** A generated script that legitimately contains that literal in
   a comment gets a spurious prompt. Vanishingly unlikely; recorded so nobody has to rediscover it.

### 3.2 D2 — Value injection must be literal-safe. **HARD.**

**Requirement.** A user-supplied value is **never** interpolated into source text. Each value is
emitted through `repr()` (for `str` and `secret`, after the value has been read as a string) or
through the type's own `repr()` after parsing (`int`, `float`). `json.dumps()` is an acceptable
substitute for the string cases and is explicitly permitted; f-string or `%`-style interpolation
of the raw value into a quoted literal is **forbidden** and must not appear in the codebase.

**Why this is a hard requirement and not a nicety.** Measured 2026-08-06, with
`value = 'Seoul"; import os; os.system("id"); x="'`:

| Prelude construction | Result |
|---|---|
| `f'city = "{value}"'` | **rc 0**, stdout begins `uid=501(kurapa) gid=20(staff) …` — the injected `os.system("id")` ran |
| `f'city = {value!r}'` | rc 0, stdout `39 'Seoul"; import os; os.system("id"); x="'` — the value arrived as a 39-character **string** |

And the quote is not even necessary. A value of `a\nimport os\nos.system("id")\nb = "` needs no
quote character at all: naively interpolated it yields four statements where the author wrote one.
`repr()` renders the same value as `'a\nimport os\nos.system("id")\nb = "'` — one literal, one
statement.

CodeRunner's threat model already accepts that *the model* writes arbitrary code
(`tech.md` §7.2: "No static screening of generated code"). It has never accepted that **the user's
answer to a prompt** is code. Those are different trust boundaries and this SPEC must not merge
them: the prompt text is written by the model, and a model that can phrase the question can choose
the answer's shape. Under naive interpolation, a prompt reading *"paste your config line here"* is
an execution primitive the model controls end to end.

**Cost.** Values are typed. `repr()` of a string is a string; a declared `int` must be parsed
before it is emitted, and a parse failure has to be handled (re-prompt once, then inject the
literal `None` and let the script fail normally — see E5). Blind interpolation would have needed
none of that. This is the correct trade and it is not free.

**AC-INJ is mandatory**: a test feeds a hostile value through the full prelude path and asserts it
arrives as **data** — asserting on the round-tripped value, not merely on the absence of a crash.

### 3.3 D3 — Prompt UX

**Recommendation.**

- Prompting happens **after** the reasoning stream has finished and **before** the execution phase
  begins — that is, between `main.py:828` and the `with processing(...)` at `main.py:830`.
  `processing()` opens a transient Rich `Live` region (`main.py:562-596`); an `input()` inside a
  Live region fights the renderer for the terminal. Collection must therefore be outside every
  `processing()` block, and there is exactly one place in the turn that qualifies.
- One status line announces the batch before the first prompt: `⚙️ [Params] This script needs 2
  values.` — using the existing `status()` renderer so it looks like every other phase line.
- **Non-secret values** are read with `input()` and a coloured prompt built to the same convention
  as `PROMPT` (`main.py:974`): every colour escape bracketed by `\001` … `\002`. `main.py:960-973`
  explains why in detail and the explanation applies verbatim — readline counts unbracketed escape
  bytes as visible columns, computes every redraw from a wrong origin, and corrupts the line the
  moment the user presses Up. The prompt renders perfectly until then, which is what makes the bug
  worth restating rather than assuming.
- **`secret` values** are read with `getpass.getpass()` (stdlib). And `getpass` **must not** reuse
  the bracketed prompt: it is not readline, it writes the prompt string raw to the terminal, so
  `\001` and `\002` would be emitted as literal SOH/STX control bytes instead of being interpreted.
  The masked prompt is therefore plain, uncoloured text. *(Reasoned from `getpass`'s documented
  behaviour and the mechanism at `main.py:960-973`; not measured in a container.)*
- After collection, one line per value confirms what was captured **without the value**:
  `⚙️ [Params] city = "Seoul"` for plain values (already visible in the terminal echo anyway) and
  `⚙️ [Params] api_key = ●●●●●●` for secrets.

**There is a second reason `secret` must use `getpass`, and it is not about the screen.**
`_install_history()` (`main.py:930-957`) wires readline and registers an `atexit` writer; any line
read through `input()` while readline is loaded enters the history buffer and is written to
`CODERUNNER_HISTORY`, which compose pins to `/home/runner/.coderunner/history`
(`docker-compose.yml:107`) — **on the `app_data` volume, which survives `--rm`**. A secret typed at
an `input()` prompt would therefore be persisted in plaintext next to the memory store, by a
mechanism entirely separate from solution capture, and no capture policy in §4 would touch it.
`getpass` does not use readline and so does not do this.

**Cost.** Two prompt paths with different escaping rules, and the masked one is visually
inconsistent with everything else the program prints. That inconsistency is the price of not
inventing a masked-input implementation on top of readline.

### 3.4 D4 — Collection happens **once per turn**

**Recommendation.** Values are collected before the first execution attempt and held in a dict
local to `agentic_turn()`, keyed by parameter name, for the life of the turn. On attempts 2 and 3
(`main.py:792`, `MAX_RETRIES` default 3 at `main.py:69`), a declaration whose name is already in
the dict is satisfied from the dict and **the user is not asked again**. A declaration with a *new*
name prompts only for that name.

This is not a new principle in this codebase, which is the argument for it: `main.py:762-764`
already states it for embeddings — *"Retrieval runs ONCE per turn, before the loop, so the
embedding round trip is not paid per attempt."* The same sentence with "prompt" for "round trip" is
this decision.

**Cost, stated because it is a real one.** A mistyped value cannot be corrected within the turn.
If the user types `Seuol` and the script fails, the model self-corrects the *code*, re-declares the
same parameter, and gets the same wrong value back — up to three times. The escape is Ctrl+C, which
`main.py:1022-1023` already handles as "abort this turn only", after which the user re-asks. The
alternative — re-prompting on every attempt — would mean typing an API key three times to watch a
script fail three times, which is worse. Recorded, not fixed.

A declined value (empty input at the prompt) is treated as an explicit empty string, cached like
any other, and injected as `''`. The script then fails on its own terms and the model sees a normal
failure. There is no "skip this parameter" state.

### 3.5 D5 — Display: the prelude is **never rendered**

**Recommendation.** The assembled prelude is not printed, not streamed, and not included in any
panel — for **all** values, sensitive or not.

The reasoning-stream display (`render_stream(..., highlight_code=True)`, `main.py:814-822`) shows
the model's output as it arrives. The prelude is not the model's output: it is assembled after the
stream completes and after `extract_last_python_block()` has run. So there is no mechanism that
would display it by accident — the requirement is to keep it that way, and to refuse the obvious
"show the user what will actually run" enhancement.

**A uniform rule rather than "hide secrets, show the rest", for one reason:** the moment display
depends on a per-value flag, the display path acquires a branch that a later reclassification can
get wrong. A masked value printed in a prelude defeats the masking completely and irreversibly —
it is on the user's scrollback and, if they are in a recorded session, in the recording. A rule
with no exceptions cannot be got wrong.

**Cost.** The user cannot see the exact literal that was injected, so a value that was mistyped, or
that picked up a trailing space from a paste, is diagnosed from the script's behaviour rather than
from the screen. Two things blunt this: non-secret values are already on screen from the terminal
echo at their own prompt, and the confirmation line (§3.3) names each parameter that was collected.

**Redaction has three sinks, not one.** Once a secret exists in a turn it can escape by three
routes, and all three must be closed by the same function:

| Sink | Site | Why it leaks |
|---|---|---|
| The screen | `show_exec_result()` at `main.py:625`, called `main.py:833` | A traceback or an error message may embed the value — e.g. an HTTP error carrying the full URL with the key in the query string |
| The model's conversation | success feedback `main.py:838-842`; failure feedback `main.py:878-884` | Both splice `result.stdout` / `result.stderr` into a `user` message, which then lives in `conv.messages` for the rest of the session |
| The persistent store | `main.py:860-869` → `remember_success()` | `stdout` is a captured field (`recall.py:240-248`) |

One redaction helper, applied at all three, replacing each `secret` value with a fixed marker by
exact substring match. **What it cannot do** is stated in §3.6.

### 3.6 D6 — Solution-memory interaction, and the setting that governs it

Successful turns are captured — task, thought, **code**, stdout — into a Milvus Lite collection on
`coderunner_app_data` (`main.py:860-869`; `tech.md` §6.4). `tech.md` §7.2 already documents that
this store is plaintext and that generated code runs as the same `runner` user that owns it, so any
later generated script can read every record. A feature that introduces secrets into a turn must
answer to that surface.

**The good news is structural, and it should not be mistaken for a policy.** `code` as captured is
the value returned by `extract_last_python_block()` at `main.py:825` and handed unchanged to
`_capture_turn()` at `main.py:860-869`. The prelude is assembled inside the execution path and is
never merged back into that object. So under this design **the injected value is absent from
`code` by construction, not by filtering.** N4 and AC-CAP exist because the first refactor that
prepends the prelude to `code` before extraction — which looks tidier and passes every other test —
destroys this silently.

What remains reachable is `stdout` (a script that prints a value derived from a secret), and the
`# @param` declaration line itself (harmless: it carries the prompt text, never the answer).

**The user's decision, recorded as given: this is a user-configurable setting.** CodeRunner asks,
persists the answer, and loads it at startup. Three policies:

| Key | Policy | Behaviour |
|---|---|---|
| `sensitive_excluded` | Mark values sensitive and exclude only those | The turn is captured. Every `secret` value is redacted from `stdout` before capture, by exact substring. `code` is asserted free of values by construction (N4) |
| `never` | Never capture a turn that used parameters | `_capture_turn()` is skipped for any turn with at least one declaration. One status line says so |
| `always` | Capture everything | No redaction. Documented as carrying the risk. Present because a user running only non-secret parameters loses recall quality for nothing under the other two |

**Recommended default: `sensitive_excluded`.** It keeps solution memory working — which is the
whole of SPEC-MEMORY-001's value — while removing the one class of content nobody intends to
persist.

**What `sensitive_excluded` cannot do, said plainly rather than discovered later.** Substring
redaction removes what it can find. It does not find a value that the script **transformed** before
printing: base64, a hash, URL-encoding, a slice, or a key spliced into a longer string with
percent-escapes. A script that prints `token[:8]` leaks eight characters that no substring search
will match. `sensitive_excluded` therefore reduces the exposure of secrets in captured stdout; it
does not eliminate it, and any documentation that says "secrets are not stored" would be false.
Users for whom that residual matters have `never`, and that is why `never` is offered rather than
being treated as the paranoid option.

### 3.7 Rejected alternative: pass values through the child's environment

Worth naming because it is the strongest thing this SPEC turns down, and because the reason is not
"it is worse".

`run_python()` could pass values via `subprocess.run(..., env={...})` and have the generated script
read `os.environ["CITY"]`. `-I` implies `-E`, which ignores `PYTHON*` variables only, so ordinary
names pass through. **That approach removes the injection class entirely rather than mitigating
it**: the value never becomes text in a source file, so there is nothing for `repr()` to have to
get right.

It is rejected on three counts, and the first is the decisive one:

1. **The model has to write the retrieval.** `os.environ["CITY"]` for strings and
   `int(os.environ["N"])` for numbers — extra syntax, per-type, that `llama3.1:8b` must get right
   on every generation, in place of a bare name it already knows how to use. The prelude approach
   asks the model for a comment line and a variable name; the environment approach asks it for a
   comment line, a variable name, a subscript, and a cast.
2. **The script stops being self-contained.** `SCRIPT_HEADER` (`main.py:422-431`) describes an
   ephemeral script; today that script is reproducible by hand. An env-dependent script is not.
3. **The value moves from a deleted temp file to the child's environment**, readable via
   `/proc/<pid>/environ` for the process's lifetime by anything running as `runner` — which is
   every other thing this container runs.

Counting honestly, (2) and (3) are minor and (1) carries the decision. The safety argument favours
the environment; the reliability argument favours the prelude, and the safety gap is closed by a
**measured** property (M3) rather than an assumed one. **If AC-INJ ever fails in the field, this is
the design to reach for**, and `plan.md` R2 says so.

---

## 4. `settings.json` — a deliberate reversal of a documented property

### 4.1 The reversal, recorded

`tech.md:204-207` states, without qualification:

> All configuration is environment-variable based. There is **no config file, no `.env` loading,
> and no `python-dotenv` dependency.**

This SPEC introduces a config file. That is a reversal of a stated architectural property and it is
recorded here rather than buried in a task, because a property that can be reversed quietly is not
a property.

**Why a file is right here and environment variables are not.** Every one of the eleven existing
variables (`main.py:66-71`, `main.py:87-96`) is set by an operator *before* the process starts, and
compose supplies each one unconditionally (`docker-compose.yml:76-108`). The capture policy is
different in kind on both axes: it is **chosen interactively, by the user, mid-session, in answer
to a question the program asks**, and it must **survive `docker compose run --rm`**. An environment
variable cannot be written by the running process in any way the next container will see. A file on
the persistent volume can. There is no third option that is not a worse file.

**No dependency is added.** `json` and `pathlib` are stdlib. `tech.md`'s "no `python-dotenv`" half
remains true and should stay in the corrected text.

### 4.2 Location

`/home/runner/.coderunner/settings.json` — inside the `app_data` volume mounted at
`docker-compose.yml:75` and named `coderunner_app_data` at `docker-compose.yml:114-115`. This is
the only path that survives the `--rm` lifecycle, and it already holds `memory.milvus.db` and
`history` (`docker-compose.yml:107`). Putting the file anywhere else means putting it somewhere
that is deleted when the container exits.

Schema, versioned from the first line so that a future key is a migration and not a guess:

```json
{
  "schema_version": 1,
  "param_capture_policy": "sensitive_excluded"
}
```

### 4.3 Precedence against the eleven environment variables

Stated unambiguously, in three rules:

1. **The namespaces are disjoint.** `settings.json` carries `param_capture_policy` and nothing
   else. It is **not** a general configuration file and must never grow a key that shadows one of
   the eleven. A key in `settings.json` whose name corresponds to any of the eleven is **ignored**,
   and one status line says so.
2. **On any overlap, the environment wins, unconditionally.** This is the tie-break for a future
   in which rule 1 is violated by accident. It is stated now so that nobody has to decide it under
   pressure, and it preserves `tech.md` §4 as the description of how CodeRunner is *configured* —
   `settings.json` describes only what the user *chose*.
3. **Full order for `param_capture_policy`:**
   `CODERUNNER_PARAM_CAPTURE` (if set and valid) → `settings.json` → built-in default.

Rule 3 introduces a twelfth environment variable, and it is **Optional** (§4.5 O1), not required,
because of a trap that must be recorded whether or not it is implemented:

> **Do not add `CODERUNNER_PARAM_CAPTURE` to `docker-compose.yml`.** Every memory variable there
> is written as `${VAR:-default}` (`docker-compose.yml:82-104`), which means the variable is
> **always set inside the container**, always with a value. Adding the policy in that form would
> make the environment override permanently active, which by rule 3 makes `settings.json` dead on
> arrival — a file that is written, read, and then unconditionally overruled. The env override is
> therefore reachable only via an explicit `docker compose run -e`, exactly as `OLLAMA_HOST`
> already is under `./coderunner` (`tech.md` §4.1). That limitation is why the requirement is
> Optional rather than mandatory.

This is the reason §6 declines to touch `docker-compose.yml`.

### 4.4 Behaviour when the file is not usable

The convention is `product.md:138` (feature 20): any fault produces **exactly one status line** and
a turn otherwise identical to the pre-feature product. Never an exception into the REPL.

| Condition | Behaviour | Line |
|---|---|---|
| **Absent** | First-run path: ask the user, then write (§4.5) | the question itself |
| **Present, unreadable** (`PermissionError`, `OSError`) | Fall back to **`never`**. Do not ask. Do not retry this session | one yellow line naming the path |
| **Malformed JSON** (`json.JSONDecodeError`) | Fall back to **`never`**. **Do not rewrite the file** | one yellow line |
| **Valid JSON, not an object** (a list, a string, `null`) | Fall back to **`never`** | one yellow line |
| **Unknown `param_capture_policy` value** | Fall back to **`never`** | one yellow line naming the unrecognised value |
| **Unknown extra keys** | Ignored, **silently** | none |
| **`schema_version` newer than known** | Fall back to **`never`** | one yellow line |
| **Write fails** (root-owned volume, full disk) | The choice applies to **this session only**; the user is asked again next launch | one yellow line |

**The fallback is `never`, not the default, and that is the whole point of the table.** A file that
cannot be read is exactly the file that might have said `never`. Falling back to
`sensitive_excluded` would mean capturing turns from a user who had explicitly asked that they not
be captured, on the strength of a file we just admitted we could not parse. The conservative
fallback is the only one that cannot violate a stated preference it cannot see. It costs
capture — announced by a status line — until the file is fixed.

**Do not rewrite a malformed file.** It may be a hand edit with a typo, and overwriting it destroys
the user's intent along with their mistake. Degrade, say so, leave it alone.

### 4.5 When the user is asked, and how they change it later

**Asked lazily, on the first turn that declares a parameter — never at startup.** A user who never
uses this feature is never asked, and `settings.json` is never created for them, so the reversal in
§4.1 costs nothing to anyone who does not opt in. The question is asked immediately before the
first value prompt, in the same phase, so the whole interaction is one block:

```
⚙️  [Params] This script needs 2 values, one of them marked secret.
     Before asking: how should solution memory treat parameterised turns?
       1) Store the turn, but never a secret value   (recommended)
       2) Never store a turn that used parameters
       3) Store everything, including secrets
     Choice [1]:
```

The answer is written to `settings.json` and never asked again. If stdin is not interactive — a
piped session, a test — the question cannot be asked, so the policy falls back to `never`, one
status line says so, and nothing is written.

**Changing it later: a `/params` command family**, dispatched in `repl()` beside `/memory`
(`main.py:1013`). `/params` prints the current policy **and where it came from** (file, environment
override, or fallback — the provenance is the useful half); `/params capture <1|2|3>` sets and
persists it. `agentic_turn()` is never invoked for either, matching how `/memory` behaves.

*Not* folded into the `/memory` family, despite the policy being a memory concern, for one
mechanical reason: `handle_memory_command()` lives in `memory.py` (`memory.py:451`), and `memory.py`
performs **no file I/O today** — its only `Path` use is construction at `memory.py:287`. Routing a
settings write through it would put file I/O and its four failure branches into the module whose
stated purpose (`memory.py:12`) is to be the stdlib-only, dependency-free core. §5 develops this.

**Cost:** a second command family for one setting, and a user who thinks of it as a memory setting
will type `/memory capture` and get nothing. Mitigated by `/memory`'s own output naming
`/params capture` in its footer.

### 4.6 Is writing the file safe when the volume is root-owned?

`tech.md` §6.5 trap A (`tech.md:513`) documents the failure this question is about: a named volume
mounted at a path **absent from the image** is created root-owned, `runner` can never write it, and
the memory subsystem degrades on every turn of every session while looking exactly like
well-behaved graceful degradation. `Dockerfile:36-46` fixes it by creating and chowning
`/home/runner/.coderunner` before `USER runner`, so Docker seeds the volume with `runner`
ownership.

**On a current image, the write is safe** — same directory, same owner, same mechanism that already
lets `memory.milvus.db` and `history` be written.

**On a pre-existing volume, it may not be.** Docker seeds ownership only into an **empty** volume at
first mount. A `coderunner_app_data` volume created by an image built before `Dockerfile:43-44`
landed keeps its root ownership permanently, and no later image fixes it. On such a machine the
memory store is already failing, and `settings.json` will fail in the same way for the same reason.

The requirement that follows (S4) is therefore not "check for root ownership" — the store's own
degradation already reports that condition once per turn. It is: **a write failure must be
distinguishable from a decision.** The session keeps the policy the user just chose, one status
line says the choice was not persisted, and the user is asked again next launch. Silently accepting
a choice that was never saved is the failure this SPEC most wants to avoid, because it looks
identical to success.

---

## 5. Where the code belongs

### 5.1 Not in `memory.py`

`memory.py:12` states the constraint — *"IMPORTS : stdlib ONLY — no rich, no ollama, no httpx, no
pymilvus, NO NUMPY"* — and two AST tests enforce it: `tests/test_source_seam.py:106-114` and
`tests/test_memory_primitives.py:24-47`.

**Settings loading would not break that test.** `json` and `pathlib` are both in
`sys.stdlib_module_names`, so the assertion would still pass. The reason to keep it out is
different and, in this codebase, better established:

1. **`memory.py` performs no file I/O.** Its only filesystem contact is `Path()` construction at
   `memory.py:287`. Adding `read_text` / `write_text` and their four failure branches would put I/O
   into the module that exists precisely so that its suite runs on a bare interpreter with nothing
   installed.
2. **`memory.py` is gated at 100%** (`conftest.py:187-192`). Every one of the degradation branches
   in §4.4 would have to be driven to keep it there. That is a *good* obligation and this SPEC
   accepts it — just not on the module whose 100% currently costs nothing to maintain.

### 5.2 Two new stdlib-only modules, both gated at 100%

| Module | Contents | Gate |
|---|---|---|
| `params.py` | Declaration parsing (`# @param` grammar), validation, type parsing, literal-safe prelude rendering, the redaction helper | **100%** |
| `settings.py` | `settings.json` load / save / degrade, policy resolution and precedence, provenance reporting | **100%** |

Both stdlib-only, both leaf modules, both testable on a bare interpreter — which is not a new
pattern here but the existing one: `memory.py` is the stdlib-only core, `recall.py` owns the
embedding backend, `vectorstore.py` owns Milvus. Two more stdlib-only leaves extend that seam
rather than departing from it.

`params.py` is gated at **100%, not 85%**, for one reason: it is the module where a bug is a
code-execution bug. `vectorstore.py`'s 85% floor (`conftest.py:187-192`) was set because its
degradation branches run against a real engine. `params.py` has no such excuse — it is pure string
handling with no external dependency, and there is no line in it that cannot be reached by a test.

**Adding a gated module takes two edits, and forgetting one is caught loudly.**
`pytest.ini:38-45` lists `--cov=memory --cov=recall --cov=vectorstore`; a module absent from that
list is not measured at all. If `conftest.py:187-192` gains `params.py` but `pytest.ini` does not,
`cov.report(include=["params.py"])` raises, the `except` at `conftest.py:207-209` records
`params.py: coverage unavailable`, and the session **fails**. That is the desirable direction for
this mistake to fail in, and it is worth knowing before someone spends an afternoon on it.

### 5.3 `main.py` is not gated, and this is said out loud

`main.py` appears in neither `pytest.ini:38-45` nor `conftest.py:187-192`.
`.moai/specs/SPEC-MEMORY-001/acceptance.md` scopes a repository-wide gate out explicitly, and
SPEC-CI-001 §6 item 7 carries that forward. **New code in `main.py` under this SPEC is therefore
not covered by any coverage floor.** That is a deliberate inheritance, not an oversight, and it has
one consequence this SPEC must act on:

**`main.py`'s share is wiring only.** Prompting, threading the collected dict through
`agentic_turn()`, and dispatching `/params`. Every decision — what counts as a declaration, how a
literal is rendered, what a malformed settings file means, what gets redacted — lives in a gated
module. The rule to hold the line: if a change to `main.py` would need a new test to be trusted,
it is in the wrong file.

---

## 6. EARS requirements

All five requirement types are represented.

### 6.1 Ubiquitous — always true

| # | Requirement |
|---|---|
| **U1** | A user-supplied value **shall always** reach the generated script as a Python **literal** produced by `repr()` or `json.dumps()`. String interpolation of a raw value into source text **shall** appear nowhere in the codebase. |
| **U2** | `run_python()` **shall always** leave the child's `stdin` exactly as it is today (`main.py:461-468`). This SPEC introduces no `stdin=` argument, no pipe, and no TTY handover. The property being protected is measured at M1. |
| **U3** | Solution capture **shall always** receive the `code` value returned by `extract_last_python_block()` (`main.py:825`) and **shall never** receive the assembled prelude. The absence of injected values from `code` is **structural**, and it is asserted by test rather than assumed. |
| **U4** | Every `settings.json` fault **shall always** produce **exactly one** status line and a turn otherwise identical to the pre-feature product, matching `product.md:138`. No fault **shall** raise into the REPL. |
| **U5** | The effective capture policy **shall always** be reportable with its **provenance** — file, environment override, or fallback. A policy whose origin cannot be named is a policy nobody can debug. |

### 6.2 Event-driven — WHEN … THEN …

| # | Requirement |
|---|---|
| **E1** | **WHEN** an extracted code block contains one or more `# @param` declarations, **THEN** CodeRunner **shall** collect a value for each, in declaration order, **after** the reasoning stream has completed and **before** the `processing()` block at `main.py:830` is entered. |
| **E2** | **WHEN** a declaration's type is `secret`, **THEN** the value **shall** be read with `getpass.getpass()` and its prompt **shall not** carry `\001`/`\002` bracketing, because `getpass` writes the prompt raw and is not readline. |
| **E3** | **WHEN** a declaration's type is not `secret`, **THEN** the value **shall** be read with `input()` and a prompt whose colour escapes are bracketed by `\001`/`\002`, per `main.py:960-973`. |
| **E4** | **WHEN** an execution attempt fails and the model emits a corrected block on attempt 2 or 3 (`main.py:792`), **THEN** any declaration whose name was already collected **shall** be satisfied from the turn's cache **without prompting**, and only genuinely new names **shall** prompt. |
| **E5** | **WHEN** a value declared `int` or `float` cannot be parsed, **THEN** CodeRunner **shall** re-prompt **once**, and on a second failure **shall** inject the literal `None` and proceed, so the script fails on its own terms into the existing self-correction loop (`main.py:872-884`). |
| **E6** | **WHEN** a turn used at least one declaration and the effective policy is `sensitive_excluded`, **THEN** every `secret` value **shall** be redacted by exact substring from `result.stdout` and `result.stderr` **before** they reach any of the three sinks: `show_exec_result()` (`main.py:833`), the feedback messages (`main.py:838-842`, `main.py:878-884`), and `_capture_turn()` (`main.py:860-869`). |
| **E7** | **WHEN** the first turn containing a declaration occurs and `settings.json` is absent, **THEN** CodeRunner **shall** ask the user to choose a policy, **shall** write the answer to `/home/runner/.coderunner/settings.json`, and **shall not** ask again on any later turn or launch. |

### 6.3 State-driven — IF/WHILE … THEN …

| # | Requirement |
|---|---|
| **S1** | **IF** the effective policy is `never` **AND** the turn contained at least one declaration, **THEN** `_capture_turn()` **shall not** be called, and one status line **shall** report that the turn was not stored. Silence here is indistinguishable from a successful capture. |
| **S2** | **IF** `settings.json` is present but unreadable, malformed, not a JSON object, carries an unknown `param_capture_policy`, or declares a `schema_version` newer than known, **THEN** the effective policy **shall** be `never`, exactly one status line **shall** be emitted, and the file **shall not** be rewritten. |
| **S3** | **IF** `CODERUNNER_PARAM_CAPTURE` is set to a recognised value, **THEN** it **shall** override `settings.json` for the session, and `/params` **shall** report the environment as the provenance. |
| **S4** | **IF** the write of `settings.json` fails, **THEN** the chosen policy **shall** apply for the current session only, one status line **shall** state that it was not persisted, and the user **shall** be asked again on the next launch. A choice that was silently not saved is the failure mode this requirement exists for (§4.6). |
| **S5** | **WHILE** the model's output is still streaming, **THEN** no prompt **shall** be issued. Collection begins only after `render_stream()` returns (`main.py:814-822`), because a prompt inside a Rich `Live` region (`main.py:562-596`) contends with the renderer for the terminal. |

### 6.4 Unwanted — shall not

| # | Requirement |
|---|---|
| **N1** | The SYSTEM_PROMPT **shall not** stop forbidding `input()`. `main.py:136` is **amended, not deleted**: the prohibition stands and gains a sanctioned alternative. M1 is why. |
| **N2** | The assembled prelude **shall not** be printed, streamed, panelled, or logged — **for any value, sensitive or not**. A per-value display branch is forbidden, because the branch is the bug (§3.5). |
| **N3** | A `secret` value **shall not** be read through `input()` under any circumstance. readline is loaded (`main.py:930-957`) and would persist the line to `CODERUNNER_HISTORY` on the `app_data` volume (`docker-compose.yml:107`), where no capture policy would ever see it. |
| **N4** | The prelude **shall not** be merged into `code` before extraction, capture, or conversation. The value handed to `_capture_turn()` at `main.py:860-869` **shall** be the value returned at `main.py:825`, unchanged. |
| **N5** | Declarations **shall not** be expressed as a separate fenced block. Measured (M2): a ```` ```params ```` block preceding the Python block makes `extract_last_python_block()` return `''`, which is falsy at `main.py:826` and silently answers the turn as if no code existed. |
| **N6** | `settings.json` **shall not** become a general configuration file. It carries `param_capture_policy` and `schema_version`. A key shadowing any of the eleven environment variables (`main.py:66-71`, `main.py:87-96`) **shall** be ignored with one status line. |
| **N7** | `docker-compose.yml` **shall not** be modified. Adding `CODERUNNER_PARAM_CAPTURE` in the file's own `${VAR:-default}` idiom (`docker-compose.yml:82-104`) would set it unconditionally inside the container, permanently overriding `settings.json` and making the file it was meant to complement inert (§4.3). |

### 6.5 Optional — where possible

| # | Requirement |
|---|---|
| **O1** | **Where** an operator needs to force a policy without touching `settings.json`, `CODERUNNER_PARAM_CAPTURE` **should** be honoured as the highest-precedence source. Optional rather than required because it is unreachable under `./coderunner` without an explicit `docker compose run -e` — see N7. |
| **O2** | **Where** a value is not `secret`, its collected value **may** be echoed in the per-parameter confirmation line, since it is already on screen from the terminal echo. Secrets **shall** show a fixed mask instead. |
| **O3** | **Where** `/memory` prints its footer (`memory.py:451`), it **should** name `/params capture` so a user looking for the capture policy in the obvious place finds the pointer. |
| **O4** | **Where** a declaration is malformed — a bad identifier, an unknown type, a missing prompt string — CodeRunner **should** ignore that line and continue with the remaining declarations rather than abandoning the turn. A malformed declaration then surfaces as a `NameError` from the script, which the self-correction loop already handles. |

---

## 7. In scope

1. `params.py` — declaration grammar, parsing, type handling, literal-safe prelude rendering,
   redaction helper. New module, stdlib-only, gated at **100%**.
2. `settings.py` — `settings.json` load / save / degrade / precedence / provenance. New module,
   stdlib-only, gated at **100%**.
3. `main.py` wiring: prompt collection between `main.py:828` and `main.py:830`, the per-turn value
   cache threaded through the `MAX_RETRIES` loop, prelude assembly inside the execution path,
   redaction at the three sinks, and `/params` dispatch beside `main.py:1013`.
4. The `SYSTEM_PROMPT` amendment at `main.py:136` — prohibition retained, `# @param` documented as
   the sanctioned alternative, with one worked example.
5. `conftest.py:187-192` and `pytest.ini:38-45` — two edits each admitting the two new modules to
   the coverage gate.
6. `.github/workflows/ci.yml:268` — raise `MIN_PASSED` from 296 to the new measured count.
7. Documentation: `tech.md` §4 (the reversal), `tech.md` §7.2 (the new sink), `product.md` §4
   (a new user-visible feature) and `product.md` §6 (the residual leak), `README.md`.

## 8. Out of scope

1. **`input()` in generated code, in any form.** M1 measured both outcomes: `EOFError` on the host,
   a blocking terminal hijack in the container. The prohibition at `main.py:136` is retained by N1
   and this is the reason the feature takes the shape it does.
2. **Passing values through the child's environment.** Named and argued at §3.7 rather than
   omitted; it removes the injection class outright and is turned down on model-reliability
   grounds. It is the designated fallback if AC-INJ ever fails (`plan.md` R2).
3. **Encryption at rest, a keyring, or any secret store.** `tech.md` §7.2 states there is no
   encryption at rest and none planned. This SPEC does not open that; it only stops adding to what
   is stored in the clear.
4. **Retro-fitting redaction over records captured before this SPEC.** There are none containing
   parameter values — the feature does not exist yet — so the migration would be a no-op with a
   migration's risk.
5. **Re-prompting to correct a mistyped value within a turn.** §3.4 records the cost and the
   Ctrl+C escape (`main.py:1022-1023`). Fixing it means either prompting per attempt (worse) or a
   value-editing UI (a different SPEC).
6. **Any change to `docker-compose.yml`.** N7 gives the mechanical reason: the file's
   `${VAR:-default}` idiom would make an env override permanent and `settings.json` inert.
7. **A general configuration file.** N6. `settings.json` holds one key. `tech.md` §4 remains the
   description of how CodeRunner is configured.
8. **Coverage gates on `main.py`.** Inherited from `.moai/specs/SPEC-MEMORY-001/acceptance.md` and
   SPEC-CI-001 §6 item 7. §5.3 states the consequence rather than leaving it implicit, and confines
   `main.py`'s share to wiring in response.
9. **Streaming or displaying the assembled prelude.** N2. The "show the user what will actually
   run" enhancement is refused on purpose.
10. **Sensitivity inference.** CodeRunner does not guess that a parameter named `api_key` is
    secret. The model declares `secret` or it does not. A heuristic that is right 95% of the time
    is a heuristic that leaks 5% of the time, and it would leak silently.

---

## 9. Traceability

| Artefact | Location |
|---|---|
| Requirements | this file, §6 (U1–U5, E1–E7, S1–S5, N1–N7, O1–O4) |
| Design decisions with costs | this file, §3 (D1–D6) and §3.7 |
| The reversal record | this file, §4.1 |
| Task decomposition, critical path, risks | `.moai/specs/SPEC-INPUT-001/plan.md` |
| Acceptance criteria | `.moai/specs/SPEC-INPUT-001/acceptance.md` |
| The prohibition being amended | `main.py:136` |
| The stdin property being preserved | `main.py:461-468` |
| The extraction path being protected | `main.py:414`, `main.py:417-419`, `main.py:825-828` |
| The capture path being governed | `main.py:860-869`, `main.py:712-751`, `recall.py:240-248` |
| The prompt mechanics | `main.py:930-957`, `main.py:960-973`, `main.py:974`, `main.py:977-981` |
| Modules to be created | `params.py`, `settings.py` |
| Gate files to be amended | `conftest.py:187-192`, `pytest.ini:38-45` |
| CI floor to be raised | `.github/workflows/ci.yml:268` (`MIN_PASSED = 296`) |
| Explicitly not amended | `docker-compose.yml` (N7) |
| Documentation to be corrected | `tech.md:204-207` (§4), `tech.md` §7.2, `product.md` §4 and §6, `README.md` |
| Project context | `.moai/project/product.md`, `.moai/project/structure.md`, `.moai/project/tech.md` |

| Requirement group | Primary acceptance criteria |
|---|---|
| U1, N5 | **AC-INJ**, **AC-SYN** |
| U2, N1 | **AC-STDIN** |
| U3, N4, E6, S1 | **AC-CAP** |
| E1, E3, E4, S5 | **AC-ONCE** |
| E2, N2, N3 | **AC-MASK** |
| U4, U5, S2, S4 | **AC-DEGRADE** |
| E7, S3, N6, N7 | **AC-SETTINGS** |
