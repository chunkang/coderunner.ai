# SPEC-INPUT-001 — Acceptance Criteria (v1.0.0)

> Requirements are in `spec.md`. Implementation detail is in `plan.md`.

**Status at authoring:** nothing here has been implemented. AC-INJ, AC-SYN, AC-STDIN and AC-FUTURE
rest on **measurements taken 2026-08-06 against the current tree** — those measurements are real
and are reproduced below; the criteria built on them are not yet verified. AC-CAP, AC-ONCE,
AC-MASK, AC-DEGRADE and AC-SETTINGS are **specified, not verified**.

Three of these criteria exist because a plausible implementation is green while doing the wrong
thing, and they are the ones to read first:

- **AC-INJ** — the difference between safe and unsafe is one character inside an f-string, and both
  versions run the script successfully.
- **AC-CAP** — the tidy refactor that breaks it passes every other test in the suite.
- **AC-DEGRADE** — a policy that silently fell back looks exactly like a policy that was chosen.

---

## AC-INJ — A hostile value arrives as data, not as code

Covers U1, and it is the reason `spec.md` §3.2 is marked HARD.

**Given** a declaration `# @param city: str = "Which city?"` and a user who types

```
Seoul"; import os; os.system("id"); x="
```

**When** the prelude is rendered by `params.render_prelude()`, prepended by `run_python()`
(`main.py:447-448`), and the script executes

**Then**

- the script prints the value's **length as 39** and its `repr` as
  `'Seoul"; import os; os.system("id"); x="'`;
- `id` **does not run** — no `uid=` string appears anywhere in stdout;
- the assertion is on **the round-tripped value**, not on the exit status.

**And** a second value containing **newlines** — `a\nimport os\nos.system("id")\nb = "`, which
needs no quote character at all — is asserted the same way, because a value with a newline is an
injection vector on its own and a test that only carries a quote would miss it.

**And** a source-level assertion, in the family of `tests/test_source_seam.py`: `params.py`
contains **exactly one** literal-emission site, and no f-string or `%`-format anywhere in the
module places a value between quote characters.

### Why this criterion asserts the value rather than the absence of a crash

Measured 2026-08-06 on this machine, driving `run_python()`'s exact `subprocess.run` argument list:

| Prelude construction | Exit | stdout |
|---|---|---|
| `f'city = "{value}"'` | **0** | `uid=501(kurapa) gid=20(staff) groups=20(staff),12(everyone),…` |
| `f'city = {value!r}'` | **0** | `39 'Seoul"; import os; os.system("id"); x="'` |

**Both exit 0.** Both produce output. Both leave a temp directory that is cleaned up at
`main.py:484-485`. In the REPL the first one shows a green `Execution OK (rc=0)` panel
(`main.py:625`), the model receives the stdout as success feedback (`main.py:838-842`), and the
turn is captured as a solved task. The only thing separating them is **what the output says**, and
the only way to test that is to assert on the value.

The two constructions differ by two characters. A reviewer reads both as "put the city in the
script". A test asserting `result.ok` passes for both.

**And note what the second row proves that a "no crash" test would not:** the hostile value did not
merely fail to execute — it arrived **intact**, all 39 characters of it, as a usable string. Safety
here is not achieved by mangling the input, so a future "just strip quotes and semicolons" defence
would be both weaker and lossier. `repr()` is the requirement (`spec.md` §3.2).

---

## AC-SYN — The declaration syntax cannot disarm code extraction

Covers U1, N5.

**Given** a model response containing declarations and a Python block

**When** `extract_last_python_block()` (`main.py:417-419`) runs against it

**Then** the extracted block is the **complete** Python source, declarations included, and is
non-empty.

**And**, asserted by inspection of `main.py:136`'s amended text as well as by execution: the
`SYSTEM_PROMPT` instructs `# @param` **inside** the existing fence and describes **no second
fenced block of any kind**.

### The measurement that disqualified the alternative

Measured 2026-08-06 against the real `CODE_BLOCK_RE` (`main.py:414`,
`` r"```(?:python|py)?\s*\n(.*?)```" `` with `DOTALL | IGNORECASE`):

