# SPEC-KEYCHAIN-001 — Implementation Plan (v1.0.0)

> Requirements are in `spec.md`. Acceptance criteria are in `acceptance.md`.

## 0. Starting position

This is the smallest SPEC in the repository and it has the largest gap between how much code it adds
and how much can go wrong with it. `keychain.py` is about thirty lines. The launcher gains about
forty. `main.py` gains six. Everything else is documentation and gate bookkeeping.

The reason it still needs eleven tasks is that three of the failure modes are **silent**, one of them
breaks **every existing user** rather than every user of the feature, and one of them is a defect
this SPEC **inherits** and cannot ship around.

| Present | Evidence |
|---|---|
| A collection seam designed to be met from outside | `params.collect_values()` behind an `ask` callable, `params.py:184-207`; the skip at `params.py:201-203` |
| A value cache that already wins over anything supplied later | `params.pending_declarations()`, `params.py:123-133` |
| One predicate governing every secret behaviour | `params.py:297`, `params.py:408`, `main.py:823`, `main.py:988` |
| A launcher that already shells out to platform-specific binaries | `coderunner:37-71`, `coderunner:73-86` |
| A launcher-only variable pattern that never reaches the container | `coderunner:17-18`; `tech.md` §4.1 |
| A `--doctor` branch to model argument handling on — and a documented record of where it was put wrong | `coderunner:233-258`; `product.md` §6.4 |
| A one-line degradation convention with two implementations to copy | `product.md:138`; `_warn_memory()` `main.py:741`; `warn()` `coderunner:27` |
| A per-file coverage gate that fails loudly when a module is added to one list and not the other | `conftest.py:200-206`, `conftest.py:221-223`, `pytest.ini:50-54` |
| A stdlib-only source-seam assertion for exactly this kind of leaf | `tests/test_source_seam.py:156-167` |
| Live CI asserting `skipped == 0` and `passed >= 469` | `.github/workflows/ci.yml:289` |

| Absent, and this SPEC must supply it | Evidence |
|---|---|
| ~~`params.py` and `settings.py` in the image~~ — **supplied by `fc19a07`, not by this SPEC.** The measurement stood when taken: `Dockerfile:34` copied five modules, `ls /app` listed six entries with neither among them, and `import params` in the image raised `ModuleNotFoundError`. That commit landed afterwards, so T7 is reduced to adding `keychain.py` alone to what is now `Dockerfile:43` | `Dockerfile:43` (was `:34`); `spec.md` §HISTORY |
| Any test harness for the launcher | 263 lines of bash, no test of any kind |

**Two things to be clear-eyed about before starting.**

**The riskiest line in this SPEC is not in `keychain.py`.** It is the one that decides whether
`_resolve_param_policy()` (`main.py:833-846`) is called on a turn where nothing was prompted. Get it
wrong and a keychain-sourced secret is captured into solution memory unredacted, under a policy the
user chose, with the entire suite green (T3, AC-POLICY).

**The most likely line to break the product is in bash.** `coderunner:10` sets `set -Eeuo pipefail`;
stock macOS `/bin/bash` is 3.2.57; an empty array expansion is fatal there. The population affected
is not "users of this feature" — it is **everyone who has not stored a secret**, which on day one is
everyone (T5, N8, AC-LAUNCH).

---

## 1. Task decomposition

Eleven tasks. All automated except the two manual checks named in T10.

