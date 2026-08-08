---
id: SPEC-KEYCHAIN-001
version: "1.0.0"
status: "draft"
created: "2026-08-07"
updated: "2026-08-07"
author: "Chun Kang"
priority: "LOW"
---

## HISTORY

### v1.0.0 partly verified (2026-08-07) — Implementation complete; status **stays `draft`**

Implemented across `479d700` (feature), `9226cc2` (documentation) and `5ffdfed` (tests). Verified on
Python 3.11.14: **541 tests passed, 0 failed, 0 skipped** (pytest, 9.72 s), **100.00% total coverage**
over **843 statements with 0 missed**; `keychain.py` is **26 statements at 100%** and the per-file
gate passed on all six gated modules. `ruff check .` reports **All checks passed**. `MIN_PASSED` at
`.github/workflows/ci.yml` was raised **469 → 541** from a real `junitxml` run, not computed from an
expected delta.

**The version is unchanged and the status does not move.** Nothing in the specification was revised;
what changed is the evidence behind it. `acceptance.md`'s definition of done has ten items and
**three were never run** — item 2 (every criterion **observed** passing), item 5 (AC-IMAGE discharged
by a real `docker compose build` followed by `import main` inside the resulting image) and item 6
(T10's two end-to-end verifications). The Docker daemon was not running on this host and no
substitute was attempted. `completed` on that evidence would be a claim this SPEC has not earned.

**AC-POLICY was verified by mutation, twice, by two independent agents.** Moving
`_resolve_param_policy()` back inside the `if asked:` branch produced **exactly one** failure —
*"`settings.ensure_policy()` was never called on a zero-prompt turn"* — while sixteen sibling
keychain tests stayed green. The part worth recording precisely: under the mutation **the output was
still redacted**, so an effect-based assertion would have passed. The assertion on the call was the
only thing that caught it. That is exactly what `acceptance.md` predicted, and it is now measured
rather than argued.

**AC-TRANSPORT round-tripped `sk-a$bc de#f "g" \h` through the real macOS keychain byte-identical, 19
characters**, and was observed red first with `--env-from-file` spliced into the launcher. That red
exposed a real defect in the **test** rather than in the launcher: the original whitespace tokenizer
never matched `RUN_ENV+=(-e "…")` — splitting on whitespace yields the single token `RUN_ENV+=(-e` —
so that check had been inspecting nothing, and would have passed against the one form the SPEC
forbids. It is now a regex, with a vacuity guard so an empty match set fails instead of passing.

**The rest, as measured.** **AC-BOOT:** a sentinel written to `$LOG_FILE` survived every secret
subcommand, which is direct evidence that `coderunner:157` is never reached. **AC-LAUNCH / N8:**
verified on stock `/bin/bash` **3.2.57** directly — the guarded expansion gives `argc=0`, `rc=0`; the
unguarded one gives `RUN_ENV[@]: unbound variable`, `rc=1`; `bash -n coderunner` parses under 3.2.
**AC-DEGRADE S5:** deleting one item behind the launcher's back produced one yellow line naming it,
still passed the other name, and left the registry unrepaired. **AC-IMAGE** was observed red twice —
once by shortening the `COPY` line, which reproduces the historical defect exactly, and once
naturally, when `main.py` first imported the new module. `--set-secret`, `--list-secrets` and
`--forget-secret` were each exercised against the real macOS keychain and every trace removed
afterwards (all three items back to rc 44); O2's case-collision refusal returns rc 1.

**What was not run, named as not run and not as not needed.**

- **AC-IMAGE's container half.** No real `docker compose build`, and no `import main` /
  `import params` / `import settings` / `import keychain` inside a built image. Only the
  source-level clause is discharged. This is definition-of-done item 5, and item 5 exists precisely
  because reading the `COPY` line was enough for everybody who looked at it last time.
- **AC-EXPOSE's live half.** `docker inspect` was never observed printing the plaintext value,
  `/proc/1/environ` was never read as `runner`, and `docker inspect` failing after `--rm` was never
  observed. Only AC-EXPOSE's **documentation** clause is discharged — and that one is an executable
  assertion in `tests/test_launcher_source.py`, not a review note.
- **T10 end to end.** The full launcher → `compose run` → `os.environ` → prelude chain was never run
  as one chain. Every link is tested; the joins between them are not.
- **A known gap in the tests themselves.** `tests/test_launcher_source.py` invokes bare `bash`, which
  resolves to 3.2.57 on this host and to 5.x on CI's Ubuntu runners. The N8 guard is therefore **not
  structurally guaranteed** to be exercised under 3.2 in CI — the exact blind spot `acceptance.md`'s
  definition of done item 4 warns about, arriving through the test rather than through the author's
  shell. The honest fix is to parametrise over both interpreters where they are present; hard-coding
  `/bin/bash` would make the check skip silently on Linux, which is the same failure by the other
  door.

**Two implementation judgement calls, recorded because neither is visible in the diff.**
`keychain.py` duplicates the `"secret"` string literal rather than importing `params`, because
`tests/test_source_seam.py` admits no first-party import in that module; the duplication is
cross-checked by an assertion that `keychain.SECRET_TYPE == params.TYPE_SECRET`, so divergence fails
a test instead of silently disabling sourcing. `ruff.toml` gained one `S603`/`S607` ignore scoped to
`tests/test_launcher_source.py` alone, with the reason written where the ignore is.

### v1.0.0 (2026-08-07) — Initial specification

Written to answer one question: **can private information be saved using only system libraries,
with no dependency?** The answer is yes, and the reason it is yes is not the reason anyone expects.
Three measurements taken 2026-08-07 settle where the feature can live, and between them they
eliminate every design that keeps the secret inside the container.

- **K1 — Python's standard library contains no reversible cipher.** *(Measured 2026-08-07 inside
  `coderunner-ai:latest`.)* Of the crypto-adjacent names in `sys.stdlib_module_names`, the image has
  exactly `crypt`, `ssl`, `hashlib`, `hmac`, `secrets`. `hashlib`, `hmac` and `crypt` are **one-way**;
  `secrets` generates randomness and decrypts nothing; `ssl` protects a socket, not a file at rest.
  Encryption at rest, stdlib-only, therefore means hand-rolling a cipher — a thing that is worse
  than not encrypting, because it looks like encryption. At-rest encryption inside the container is
  out of scope **by impossibility, not by preference** (§8 item 1).

- **K2 — the shipped container has no keyring tooling at all.** *(Measured 2026-08-07 by probing
  `coderunner-ai:latest`.)* `secret-tool`, `gnome-keyring-daemon`, `security`, `pass`, `gpg`,
  `dbus-send` and `keyctl` are **all ABSENT**. That is not an oversight to correct: `Dockerfile:27-29`
  installs `ca-certificates` and nothing else, deliberately, and the image is already 754 MB
  (`tech.md` §6.1). There is no secret store inside the container to talk to and adding one is a
  dependency, which the question forbids.

- **K3 — file permissions protect nothing in this threat model.** *(Measured 2026-08-07.)* `id`
  inside the container reports `uid=1000(runner) gid=1000(runner)`. `Dockerfile:42-45` creates
  `runner`, creates `/home/runner/.coderunner` and chowns it to `runner`. Generated code runs **as
  runner** — `tech.md` §7.2 and `product.md` §6.11 already document exactly this for the memory
  store. A `chmod 0600` file owned by `runner` excludes **nobody** that matters: the one process we
  are defending against is the one holding that uid.

Therefore the only place real OS-backed secret storage exists is **the host** — and `coderunner` is
bash on the host (`coderunner:1`), where `security` (macOS) and `secret-tool` (Linux) live. Calling
them costs zero Python dependencies because it is not Python at all. *(Measured 2026-08-07 on this
machine: `security` is present at `/usr/bin/security`; `secret-tool` and `pass` are absent.)*

**The central difficulty, and the sentence the rest of this document exists to earn.** The launcher
runs **once**, before the session (`coderunner:260-263`). Parameter needs arise **per turn**
(`main.py:973-974`). A launcher that has already handed control to `compose run` cannot answer a
prompt that has not been asked yet, and there is no channel back out of the container that is not
also a channel available to generated code (§3.2). So the keychain can serve only what was
**pre-declared**, and everything else prompts exactly as SPEC-INPUT-001 already makes it prompt.