| Response shape | `findall()` | `extract_last_python_block()` | In the REPL |
|---|---|---|---|
| ```` ```params ```` block, **then** ```` ```python ```` block | `['']` | `''` | **`if not code:` at `main.py:826` is TRUE.** Turn takes the "No code produced — returning direct answer" branch at `main.py:827-828` |
| ```` ```python ```` block, **then** ```` ```params ```` block | `['print(city)\n']` | `'print(city)'` | works |
| `# @param` comment **inside** the python fence | full block, declarations included | intact | works |
| `PARAMS:` header line **above** the fence | `['print(city)\n']` | `'print(city)'` | works |

Row one is the finding. The regex's optional `(?:python|py)?` does not match `params`, so the
opening fence of a `params` block is not a match — but its **closing** fence pairs with the
**opening** fence of the following `python` block, and `(.*?)` captures the empty string between
them. `extract_last_python_block()` takes `matches[-1]`, which is that empty string, and the empty
string is falsy.

The consequence is the worst available: **the script is never executed, and nothing reports an
error.** The user sees the model's reasoning, then a yellow line saying no code was produced, and
the turn ends. There is no exception, no failed execution, no retry — the agentic loop at
`main.py:792` is never entered.

Row two works, and works *only* because of the order the model happened to choose. A syntax that is
correct or catastrophic depending on which block an 8B model emits first is not a syntax, and
row one is why N5 forbids the separate-fence form outright rather than mandating an order.

---

## AC-STDIN — The child's stdin is untouched and `input()` stays forbidden

Covers U2, N1.

**Given** the amended `SYSTEM_PROMPT` at `main.py:136`

**When** the source is inspected and the sandbox is driven

**Then**

- `run_python()`'s `subprocess.run` call (`main.py:461-468`) contains **no `stdin=` argument** —
  asserted at source level, in the family of `tests/test_source_seam.py`, so the assertion survives
  a refactor rather than depending on a runtime observation;
- the amended prompt text still contains the words forbidding `input()`;
- the amended prompt text **also** documents `# @param` as the sanctioned alternative — the
  prohibition is **amended, not deleted**;
- a generated script containing `input()`, executed through `run_python()`, still fails with
  `EOFError` on a host, and that failure reaches the model through the existing feedback path at
  `main.py:878-884` as an ordinary execution failure.

### Why the prohibition is retained rather than relaxed

Measured 2026-08-06, driving `run_python()`'s exact argument list against a script whose only
statement is `input("hi: ")`:

```
rc = 1
stdout = 'hi: '
stderr = 'Traceback (most recent call last):\n  File ".../run.py", line 1, in <module>\n
           x = input("hi: ")\nEOFError: EOF when reading a line\n'
```

`capture_output=True` pipes stdout and stderr and **says nothing about stdin**, so the child
inherits the parent's descriptor 0. Under pytest that is closed or a pipe, hence `EOFError`.

Inside the container it is the REPL's own TTY — `docker-compose.yml:67-68` set `stdin_open: true`
and `tty: true` — so the child would **block**, consuming the user's keystrokes, for the full
`CODERUNNER_TIMEOUT` (default 30 s, `main.py:68`). *(That row is reasoned from descriptor
inheritance, not measured end to end in a container; it is marked as such in `spec.md` §2.1.)*

The two failure modes are asymmetric in the way that matters: the host one is loud and instant, the
container one is a silent thirty-second hijack of the terminal the user is sitting at. That is the
behaviour `main.py:136` has been preventing, and this SPEC exists to give the model something to do
**instead of** it — not permission to do it.

---

## AC-CAP — The injected value is absent from the store by construction

Covers U3, N4, E6, S1.

**Given** a turn containing `# @param api_key: secret = "…"`, a user-supplied secret value, and a
successful execution

**When** the turn completes and `_capture_turn()` is invoked at `main.py:860-869`

**Then**

- the `code` argument received by `_capture_turn()` **is the same object** returned by
  `extract_last_python_block()` at `main.py:825` — asserted by **identity**, not by comparing
  strings;
- the secret value appears **nowhere** in the arguments passed to `remember_success()`
  (`main.py:736-738`, `recall.py:240-248`): not in `task`, not in `thought`, not in `code`, not in
  `stdout`;
- under `sensitive_excluded`, a secret echoed by the script into stdout is **redacted before** it
  reaches `show_exec_result()` (`main.py:833`), the feedback strings (`main.py:838-842`,
  `main.py:878-884`) and the capture call — all three sinks, asserted separately;
- under `never`, `_capture_turn()` is **not called at all** for a parameterised turn, **and one
  status line reports that the turn was not stored**.