| # | Task | Artefact | Depends on |
|---|---|---|---|
| **T1** | **Write `keychain.py`.** `ENV_PREFIX = "CODERUNNER_SECRET_"`. `load(environ) -> dict[str, str]` reads every prefixed variable and **pops** it, keeping only non-empty values. `prefill(declarations, values, loaded) -> list[str]` fills `values` for declarations whose `type == secret` (S3) and whose name is not already present (S2), returning the names it filled. Stdlib only, no subprocess, no platform branch, no `Path`. Every platform decision is in bash and stays there. | `keychain.py` | — |
| **T2** | **Admit `keychain.py` to the gates.** `--cov=keychain` in `pytest.ini:50-54`; `"keychain.py": 100.0` in `conftest.py:200-206`; add it to the stdlib-only assertion at `tests/test_source_seam.py:156-167`. **The first two are both edits or neither**: with the conftest entry alone, `cov.report(include=["keychain.py"])` raises and `conftest.py:221-223` fails the session with `coverage unavailable`. Land this **early** — it turns "we forgot a test" into a red suite now rather than at T9. | `pytest.ini`, `conftest.py`, `tests/test_source_seam.py` | T1 |
| **T3** | **Wire `main.py` — and this is the task to review hardest.** Module-level `SECRETS = keychain.load(os.environ)` at **import**, not first use: `run_python()` passes no `env=` (`main.py:496-503`), so any child started before the pop reads the value from `os.environ`. Then rework `_collect_params()` (`main.py:849-869`) to the shape in `spec.md` §3.6. **Two invariants, both invisible when broken:** (a) `_resolve_param_policy()` becomes unconditional on `pending` and **must not** be conditional on `asked` — otherwise `param_session.policy` stays `None`, `main.py:981` reads `""`, and both the redaction gate (`main.py:988`) and the `never` skip (`main.py:1026`) are silently off; (b) the function still returns **`pending`**, not `asked`, because `main.py:974` accumulates it into `param_declared` and `main.py:987` builds the redaction set from that. **`code` is still never reassigned** — SPEC-INPUT-001's U3/N4 are untouched and must stay that way. | `main.py` | T1 |
| **T4** | **Launcher: the secret subcommands.** `--set-secret NAME`, `--forget-secret NAME`, `--list-secrets`, dispatched immediately after `coderunner:34` and **before** `coderunner:157`. Each prints one line and exits; none touches Docker. On macOS use `security add-generic-password -U -a NAME -s coderunner -w` with **`-w` last and no value**, so `security` prompts and masks it and the plaintext never enters an argv, a shell variable or the launcher's environment; on Linux `secret-tool store`, which reads stdin. Maintain the `__names__` registry item in the same store. Model the argument handling on `coderunner:233-258` and **not** its placement — `product.md` §6.4 records what that costs. | `coderunner` | — |
| **T5** | **Launcher: the fetch and the `-e` array.** Before `coderunner:263`, read the registry, fetch each name, and build `RUN_ENV+=(-e "CODERUNNER_SECRET_$UPPER")` after `export`ing the value. **Name only, never `-e NAME=value`** (N4, measured: the value lands in `ps -Ao args` for the whole session). **Guard the expansion**: `"${RUN_ENV[@]}"` on an empty array under `set -u` is fatal on bash 3.2.57, which is stock macOS `/bin/bash`. Use `${RUN_ENV[@]+"${RUN_ENV[@]}"}` or an explicit `(( ${#RUN_ENV[@]} ))` branch — both measured to work on 3.2.57. A name is supplied only when the client exits **0** and prints a **non-empty** value (U3); anything else is one `warn()` line and no variable. | `coderunner` | T4 |
| **T6** | **Launcher: `--doctor` gains two fields.** `keychain backend` and `stored secrets`, in the existing `printf` shape, **names only, never values** (N5). Twelve fields become fourteen. `product.md:123` documents the count and the parenthesised list and must change in the same commit; a documented count that is wrong is worse than no count. | `coderunner`, `product.md` | T4 |
| **T7** | **The `COPY` line at `Dockerfile:43` — add `keychain.py`.** ~~`Dockerfile:34` — add three modules, not one. The line currently reads `COPY main.py tools.py memory.py recall.py vectorstore.py ./`. Add `keychain.py` **and** `params.py` **and** `settings.py`. Measured 2026-08-07: the latter two are absent from `coderunner-ai:latest` and `import params` inside it raises `ModuleNotFoundError`; the fault is latent only because the built image predates SPEC-INPUT-001 (`/app/main.py` is 1045 lines against the tree's 1227), which is `product.md` §6.3 exactly.~~ **SUPERSEDED by `fc19a07`**, which added `params.py` and `settings.py` after that measurement was taken. The measurement stood when taken and the defect it names had shipped; what is reduced is the obligation — one name, not three, onto a line that has since moved from `:34` to `:43`. **Verify by rebuilding and importing**, not by reading the diff — the whole point of this task is that reading the line was not enough last time, and `fc19a07` has made that *more* pressing rather than less: it removed the natural red state, so `keychain.py`'s absence would now be the only fault on that line and there is nothing else on it to trip over. | `Dockerfile` | T1 |
| **T8** | **Tests for `keychain.py` and the wiring.** `tests/test_keychain.py` drives `load()` and `prefill()` to 100% — including the pop, the empty-value rejection, the non-`secret` skip (S3), the cache-wins case (S2) and the case-collision mapping. `tests/test_main_integration.py` gains the AC-POLICY and AC-SOURCE scenarios. The full set is in `acceptance.md`. | `tests/test_keychain.py`, `tests/test_main_integration.py`, `tests/test_source_seam.py` | T2, T3 |
| **T9** | **Raise `MIN_PASSED`.** `.github/workflows/ci.yml:289` reads `469`; set it to the count **measured** after T8 lands. **Measure it, do not compute it** — the floor exists to catch tests that stopped being *collected*, and a number derived by arithmetic from an expected delta cannot see that. T8 and T9 land together or the branch is knowingly red in between. | `.github/workflows/ci.yml` | T8 |
| **T10** | **The two manual verifications, which are deliverables and not formalities.** **(a)** Store a real secret with `--set-secret`, relaunch, and confirm a turn declaring it is **not** prompted and the script receives the right value — this is the only end-to-end check of the launcher→compose→`os.environ`→prelude chain, and none of it is under test. **(b)** Run `docker inspect` against the live session and **observe the value in plaintext**, then record the observation. That second one is not a bug hunt; it is AC-EXPOSE, and the documented limitation is worth nothing if nobody has ever looked at it. | — | T5, T7 |
| **T11** | **Documentation, and it carries the honest summary unsoftened.** `README.md` gains the three subcommands and `spec.md` §4.3 **verbatim**. `tech.md` §7.2 gains `docker inspect` as a sink; `tech.md` §7.1 gets its two stale citations fixed in the rows this SPEC touches (`main.py:135`→`:139` for the prompt row, `docker-compose.yml:67-68`→`:74-75` for the bind-mount row). `product.md` §4 gains the feature, `product.md:123` becomes 14 fields, and `product.md` §6 gains the added exposure. **No sentence anywhere may state or imply that this makes a secret private** (U6, R5). | `README.md`, `tech.md`, `product.md` | T10 |

### 1.1 Dependencies and critical path

```
T1 ──┬── T2 ──┐
     │        │
     ├── T3 ──┼───────── T8 ── T9 ──┐
     │        │                     │
     └── T7 ──┼─────────── T10 ── T11
              │             │
T4 ──┬── T5 ──┘─────────────┘
     │
     └── T6 ── (product.md:123)
```

**Critical path: T1 → T3 → T8 → T9 → T11**, with **T4 → T5 → T10** joining at T10.

`T4`/`T5`/`T6` are bash and share no code with `T1`/`T3`; they can be written in parallel and only
meet at T10, where the chain is driven end to end for the first time. `T7` hangs off `T1` only
because it needs the filename, and it should land **early** — it is a one-line edit that fixes a
defect the repository already has, and holding it back means every intermediate build is broken for
a reason unrelated to this SPEC.

**T3 is the convergence point and the one to review hardest.** It is the only task where a correct
implementation and a subtly wrong one produce identical output on every turn anybody will run by
hand.

### 1.2 Priority

| Priority | Tasks | Rationale |
|---|---|---|
| **High** | T3, T5, T7, T8 | T3 is where the capture policy is silently disabled or not; T5 is where every existing user's launcher breaks or not; **T7 stays High even though `fc19a07` reduced it to one name**, because `keychain.py` is imported at `main.py` module level (`main.py:49`): omitting it is not a degraded feature, it is total failure at container start; T8 is the only thing that makes any of it checkable |
| **Medium** | T1, T2, T4, T10 | T1 is thirty lines of dictionary handling with no failure mode that is not obvious. T4 decides whether the feature is *usable*, which is a different axis from whether it is *safe*. T10 is the only end-to-end evidence that exists |
| **Low** | T6, T9, T11 | T6 is two `printf` lines and a documentation count. T9 is bookkeeping. T11 is necessary for the work to hold and nothing depends on it — **except R5, which is a documentation risk and lives entirely in T11** |

Primary goal: T3 and T7 landing with AC-POLICY and AC-LAUNCH green. Secondary goal: T5 with
AC-DEGRADE and AC-TRANSPORT green. Final goal: T10's observation recorded and T11's summary written
without softening. No optional goals — every task listed is required.

---

## 2. Technical approach — the five decisions worth defending

### 2.1 The keychain is reached from bash, and that is the entire answer

The question this SPEC started from was whether private information can be stored with **system
libraries and no dependency**. The container cannot do it — measured three ways (`spec.md` §2.1) —
and the temptation is to conclude that it cannot be done.

It can, because the launcher is not Python. `coderunner:1` is bash, `coderunner:34` already branches
on `uname -s`, and `coderunner:37-99` already installs platform-specific software by shelling out.
Calling `/usr/bin/security` from that file adds **zero** to `requirements.txt`, zero to the image,
and zero to `tech.md` §2.

This is worth stating as an approach rather than a fact because it dictates where every subsequent
decision lands: **no platform knowledge crosses into Python.** `keychain.py` has no `subprocess`, no
`sys.platform`, no `security`/`secret-tool` string anywhere. It reads a dictionary. If a third
platform is ever supported, `keychain.py` does not change and neither does its test.

### 2.2 Meet the seam, do not widen it

`params.collect_values()` takes `ask` as a callable (`params.py:184-207`) and skips a name already in
`values` (`params.py:201-203`). Two implementations were available:

- **Widen the seam:** teach `collect_values` about a second source, or pass a second callable.
- **Fill `values` first:** call `keychain.prefill()` before `collect_values()`, and let the existing
  skip do the work.

The second, and not for tidiness. `params.py` is gated at **100%** and its file banner
(`params.py:18-28`) makes a specific promise about what it contains. Every branch added to
`collect_values` is a branch someone has to drive to keep that gate, in the module whose 100%
currently costs nothing to maintain — which is precisely the argument SPEC-INPUT-001 §5.1 used to
keep settings I/O out of `memory.py`.

The mechanical consequence is worth naming: **`ask` is never called for a sourced name**, so
`_ask_param()` (`main.py:799-825`) never runs, so `getpass` never runs, so there is no prompt to
suppress and no code path that has to know not to prompt. The absence of a call is easier to verify
than the presence of a guard.

### 2.3 The policy must be resolved even when nothing is asked

This is `spec.md` S1 restated as code shape, because it will read like a gratuitous change to
whoever implements it.

Today, `_resolve_param_policy()` sits at `main.py:865`, inside the block guarded by
`if not pending: return pending`. That guard is correct: a turn with no declarations must be
byte-for-byte the pre-feature turn. What is **not** correct after this SPEC is putting the resolution
inside the narrower block that runs when something is prompted, because that block can now be empty
while the turn still holds a secret.

The chain, in full, so nobody has to reconstruct it:

```
policy never resolved
  -> param_session.policy is None
  -> main.py:981 evaluates `policy` to ""
  -> main.py:988  `policy == settings.POLICY_SENSITIVE`  is False -> no redaction
  -> main.py:1026 `policy == settings.POLICY_NEVER`      is False -> capture proceeds
  -> _capture_turn() stores stdout containing the secret, in plaintext, on a volume
     tech.md 7.2 says any later generated script can read
```

Nothing in that chain raises, prints, or fails a test. The script runs, the answer streams, the panel
is green. **AC-POLICY asserts the call happened**, not the outcome, for the same reason AC-CAP
asserts object identity: an assertion on the outcome passes whenever the fixture's script happens not
to print the secret, which is every fixture anyone writes by accident.

### 2.4 `-e NAME`, and why the careful-looking option was disqualified

Three transports were measured on 2026-08-07 with the value `sk-a$bc de#f "g" \h`
(`spec.md` §2.3), and the result inverts the intuition:

- `--env-from-file` is the one that *looks* careful — the value never enters an argument list — and
  it **delivered `sk-a de#f "g" \h`**. Compose parses the file with dotenv semantics and expands
  `$bc` to nothing. Three characters gone, no error, no warning. A corrupted credential fails as a
  `401` from a remote service, which the model then tries to "fix" by rewriting the script.
- `-e NAME=value` is intact and puts the value in `ps -Ao args` for the whole session, because
  `coderunner:260-263` deliberately does not `exec`.
- `-e NAME` is intact and absent from argv.

Only the third survives both tests. Its residual cost — the value sits in the launcher's exported
environment — is real and is stated (`spec.md` §3.3), and it is strictly narrower than argv on every
platform.

**The general lesson, worth carrying:** a transport that silently alters a credential is worse than
one that exposes it, because exposure is detectable and corruption is diagnosed at the far end of a
network call. AC-TRANSPORT asserts the **round-tripped value**, in the same spirit as
SPEC-INPUT-001's AC-INJ.

### 2.5 The registry lives in the keychain because the launcher cannot read `settings.json`

`settings.json` is the obvious home for a list of names and it is unreachable from where the list is
needed. It sits at `/home/runner/.coderunner/settings.json` (`settings.py:63`) inside the
`coderunner_app_data` named volume; the launcher is on the host; on macOS under Docker Desktop the
volume's mountpoint is inside the VM and does not exist on the host at all — which is why
`coderunner:248` prints it as a diagnostic rather than using it.

Reading it would require starting a throwaway container *before* the bootstrap that guarantees the
image exists. And even then, `settings.json` resolution is **lazy and interactive** by design
(`settings.py:283-288`, `settings.py:346-375`) — a host-side reader would be reading a file whose
every assumption is about an in-container, mid-session caller.

So the registry is a keychain item. One code path, both platforms, no container start, and no host
footprint beyond the store the user already has.

**The cost is drift**, and the mitigation is that drift is indistinguishable from the degradation
path that already exists: a registered name with no item returns rc 44, is not supplied, and the
container prompts. The user loses nothing they had. `--list-secrets` is what makes drift visible when
they go looking.

---

## 3. Risks and mitigations

| # | Risk | Assessment | Mitigation |
|---|---|---|---|
| **R1** | **The policy is resolved only when something is prompted, and a keychain-sourced secret is captured unredacted.** The chain is at §2.3: `None` policy → `""` at `main.py:981` → redaction gate false at `main.py:988` → `never` skip false at `main.py:1026` → plaintext secret in `coderunner_app_data`. | **The most serious risk in this SPEC, and the least visible.** The turn looks perfect: script runs, panel green, answer streams, capture succeeds. Every existing test passes, because none of them declares a parameter *and* supplies it without prompting — that combination does not exist before this SPEC. | **AC-POLICY asserts that `_resolve_param_policy()` was called on a turn where nothing was prompted**, by spying on the call rather than on its effect. `spec.md` S1 states it as a requirement in its own right. And the definition of done requires AC-POLICY to have been **observed failing** against a deliberately conditional implementation, because a gate never seen red is not known to be a gate. |
| **R2** | **The empty-array expansion kills the launcher for every user who has no stored secrets.** `coderunner:10` sets `set -Eeuo pipefail`; `coderunner:1` is `#!/usr/bin/env bash`; stock macOS resolves that to `/bin/bash` **3.2.57**. Measured 2026-08-07: `printf … "${A[@]}"` with `A=()` under `set -u` is a fatal `unbound variable`, rc 1. | **Certain on stock macOS, invisible on any machine with Homebrew bash 5** — which is most developer machines, including the one this SPEC was written on. That asymmetry is what makes it dangerous: it will pass every check the author runs and break on the first clean Mac. | `spec.md` N8 makes the guard a requirement. `${RUN_ENV[@]+"${RUN_ENV[@]}"}` and `(( ${#RUN_ENV[@]} ))` were both measured to work on 3.2.57. **AC-LAUNCH drives the no-secrets path under `/bin/bash` explicitly, not under `env bash`**, because running it under the wrong interpreter is how this gets missed. |
| **R3** | ~~**`Dockerfile:34` is edited for `keychain.py` and the two missing modules are not noticed.** Measured 2026-08-07: `params.py` and `settings.py` are absent from `coderunner-ai:latest`; `import params` inside the image raises `ModuleNotFoundError`. The image only starts because it is stale (`/app/main.py` is 1045 lines, pre-SPEC-INPUT-001) — `product.md` §6.3.~~ **That half was discharged by `fc19a07`, after the measurement was taken.** What survives is narrower: **`keychain.py` omitted from the `COPY` line at `Dockerfile:43`.** | **The surviving residual is real and is worth stating precisely.** `keychain.py` is imported at `main.py` **module level** (`main.py:49`), so its omission kills the container **at import** — loud, not silent, and not a degraded feature. But it fails **late**: `coderunner:163` builds only when the image is **absent**, so a developer with a stale image never triggers a rebuild and never sees it. That is the same concealment that let the previous omission live for a whole SPEC, and it did not go away with the omission. | **T7 adds `keychain.py` and verifies by rebuilding and importing**, not by reading the diff. AC-IMAGE asserts that every first-party module `main.py` imports is present in the built image, derived from `main.py`'s import list rather than from a hand-maintained second list — so the next module to be added fails this test instead of shipping missing. |
| **R4** | **`--env-from-file` gets adopted later as an "improvement".** It is the option that looks safer, and the argument for it — "the secret is not in the process table" — is correct. Measured: it also expanded `$bc` out of the value and delivered three characters fewer, silently. | Moderate probability over a long window, total impact when it bites: the credential is wrong, the remote service returns 401, and the model burns its three attempts at `main.py:925` rewriting a script that was correct. | The measurement is in `spec.md` §2.3 and N3 forbids the flag by name. **AC-TRANSPORT asserts the round-tripped value** with a `$`-bearing fixture, so the substitution fails a test rather than a code review. A `$`-free fixture would pass under both transports, which is why the fixture is specified rather than left to the implementer. |
| **R5** | **The documentation softens the exposure.** "Your secrets are stored securely in the system keychain" is true, flattering, and reads as a claim about the session — which is exactly wrong, because during the session the value is in `docker inspect` in plaintext. | **Certain unless actively prevented.** It is the sentence a `README` wants to write, and it will be believed and acted on. This is the same failure `plan.md` R5 of SPEC-INPUT-001 guarded against for `sensitive_excluded`, and it is worse here because the reassuring words are more available. | `spec.md` §4.3 is written as a block to be carried **verbatim** into `README.md` and `tech.md` §7.2, and U6 makes it a requirement. The definition of done requires that no text states or implies privacy. **And the `never` interaction must be carried too** (`spec.md` §4.4): a user who chose `never` was promised the strongest capture policy, and for a keychain-sourced value that policy no longer bounds the exposure. |
| **R6** | **A GUI unlock prompt blocks the launcher.** On a locked keychain in a TTY session, `security find-generic-password` may raise an OS dialog and wait. The launcher would appear to hang before the banner. *(Measured only in a non-TTY shell, where it returned rc 128 immediately with no prompt.)* | Low probability — the login keychain is normally unlocked at login, and `security add-generic-password -h` states that the creating application is trusted to read the item back without warning, so the common path is silent. Non-trivial impact: a hang with no output. | **Not worked around, and that is deliberate.** The dialog is the operating system asking the user for consent to release their own credential, which is the entire reason to use a keychain. Cancelling it produces a non-zero exit, which U3 already routes to "not supplied" and a prompt. A timeout wrapper is declined: `timeout(1)` is not present on stock macOS, and hand-rolling one in bash 3.2 to defeat a consent dialog is both more machinery and worse behaviour. Recorded so the first hang is recognised rather than debugged. |
| **R7** | **Registry drift accumulates.** A user deletes an item with `security delete-generic-password` outside `--forget-secret`, or renames a parameter, and the registry keeps a name with no value behind it. | Certain over time, and self-limiting: the fetch returns rc 44, the name is not supplied, the container prompts, and the user is exactly where they were before the feature. | S5 requires per-name isolation — one stale name must not stop the others — and one line naming it. `--list-secrets` makes the registry inspectable. **No automatic repair**: pruning the registry on a failed read would delete a name whose item is merely temporarily unreadable (a locked keychain returns rc 128, but a partially-unlocked one is not a state this SPEC can enumerate), and silently forgetting a user's registration is worse than carrying a stale one. |
| **R8** | **The first-run capture-policy question fires on a turn where the user typed nothing.** S1 makes resolution unconditional, so a user whose values all came from the keychain, on a machine with no `settings.json`, is asked how solution memory should treat parameterised turns — in the middle of a turn they thought was ordinary. | Certain on exactly one turn per machine. Low impact, high surprise. | Accepted and recorded rather than designed around, because the alternatives are worse: making resolution conditional reintroduces R1, and asking at startup was already rejected by SPEC-INPUT-001 §4.5 on the ground that it imposes the question on every user of the product and creates `settings.json` on every machine. `spec.md` §3.6 states the cost so it is not "fixed" later by someone who reads it as a bug. |
| **R9** | **Three modules at 100% make the gate expensive and the fourth one tempting to exempt.** `keychain.py` joins `memory.py`, `recall.py`, `params.py` and `settings.py`, bringing the gated set to five files plus `vectorstore.py`'s 85%. | Low here specifically — `keychain.py` is a dictionary reader with no external dependency and no branch a test cannot reach. It has **less** excuse for 85% than `settings.py` did, and `settings.py` did not get one. | The floor is asserted in `conftest.py:200-206` and measured through `pytest.ini:50-54`. If it is ever lowered it should be by an amendment to this SPEC naming which branch is going untested and why. |
| **R10** | **The launcher has no tests, and this SPEC adds forty lines to it.** T4, T5 and T6 are unverified by anything except T10's manual run. | Inherited, not introduced — all 263 existing lines are equally untested — but the surface grows and the two sharpest edges (R2's array guard, U3's rc-and-non-empty predicate) both live there. | **T10's manual verification is a deliverable with a recorded outcome**, not a formality, and the definition of done requires the observation to be written down. Building a bash harness is scoped out (`spec.md` §8 item 9): a test framework introduced as a rider on a `LOW`-priority feature is a framework nobody maintains. If the launcher grows again, it should be its own SPEC. |

---

## 4. Follow-up notes

- **`product.md` §6.4 will still be true after this SPEC, and slightly worse.** `--doctor` gains two
  keychain fields that need no Docker, in a branch that runs after the entire bootstrap. Moving the
  branch is scoped out (`spec.md` §8 item 6), but the right eventual fix is now obvious: `--doctor`
  belongs beside the secret subcommands, before `coderunner:157`, with only the Docker-dependent rows
  needing the daemon. That is a small SPEC and it would delete a documented defect.

- **`structure.md` is three SPECs behind and this SPEC does not fix it** (`spec.md` §8 item 8). Its
  tree lists none of the five current modules, its §5.1 states that "`main.py` imports no first-party
  module" against `main.py:49-51`, and its §6 says the test suite does not exist. Whoever brings it
  current should do it as documentation work with its own scope, not as a rider.

- **If a second setting ever needs to be visible to both the host and the container**, the answer is
  not to put it in `settings.json` and teach the launcher to read the volume. It is to note that this
  SPEC established a second store — the keychain registry — that both sides can already reach, and to
  decide deliberately which of the two owns which kind of state. `settings.json` owns what the user
  chose mid-session; the registry owns what the launcher must know before the container exists.

- **`spec.md` §3.2's rejected runtime channel should be re-read, not just remembered, if the "type it
  once, then register it" workflow (§3.1's stated cost) turns out to be the thing users complain
  about.** The rejection is structural — generated code shares the `runner` uid, so any channel given
  to `main.py` is given to the sandbox — and it does not weaken with use. What could change is the
  premise: if a future SPEC ever separates the REPL's uid from the sandbox's, the rejection is void
  and the design becomes available. That is a much larger change than this feature justifies, and it
  is the only thing that would reopen it.