**And the part that matters most is the accounting, not the mechanism.** Measured 2026-08-07:
`docker run -e MY_SECRET=hunter2` followed by
`docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}'` prints **`MY_SECRET=hunter2`
in plaintext**; the same value is readable inside the container from `/proc/1/environ` by the same
`runner` uid. This feature does **not** make the secret private. It **moves** the exposure, and §4
states what it removes, what it retains, and what it adds, in those three words.

One thing was found rather than designed, and it is recorded because this SPEC must touch the line
it lives on. `Dockerfile:34` reads
`COPY main.py tools.py memory.py recall.py vectorstore.py ./` — **`params.py` and `settings.py` are
not copied.** *(Measured 2026-08-07: `ls /app` in `coderunner-ai:latest` lists six entries and
neither module is among them; `import params` inside the image raises `ModuleNotFoundError`.)* The
fault is latent only because the built image is itself stale — `/app/main.py` is 1045 lines against
the working tree's 1227 and contains no `import params`, which is `product.md` §6.3 exactly. The
next rebuild produces an image that dies at import. This SPEC adds a third module to that same
`COPY` line and therefore inherits the obligation to fix it (§7 item 6).

**SUPERSEDED by `fc19a07` ("fix(docker): copy `params.py` and `settings.py` into the image"), which
landed after the measurement above was taken.** The measurement stands: the omission was real, it had
shipped, and `import params` inside `coderunner-ai:latest` did raise. What no longer stands is the
obligation — the line is now `Dockerfile:43` and copies both modules, so this SPEC adds **one** name
to it rather than three, and §7 item 6 is that much smaller. The reason for the finding is untouched:
the list is hand-maintained, and a module in `main.py`'s imports but absent from that line still
fails at **import**, inside a container that exits immediately, and still fails **late**, because
`coderunner:163` builds only when the image is absent.

---

# SPEC-KEYCHAIN-001 — Host-keychain secrets for declared parameters

**Title:** Pre-declared `secret` parameters fetched from the host OS keychain by the bash launcher
and handed to the container as environment, with an honest statement of the exposure that buys

## 1. Scope statement

Extends SPEC-INPUT-001. That SPEC gave the model a sanctioned way to ask the user for a value it
does not have; this one lets the user stop typing the same API key at the start of every session,
by keeping it where their operating system already keeps credentials.

`./coderunner --set-secret NAME` stores a value in the macOS keychain or the Linux Secret Service.
At the next launch the launcher fetches every stored name and passes it into the container as an
environment variable. A `# @param NAME : secret = "…"` whose name matches one of those is satisfied
**without prompting**; every other declaration prompts exactly as it does today.

Nothing about the model's job changes. It still writes `# @param api_key: secret = "…"` and then a
bare `api_key`, and the value still reaches the script through `params.render_prelude()`
(`params.py:327-342`) and `params.splice_prelude()` (`params.py:372-390`) as a `repr()`-produced
literal. Every property SPEC-INPUT-001 established — literal safety (U1), stdin untouched (U2),
capture-by-construction (U3), redaction at three sinks (E6) — continues to hold unchanged, and §4.4
works out the one place where what those properties *govern* has changed.

**No Python dependency is added.** The host side is bash calling a binary that ships with the
operating system. The container side reads `os.environ` and nothing else.

**This is a convenience feature and its priority is `LOW` for a reason that §4 states in full:** it
does not make a secret private. It removes it from three places and adds it to one. A user who needs
the secret to be private does not get that from this SPEC and must not be told otherwise.

---

## 2. Verified environment

Everything in §2.1–§2.3 was measured on 2026-08-07 against this host (macOS, arm64) and the image
`coderunner-ai:latest` (`sha256:0df09685…`, built 2026-08-07T04:02Z).

### 2.1 What the container cannot do

| Question | Measurement | Consequence |
|---|---|---|
| Can it encrypt at rest, stdlib-only? | Crypto-adjacent stdlib names present: `crypt`, `ssl`, `hashlib`, `hmac`, `secrets`. All one-way or transport-only | **No.** Hand-rolling a cipher is worse than not encrypting. §8 item 1 |
| Can it talk to a keyring? | `secret-tool`, `gnome-keyring-daemon`, `security`, `pass`, `gpg`, `dbus-send`, `keyctl` — **all ABSENT** | **No.** `Dockerfile:27-29` installs `ca-certificates` only |
| Can file permissions help? | `id` → `uid=1000(runner) gid=1000(runner)`; `/home/runner/.coderunner` owned by `runner` (`Dockerfile:42-45`); generated code runs as `runner` (`tech.md` §7.2) | **No.** `0600` as `runner` excludes nobody in this threat model |

The third row is the one that generalises. It is the same fact that makes the solution-memory store
readable by generated code (`product.md` §6.11), and it is why §3.2 can reject an entire family of
designs in one sentence.

### 2.2 What the host can do

`coderunner:1` is `#!/usr/bin/env bash`. macOS and Linux both ship a credential store with a
command-line client, and the launcher is already a program that shells out to platform-specific
binaries (`coderunner:37-71`, `coderunner:73-86`).

*Measured 2026-08-07 against a temporary keychain created and deleted for the purpose:*

| Operation | Command | Result |
|---|---|---|
| Store | `security add-generic-password -U -a NAME -s coderunner -w` | item created |
| Fetch | `security find-generic-password -a NAME -s coderunner -w` | prints `hunter2` on stdout, rc **0** |
| Locked keychain | same | **rc 128**, stdout empty, no prompt in a non-TTY shell |
| Missing item | same, unknown name | **rc 44**, `SecKeychainSearchCopyNext: The specified item could not be found in the keychain.` on stderr, stdout empty |

Three properties from `security add-generic-password -h`, quoted because they govern §3.5:

> Use of the `-p` or `-w` options is insecure. Specify `-w` as the last option to be prompted.

> `-U` Update item if it already exists (if omitted, the item cannot already exist)

> By default, the application which creates an item is trusted to access its data without warning.

The first means the launcher **never has to handle the plaintext on the store path** — `security`
prompts and masks it itself, and the value never enters any argv. The third means an item created by
`/usr/bin/security` is read back by `/usr/bin/security` without an ACL dialog, so the common path is
silent. The lock state still governs, which is what the rc-128 row is.

The Linux equivalents are `secret-tool store --label='…' service coderunner name NAME` (reads the
value from stdin, so likewise never in argv) and `secret-tool lookup service coderunner name NAME`.
*(Not measured: `secret-tool` is absent from this host. Marked as reasoned, per the convention this
project already uses for the container-blocking row of `spec.md` §2.1 in SPEC-INPUT-001.)*

### 2.3 The channel between them, measured

This is the section that chose the transport, and it disqualified the tidier candidate by
measurement rather than by taste.

Value under test: `sk-a$bc de#f "g" \h`.