**And** under `always`, no redaction occurs and the turn is captured in full — asserted so that the
policy is known to be doing something rather than being a no-op that happens to look safe.

### Why identity, and not string comparison

The property being protected is **structural**: the prelude is assembled inside `run_python()` and
never merged back, so there is no variable in `agentic_turn()`'s scope holding user values
alongside code. That is what makes the value's absence from the store a fact about the program's
shape rather than a filter that has to be maintained.

The refactor that destroys it is one line — `code = prelude + code` — and it is the tidy version.
It reads better, it removes an argument from `run_python()`, and a reviewer would plausibly suggest
it. Every other test in the suite still passes: the script runs, the output is right, the answer
streams, the turn is captured. The only visible difference is that
`coderunner_app_data` now holds the user's API key in plaintext, in a store `tech.md` §7.2 states
any later generated script can read.

A string comparison would pass under that refactor whenever the prelude happened to be empty —
which is every test that does not declare a parameter, i.e. almost all of them. **Identity is the
assertion that cannot be satisfied by accident.**

### What this criterion does not claim

Under `sensitive_excluded`, redaction is by **exact substring**. A script that prints a
**transformed** value — `token[:8]`, a base64 encoding, a hash, a key spliced into a percent-encoded
URL — leaks material that no substring search matches. The criterion asserts what redaction does; it
does not assert that secrets cannot reach the store. `spec.md` §3.6 states the limit, `plan.md` R5
requires it to survive into `README.md` unsoftened, and `never` exists for users who need the
guarantee rather than the reduction.

---

## AC-ONCE — Values are collected once per turn and reused across retries

Covers E1, E3, E4, S5.

**Given** a turn whose first attempt declares `# @param city: str = "Which city?"`, and a first
execution that **fails**, so the loop at `main.py:792` runs a second attempt (`MAX_RETRIES` default
3, `main.py:69`)

**When** the model's corrected block re-declares the same parameter

**Then**

- the user is prompted **exactly once** across the whole turn;
- attempt 2's prelude carries the **same value** as attempt 1's;
- a parameter declared for the **first time** on attempt 2 — a name not previously collected —
  prompts, and only for that name.

**And** the ordering is asserted as well as the count: collection completes **before** the
`with processing(...)` block at `main.py:830` is entered. `processing()` opens a transient Rich
`Live` region (`main.py:562-596`); an `input()` inside it contends with the renderer for the
terminal. There is exactly one point in the turn that satisfies this — between `main.py:828` and
`main.py:830` — and asserting the count alone would not catch a correct-but-misplaced prompt.

**And** the principle is not new: `main.py:762-764` already states it for embeddings — *"Retrieval
runs ONCE per turn, before the loop, so the embedding round trip is not paid per attempt."* This
criterion is the same sentence with "prompt" in place of "round trip", and it is written down
because the obvious implementation — parse and prompt at the top of each loop iteration — is
simpler, passes a single-attempt test, and asks the user for their API key three times before the
turn gives up.

**And** the cost is accepted rather than tested around: a **mistyped** value cannot be corrected
within the turn. The escape is Ctrl+C, already handled as "abort this turn only" at
`main.py:1022-1023`. There is no acceptance criterion for correcting a value mid-turn because there
is no such feature (`spec.md` §8 item 5).

---

## AC-MASK — A secret is never echoed, never printed, and never persisted to history

Covers E2, N2, N3.

**Given** a declaration `# @param api_key: secret = "OpenWeather API key"`

**When** the value is collected

**Then**

- it is read through `getpass.getpass()`, **not** `input()` — asserted at source level;
- the `getpass` prompt string contains **no `\001` or `\002`** bytes;
- the confirmation line shows a fixed mask, never the value;
- the assembled prelude is **not printed, streamed, panelled or logged** — for **any** value,
  secret or not (N2).

**And** after collection, the value is **absent from the readline history buffer** — asserted
directly against `readline`, not inferred from the choice of function.

### Both halves of this criterion protect against a cleanup, not against a bug

**The bracketing asymmetry.** `PROMPT` at `main.py:974` brackets its colour escapes with
`\001`/`\002`, and `main.py:960-973` explains at length why: readline counts every unbracketed
prompt byte as a visible column, computes every redraw from a wrong origin, and corrupts the line
the moment the user presses Up — *"The bug is invisible until the user presses an arrow key, which
is why a prompt that looks perfect can still be wrong."* That reasoning applies to the `input()`
path here verbatim.

