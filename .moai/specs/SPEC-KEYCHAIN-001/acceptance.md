# SPEC-KEYCHAIN-001 — Acceptance Criteria (v1.0.0)

> Requirements are in `spec.md`. Implementation detail is in `plan.md`.

**Status at authoring:** nothing here has been implemented. Every measurement quoted below was taken
**2026-08-07** against this host (macOS arm64, `/bin/bash` 3.2.57, `security` at `/usr/bin/security`)
and the image `coderunner-ai:latest` (`sha256:0df09685…`). Those measurements are real. The criteria
built on them are **specified, not verified**.

Three of these criteria exist because a plausible implementation is green while doing the wrong
thing, and they are the ones to read first:

- **AC-POLICY** — a turn whose values all came from the keychain looks identical whether the capture
  policy was resolved or silently skipped. The difference is a secret in plaintext on a persistent
  volume.
- **AC-TRANSPORT** — the transport that *looks* safer silently deletes characters from the
  credential, and a fixture without a `$` in it passes under both.
- **AC-LAUNCH** — the failure breaks every user who has **not** used the feature, on an interpreter
  most developer machines do not have.

And one exists for the opposite reason. **AC-EXPOSE asserts that this feature leaks**, on purpose, so
that the limitation `spec.md` §4 states in prose is a thing the suite has looked at rather than a
thing the suite was written around.

---

## AC-EXPOSE — The documented exposure is verified, not merely written down

Covers U6 and the whole of `spec.md` §4. **This criterion asserts a leak.**

**Given** a secret stored with `./coderunner --set-secret api_key`, and a session launched normally
so that the launcher passes `-e CODERUNNER_SECRET_API_KEY`

**When** the session is running and the container `coderunner` exists

**Then**

- `docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' coderunner` **prints
  `CODERUNNER_SECRET_API_KEY=<the value>` in plaintext**, and the assertion is on **the value**, not
  on the presence of the variable name;
- inside the container, `/proc/1/environ` **contains the value**, and a process running as `runner` —
  which is what generated code is — **can read it**;
- after `os.environ.pop()` at import (E3), a child started by `run_python()` reads **`None`** from
  `os.environ` for that name — the pop is asserted to work **and** asserted not to be enough;
- the container is `--rm` (`coderunner:263`, `docker-compose.yml:109`), so after the session ends
  `docker inspect coderunner` **fails**: the exposure is transient, and that is asserted too.

**And** the corresponding documentation assertion, in the family of
`tests/test_source_seam.py`: `README.md` and `tech.md` §7.2 each contain the `docker inspect`
statement, and **no** file in the repository contains a sentence asserting that this feature makes a
secret private, secure, or hidden.

### Why a criterion asserts a leak

`spec.md` §4.1 says the environment route removes three things, retains one, and adds one. The
removals and the retention are ordinary and nobody will get them wrong. The **addition** is the whole
cost of the feature, it is the reason the SPEC is priority `LOW`, and it is the kind of claim that
rots: someone adds `--env-from-file`, or a future compose version stops recording `Config.Env` the
same way, and the paragraph in the `README` quietly stops describing the program.

**A limitation that is documented but never executed is a limitation that drifts.** This criterion is
the only thing in the repository that will notice.

### The measurements this is built on

Measured 2026-08-07:

```
$ docker run -d -e MY_SECRET=hunter2 … coderunner-ai:latest
$ docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' <id> | grep -i secret
MY_SECRET=hunter2

$ docker exec <id> sh -c 'tr "\0" "\n" < /proc/1/environ | grep -i secret; id'
MY_SECRET=hunter2
uid=1000(runner) gid=1000(runner) groups=1000(runner)
```

And, separately, on whether popping helps:

| Route, after `os.environ.pop("KC_PROBE")` | Result |
|---|---|
| `python -I` child reading `os.environ` | **`None`** — closed |
| `/proc/self/environ` of the parent | **still present** — not closed |
| `/proc/1/environ`, read by a `-I` child | **still present** — not closed |
| `/proc/1/comm` under `--init` | `docker-init`, and its environ carries the value |

