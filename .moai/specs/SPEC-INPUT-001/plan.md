# SPEC-INPUT-001 — Implementation Plan (v1.0.0)

> Requirements are in `spec.md`. Acceptance criteria are in `acceptance.md`.

## 0. Starting position

Everything this feature needs already exists except the feature. What is unusual about the starting
position is how much of the design is **already enforced by the code** and merely needs to be
prevented from eroding.

| Present | Evidence |
|---|---|
| A prohibition on `input()` with a measured justification | `main.py:136`; measurement M1 (`spec.md` §1) |
| A code extractor whose failure mode is silent and measured | `main.py:414`, `main.py:417-419`, `main.py:825-828`; measurement M2 |
| A capture path that receives the **extracted** block, not the executed script | `main.py:825` → `main.py:860-869` |
| A once-per-turn precedent for expensive per-turn work, with the rationale written at the site | `main.py:762-764` |
| A persistent volume that survives `--rm`, correctly owned by `runner` | `docker-compose.yml:75`, `docker-compose.yml:114-115`, `Dockerfile:36-46` |
| A one-line degradation convention with an existing implementation to copy | `product.md:138`; `_warn_memory()` at `main.py:706-709` |
| A per-file coverage gate that fails loudly when a module is added to it but not to `--cov` | `conftest.py:187-192`, `conftest.py:206-209`, `pytest.ini:38-45` |
| Live CI on `main` asserting `skipped == 0` and `passed >= MIN_PASSED` | `.github/workflows/ci.yml:268` |

So this is not a "build a subsystem" plan. Three of the ten tasks are new modules; the rest is
wiring, and **two of the tasks exist only to stop an existing property from being lost** (T5, T9).

**One thing to be clear-eyed about before starting.** The riskiest code in this SPEC is about
forty lines: the prelude renderer in `params.py`. Everything else is UX and bookkeeping. Budget
attention accordingly — the coverage floor on `params.py` is 100% for that reason
(`spec.md` §5.2), and T10 is where the value is.

---

## 1. Task decomposition

Eleven tasks. All are automated; none requires a manual settings change.