It applies **inversely** to `getpass`. `getpass` is not readline: it writes the prompt string raw
to the terminal, so `\001` and `\002` would be emitted as literal SOH/STX control bytes rather than
interpreted. *(Reasoned from `getpass`'s documented behaviour and the mechanism at
`main.py:960-973`; not measured in a container.)* The result is two prompt paths that look
gratuitously inconsistent — one coloured and bracketed, one plain — which is exactly what invites
someone to unify them.

**The history leak is the reason unification must not happen.** `_install_history()`
(`main.py:930-957`) wires readline and registers an `atexit` writer. Any line read through
`input()` while readline is loaded enters the history buffer and is written to
`CODERUNNER_HISTORY`, which compose pins to `/home/runner/.coderunner/history`
(`docker-compose.yml:107`) — on `coderunner_app_data` (`docker-compose.yml:75`,
`docker-compose.yml:114-115`), **the volume that survives `--rm`**.

So a secret typed at an `input()` prompt would be persisted in plaintext, on the same volume as the
memory store, by a mechanism **no capture policy in this SPEC inspects**. Every policy in §4 —
including `never` — would report that nothing was stored, and would be telling the truth about the
only store it knows about.

That is why the history assertion is on the buffer rather than on the function call: the function
call is the implementation, and the buffer is the property.

---

## AC-DEGRADE — A malformed `settings.json` degrades to `never`, in one line, without an exception

Covers U4, U5, S2, S4.

**Given** `/home/runner/.coderunner/settings.json` containing

```
{ "schema_version": 1, "param_capture_policy": "sensitive_excluded"
```

— valid-looking, truncated, missing its closing brace, which is what a hand edit or an interrupted
write produces

**When** the first turn declaring a parameter resolves the capture policy

**Then**

- the effective policy is **`never`**;
- **exactly one** status line is emitted, in the style of `_warn_memory()` (`main.py:706-709`) and
  matching the convention at `product.md:138`;
- **no exception reaches the REPL** — the turn otherwise proceeds identically to a turn with a
  valid file;
- **the file is not rewritten.** It may be a typo in a deliberate edit, and overwriting it destroys
  the user's intent along with their mistake;
- the user is **not** re-asked for a choice, because a file exists — a malformed file is a broken
  setting, not an absent one.

**And** the same assertions hold for every other unusable condition, each driven separately:

| Condition | Effective policy | One line | File rewritten |
|---|---|---|---|
| Unreadable (`PermissionError`) | `never` | yes | no |
| Valid JSON, not an object (`[]`, `"x"`, `null`) | `never` | yes | no |
| Unknown `param_capture_policy` value | `never` | yes, naming the value | no |
| `schema_version` newer than known | `never` | yes | no |
| Unknown **extra** keys, otherwise valid | the file's policy | **no line** | no |
| Save fails (read-only directory) | the **chosen** policy, this session only | yes, stating it was not persisted | n/a |

**And** `/params` reports the **provenance** in every one of these cases (U5) — file, environment
override, or fallback. A policy whose origin cannot be named is a policy nobody can debug, and the
fallback and the default are **different values** precisely so that provenance is the only way to
tell them apart.

### Why the fallback is `never` and not the recommended default

`sensitive_excluded` is what a user is *offered* when asked (`spec.md` §4.5). `never` is what an
**unreadable file** falls back to. That those differ will read as a bug to whoever implements it,
so it is asserted here rather than left in a comment.

A file we cannot parse is exactly the file that might have said `never`. Falling back to
`sensitive_excluded` means capturing turns from a user who explicitly asked that they not be
captured, on the strength of a file we have just admitted we could not read. A choice made in
answer to a question carries information; a fallback carries none, and must assume the strictest
thing the missing information could have said.

The cost is real, announced, and accepted: capture stops for parameterised turns until the file is
fixed, and one line per turn says so.

### Why the save-failure row is separate from the rest

`Dockerfile:36-46` creates and chowns `/home/runner/.coderunner` before `USER runner`, so a volume
seeded by a current image is writable. But Docker seeds ownership only into an **empty** volume at
first mount: a `coderunner_app_data` created by a pre-SPEC-MEMORY-001 image stays root-owned
permanently, and `tech.md` §6.5 trap A records that this condition *"looks exactly like graceful
degradation"*.