The pop is worth its one line and it is not a fix. Both halves are asserted, because asserting only
the first is how "we remove it from the environment" ends up in a `README`.

---

## AC-SOURCE — A keychain value takes the same path as a typed one

Covers U1, U2, E3, E4, S2, S3, N2.

**Given** `CODERUNNER_SECRET_API_KEY` present in the environment at `main.py` import, and a turn
whose extracted block declares `# @param api_key: secret = "OpenWeather API key"`

**When** the turn reaches `_collect_params()` (`main.py:849-869`)

**Then**

- `ask` is **never invoked** for `api_key` — asserted by spying on the callable passed to
  `params.collect_values()` (`params.py:184-207`), not by asserting the absence of output;
- `values["api_key"]` holds the value **before** `params.collect_values()` is called, so the skip at
  `params.py:201-203` is what does the work and no new branch was added to `params.py`;
- the value reaches the script through `params.render_prelude()` (`params.py:327-342`) and
  `params.splice_prelude()` (`params.py:372-390`) as a `repr()`-produced literal — **the same single
  emission site** (`params.py:309-324`) a typed value uses;
- `code` is **not reassigned**: the object handed to `_capture_turn()` at `main.py:1030` is the
  object returned by `extract_last_python_block()` at `main.py:958`, asserted by **identity**, exactly
  as SPEC-INPUT-001's AC-CAP requires;
- `_collect_params()` returns **`pending`**, including the sourced declaration, so `main.py:974`
  accumulates it into `param_declared` and `params.secret_values()` (`params.py:398-413`) at
  `main.py:987` includes it in the redaction set.

**And** the three exclusions, each driven separately:

| Case | Expected |
|---|---|
| Declaration type is `str`, matching variable exists (S3) | **prompted**. One predicate governs the mask, the redaction set, `getpass` and the policy gate; keychain sourcing joins it rather than adding a second |
| Name already in the turn's value cache from attempt 1 (S2) | the **cached** value is used on attempt 2, not the keychain's |
| Variable exists but is the empty string (U3) | **prompted**. An empty secret is not a secret |

**And** the prompt is unchanged: `main.py:140-148` still instructs `# @param` and a bare name, and
**contains no mention of `os.environ`, a keychain, or a variable** (N2). The model must not learn
that this feature exists — asserted by inspection of the prompt text, in the family of
`tests/test_source_seam.py:297-311`.

### Why identity is asserted again here

SPEC-INPUT-001's AC-CAP asserts that `code` reaching `_capture_turn()` is the object from
`extract_last_python_block()`, so that `code = prelude + code` fails a test instead of quietly
persisting secrets. That property is **not** re-derived by this SPEC — it is **inherited**, and the
inheritance is the point.

A keychain-sourced secret is a secret the user never typed and may never think about again. It is
therefore the value most likely to be forgotten in a refactor, and the property protecting it is one
this SPEC did not build. Re-asserting it under a keychain fixture costs one test and makes the
inheritance explicit rather than assumed.

---

## AC-POLICY — The capture policy is resolved even when nothing is prompted

Covers S1. **This is the AC-CAP-shaped criterion of this SPEC.**

**Given** a machine whose `settings.json` selects `sensitive_excluded`, and a turn declaring exactly
one `# @param api_key: secret = "…"` whose value is supplied entirely from the keychain — so that
**nothing is prompted at all**

**When** the turn runs to completion and the script prints the secret to stdout

**Then**

- `settings.ensure_policy()` (`settings.py:346-375`) **was called** — asserted by spying on the call,
  not by observing its effect;
- `param_session.policy` is **not `None`**, so `main.py:981` resolves to `sensitive_excluded` rather
  than `""`;