| # | Task | Artefact | Depends on |
|---|---|---|---|
| **T1** | **Write `params.py`: the grammar and the parser.** `# @param <name> : <str\|int\|float\|secret> = "<prompt>"`, matched only inside an extracted code block, `name` restricted to `[A-Za-z_][A-Za-z0-9_]*`. Return an ordered list of declarations, deduplicated by name, first occurrence wins. Malformed lines are **skipped, not fatal** (O4) — a bad declaration becomes a `NameError` from the script, which the loop at `main.py:872-884` already handles. **Do not use `ast` to find these**: the declarations are comments, which `ast.parse` discards, and reaching for the tokeniser to recover them is more machinery than a line-oriented scan deserves. | `params.py` | — |
| **T2** | **Write `params.py`: the literal-safe renderer.** `render_prelude(values) -> str`, one assignment per line, every value emitted through `repr()` (or `json.dumps()` for the string cases; pick one and use it everywhere). **The function must not be capable of interpolation** — it should never build a quoted literal by hand, so that there is no code path a future edit could route a raw value through. Include the `from __future__` guard from R4. | `params.py` | T1 |
| **T3** | **Write `settings.py`.** Load `/home/runner/.coderunner/settings.json`; resolve the policy through `CODERUNNER_PARAM_CAPTURE` → file → default; return the policy **with its provenance** (U5). Implement every row of `spec.md` §4.4 — absent, unreadable, malformed, not-an-object, unknown value, unknown extra keys, future `schema_version`, write failure — each degrading to `never` with exactly one message, and **never rewriting a file it could not parse**. Save is a separate function returning success/failure so that S4 can distinguish "chosen" from "persisted". | `settings.py` | — |
| **T4** | **Admit both modules to the coverage gate.** Add `--cov=params` and `--cov=settings` to `pytest.ini:38-45`, and `"params.py": 100.0` / `"settings.py": 100.0` to `PER_FILE_COVERAGE_TARGETS` at `conftest.py:187-192`. **Both edits or neither**: with the conftest entry alone, `cov.report(include=["params.py"])` raises and `conftest.py:207-209` fails the session with `coverage unavailable`. That is the right direction to fail in and it will happen to whoever does this in one step instead of two. | `pytest.ini`, `conftest.py` | T2, T3 |
| **T5** | **Wire collection into `agentic_turn()`.** Parse declarations from the extracted `code` immediately after `main.py:825-828`; if any, resolve the policy (asking on first run, T7); collect values into a dict local to the turn; reuse that dict on attempts 2 and 3 (`main.py:792`), prompting only for names not already held. **The collection must sit before the `with processing(...)` at `main.py:830`** — S5, because a prompt inside a transient `Live` region (`main.py:562-596`) fights the renderer for the terminal. **`code` must not be reassigned.** The prelude is passed to `run_python()` as a separate argument; the object handed to `_capture_turn()` at `main.py:860-869` stays exactly the object returned at `main.py:825`. This is the task where U3/N4 are won or lost, and losing them is invisible. | `main.py` | T2, T3 |
| **T6** | **Wire the prompts.** Non-secret values through `input()` with a `\001`/`\002`-bracketed coloured prompt in the style of `PROMPT` (`main.py:974`), for the reason set out at `main.py:960-973`. Secret values through `getpass.getpass()` with a **plain, unbracketed** prompt — `getpass` is not readline and would emit the brackets as literal control bytes. One batch announcement line, one confirmation line per parameter, secrets masked. **The prelude is never printed** (N2). | `main.py` | T5 |
| **T7** | **Wire `settings.py` into the REPL: first-run question and `/params`.** Ask lazily, on the first turn carrying a declaration, immediately before the first value prompt — **never at startup**, so a user who never uses the feature is never asked and no file is ever created for them. Dispatch `/params` and `/params capture <1\|2\|3>` beside `/memory` at `main.py:1013`, never reaching `agentic_turn()`. `/params` reports the policy **and its provenance**. If stdin is not interactive the question cannot be asked: fall back to `never`, one line, write nothing. | `main.py` | T3, T5 |
| **T8** | **Wire redaction at all three sinks.** Under `sensitive_excluded`, redact every `secret` value by exact substring from `result.stdout` and `result.stderr` before they reach `show_exec_result()` (`main.py:833`), the feedback strings (`main.py:838-842`, `main.py:878-884`), and `_capture_turn()` (`main.py:860-869`). Under `never`, skip `_capture_turn()` entirely for any parameterised turn **and say so in one line** — S1, because silence there is indistinguishable from a successful capture. Under `always`, do neither. **One helper, three call sites**; three helpers is three chances to update two of them. | `main.py`, `params.py` | T5, T7 |
| **T9** | **Amend `SYSTEM_PROMPT` at `main.py:136`.** The line becomes: `input()` still forbidden, `# @param` documented as the sanctioned alternative, with **one** worked example inside the fence. Keep it short — this prompt is already 50 lines and every line competes for an 8B model's attention. **Do not delete the prohibition**; M1 is why it is there. Then re-verify by hand that the model actually emits the syntax: an unusable declaration format is a failed feature no test will catch, because every test will use a hand-written fixture. | `main.py` | T1 |
| **T10** | **Tests, including the two that exist to catch silent regressions.** The full set is in `acceptance.md`; two deserve naming here. **(a) AC-INJ** — feed `'Seoul"; import os; os.system("id"); x="'` and a newline-bearing value through the real prelude path and assert the value arrives as **data**, by comparing the round-tripped value, not by asserting the absence of a crash. **(b) AC-CAP** — assert that the object passed to `_capture_turn()` is the object returned by `extract_last_python_block()`, so that a future "tidy-up" merging the prelude into `code` fails a test instead of quietly persisting secrets. | `tests/test_params.py`, `tests/test_settings.py`, `tests/test_main_integration.py` | T4, T5, T6, T7, T8 |
| **T11** | **Raise `MIN_PASSED` and document.** `.github/workflows/ci.yml:268` currently reads `MIN_PASSED = 296`; set it to the count measured after T10 lands. **Measure it, do not compute it** — the floor exists to catch tests that stopped being *collected*, and a floor derived by arithmetic from an expected delta cannot do that. Then: `tech.md:204-207` records the `settings.json` reversal and why a file is right here (`spec.md` §4.1); `tech.md` §7.2 gains stdout-under-`sensitive_excluded` as a partial mitigation with its **stated limits** (§3.6); `product.md` §4 gains the feature and §6 gains the residual leak; `README.md` documents `# @param` and the three policies. Fix the two stale citations noted at `spec.md` §2.2 (`tech.md` §4.1's `main.py:65-95` and `docker-compose.yml:100`) in the same pass. | `.github/workflows/ci.yml`, `tech.md`, `product.md`, `README.md` | T10 |

### 1.1 Dependencies and critical path

```
T1 ── T2 ──┬── T4 ──┐
           │        │
           ├── T5 ──┼── T6 ──┐
           │        │        │
T3 ────────┴── T7 ──┴── T8 ──┴── T10 ── T11
                                  │
T1 ── T9 ─────────────────────────┘
```

**Critical path: T1 → T2 → T5 → T8 → T10 → T11.**

`T3` (settings) is independent of `T1`/`T2` (params) and should be written in parallel — they share
no code and only meet at `T7`. `T4` is a two-line edit that can land any time after both modules
exist, and landing it **early** is better: it turns "we forgot a test" into a red suite immediately
rather than at T10. `T9` hangs off `T1` only because the prompt has to document the grammar the
parser accepts, and it joins at T10 because the manual model check belongs with the other
verification.

**T5 is the convergence point and the one to review hardest.** It is where `code` could be
reassigned and where U3/N4 stop holding — silently, with every test still green except the one
written to catch exactly that.

### 1.2 Priority

| Priority | Tasks | Rationale |
|---|---|---|
| **High** | T1, T2, T5, T8, T10 | The renderer is a code-execution surface (`spec.md` §3.2, M3); T5 is where the structural capture property is preserved or lost; T10 is the only thing that makes either claim checkable |
| **Medium** | T3, T4, T7, T9 | The policy machinery matters, but a wrong policy leaks data that a right renderer already kept out of `code`. T9 decides whether the feature is *usable*, which is a different axis from whether it is *safe* |
| **Low** | T6, T11 | T6 is UX with one sharp edge (the `getpass` bracketing, and the readline-history leak N3 closes). T11 is necessary for the work to hold and nothing depends on it |

Primary goal: T2 and T5 landing with AC-INJ and AC-CAP green. Secondary goal: T7/T8 with
AC-DEGRADE green. Final goal: T11. No optional goals — every task listed is required.

---

## 2. Technical approach — the four decisions worth defending

### 2.1 The prelude is assembled inside the execution path, not merged into `code`

This is the single most consequential implementation choice and it is worth restating as code
shape rather than as a requirement.

`run_python()` writes `SCRIPT_HEADER + "\n" + code + "\n"` at `main.py:447-448`. The change is to
give it a second argument — `run_python(code, prelude=...)` — and write
`SCRIPT_HEADER + "\n" + prelude + code + "\n"`. It is **not** to build a combined string in
`agentic_turn()` and pass that.

The difference looks cosmetic and is not. `agentic_turn()` passes `code` to `_capture_turn()` at
`main.py:860-869`; if the combined string is built there, the natural next edit is to pass the
combined string, and injected values start persisting to `coderunner_app_data` in plaintext where
any later generated script can read them (`tech.md` §7.2). Keeping the assembly inside
`run_python()` means there is **no variable in `agentic_turn()`'s scope** that contains a user
value alongside code. The property is then enforced by the absence of a thing, which is the only
kind of enforcement that survives refactoring.

### 2.2 The renderer must be incapable of interpolation

`render_prelude()` should never construct a quoted literal. Not "should avoid" — should be
structurally unable to, so that there is no path through the function that a raw value could take.
One line per value, each of the form `name = <repr>`, with `<repr>` produced by exactly one call
site.

The reason is M3 (`spec.md` §1): the difference between the safe and unsafe versions is one
character — `{value}` versus `{value!r}` — inside an f-string that reads correctly either way. A
reviewer will not catch it, and a test that only asserts "the script ran" will not either. AC-INJ
catches it; a renderer with one emission site means there is only one line for AC-INJ to be
protecting.

### 2.3 The conservative fallback is `never`, and it is not the default

`spec.md` §4.4 sets the fallback for every unusable-file condition to `never`, while the
recommended default for a user who is *asked* is `sensitive_excluded`. Those being different values
is deliberate and will look like a bug to whoever implements it, so:

A file we cannot read is exactly the file that might have said `never`. Defaulting an unreadable
file to `sensitive_excluded` means capturing turns from a user who explicitly asked that they not
be captured, on the strength of a file we have just admitted we cannot parse. A default chosen by
a user in answer to a question carries information; a fallback carries none, and must therefore
assume the strictest thing the missing information could have said.

The cost is real and is announced: capture stops for parameterised turns until the file is fixed,
and one status line per turn says so.

### 2.4 Ask lazily, not at startup

The alternative — resolve the policy in `repl()` before the first prompt — is simpler and is wrong
in one specific way: it imposes a question about solution memory on every user of the product, the
overwhelming majority of whom will never declare a parameter, and it creates `settings.json` on
every machine. Since introducing that file reverses a documented property (`tech.md:204-207`), the
smallest honest version of the reversal is one where **the file only exists for users who used the
feature that needs it**.

Cost: the question interrupts a turn that is already in flight, between the reasoning stream and
execution. Mitigated by asking it in the same block as the value prompts, so the user experiences
one interaction rather than two.

---

## 3. Risks and mitigations

| # | Risk | Assessment | Mitigation |
|---|---|---|---|
| **R1** | **`llama3.1:8b` does not reliably emit the declaration syntax.** The whole feature routes through a 50-line system prompt (`main.py:101-152`) competing for an 8B model's attention, and the failure is not an error — the model just writes `input()` or hard-codes a placeholder, and the turn fails in an ordinary-looking way. | **The highest-probability failure in this SPEC**, and the only one no unit test can detect: every test will use a hand-written fixture that has the syntax right by construction. | **T9 includes a manual model check as an explicit deliverable, not a formality.** Drive real turns that need a value and count how often the syntax comes out right. If it does not, the fix is prompt engineering — one worked example inside the fence, matching the CODE-protocol example already at `main.py:113-118` — not a looser grammar. A grammar loose enough for an unreliable model is a grammar with ambiguous parses. |
| **R2** | **The prelude approach is chosen over environment injection on reliability grounds, and reliability is the thing R1 says is uncertain.** If R1 bites, the argument at `spec.md` §3.7 for preferring the prelude weakens at exactly the moment its safety argument matters most. | Coupled to R1, and worth naming rather than leaving as an unstated dependency between two decisions. | Environment injection is **specified as the designated fallback** (`spec.md` §8 item 2). It removes the injection class outright rather than mitigating it. If T9's manual check shows the model handles `os.environ["CITY"]` more reliably than a bare name — which would be surprising — the decision flips on measured evidence and `spec.md` §3.7 is amended rather than argued with. |
| **R3** | **`code` gets reassigned in `agentic_turn()`.** The tidy version — `code = prelude + code` — is one line, reads better than threading a second argument through `run_python()`, and silently starts persisting user-typed secrets to `coderunner_app_data` where `tech.md` §7.2 says any later generated script can read them. | **Certain over a long enough window.** It is the refactor a competent reviewer would *suggest*. | §2.1 keeps assembly inside `run_python()` so no combined variable exists in the caller's scope; **AC-CAP asserts object identity**, so the tidy version fails a test rather than a review. Both, because either alone is one careless afternoon from being undone. |
| **R4** | **A prelude in front of `from __future__` is a `SyntaxError`.** Measured 2026-08-06: a file whose first statement is an assignment and whose second is `from __future__ import annotations` fails with *"from `__future__` imports must occur at the beginning of the file"*. **This SPEC creates the hazard** — `SCRIPT_HEADER` (`main.py:422-431`) is comments only, so it does not exist today. | Low probability, total impact: the script does not run at all and the model is handed a `SyntaxError` for code it wrote correctly. `main.py:136` asks for self-contained scripts and has never been observed producing a `__future__` import. | **T2 scans the extracted block for a leading `from __future__` import** — after comments, docstring and blank lines — and inserts the prelude **after** it if present, before it otherwise. Ten lines, and it converts a total failure into a non-event. Covered by an acceptance scenario so it is not carried as an untested claim. |
| **R5** | **`sensitive_excluded` is trusted further than it can carry.** Substring redaction cannot find a value the script transformed before printing: base64, a hash, `token[:8]`, a URL-encoded key. The policy reduces exposure; it does not eliminate it. | Certain, and the risk is **documentation** rather than code: a `README` line reading "secrets are not stored" would be false and would be believed. | `spec.md` §3.6 states the limit in the requirement itself. **T11 must carry that sentence into `tech.md` §7.2 and `README.md` unsoftened**, and `never` must be presented as the option for users who need the guarantee rather than as the paranoid choice. An overstated safety claim is worse than no claim, because it is acted on. |
| **R6** | **The readline history leak reopens.** N3 routes secrets through `getpass` because `input()` under readline (`main.py:930-957`) writes the line to `CODERUNNER_HISTORY`, pinned to `/home/runner/.coderunner/history` on the persistent volume (`docker-compose.yml:107`). A later "unify the two prompt paths" cleanup would restore the leak — into a file **no capture policy inspects**. | The two prompt paths look gratuitously different (one bracketed and coloured, one plain), which is precisely what invites unification. | The asymmetry is **documented at the call site** with the `getpass`-is-not-readline reason and the history-volume reason, both. An acceptance scenario asserts a secret value is absent from the readline history buffer after collection. |
| **R7** | **A root-owned `coderunner_app_data` makes the settings write fail, and the failure looks like a decision.** `Dockerfile:36-46` prevents this for volumes seeded by a current image, but Docker seeds ownership only into an **empty** volume at first mount: a volume created before `Dockerfile:43-44` landed stays root-owned forever. `tech.md` §6.5 trap A records that this is indistinguishable from graceful degradation. | Live on any machine that ran a pre-SPEC-MEMORY-001 image. On such a machine the memory store is already failing for the same reason. | **S4 makes the two cases distinguishable**: the chosen policy applies for the session, one status line states it was **not persisted**, and the user is asked again next launch. The plan does **not** add an ownership probe — the store's own per-turn degradation line already reports that condition, and a second detector for the same fault is a second thing to keep correct. |
| **R8** | **`MIN_PASSED` blocks the merge, or is raised wrongly.** `.github/workflows/ci.yml:268` holds 296; T10 adds tests, so CI is red between T10 and T11. Worse, a floor **computed** from an expected delta rather than measured defeats the check: its purpose is to catch tests that stopped being *collected*, which arithmetic cannot see. | Certain, and trivially handled if anticipated. Non-trivially wrong if not. | **T11 measures the count from a real run and writes that number.** T10 and T11 land together or the branch is knowingly red in between. `acceptance.md`'s definition of done requires the number to be sourced from a run. |
| **R9** | **Two new modules at 100% coverage make the gate expensive to satisfy and tempting to soften.** `params.py` and `settings.py` bring the gated set to five files, and `settings.py`'s eight degradation branches (`spec.md` §4.4) all need driving. | The realistic pressure point. The first person under a deadline will propose 85% for `settings.py`. | The floors are worth what they cost **because the branches being forced are the failure paths** — the ones that ship looking healthy, which is the family `tech.md` §6.5 exists to catalogue. Both modules are stdlib-only with no external dependency, so there is no line in either that a test cannot reach; unlike `vectorstore.py`, they have **no excuse** for 85%. If a floor is ever lowered, it should be by an amendment to this SPEC that says which branch is going untested and why. |

---

## 4. Follow-up notes

- **`tech.md` §4's opening sentence needs rewriting, not patching.** It currently makes an absolute
  claim (`tech.md:204-207`) that will be false the moment `settings.py` lands. Adding "…except
  `settings.json`" produces a sentence that reads like an exception when the honest version is a
  distinction: **configuration** is environment-based; **a user's persisted interactive choice** is
  not configuration and does not belong in an environment variable. T11 owns it.
- **`product.md` §4 is a numbered list of twenty features** (`product.md:113-138`). This adds the
  twenty-first, and it is the first that asks the user a question mid-turn. Worth stating in the
  feature line, because it is a new interaction category rather than a new capability.
- **The `# @param`-in-recalled-records annoyance has no fix at the store layer** (`spec.md` §3.1,
  cost 2). If it turns out to be common in practice, the place to address it is
  `format_recall_block()` (`memory.py:383`), by stripping declaration lines from the recalled
  code before it is shown to the model. That would be a small amendment to SPEC-MEMORY-001's
  formatting, not to this SPEC, and it should not be pre-emptively built.
- **`spec.md` §3.7's rejected alternative should be re-read, not just remembered, if AC-INJ ever
  fails.** Environment injection removes the injection class rather than mitigating it. The
  decision against it rests on one measured-in-future claim about model reliability (R1), and it is
  the only decision in this SPEC that is expected to be revisited.