S4 is what makes it not look like that. The chosen policy applies for the session — the user's
answer is honoured — one line states it was **not persisted**, and the question returns next launch.
A silently unsaved choice is indistinguishable from a saved one until the next container, which is
the failure this row exists to make impossible.

No ownership probe is specified. The memory store already degrades once per turn on the same
condition, and a second detector for one fault is a second thing to keep correct.

---

## AC-SETTINGS — First run asks once; precedence is unambiguous; compose is untouched

Covers E7, S3, N6, N7.

**Given** a machine with **no** `settings.json`

**When** the first turn containing a `# @param` declaration reaches the collection phase

**Then**

- the user is asked to choose a policy, **once**, immediately before the first value prompt and
  **not at startup**;
- the answer is written to `/home/runner/.coderunner/settings.json` with `schema_version: 1`;
- no later turn and no later launch asks again;
- **a session that never declares a parameter never asks and never creates the file.**

**And when** `CODERUNNER_PARAM_CAPTURE` is set to a recognised value

**Then** it overrides the file for the session, and `/params` names **the environment** as the
provenance (S3).

**And when** the file contains a key corresponding to one of the eleven environment variables
(`main.py:66-71`, `main.py:87-96`)

**Then** that key is **ignored** and one status line says so (N6). `settings.json` is not a
configuration file; `tech.md` §4 remains the description of how CodeRunner is configured.

**And**, asserted by inspection rather than by execution: **`docker-compose.yml` is unmodified.**

### Why the last assertion is by inspection, and why it is not pedantry

Every memory variable in compose is written as `${VAR:-default}` (`docker-compose.yml:82-104`),
which means the variable is **always set inside the container, always with a value**. Adding
`CODERUNNER_PARAM_CAPTURE` in that idiom — the obviously consistent thing to do — would make the
environment override permanently active. By the precedence rule at `spec.md` §4.3, the environment
wins unconditionally, so `settings.json` would be written, read, and then overruled on every single
launch: a file that exists, is correct, and does nothing.

The user's choice would appear to be saved. `/params` would report the environment as the
provenance, which is the only reason anyone would ever find out.

That is also why the env override is **Optional** (`spec.md` §4.5 O1) rather than required: kept out
of compose, it is unreachable under `./coderunner` without an explicit `docker compose run -e` —
exactly the limitation `tech.md` §4.1 already records for `OLLAMA_HOST`. An escape hatch that is
honestly documented as hard to reach is better than a convenient one that inverts the design.

### The first-run timing, and what it costs

Asking lazily means the question interrupts a turn that is already in flight, between the reasoning
stream and execution. Asking at startup would be tidier for that one turn and would impose a
question about solution memory on **every** user of the product, the overwhelming majority of whom
will never declare a parameter — and would create `settings.json` on every machine.

Since that file reverses a documented property (`tech.md:204-207`), the smallest honest version of
the reversal is the one where **the file only exists for users who used the feature that requires
it.** The interruption is mitigated by asking the question in the same block as the value prompts,
so the user experiences one interaction rather than two.

---

## AC-FUTURE — A `from __future__` import survives the prelude

Covers U1's mechanics; recorded because **this SPEC creates the hazard**.

**Given** an extracted block whose first statement is `from __future__ import annotations`

**When** a prelude is assembled and prepended

**Then**

- the prelude is inserted **after** the `__future__` import, and the script runs;
- with no `__future__` import present, the prelude is inserted **before** all code, immediately
  after `SCRIPT_HEADER` (`main.py:422-431`);
- comments, a leading docstring and blank lines before the `__future__` import do not defeat the
  detection.

### The measurement

Measured 2026-08-06. A file whose first statement is an assignment and whose second is
`from __future__ import annotations`:

```
rc = 1
SyntaxError: from __future__ imports must occur at the beginning of the file
```

This cannot happen today: `SCRIPT_HEADER` is comments only, and comments are not statements. The
hazard is **introduced by this SPEC**, which is why it carries a criterion rather than a note. The
impact is total — the script does not run at all, and the model is handed a `SyntaxError` for code
it wrote correctly, then burns its remaining attempts at `main.py:792` "fixing" it.