- the redaction gate at `main.py:988` is **true** and the secret is replaced by
  `params.REDACTION_MARKER` (`params.py:223`) in `result.stdout` **before** it reaches
  `show_exec_result()` (`main.py:995`), the feedback splice (`main.py:1000-1004`) and
  `_capture_turn()` (`main.py:1030`);
- the secret appears **nowhere** in the arguments passed to `remember_success()`.

**And** the same turn under the `never` policy: `_capture_turn()` is **not called**, and the status
line at `main.py:1026-1028` is emitted — because silence there is indistinguishable from a successful
capture.

**And** the surprise is asserted rather than avoided (R8): on a machine with **no** `settings.json`,
the same turn **asks the first-run question** (`settings.py:290-296`) even though the user typed
nothing. That is correct — the policy governs capture, not prompting — and it is asserted so that
nobody "fixes" it by making resolution conditional again.

### The chain this criterion protects, written out

The wrong implementation is one line different from the right one: resolving the policy inside the
block that prompts, rather than the block that has pending declarations.

```
_resolve_param_policy() not called
  -> param_session.policy is None
  -> main.py:981   policy == ""
  -> main.py:988   policy == settings.POLICY_SENSITIVE  ->  False  ->  no redaction
  -> main.py:1026  policy == settings.POLICY_NEVER      ->  False  ->  capture proceeds
  -> _capture_turn() persists stdout containing the secret, in plaintext, to
     coderunner_app_data, which tech.md 7.2 states any later generated script can read
```

Nothing in that chain raises, warns, or prints. The panel is green, the answer streams, the turn is
captured as solved. **Every test in the repository passes**, because before this SPEC there was no
such thing as a turn that declares a parameter and supplies it without asking — the combination did
not exist, so nothing tests it.

### Why the assertion is on the call and not on the redaction

An assertion on the redacted output passes whenever the fixture's script happens not to print the
secret — which is what a fixture written to test "the value arrives correctly" naturally does. The
call is the property; the redaction is one of its consequences. Both are asserted, but the call is
the one that cannot be satisfied by a well-behaved fixture.

---

## AC-DEGRADE — Every keychain fault ends in a prompt, and never in a failure

Covers U3, U4, S4, S5.

**Given** each condition below in turn

**When** the launcher runs

**Then** the affected names are not passed, the session starts normally, and the container prompts
exactly as it does today.

| Condition | Driven by | Names passed | Line | Session |
|---|---|---|---|---|
| No keychain client on `PATH` | `PATH` stripped of `security`/`secret-tool` | none | one yellow | starts |
| No registry item — a user who has never used the feature | fresh keychain | none | **none** | starts, byte-for-byte as today |
| Registered name with no item (drift) | measured **rc 44**, `SecKeychainSearchCopyNext: The specified item could not be found in the keychain.` | **all the others** | one yellow naming that name | starts |
| Keychain locked | measured **rc 128**, stdout empty | none | one yellow | starts |
| User cancels the OS prompt | non-zero rc, stdout empty | none | one yellow | starts |
| Item exists, value empty | rc 0, stdout empty | none | one yellow | starts |
| `CODERUNNER_KEYCHAIN=0` | environment | none, and nothing is probed | one yellow | starts |

**And** the predicate is asserted as **one rule, not seven**: a name is supplied **only if** the
client exits `0` **and** prints a non-empty value. Both conditions, asserted together, so that a
failure mode nobody has met yet — a future `security` returning 0 with a diagnostic on stdout, a
client that prints a trailing newline and nothing else — lands in the same branch as the two that
were measured.

**And** per-name isolation is asserted directly (S5): with three registered names of which the middle
one is missing, the first and third **are** passed. A loop that aborts on the first failure passes a
one-name test and silently disables the feature for anyone with a stale registry entry.

**And** the failure is **not repaired**: a name whose item cannot be read is **still in the registry**
afterwards, and `--list-secrets` still shows it. Pruning on a failed read would delete a registration
because the keychain happened to be locked.

### Why the registry-absent row emits no line