| Transport | Value as received in the container | Present in host `ps -Ao args`? | Present in `docker inspect`? |
|---|---|---|---|
| `compose run --env-from-file FILE` | **`sk-a de#f "g" \h`** — `$bc` expanded away, **3 characters lost silently** | no | **yes** |
| `compose run -e NAME=value` | `sk-a$bc de#f "g" \h` — intact | **yes**, for the lifetime of the CLI process | **yes** |
| `compose run -e NAME` *(name only, value from the launcher's exported environment)* | `sk-a$bc de#f "g" \h` — intact | **no** — match count 0 | **yes** |

Row one is the finding. `--env-from-file` looks like the careful choice — the value never touches an
argument list — and it **corrupts the value**, because compose parses the file with dotenv semantics
and interpolates `$`. The failure surfaces as a `401` from a remote API, nowhere near its cause, and
no test that uses a `$`-free fixture will ever see it. It is disqualified.

Row two is what an implementer reaches for first. It is correct and it publishes the secret to the
host process table for the whole session — `coderunner:260-263` deliberately does **not** `exec`, so
the `docker compose` process lives as long as the REPL does. On Linux `/proc/<pid>/cmdline` is
world-readable by default, so row two hands the value to every local user.

Row three is chosen. *(macOS `ps -Eww -p PID` was measured not to print environments at all on this
host, so the launcher's own environment is not exposed by `ps` here; on Linux
`/proc/<pid>/environ` is readable by the same uid and by root — reasoned, not measured.)*

**Two further measurements govern §4:**

- **The value is in `docker inspect` under all three transports.** *(Measured: `docker run -e
  MY_SECRET=hunter2`, then `docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}'`
  prints `MY_SECRET=hunter2`.)* This is irreducible. It is not a property of how we pass it; it is a
  property of the container having an environment.
- **`os.environ.pop()` closes the child route and does not close `/proc`.** *(Measured inside the
  image: after `os.environ.pop("KC_PROBE")`, a `python -I` child reads `None` from `os.environ`;
  `/proc/self/environ` **still contains** the value; `/proc/1/environ` **still contains** it and a
  `-I` child can read it. Under `--init`, `/proc/1/comm` is `docker-init` and its environ carries
  the value too.)* So popping is a real mitigation with a stated ceiling, not a fix.

### 2.4 Repository facts this SPEC stands on

| Fact | Evidence |
|---|---|
| The launcher is bash, macOS and Linux only | `coderunner:1`; `OS="$(uname -s)"` at `coderunner:34`; the `die` arms at `coderunner:95`, `coderunner:141` |
| `set -Eeuo pipefail` is live for the whole launcher | `coderunner:10` |
| Bootstrap sequence, and everything that happens before argument handling | `coderunner:156-160`, build at `coderunner:163-167`, Ollama at `coderunner:219` |
| The `--doctor` branch and its twelve printed fields | `coderunner:233-258`; fields at `:236`, `:237`, `:238`, `:239`, `:240`, `:241`, `:244`, `:246`, `:247`, `:248`, `:251`/`:254`, `:256` |
| `--doctor` sits **after** the whole bootstrap, and this is a recorded mistake | `product.md` §6.4 (`product.md:270-277`) |
| The launcher's one-line status helpers | `cyan`/`green`/`yellow`/`red` at `coderunner:21-24`; `warn()` at `coderunner:27` |
| Precedent for launcher-only variables that never reach the container | `coderunner:17-18`; `tech.md` §4.1 rows for `CODERUNNER_DOCKER_BOOT_TIMEOUT` and `CODERUNNER_BOOTSTRAP_LOG` |
| The run invocation to be amended, and why it is not `exec` | `coderunner:260-263` |
| Docker-group membership is granted by the launcher itself | `coderunner:83-84` |
| The image copies eight modules and misses none. ~~Five, missing two~~ — measured 2026-08-07 (§HISTORY), superseded by `fc19a07` and by this SPEC's own `keychain.py` | `Dockerfile:43` (`:34` when that measurement was taken) |
| The container user and the chowned store directory | `Dockerfile:42-46` |
| Declaration grammar and the `secret` type | `params.py:72-80`, `params.py:43-55` |
| The `ask` seam this SPEC works with rather than around | `params.collect_values()` at `params.py:184-207`; `pending_declarations()` at `params.py:123-133` |
| Values already present are skipped, by construction | `params.py:201-203` |
| Secret detection keys on the declared type, in four places | `params.py:297` (mask), `params.py:408` (redaction), `main.py:823` (`getpass`), `main.py:988` (policy gate) |
| The collection wiring to be amended | `_collect_params()` at `main.py:849-869` |
| Policy resolution, and the fact that it happens inside collection | `main.py:865` → `_resolve_param_policy()` at `main.py:833-846` → `settings.ensure_policy()` at `settings.py:346-375` |
| The policy is read back as `""` when never resolved | `main.py:981` |
| Redaction gate and the `never` capture skip | `main.py:987-993`, `main.py:1026-1028` |
| `settings.json` location, schema and version discipline | `settings.py:55`, `settings.py:63`, `settings.py:202-207` |
| Unknown extra keys are ignored **silently** | `settings.py:216-224` |
| The eleven environment variables `settings.json` may not shadow | `settings.py:95-109`; `main.py:69-73`, `main.py:90-99` |
| Coverage gate: two edits, both required | `pytest.ini:50-54`, `conftest.py:200-206`; the failure branch at `conftest.py:221-223` |
| The stdlib-only source-seam assertion the new module joins | `tests/test_source_seam.py:156-167` |
| CI pass floor | `MIN_PASSED = 469` at `.github/workflows/ci.yml:289` |
| One-line degradation convention | `product.md:138` (feature 20) |
| Stale-image hazard | `product.md` §6.3 (`product.md:263-268`); `coderunner:163` |

**Drift noted in passing, partly fixed and partly declined.**

`tech.md` §7.1's `main.py` citations predate the current file by a wide margin: it gives
`main.py:248-249`/`:262-269` for `run_python()` (now `main.py:455-521`), `main.py:285-286` for the
`rmtree` (now `main.py:520`), and `main.py:135` for the prompt that forbids `input()` (now
`main.py:139`). `tech.md:538` cites `docker-compose.yml:67-68` for "the only `volumes` entry is a
named volume"; that entry is at `docker-compose.yml:74-75` and `:67-68` are `stdin_open` and `tty`.
This SPEC edits two of those rows and fixes the citations in the rows it edits (§7 item 7); it does
not sweep the rest.

`structure.md` is further behind than that — its tree lists neither `memory.py`, `recall.py`,
`vectorstore.py`, `params.py` nor `settings.py`, its §5.1 states that "`main.py` imports no
first-party module" (contradicted at `main.py:49-51`), and its §6 states "There is none" of the test
suite that now has ten files and a 469-test CI floor. That is three SPECs of drift and rewriting it
is not this SPEC's work; recorded here so the next person does not read it as current (§8 item 8).

---

## 3. Design decisions

Seven questions, each answered with a recommendation and the price of that recommendation.

### 3.1 D1 — Only **pre-declared** secrets are fetched, at launch, and everything else prompts

**Recommendation.** The launcher fetches, before the container starts, the value of every name the
user has registered with `--set-secret`. Each is exported and passed with `-e CODERUNNER_SECRET_<NAME>`
(name only — §3.3). Inside the container, a `# @param NAME : secret = "…"` whose uppercased name
matches an exported variable is satisfied from it, silently. Anything else — a new name, a
non-`secret` type, a name the user never registered — prompts exactly as SPEC-INPUT-001 already
prompts.

This is the whole feature, and it is small on purpose, because §3.2 is what remains after the
alternative is removed.

**Eligibility is `type == secret` only.** Four separate behaviours in the existing code key on that
one predicate — the mask (`params.py:297`), the redaction set (`params.py:408`), the `getpass` route
(`main.py:823`) and the policy gate (`main.py:988`). Making keychain sourcing key on the **same**
predicate means one condition governs all five behaviours instead of two conditions that can
disagree. A user who stores `city` gets prompted for it anyway, because the model declared it `str`.

**Cost, stated plainly.** The feature helps only with values the user knew about in advance. The
first time a model asks for a key the user has not registered, they type it — and typing it does not
register it, because the container cannot write the host keychain (§3.2). So the workflow is: type it
once, notice, exit, run `--set-secret`, relaunch. That is a worse first-run experience than a design
that captured the value on first use, and there is no such design available here.

### 3.2 D2 — Rejected: a runtime channel out of the container

Worth naming because it is the design that would remove the cost in §3.1, and because the reason it
is rejected is structural rather than a matter of effort.

The candidates, all of which were considered:

| Candidate | Mechanism |
|---|---|
| Unix socket | The launcher runs a helper on the host; the socket is bind-mounted into the container; `main.py` writes a name and reads a value |
| Request file on the volume | The container writes a request to `/home/runner/.coderunner`; a host-side watcher answers it |
| `docker exec` callback | A backgrounded launcher subshell polls and injects values into the running container |

Each is rejected, and one sentence disposes of all three: **generated code runs as the same `runner`
uid as the REPL** (`Dockerfile:42-46`, `tech.md` §7.2, `product.md` §6.11), so **any capability
given to `main.py` at runtime is given to every model-written script in the same session.** A socket
`main.py` can query is a socket a generated script can query, and it does not answer only for names
the model declared — it answers for whatever it is asked. That turns the user's keychain into an
oracle addressable from inside the sandbox. The environment route exposes exactly the pre-declared
set; a runtime channel exposes the store.

Two of them fail a second time on their own terms:

1. **The socket needs a host bind mount.** `tech.md` §7.1 records "No host bind mounts — the
   `coderunner` service's only `volumes` entry is a **named** volume … No host path is projected
   into the container, and the host filesystem remains unreachable." That is a documented control
   and this feature is not worth reversing it.
2. **The request-file variant writes the secret to `coderunner_app_data`**, the volume that survives
   `--rm` (`docker-compose.yml:74-75`, `:114-115`). That is the precise failure SPEC-INPUT-001's N3
   closed for readline history — persistence "by a mechanism no capture policy inspects". Rebuilding
   it deliberately, three months after closing it, would be indefensible.

### 3.3 D3 — Transport: `-e NAME`, **name only**

**Recommendation.** The launcher exports each fetched value into its own environment and passes
`-e CODERUNNER_SECRET_<NAME>` with **no `=value`**. Compose reads the value from the launcher's
environment.

The evidence is the table at §2.3 and it is worth restating as three sentences:
`--env-from-file` **corrupts the value** (`$bc` vanished; measured). `-e NAME=value` publishes it to
the host process table for the whole session (measured; `coderunner:260-263` does not `exec`).
`-e NAME` is intact and absent from argv (measured).

**Cost.** The value lives in the launcher bash process's exported environment for the session. On
Linux that is `/proc/<pid>/environ`, readable by the same uid and by root; on macOS `ps -E` does not
print it (measured on this host) and there is no `/proc`. This is strictly narrower than argv and it
is not zero. It is also unavoidable under any transport that does not use a file, and the file
option is disqualified.

**One trap that will break every existing user if it is missed.** `coderunner:10` sets
`set -Eeuo pipefail`, `coderunner:1` is `#!/usr/bin/env bash`, and stock macOS resolves that to
`/bin/bash` **3.2.57**. *(Measured 2026-08-07.)* Under bash 3.2 with `set -u`, expanding an **empty**
array — `"${RUN_ENV[@]}"` — is a fatal `unbound variable` and the script exits 1. A user with no
stored secrets has an empty array on **every launch**. The guard is
`${RUN_ENV[@]+"${RUN_ENV[@]}"}` or an explicit `(( ${#RUN_ENV[@]} ))` branch; both were measured to
work on 3.2.57. This is a HARD requirement (N8) because the impact is total and the population is
"everyone who has not used the feature".

### 3.4 D4 — Where the name list lives: **the keychain**, not `settings.json`

The obvious place is `settings.json`. SPEC-INPUT-001 created it, `settings.py` reads it, it is
already versioned, and adding a `secrets: [...]` array would be four lines. It is the wrong place,
for a reason that is measurable rather than aesthetic.

**`settings.json` is at `/home/runner/.coderunner/settings.json` (`settings.py:63`), inside the
`coderunner_app_data` named volume. The launcher is on the host and cannot read it.** On Linux
`docker volume inspect … --format '{{.Mountpoint}}'` yields a root-owned host path; on macOS under
Docker Desktop that path is inside the VM and does not exist on the host at all — the launcher
already prints it as a diagnostic (`coderunner:248`) precisely because it is otherwise opaque. To
read the file, the launcher would have to start a throwaway container
(`docker run --rm -v coderunner_app_data:… --entrypoint cat coderunner-ai:latest …`) **before** the
bootstrap that guarantees the image exists — a container start to decide whether to start a
container.

There is a second, independent reason. The name list must be consulted **before** the container
starts. `settings.json` is resolved **lazily, on the first parameterised turn**
(`settings.py:283-288`, `settings.py:346-375`), and resolving it can **ask the user a question**.
A host-side reader would be reading a file whose whole design assumes an in-container, mid-session
reader.

**Recommendation: the registry is an item in the keychain itself**, under the same service name, at
a fixed account (`__names__`), holding the registered names as text. `--set-secret NAME` adds the
name; `--forget-secret NAME` removes it. One code path on both platforms, zero host footprint beyond
the keychain the user already has, and no container start to read a list.

**Rejected within that: enumerate the keychain instead of keeping a registry.** On Linux
`secret-tool search --all service coderunner` would do it. On macOS the only enumeration is
`security dump-keychain`, which prompts per item and **exports the user's entire keychain** —
including every credential that has nothing to do with this program. Absolutely not.

**Cost of the registry: it can drift.** A user who deletes an item with
`security delete-generic-password` outside our subcommand leaves a stale name behind. The launcher
then fetches it, gets rc 44, and passes nothing — so the container prompts, which is the documented
fallback (§3.8). The drift is self-healing and costs one status line. Recorded rather than fixed.

**`settings.json` therefore gains no key and `schema_version` stays 1** (`settings.py:55`). That is
a decision, not an omission, and it is stated because "we looked and chose not to" is more useful
than silence. Two things follow for anyone who later disagrees:

1. A key added to a `schema_version: 1` file today is an **unknown extra key** and is ignored
   **silently** (`settings.py:216-224`). Adding `keychain_params` without bumping the version means
   writing a setting nothing reads and nothing complains about.
2. Bumping to `schema_version: 2` is a **one-way door for older builds**: `settings.py:202-207`
   refuses any file declaring a version higher than the build knows and falls back to `never`. A
   user who runs a new image once and then an old one loses capture until they delete the file.

**Precedence for a declared name, in full:**

`the turn's value cache` → `CODERUNNER_SECRET_<NAME>` → `prompt`

The cache wins first and that is not a formality: a value the user typed on attempt 1 must not be
replaced by a keychain value on attempt 2. `params.pending_declarations()` (`params.py:123-133`) and
the `if decl.name in values: continue` at `params.py:201-203` already enforce it; the keychain
prefill must run **through** that filter rather than around it.

### 3.5 D5 — How a secret gets in: a launcher subcommand that runs **before** the bootstrap

**Recommendation.** Three subcommands, dispatched immediately after `OS="$(uname -s)"`
(`coderunner:34`) and **before** `coderunner:157`:

| Subcommand | macOS | Linux |
|---|---|---|
| `--set-secret NAME` | `security add-generic-password -U -a NAME -s coderunner -w` (`-w` **last**, no value) | `secret-tool store --label="CodeRunner NAME" service coderunner name NAME` |
| `--forget-secret NAME` | `security delete-generic-password -a NAME -s coderunner` | `secret-tool clear service coderunner name NAME` |
| `--list-secrets` | read the `__names__` registry item | read the `__names__` registry item |

Each prints one line and exits. **None of them starts Docker.**

`--doctor` is the model for the argument handling and the anti-model for its placement. Its branch
is at `coderunner:233-258`, and `product.md` §6.4 records the consequence without softening it:

> The `--doctor` branch sits at `coderunner:233`, *after* the entire bootstrap at `coderunner:157-219`.
> Running `./coderunner --doctor` on a clean machine will therefore install Docker, start the daemon,
> build the image, start the Ollama sidecar, and pull a multi-GB model **before** printing a single
> diagnostic line. It is not a read-only health check.

Storing a password must not install Docker. The secret subcommands need no daemon, no image, no
compose, no Ollama and no model, and placing them before `coderunner:157` is the difference between
a two-second command and a first-run download measured in gigabytes.

**The launcher never handles the plaintext on the store path.** `security add-generic-password -h`
states that `-w` given **last, with no value**, causes `security` to prompt — so the OS reads and
masks the value itself, and it never appears in an argv, a bash variable, or the launcher's
environment. `secret-tool store` reads from stdin and has the same property. This is a genuinely
free win and it is worth not throwing away by "simplifying" to `-w "$value"`.

**Cost.** Three more branches in a launcher that had one, and an argument surface on a program that
`product.md` §6.9 correctly describes as having "no command-line interface". The subcommands must
also **exit** rather than fall through to `coderunner:263`, which forwards `"$@"` into a `main.py`
that parses nothing and discards it silently.

### 3.6 D6 — The container-side seam: prefill **through** `params.collect_values`, not around it

SPEC-INPUT-001 put collection in `params.py` behind an `ask` callable (`params.py:184-207`), and
that seam is exactly the right place to meet.

`params.collect_values()` already skips a name that is present in `values` (`params.py:201-203`), and
`params.pending_declarations()` already filters to names that are not (`params.py:123-133`). So the
entire mechanism is: **put the keychain value into `values` before `collect_values` is called.**
Nothing in `params.py` needs to know the keychain exists, `ask` is never invoked for a sourced name,
and `params.py`'s 100% gate is untouched.

The wiring lives in `_collect_params()` (`main.py:849-869`) and is roughly six lines:

```
pending  = params.pending_declarations(declarations, values)
if not pending: return pending
sourced  = keychain.prefill(pending, values, SECRETS)     # new
asked    = params.pending_declarations(pending, values)
if asked: status(announcement(asked))
_resolve_param_policy(session)                            # UNCONDITIONAL — see below
for name in sourced: status(f"{name} supplied from the keychain (not asked).")
if asked: params.collect_values(asked, _ask_param, values)
for line in params.confirmations(pending, values): status(line)
return pending
```

**Two things in that sketch are load-bearing and both are invisible when wrong.**

**(a) `_resolve_param_policy()` must become unconditional on `pending`, not conditional on `asked`.**
Today it sits at `main.py:865`, inside the block that runs when something needs prompting. If a turn
declares one `secret` and the keychain supplies it, nothing is prompted — and if policy resolution
is skipped, `param_session.policy` stays `None`, `main.py:981` reads the policy as `""`, the
redaction gate at `main.py:988` (`policy == settings.POLICY_SENSITIVE`) is **false**, and the `never`
capture skip at `main.py:1026` is **false**. A keychain-sourced secret echoed into stdout would then
be captured **unredacted**, under a policy the user chose, because no code asked what the policy was.
Every test in the suite stays green: the script runs, the answer streams, the turn is captured. This
is the AC-CAP-shaped hazard of this SPEC and **AC-POLICY** exists for it.

**(b) `pending` — not `asked` — is what is returned.** `main.py:974` accumulates the return value
into `param_declared`, which `main.py:987` feeds to `params.secret_values()` to build the redaction
set. A keychain-sourced declaration that is dropped from the return value is a secret that
redaction never sees.

**Cost.** The first-run capture-policy question can now fire on a turn where the user typed nothing
at all — they asked for the weather, and CodeRunner asks them how solution memory should treat
parameterised turns. That is correct (the policy governs capture, not prompting) and surprising.
Accepted, and recorded here so it is not "fixed" by making resolution conditional again.

**Where the values come from.** `keychain.load(os.environ)` runs **once, at `main.py` import**, and
**pops** each `CODERUNNER_SECRET_*` variable out of `os.environ` as it reads it. Import time and not
first use: `run_python()` passes no `env=` (`main.py:496-503`), so a child inherits whatever
`os.environ` holds when it starts, and any script run before the pop would see the value. Measured
(§2.3): the pop closes the child route completely and closes neither `/proc/self/environ` nor
`/proc/1/environ`. It is one line, it removes the trivially-discoverable route
(`print(os.environ)` in a generated script), and §4.1 states what it leaves open.

**Name mapping.** `CODERUNNER_SECRET_` + the declared name uppercased. Declared names are
`[A-Za-z_][A-Za-z0-9_]*` (`params.py:75`), every character of which is legal in an environment
variable name, so no escaping is needed and none is invented. Two names differing only in case
collide; `--set-secret` refuses the second one with a message rather than letting the container pick
a winner.

### 3.7 D7 — `--doctor` gains two fields: twelve become fourteen

`product.md:123` documents `--doctor` as printing **12 fields** and the branch prints exactly twelve
(`coderunner:236`, `:237`, `:238`, `:239`, `:240`, `:241`, `:244`, `:246`, `:247`, `:248`,
`:251`/`:254`, `:256`). Two more, in the same `printf '  %-16s : %s\n'` shape:

```
  keychain backend : security (/usr/bin/security)
  stored secrets   : api_key, weather_key (2)
```

`none` when neither client is on `PATH`; `unavailable (keychain locked)` when the registry read
returns non-zero. **Names only, never values** — and this is worth stating as a requirement (N5)
rather than assuming, because `--doctor` output is what a user pastes into a bug report.

`product.md:123`'s "12 fields" and its parenthesised list must change in the same commit as the
launcher. A documented count that is wrong is worse than no count.

**Cost, inherited rather than introduced.** The new fields sit in a branch that `product.md` §6.4
records as arriving after the entire bootstrap. `./coderunner --doctor` will still install Docker
before telling you whether your keychain works. Fixing that means moving `--doctor` earlier, which
changes the behaviour of an existing feature for reasons unrelated to this SPEC, and it is scoped out
(§8 item 6).

### 3.8 Degradation: never fail the session

`product.md:138` (feature 20) sets the convention — any fault produces **exactly one status line**
and a turn otherwise identical to the pre-feature product. Every keychain fault degrades to the
behaviour that existed before this SPEC: **the user is prompted.**

| Condition | Detected by | Behaviour | Line |
|---|---|---|---|
| No keychain client on `PATH` | `command -v` | Pass nothing. Every declaration prompts | one yellow line, once, at launch |
| Registry item absent (first ever run) | rc **44** | Pass nothing. **No line** — this is the state of a user who has never used the feature | none |
| Registered name has no item (drift, §3.4) | rc **44** | Pass nothing **for that name**; other names unaffected | one yellow line naming the name |
| Keychain locked | rc **128**, empty stdout | Pass nothing | one yellow line |
| User cancels the OS unlock or ACL prompt | non-zero rc, empty stdout | Pass nothing | one yellow line |
| Item exists but is empty | rc 0, empty stdout | Pass nothing — an empty secret is not a secret | one yellow line |
| `CODERUNNER_KEYCHAIN=0` | environment | Pass nothing, fetch nothing, probe nothing | one yellow line |

**One rule covers the first six: a name is supplied only if the client exits 0 and prints a
non-empty value.** Not "rc 0"; not "non-empty". Both. The two measured failures (rc 44 with a
message on stderr, rc 128 with nothing at all) are then handled by the same predicate as every
failure nobody has met yet.

**The line appears in the launcher's output, not in the turn**, because that is where the fetch
happens — before the banner, in `warn()`'s yellow (`coderunner:27`). A user who scrolls past it sees
only that they were prompted. That is a real cost and the mitigation is thin: the prompt itself is
the signal, and `--doctor` reports the backend and the registry. Deliberately **no** per-turn line
in the container: the alternative is a status line on every parameterised turn of every session,
which is how a warning becomes furniture.

**`CODERUNNER_KEYCHAIN` is launcher-only, and that is what keeps `docker-compose.yml` out of this
SPEC.** SPEC-INPUT-001's N7 records the trap: every variable in compose is written `${VAR:-default}`
(`docker-compose.yml:78-103`), so anything added there is **always set inside the container**. A
launcher-only variable — the pattern already used by `CODERUNNER_DOCKER_BOOT_TIMEOUT` and
`CODERUNNER_BOOTSTRAP_LOG` (`coderunner:17-18`, `tech.md` §4.1) — never reaches the container, never
needs a compose entry, and cannot spring that trap. `docker-compose.yml` is untouched (N7).

---

## 4. The security accounting

This is the section the SPEC exists for. It is modelled on `tech.md` §7.3, which states what the
sandbox does and does not protect and does not soften it.

### 4.1 Removed, retained, added

The environment route does **not** make the secret private. It **moves** the exposure.

**REMOVED — three places the value used to be, and now is not:**

| Removed | Why it was there | Evidence |
|---|---|---|
| The rendered prompt session on screen | The user typed it, at a `getpass` prompt, in front of whoever is looking at the terminal | `main.py:823-824` |
| The temp script on disk | `params.splice_prelude()` writes the value into `run.py` in the workdir | `params.py:372-390`, `main.py:482-483` — *the file is still written; what is removed is the user having to re-supply the value every session, and the window in which they might paste it into the wrong terminal* |
| readline history | Not removed by this SPEC — already closed by SPEC-INPUT-001's N3 via `getpass` | `main.py:799-825`, `params.py:252-271` |

*Stated precisely, because the loose version would be false:* the value still reaches `run.py` under
this SPEC, exactly as it does today, because §3.6 routes it through the same prelude. What this
feature removes is the **repetition** — the value is typed once, into the OS, rather than once per
session into a terminal.

**RETAINED — readable by generated code, and it must be:**

The script needs the value. `api_key` is a module-level name in `run.py` and any code in that script
can read it. That is not a defect; it is the feature. It was true under SPEC-INPUT-001 and it is
true here.

**ADDED — one place the value did not use to be:**

**Anyone who can query the Docker daemon can read it in plaintext.** Measured 2026-08-07:
`docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}'` prints
`MY_SECRET=hunter2`. Also, inside the container, `/proc/1/environ` carries it and is readable by
`runner` — which is the uid generated code runs as. `os.environ.pop()` at import removes the
`os.environ` route for children (measured) and removes neither `/proc` route (measured).

There is a **second** addition that is easy to miss and belongs in the accounting: the value is now
in the **host keychain**, which is a store no capture policy in SPEC-INPUT-001 inspects — the same
category of finding as N3's readline history. That one is intentional and is the entire point; it is
listed so that the sentence "nothing was stored" is never said about a session that used this
feature.

**Scope of the added exposure, stated exactly:** the container is `--rm` (`coderunner:263`,
`docker-compose.yml:109`), so the `Config.Env` record exists only while the session runs and is
destroyed with the container. It is transient. It is not absent.

### 4.2 The mitigating context, and why it is not an excuse

Access to the Docker daemon is root-equivalent on the host. Someone who can `docker inspect` can
`docker run -v /:/host` and read anything. *(Reasoned, not measured — but this project grants that
capability itself: `coderunner:83-84` adds the invoking user to the `docker` group "so we don't need
sudo for docker calls".)* The marginal exposure over what such an observer already has is therefore
**small**.

Three reasons that is context and not a defence:

1. **Small is not zero.** An observer who has root-equivalent access but has not used it still learns
   the secret from a one-line command, with no filesystem forensics and no timing.
2. **On Linux the group is often wider than the person.** `usermod -aG docker` at `coderunner:84` is
   run for the invoking user, and on a shared machine the `docker` group can hold accounts that were
   never meant to hold this key.
3. **"They could have got it anyway" is the argument that ends every accounting.** It is true of the
   memory store too (`tech.md` §7.2 declines to use it there, and says so: *"This is not a privilege
   escalation … What is new is durability."*). The same discipline applies: name the capability, name
   what is new, and do not let the first cancel the second.

### 4.3 Honest summary

> `./coderunner --set-secret` keeps a value in your operating system's credential store instead of
> in your fingers. While a session is running, that value is present in the container's environment,
> where **anyone able to query the Docker daemon can read it in plaintext with `docker inspect`**,
> and where the generated code that needs it can read it — as it must. The container is `--rm`, so
> the record is destroyed when the session ends.
>
> This feature does **not** make a secret private. It removes the need to retype it and it adds a
> reader: the Docker daemon. Docker-daemon access is already root-equivalent on the host, so the
> marginal exposure is small — and it is not zero.
>
> If you need a secret that the Docker daemon cannot see, do not use this feature. Type it at the
> prompt, where SPEC-INPUT-001 already routes it through `getpass` and keeps it out of readline
> history, out of the rendered script, and — under the `sensitive_excluded` or `never` capture
> policies — out of solution memory.

That paragraph is the requirement (U6). It goes into `README.md` and `tech.md` §7.2 **unsoftened**,
and no documentation anywhere may state or imply that this feature makes a secret private.

### 4.4 Interaction with SPEC-INPUT-001's capture policy

The brief that produced this SPEC put it as: *a keychain-sourced value never passes through the
prelude at all if env is used, which changes what `sensitive_excluded` governs.* That is true of one
design and false of the one recommended here, and the difference is worth being exact about because
it decides how much of SPEC-INPUT-001 survives.

**Under env-direct** — generated code reads `os.environ["CODERUNNER_SECRET_API_KEY"]` itself — the
value never enters the prelude, `params.render_prelude()` never sees it, `params.secret_values()`
(`params.py:398-413`) returns an empty list because `values` is empty, and **`sensitive_excluded`
governs nothing at all**: the redaction gate at `main.py:988` has no secrets to redact and the turn
is captured with whatever the script printed. That is a silent, total loss of the policy. It is also
the design SPEC-INPUT-001 §3.7 already rejected, on the separate ground that it makes the model write
`os.environ["…"]` instead of a bare name.

**Under env→prelude** — recommended, §3.6 — the value enters `values` before `collect_values`, so
everything downstream is byte-for-byte the SPEC-INPUT-001 path: `render_prelude()` emits it through
the single `_literal()` site (`params.py:309-324`), `secret_values()` collects it because the
declaration type is `secret`, redaction runs at `main.py:987-993`, capture-by-construction holds
because `code` is still never reassigned (`main.py:963-966`), and `never` still skips
`_capture_turn()` at `main.py:1026-1028`.

**So what actually changes is not what `sensitive_excluded` governs. It is what it can be truthfully
said to mean.**

| Statement | Before this SPEC | After |
|---|---|---|
| "The secret is not in solution memory" (under `sensitive_excluded`, modulo the transform limit at `params.py:416-431`) | true | **still true** |
| "The secret is not in readline history" | true | **still true** |
| "The secret is not on disk after the session" | true | **still true of the container**; the host keychain now holds it, by the user's own instruction |
| "The secret is not readable by anything outside this process tree" | true-ish | **false** — `docker inspect` |
| "This turn was not stored" (under `never`) | true, and complete | **true, and no longer complete** — the value is in `Config.Env` for the session regardless of policy |

The last row is the one that must reach the user. `never` was offered in SPEC-INPUT-001 as the option
for people who need a guarantee rather than a reduction (`params.py:416-431` states the substring
limit; `spec.md` §3.6 of that SPEC says so directly). For a keychain-sourced value, `never` is still
the strongest capture policy and it no longer bounds the exposure, because the exposure is now
outside the store the policy governs. **A user who chose `never` deserves to be told this.**
Requirement U6 and criterion **AC-EXPOSE** are what make sure they are.

One consequence for the code: because the redaction set is built from `values` via
`params.secret_values()`, and because §3.6 puts keychain values into `values`, **a keychain-sourced
secret is redacted from stdout exactly like a typed one** — which is the desirable outcome and comes
for free from meeting at the `ask` seam rather than beside it.

---

## 5. Where the code belongs

`keychain.py` — a new module, stdlib-only, gated at **100%**, joining `params.py` and `settings.py`
as a leaf. Its whole content is: map declarations to variable names, read them out of a mapping, pop
them, and report which ones were filled. There is no I/O, no subprocess, and no platform branch —
all of that is in bash, which is the answer to the question this SPEC started from.

It is a third module rather than a function in `params.py` for one reason: `params.py`'s file banner
(`params.py:18-28`) and its source-seam tests (`tests/test_source_seam.py:202-229`) are built around
the claim that it has exactly one site where a user value becomes source text. Adding an
environment reader to it does not break that claim but does dilute the file whose point is to be
readable in one sitting.

**Adding a gated module still takes two edits, and forgetting one still fails loudly.**
`pytest.ini:50-54` lists the `--cov` targets; `conftest.py:200-206` lists the floors. A module in
the second but not the first makes `cov.report(include=["keychain.py"])` raise, which
`conftest.py:221-223` records as `coverage unavailable` and the session **fails**. That is the right
direction for this mistake to fail in.

**And a third edit, which is new to this SPEC and is the one this repository has already got wrong
once.** `keychain.py` must be added to the `COPY` line at `Dockerfile:43`, or this SPEC ships a
module that is not in the image that runs it.

*As written, this paragraph required three names, not one: `params.py` and `settings.py` were
measured absent from `coderunner-ai:latest` and `import params` inside it raised (§HISTORY).
`fc19a07` added them after that measurement was taken. The sentence "has already got wrong once" is
left standing because it is the whole reason for the edit — the omission cost a SPEC's worth of
latency, and nothing about the mechanism that allowed it has changed.*

`main.py`'s share stays wiring, per SPEC-INPUT-001 §5.3: it is not covered by any floor
(`pytest.ini:50-54`, `conftest.py:200-206`), so every decision — which names are eligible, what a
missing value means, what gets popped — lives in `keychain.py`, and `main.py` gets the six lines at
§3.6 and the module-level `keychain.load()` call.

The launcher has no coverage gate and no test harness of any kind. That is inherited, it is not
addressed here, and it is the reason N8 (the bash 3.2 array trap) is written as a requirement rather
than left to a test.

---

## 6. EARS requirements

All five requirement types are represented.

### 6.1 Ubiquitous — always true

| # | Requirement |
|---|---|
| **U1** | A keychain-sourced value **shall always** reach the generated script by the same path as a typed one — into `values`, then through `params.render_prelude()` (`params.py:327-342`) and `params.splice_prelude()` (`params.py:372-390`) as a `repr()`-produced literal. It **shall never** be read by generated code from `os.environ`. |
| **U2** | Every property established by SPEC-INPUT-001 **shall always** continue to hold unchanged: literal safety (U1), the child's stdin untouched (U2), `code` never reassigned before capture (U3/N4), and redaction at all three sinks (E6). This SPEC amends the **source** of a value, never its handling. |
| **U3** | A name **shall always** be supplied from the keychain only if the client exits **0** *and* prints a **non-empty** value. Either condition failing **shall** mean the name is not supplied and the container prompts. |
| **U4** | Every keychain fault **shall always** produce **at most one** status line per launch and a session otherwise identical to the pre-feature product, matching `product.md:138`. No fault **shall** abort the launcher or the session. |
| **U5** | `--doctor` **shall always** report the keychain backend and the registered names, and **shall never** print a stored value. |
| **U6** | Documentation **shall always** state that this feature does not make a secret private, that a value in the container's environment is readable via `docker inspect`, and that `never` no longer bounds the exposure (§4.3, §4.4). No text anywhere **shall** state or imply the contrary. |

### 6.2 Event-driven — WHEN … THEN …

| # | Requirement |
|---|---|
| **E1** | **WHEN** the launcher starts and a keychain client is on `PATH` and `CODERUNNER_KEYCHAIN` is not `0`, **THEN** it **shall** read the `__names__` registry item and fetch each registered name, **before** `coderunner:157`'s bootstrap is reached for the run path and before `compose run` at `coderunner:263`. |
| **E2** | **WHEN** at least one value is fetched, **THEN** each **shall** be exported into the launcher's environment and passed as `-e CODERUNNER_SECRET_<NAME>` — **name only, no `=value`** — because `-e NAME=value` was measured to publish the value to the host process table and `--env-from-file` was measured to corrupt it (§2.3). |
| **E3** | **WHEN** `main.py` is imported, **THEN** `keychain.load()` **shall** read every `CODERUNNER_SECRET_*` variable and **pop** it from `os.environ`, so that no child started by `run_python()` (`main.py:496-503`, which passes no `env=`) can read it from `os.environ`. |
| **E4** | **WHEN** an attempt declares a parameter of type `secret` whose uppercased name matches a loaded variable **and** the name is not already in the turn's value cache, **THEN** the value **shall** be placed into `values` before `params.collect_values()` is called, and `ask` **shall not** be invoked for that name. |
| **E5** | **WHEN** a value is supplied from the keychain, **THEN** exactly one status line **shall** name the parameter and its source, and the existing masked confirmation line (`params.py:296-301`) **shall** still be emitted, so a sourced secret is as visible in the transcript as a typed one. |
| **E6** | **WHEN** `./coderunner --set-secret NAME` is invoked, **THEN** the launcher **shall** store the value using the platform client with the value read by that client — `-w` given **last with no value** on macOS, stdin on Linux — **shall** add `NAME` to the registry, and **shall exit** without invoking `ensure_docker_installed` (`coderunner:158`) or anything after it. |
| **E7** | **WHEN** `./coderunner --doctor` is invoked, **THEN** it **shall** print fourteen fields — the existing twelve plus the keychain backend and the registered names — and `product.md:123` **shall** be updated in the same change. |

### 6.3 State-driven — IF/WHILE … THEN …

| # | Requirement |
|---|---|
| **S1** | **IF** an attempt has at least one pending declaration, **THEN** the capture policy **shall** be resolved, **whether or not anything is prompted**. Resolution conditional on prompting leaves `param_session.policy` as `None`, makes `main.py:981` read `""`, and silently disables both the redaction gate (`main.py:988`) and the `never` capture skip (`main.py:1026`) for a turn whose values came entirely from the keychain. |
| **S2** | **IF** a declared name is already in the turn's value cache, **THEN** the cached value **shall** win over the keychain. A value typed on attempt 1 **shall not** be replaced on attempt 2. |
| **S3** | **IF** a declaration's type is not `secret`, **THEN** it **shall not** be eligible for keychain sourcing, regardless of whether a matching variable exists. One predicate governs the mask (`params.py:297`), the redaction set (`params.py:408`), the `getpass` route (`main.py:823`), the policy gate (`main.py:988`) and this. |
| **S4** | **IF** no keychain client is present, the keychain is locked (measured rc **128**), an item is missing (measured rc **44**), the user cancels the OS prompt, the value is empty, or `CODERUNNER_KEYCHAIN=0`, **THEN** the affected names **shall** simply not be supplied and the container **shall** prompt exactly as it does today. The session **shall not** fail. |
| **S5** | **IF** the registry names a secret that no longer has an item, **THEN** that name alone **shall** be skipped with one line and every other name **shall** still be fetched. Registry drift **shall not** be fatal and **shall not** be repaired automatically. |
| **S6** | **WHILE** the set of names to pass is empty — the state of every user who has not used this feature — **THEN** the `compose run` invocation at `coderunner:263` **shall** be byte-for-byte what it is today. Measured: `/bin/bash` on stock macOS is 3.2.57, and under `set -u` (`coderunner:10`) expanding an empty array is a fatal `unbound variable`. |

### 6.4 Unwanted — shall not

| # | Requirement |
|---|---|
| **N1** | There **shall be** no runtime channel out of the container — no bind-mounted socket, no request file on `coderunner_app_data`, no `docker exec` callback. Generated code runs as the same `runner` uid as the REPL (`Dockerfile:42-46`, `tech.md` §7.2), so any such channel is an oracle addressable from inside the sandbox (§3.2). |
| **N2** | Generated code **shall not** be instructed or expected to read `os.environ`. The `SYSTEM_PROMPT` at `main.py:140-148` is **unchanged**: the model declares `# @param` and uses a bare name, and does not learn that a keychain exists. |
| **N3** | `--env-from-file` **shall not** be used. Measured 2026-08-07: it expanded `$bc` out of `sk-a$bc de#f "g" \h`, losing three characters silently. A transport that corrupts a credential is not a transport. |
| **N4** | `-e NAME=value` **shall not** be used. Measured: the value appears in `ps -Ao args` for the lifetime of the `docker compose` process, which under `coderunner:260-263` is the whole session. |
| **N5** | `--doctor`, `--list-secrets` and every status line **shall not** print a stored value. Names only. `--doctor` output is what a user pastes into a bug report. |
| **N6** | The secret subcommands **shall not** run the bootstrap. `--set-secret`, `--forget-secret` and `--list-secrets` need no daemon, no image and no model, and `product.md` §6.4 records what happens when a subcommand is placed after `coderunner:157`. |
| **N7** | `docker-compose.yml` **shall not** be modified. `CODERUNNER_KEYCHAIN` is launcher-only, in the pattern of `coderunner:17-18`, so no variable needs adding and SPEC-INPUT-001's N7 trap — `${VAR:-default}` making an override permanently active — cannot be sprung. |
| **N8** | An empty array **shall not** be expanded unguarded in the launcher. `coderunner:10` sets `set -Eeuo pipefail`; `/bin/bash` on stock macOS is 3.2.57; measured, `"${A[@]}"` with `A=()` is a fatal `unbound variable`. The guard is `${A[@]+"${A[@]}"}` or a `(( ${#A[@]} ))` branch, both measured to work. |

### 6.5 Optional — where possible

| # | Requirement |
|---|---|
| **O1** | **Where** an operator needs to disable the feature for one launch without deleting anything, `CODERUNNER_KEYCHAIN=0` **should** be honoured. Launcher-only by design (N7), so it never reaches `main.py` and never needs a compose entry. |
| **O2** | **Where** `--set-secret` is given a name whose uppercased form collides with an already-registered name, the launcher **should** refuse with a message naming both, rather than letting the container silently pick one value for two parameters. |
| **O3** | **Where** `/params` prints its report (`settings.py:424-436`), it **should** name which parameters of the current turn came from the keychain, since that is the natural place a user will look for "why was I not asked". |
| **O4** | **Where** a stored value ends in a newline, it **may** be delivered without it: `$(security … -w)` strips trailing newlines and this SPEC does not work around it. Non-UTF-8 values are likewise unsupported. Recorded rather than fixed; `-X`/hex round-tripping is a different SPEC. |

---

## 7. In scope

1. `keychain.py` — declaration-to-variable-name mapping, reading from a mapping, popping from
   `os.environ`, reporting filled names. New module, stdlib-only, gated at **100%**.
2. `main.py` wiring only: a module-level `keychain.load()` at import, and the six lines in
   `_collect_params()` (`main.py:849-869`) described at §3.6 — including making
   `_resolve_param_policy()` unconditional on `pending` (S1).
3. `coderunner`: the `--set-secret` / `--forget-secret` / `--list-secrets` branch placed **before**
   `coderunner:157`; the fetch loop and the `-e NAME` array; the guarded array expansion at
   `coderunner:263` (N8); two new `--doctor` fields.
4. `conftest.py:200-206` and `pytest.ini:50-54` — two edits admitting `keychain.py` to the gate.
5. `tests/test_source_seam.py:156-167` — add `keychain.py` to the stdlib-only assertion.
6. **`Dockerfile:34` — add `keychain.py`, and add the missing `params.py` and `settings.py`.**
   Measured absent from `coderunner-ai:latest`; the omission is inherited, and this SPEC cannot ship
   a module into an image that does not contain it.
7. `.github/workflows/ci.yml:289` — raise `MIN_PASSED` from 469 to the count **measured** after the
   tests land.
8. Documentation: `README.md` (the subcommands and §4.3's honest summary verbatim); `tech.md` §7.2
   (the `docker inspect` sink) and §7.1 (fix the two stale citations in the rows this SPEC touches —
   `main.py:135`→`:139`, `docker-compose.yml:67-68`→`:74-75`); `product.md` §4 (the new feature; and
   `product.md:123`'s "12 fields" → 14) and §6 (the added exposure).

## 8. Out of scope

1. **Encryption at rest inside the container.** Out by **impossibility**, not preference. Measured
   (K1): the image's crypto-adjacent stdlib is `crypt`, `ssl`, `hashlib`, `hmac`, `secrets` — all
   one-way or transport-only. A stdlib-only cipher means a hand-rolled cipher, which is worse than
   none because it looks like protection. `tech.md` §7.2 already states there is no encryption at
   rest and none planned; this SPEC does not open it.
2. **Windows.** `coderunner:1` is `#!/usr/bin/env bash`, `coderunner:34` reads `uname -s`, and the
   `case` statements at `coderunner:92-96` and `coderunner:138-142` `die` on anything that is not
   `Darwin` or `Linux`. macOS and Linux only, and that is the launcher's pre-existing boundary rather
   than a new one.
3. **Remote secret managers** — Vault, AWS Secrets Manager, 1Password, `gopass`. Each is a network
   dependency, a credential to reach the credential store, and a configuration surface. The question
   this SPEC answers is what can be done with **system libraries and no dependency**; a remote
   manager is the opposite of that answer.
4. **Any new Python dependency**, including `keyring`. `requirements.txt` is six lines and
   `tech.md` §2 treats each one as load-bearing. `keychain.py` imports nothing outside the stdlib and
   the source-seam test at `tests/test_source_seam.py:156-167` will assert it.
5. **Capturing a typed value into the keychain on first use.** It would remove §3.1's stated cost and
   it requires the container to write the host keychain — §3.2's rejected channel, by another name.
6. **Moving `--doctor` before the bootstrap.** `product.md` §6.4 records the defect and this SPEC's
   new fields inherit it. Fixing it changes the behaviour of an existing feature for reasons
   unrelated to this SPEC.
7. **Non-UTF-8 and trailing-newline-bearing secrets.** O4 records the limit. `security -X` exists;
   plumbing hex through bash, compose and Python for a case nobody has hit is not warranted.
8. **Rewriting `structure.md`.** It is three SPECs behind (§2.4). Bringing it current is a documented
   task for whoever owns documentation, not a rider on a `LOW`-priority feature.
9. **A test harness for the launcher.** There is none today, for any of the 263 lines. N8 exists
   because the trap it names cannot be caught by a test that does not exist.
10. **Any change to `docker-compose.yml`.** N7.

---

## 9. Traceability

| Artefact | Location |
|---|---|
| Requirements | this file, §6 (U1–U6, E1–E7, S1–S6, N1–N8, O1–O4) |
| Design decisions with costs | this file, §3 (D1–D7) |
| The rejected runtime channel | this file, §3.2 |
| The transport measurement that chose `-e NAME` | this file, §2.3 |
| The security accounting and the honest summary | this file, §4 |
| Task decomposition, critical path, risks | `.moai/specs/SPEC-KEYCHAIN-001/plan.md` |
| Acceptance criteria | `.moai/specs/SPEC-KEYCHAIN-001/acceptance.md` |
| The SPEC this extends | `.moai/specs/SPEC-INPUT-001/spec.md` |
| The seam being met | `params.py:123-133`, `params.py:184-207`, `params.py:201-203` |
| The wiring being amended | `main.py:849-869`, `main.py:865`, `main.py:974`, `main.py:981`, `main.py:987-993`, `main.py:1026-1028` |
| The launcher sites | `coderunner:34`, `coderunner:156-160`, `coderunner:233-258`, `coderunner:260-263` |
| The image line that must gain three modules | `Dockerfile:34` |
| Gate files to be amended | `pytest.ini:50-54`, `conftest.py:200-206`, `tests/test_source_seam.py:156-167` |
| CI floor to be raised | `.github/workflows/ci.yml:289` (`MIN_PASSED = 469`) |
| Explicitly not amended | `docker-compose.yml` (N7); `SYSTEM_PROMPT` at `main.py:140-148` (N2); `settings.json` schema (`settings.py:55`, D4) |
| Documentation to be corrected | `product.md:123`, `product.md` §4 and §6; `tech.md` §7.1 and §7.2; `README.md` |
| Project context | `.moai/project/product.md`, `.moai/project/structure.md`, `.moai/project/tech.md` |

| Requirement group | Primary acceptance criteria |
|---|---|
| U6, §4.1, §4.4 | **AC-EXPOSE** |
| U1, U2, E3, E4, S2, S3, N2 | **AC-SOURCE** |
| S1 | **AC-POLICY** |
| U3, U4, S4, S5 | **AC-DEGRADE** |
| E1, E6, N6 | **AC-BOOT** |
| E2, N3, N4 | **AC-TRANSPORT** |
| S6, N8 | **AC-LAUNCH** |
| §7 item 6 | **AC-IMAGE** |
| U5, E7, N5 | **AC-DOCTOR** |