The probability is low: `main.py:136` asks for self-contained scripts and the model has not been
observed emitting `__future__` imports. Low probability and total impact is the profile that gets
shipped untested, so it is written down.

---

## Success criteria and quality gates

### Gates

| Gate | Enforced by | Threshold |
|---|---|---|
| Literal safety | **AC-INJ** | Hostile value round-trips as data; `params.py` has exactly one emission site |
| Extraction integrity | **AC-SYN** | Declarations never produce an empty extracted block |
| stdin untouched | **AC-STDIN** | No `stdin=` in `main.py:461-468`, asserted at source level |
| Capture isolation | **AC-CAP** | `code` passed to `_capture_turn()` is **identical** to the object from `main.py:825` |
| Per-file coverage | `conftest.py:195-225` — **never restated in YAML** (SPEC-CI-001 N5) | `memory.py` 100%, `recall.py` 100%, `vectorstore.py` ≥ 85%, **`params.py` 100%**, **`settings.py` 100%** (`conftest.py:187-192`) |
| Coverage measurement | `pytest.ini:38-45` | `--cov=params` and `--cov=settings` present; absent, `conftest.py:206-209` fails the session with `coverage unavailable` |
| Test count | `.github/workflows/ci.yml:268` | `skipped == 0`, `passed >= MIN_PASSED`, **measured** after T10, raised from 296 |
| Lint | SPEC-CI-001 AC-4 | `ruff check .` zero findings, ruff 0.16.1 |
| `main.py` coverage | **not gated, by design** | Inherited from `.moai/specs/SPEC-MEMORY-001/acceptance.md` and SPEC-CI-001 §6 item 7. `spec.md` §5.3 states the consequence and confines `main.py`'s share to wiring |

### Verification status

| Criterion | Status | Discharged by |
|---|---|---|
| AC-INJ | **not verified** — the underlying injection is **measured** (2026-08-06); the defence is not built | T2, T10 |
| AC-SYN | **not verified** — the regex collision is **measured** (2026-08-06); the grammar is not built | T1, T9, T10 |
| AC-STDIN | **not verified** — the `EOFError` is **measured** (2026-08-06); the container blocking case is reasoned, not measured | T9, T10 |
| AC-CAP | **not verified** | T5, T8, T10 |
| AC-ONCE | **not verified** | T5, T10 |
| AC-MASK | **not verified**; the `getpass` bracketing reasoning is **not measured in a container** | T6, T10 |
| AC-DEGRADE | **not verified** | T3, T10 |
| AC-SETTINGS | **not verified** | T7, T10 |
| AC-FUTURE | **not verified** — the `SyntaxError` is **measured** (2026-08-06); the guard is not built | T2, T10 |

### Definition of done

1. `params.py` and `settings.py` exist, are stdlib-only, and are gated at **100%** in **both**
   `pytest.ini:38-45` and `conftest.py:187-192`.
2. AC-INJ through AC-FUTURE have each been **observed passing** — not inferred from a green suite.
3. **AC-INJ and AC-CAP have each been observed FAILING at least once**, deliberately, against a
   knowingly-broken implementation: an f-string interpolation for AC-INJ, and `code = prelude + code`
   for AC-CAP. Both of those are green under every other test in the repository, which is the whole
   reason they have criteria. *A gate never observed failing is not known to be a gate.*
4. The manual model check in T9 has been run against real turns, and the **observed hit rate** of
   the `# @param` syntax is recorded. If it is poor, the fix is the prompt (`plan.md` R1), not a
   looser grammar.
5. `MIN_PASSED` at `.github/workflows/ci.yml:268` has been raised to a number **taken from a real
   run**, not computed from an expected delta. A computed floor cannot catch tests that stopped
   being collected, which is what the floor is for.
6. `tech.md:204-207` records the `settings.json` reversal and the reason a file is right here where
   environment variables are not; `tech.md` §7.2 records stdout redaction **with its stated
   limits**; `product.md` §4 carries the new feature and §6 the residual leak; `README.md`
   documents `# @param` and the three policies.
7. **No claim anywhere states or implies that secrets are not stored.** `sensitive_excluded`
   reduces exposure by exact-substring redaction and cannot see a transformed value
   (`spec.md` §3.6, `plan.md` R5). `never` is presented as the option for users who need a
   guarantee, not as the paranoid choice.
8. `docker-compose.yml` is unmodified (N7), and the reason is recorded where the next person to
   reach for it will look.