Every other row is a fault. That one is a **state** — it is what every user who has never run
`--set-secret` looks like, which on the day this ships is every user. A yellow line there would appear
on every launch of every session for everybody, and `product.md:138`'s convention is one line **per
fault**, not one line per absence of an opt-in feature.

The distinction is worth asserting because the two are one `if` apart in the implementation and the
wrong side of it turns a status convention into furniture.

---

## AC-TRANSPORT — The value arrives intact, and not through the flag that corrupts it

Covers E2, N3, N4.

**Given** a stored value containing a dollar sign, a hash, quotes and a backslash:

```
sk-a$bc de#f "g" \h
```

**When** the launcher passes it to the container and a declared parameter receives it

**Then**

- the value reaching the generated script is **`sk-a$bc de#f "g" \h`**, asserted by comparing the
  **round-tripped value** — its `repr` and its length — not by asserting that the script ran;
- `--env-from-file` appears **nowhere** in the launcher, asserted at source level;
- `-e NAME=value` appears **nowhere**: every `-e` in the launcher carries a **bare name**, asserted at
  source level;
- while the session runs, `ps -Ao args` contains **no match** for the value.

### The measurement that disqualified the careful-looking option

Measured 2026-08-07, same value, three transports:

| Transport | Received in the container | In host `ps -Ao args`? | In `docker inspect`? |
|---|---|---|---|
| `compose run --env-from-file FILE` | **`sk-a de#f "g" \h`** | no | yes |
| `compose run -e NAME=value` | `sk-a$bc de#f "g" \h` | **yes** | yes |
| `compose run -e NAME` | `sk-a$bc de#f "g" \h` | **no** | yes |

Row one is the finding, and it inverts the intuition. `--env-from-file` is the option chosen by
someone thinking carefully about the process table — and compose parses the file with dotenv
semantics, expands `$bc` to nothing, and delivers a credential **three characters shorter than the
one the user stored**. There is no error. There is no warning. The exit status is 0.

The failure surfaces as a `401` from a remote service, at which point the self-correction loop
(`main.py:925`) hands the model a stderr dump and it rewrites a script that was already correct,
three times, and gives up.

**And note what the fixture is doing.** A value without a `$` in it round-trips identically under all
three transports. A test written with `hunter2` passes under the corrupting flag. The `$` is not
decoration — it is the entire discriminating power of the criterion, which is why it is specified here
rather than left to whoever writes the test.

Row two is what an implementer reaches for first and it publishes the credential to the host process
table for the whole session: `coderunner:260-263` deliberately does **not** `exec` — *"exec replaces
this shell and would skip the EXIT trap above"* — so the `docker compose` process outlives nothing.
On Linux `/proc/<pid>/cmdline` is world-readable by default.

Row three is chosen, and `docker inspect` still shows the value, which is AC-EXPOSE's business and not
a defect of the transport.

---

## AC-LAUNCH — A user with no stored secrets launches exactly as before

Covers S6, N8, and `spec.md` §7 item 6.

**Given** a machine with **no** registered secrets

**When** `./coderunner` is run **under `/bin/bash`**, not under `env bash`

**Then**

- the launcher reaches `compose run` and starts the session;
- the `compose run` invocation at `coderunner:263` is **byte-for-byte** what it is today — no stray
  `-e`, no empty argument;
- no keychain status line is emitted (AC-DEGRADE's registry-absent row).

### Why the interpreter is named in the criterion

Measured 2026-08-07 on this host:

```
$ /bin/bash --version
GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)

$ /bin/bash -c 'set -Eeuo pipefail; A=(); printf "%s\n" "${A[@]}"'
/bin/bash: A[@]: unbound variable
rc=1
```

`coderunner:1` is `#!/usr/bin/env bash` and `coderunner:10` is `set -Eeuo pipefail`. On a stock Mac,
`env bash` resolves to `/bin/bash` 3.2.57 and **an empty array expansion kills the launcher**. On a
machine with Homebrew bash 5 — which is most developer machines, including the one this SPEC was
written on — it does not.

So the criterion cannot say "run the launcher". It has to name the interpreter, because the whole
risk is that the author's machine has the other one. The guards were measured to work on 3.2.57:

```
$ /bin/bash -c 'set -Eeuo pipefail; A=(); echo "count=${#A[@]}"; printf "[%s]" ${A[@]+"${A[@]}"}'
count=0
```

**And the population is the wrong way round from every other risk here.** This does not break users
of the feature. It breaks users who have **never touched it** — which, on the day this ships, is
everybody.

---

## AC-BOOT — Storing a password does not install Docker

Covers E1, E6, N6.

**Given** a machine on which Docker is **not installed**, or is installed and **not running**

**When** `./coderunner --set-secret api_key` is run

**Then**

- the value is stored and the command **exits 0**;
- `ensure_docker_installed()` (`coderunner:158`), `ensure_docker_running()` (`coderunner:159`),
  `detect_compose()` (`coderunner:160`), the build at `coderunner:163-167` and
  `ensure_ollama_service()` (`coderunner:219`) are **none of them reached** — asserted by observing
  that the Docker daemon is still not running and `$LOG_FILE` (`coderunner:18`) was not truncated at
  `coderunner:157`;
- the command **does not fall through** to `compose run` at `coderunner:263`.

**And** the same for `--forget-secret NAME` and `--list-secrets`.

**And** the value never appears in an argument list: `security add-generic-password` is invoked with
`-w` **last and with no value**, so the OS reads and masks it. Asserted at source level — the string
`-w "` must not appear on the store path.

**And** the fetch at launch happens **before** `compose run` at `coderunner:263` and after the
bootstrap (E1), which is the opposite placement from the subcommands and is deliberate: the fetch
needs the compose command, and the subcommands need nothing.

### The mistake this criterion exists not to repeat

`product.md` §6.4 records it in the project's own words:

> The `--doctor` branch sits at `coderunner:233`, *after* the entire bootstrap at `coderunner:157-219`.
> Running `./coderunner --doctor` on a clean machine will therefore install Docker, start the daemon,
> build the image, start the Ollama sidecar, and pull a multi-GB model **before** printing a single
> diagnostic line. It is not a read-only health check.

`--set-secret` is a command a user runs once, in a hurry, to put a password somewhere. If it behaves
like `--doctor`, the first person to run it on a clean machine waits for a multi-gigabyte model pull
to store an API key — and every subsequent reader of the launcher will assume the placement was
considered, because there is already a precedent for it three sections down.

The criterion asserts the **absence** of side effects rather than the presence of a stored value,
because the stored value is the easy half and nobody will get it wrong.

---

## AC-IMAGE — Every first-party module `main.py` imports is present in the built image

Covers `spec.md` §7 item 6, and it exists because the repository has already got this wrong.

**Given** a freshly built `coderunner-ai:latest`

**When** the image is inspected

**Then**

- every first-party module named in `main.py`'s import block (`main.py:49-51` and the `from memory
  import …` that follows) is present in `/app`;
- `python -c 'import main'` inside the image **succeeds**, and so does `import params`,
  `import settings` and `import keychain`;
- the module list is derived from **`main.py`'s imports**, not from a hand-maintained second list, so
  the next module added to the application fails this test instead of shipping missing.

### The measurement, and why the fault is currently invisible

Measured 2026-08-07 against `coderunner-ai:latest`:

```
$ docker run --rm --entrypoint sh coderunner-ai:latest -c 'ls -1 /app'
main.py
memory.py
recall.py
requirements.txt
tools.py
vectorstore.py

$ docker run --rm --entrypoint python coderunner-ai:latest -c 'import params'
ModuleNotFoundError: No module named 'params'
```

`Dockerfile:34` reads `COPY main.py tools.py memory.py recall.py vectorstore.py ./`. **`params.py`
and `settings.py` were never added.** The next `docker compose build` produces an image whose
`main.py` cannot import, and the user sees a raw traceback from a container that exits immediately.

It has not happened yet for one reason, and it is a documented one:

```
$ docker run --rm --entrypoint sh coderunner-ai:latest -c 'wc -l /app/main.py; grep -c "import params" /app/main.py'
1045 /app/main.py
0
```

The built image's `main.py` is **1045 lines against the working tree's 1227** and contains no
`import params` at all — it predates SPEC-INPUT-001 entirely. `coderunner:163` builds only when the
image is **absent**, so editing source never triggers a rebuild. That is `product.md` §6.3, the
"stale-image hazard", concealing a second defect underneath itself.

This SPEC adds a third module to that same `COPY` line, which is why the criterion is here rather
than in a backlog: shipping `keychain.py` into an image that does not contain it would be the same
mistake for the third time, and the assertion derived from `main.py`'s own imports is what stops
there being a fourth.

---

## AC-DOCTOR — Fourteen fields, names only

Covers U5, E7, N5.

**Given** two registered secrets

**When** `./coderunner --doctor` runs

**Then**

- **fourteen** fields are printed — the existing twelve (`coderunner:236`, `:237`, `:238`, `:239`,
  `:240`, `:241`, `:244`, `:246`, `:247`, `:248`, `:251`/`:254`, `:256`) plus `keychain backend` and
  `stored secrets`;
- `stored secrets` lists the **names** and a count, and **no stored value appears anywhere in the
  output** — asserted against the whole report, not against that one field;
- `keychain backend` reads `none` with no client on `PATH`, and `unavailable (keychain locked)` when
  the registry read returns non-zero;
- `product.md:123` says **14 fields** and its parenthesised list names both new ones.

**And** the exit status is still `0` and the branch still returns before `coderunner:260-263`.

### Why "names only" is a requirement and not an assumption

`--doctor` output is what a user pastes into a bug report, a forum post or an issue. It is the single
most likely piece of this program's output to be published verbatim by someone who has not read it
first.

A value printed there is a value in a public issue tracker, and unlike every other exposure in this
SPEC it is neither transient nor bounded by who can reach the Docker daemon. The assertion is
therefore against the **entire report** rather than against the `stored secrets` field, so that a
future field that happens to include a value — a debug dump, a "raw registry" line — fails the test
rather than passing it by living somewhere else.

---

## Success criteria and quality gates

### Gates

| Gate | Enforced by | Threshold |
|---|---|---|
| Documented exposure verified | **AC-EXPOSE** | `docker inspect` shows the value; no file claims privacy |
| Same path as a typed value | **AC-SOURCE** | `ask` never called for a sourced name; `code` identity preserved |
| Policy always resolved | **AC-POLICY** | `settings.ensure_policy()` called on a turn with zero prompts |
| Degradation | **AC-DEGRADE** | Seven conditions, one predicate, per-name isolation, no repair |
| Transport fidelity | **AC-TRANSPORT** | `$`-bearing value round-trips; no `--env-from-file`, no `-e NAME=value` |
| Bootstrap not run by subcommands | **AC-BOOT** | `--set-secret` stores and exits with the daemon still down |
| No regression for non-users | **AC-LAUNCH** | Clean launch under `/bin/bash` 3.2 with an empty array |
| Image completeness | **AC-IMAGE** | Every module in `main.py`'s imports present in `/app`; `import main` succeeds |
| Diagnostics | **AC-DOCTOR** | 14 fields; no value anywhere in the report |
| Per-file coverage | `conftest.py:210-234` | `memory.py` 100%, `recall.py` 100%, `vectorstore.py` ≥ 85%, `params.py` 100%, `settings.py` 100%, **`keychain.py` 100%** (`conftest.py:200-206`) |
| Coverage measurement | `pytest.ini:50-54` | `--cov=keychain` present; absent, `conftest.py:221-223` fails the session with `coverage unavailable` |
| Stdlib-only leaf | `tests/test_source_seam.py:156-167` | `keychain.py` imports nothing outside `sys.stdlib_module_names` |
| Test count | `.github/workflows/ci.yml:289` | `skipped == 0`, `passed >= MIN_PASSED`, **measured** after T8, raised from 469 |
| Lint | SPEC-CI-001 AC-4 | `ruff check .` zero findings |
| `main.py` coverage | **not gated, by design** | Inherited from SPEC-MEMORY-001 and SPEC-INPUT-001 §5.3. `main.py`'s share here is six lines of wiring |
| The launcher | **not gated, and there is no harness** | 263 lines, no test. T10's manual verification is the only evidence; `spec.md` §8 item 9 scopes a harness out and says why |

### Verification status

| Criterion | Status | Discharged by |
|---|---|---|
| AC-EXPOSE | **not verified** — the `docker inspect` leak and the `/proc` routes are **measured** (2026-08-07); the feature that produces them is not built | T5, T10, T11 |
| AC-SOURCE | **not verified** | T1, T3, T8 |
| AC-POLICY | **not verified** | T3, T8 |
| AC-DEGRADE | **not verified** — rc 44 and rc 128 are **measured**; the handling is not built | T5, T8 |
| AC-TRANSPORT | **not verified** — the `--env-from-file` corruption and the `ps` visibility are **measured**; the transport is not wired | T5, T8, T10 |
| AC-BOOT | **not verified** | T4, T5 |
| AC-LAUNCH | **not verified** — the bash 3.2 array failure and both guards are **measured** | T5, T10 |
| AC-IMAGE | **not verified**, and **currently failing**: `params.py` and `settings.py` are measured absent from the built image | T7 |
| AC-DOCTOR | **not verified** | T6, T11 |

### Definition of done

1. `keychain.py` exists, is stdlib-only, contains **no `subprocess`, no `sys.platform` and no
   `security`/`secret-tool` string**, and is gated at **100%** in **both** `pytest.ini:50-54` and
   `conftest.py:200-206`, and asserted at `tests/test_source_seam.py:156-167`.
2. AC-EXPOSE through AC-DOCTOR have each been **observed passing** — not inferred from a green suite.
3. **AC-POLICY and AC-TRANSPORT have each been observed FAILING at least once**, deliberately, against
   a knowingly-broken implementation: a `_resolve_param_policy()` moved inside the prompting branch
   for AC-POLICY, and `--env-from-file` for AC-TRANSPORT. Both are green under every other test in the
   repository, which is the whole reason they have criteria. *A gate never observed failing is not
   known to be a gate.*
4. **AC-LAUNCH has been run under `/bin/bash` explicitly**, with the version printed into the record.
   Running it under a Homebrew bash 5 proves nothing about the population it protects.
5. **AC-IMAGE has been discharged by a real `docker compose build` followed by `import main`** inside
   the resulting image — not by reading the `Dockerfile` diff. The defect it fixes was in the
   repository for a whole SPEC because reading the line was enough for everybody who looked at it.
6. T10's two manual verifications have been run and their outcomes **recorded**: the end-to-end
   no-prompt path, and the `docker inspect` observation of the plaintext value.
7. `MIN_PASSED` at `.github/workflows/ci.yml:289` has been raised to a number **taken from a real
   run**, not computed from an expected delta.
8. `README.md` and `tech.md` §7.2 carry `spec.md` §4.3's honest summary **verbatim**;
   `product.md:123` says 14 fields; `tech.md` §7.1's two stale citations in the rows this SPEC edits
   are corrected.
9. **No claim anywhere states or implies that this feature makes a secret private.** It removes a
   retyping burden and adds a reader — the Docker daemon. `never` remains the strongest capture
   policy and **no longer bounds the exposure**, and a user who chose `never` is told so
   (`spec.md` §4.4).
10. `docker-compose.yml` is unmodified (N7), `main.py:140-148` is unmodified (N2), and
    `settings.json`'s schema is unchanged at version 1 (`settings.py:55`, `spec.md` §3.4) — the reason
    for each recorded where the next person to reach for it will look.
