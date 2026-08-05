# CodeRunner.AI — Product Overview

> Scope note: this document describes the CodeRunner.AI product only — the files
> `coderunner`, `main.py`, `tools.py`, `Dockerfile`, `docker-compose.yml`,
> `requirements.txt`, `README.md`, `LICENSE`. The `.claude/` and `.moai/`
> directories (including `CLAUDE.md`) are AI-agent tooling checked into the same
> repository and are **not** part of the product.

---

## 1. Identity

| Field | Value |
| --- | --- |
| Project name | CodeRunner.AI (`main.py:10`) |
| Author | kurapa \<kurapa@kurapa.com\> (`main.py:14`) |
| License | Apache License 2.0 (`LICENSE:1-3`) |
| Runtime | Python 3.11+, Docker-only, ephemeral `--rm` (`main.py:16`, `Dockerfile:9`) |
| Repository state | 2 commits, no tags, no releases |

### Value proposition

> "An AI that doesn't just stop at coding without token worries, but takes
> responsibility all the way through to execution (Run)." — `README.md:3`

CodeRunner.AI is a **local, agentic Python code interpreter powered by LLaMA via
Ollama** (`README.md:5`). It reasons about a task, writes Python, executes that
Python in a sandboxed subprocess inside an ephemeral Docker container, reads the
real stdout/stderr back, and self-corrects on failure — with no paid API key.

---

## 2. The problem it solves

### 2.1 Code generation stops one step short of an answer

A generic chat assistant emits code and hands the user the burden of running it,
reading the traceback, and pasting the failure back. CodeRunner.AI closes that
loop mechanically:

- The last fenced Python block in the model's reply is extracted automatically
  (`extract_last_python_block()`, `main.py:218-220`).
- It is executed for real (`run_python()`, `main.py:244-286`).
- On success, the captured stdout is re-injected into the conversation as a
  synthetic user message with the instruction *"Please provide the final Answer
  to the user in Markdown"* (`main.py:495-499`), forcing the final answer to be
  **grounded in a value that was actually computed**, not predicted.
- On failure, stderr and stdout are re-injected with *"Diagnose briefly, then
  emit a corrected Python block"* (`main.py:533-539`) and the loop retries.

### 2.2 No paid API key, no data egress to a model vendor

Inference runs against an Ollama server. `docker-compose.yml:15-27` bundles
`ollama/ollama:latest` as a sidecar on the internal compose network with **no
host port published** (`docker-compose.yml:21`), and the app container talks to
it at `http://ollama:11434` (`docker-compose.yml:70`). Model weights persist in
the named volume `coderunner_ollama_data` (`docker-compose.yml:104-106`), so the
multi-GB pull happens once (`coderunner:206-207`).

### 2.3 Zero-setup — and, since solution memory, no longer zero-residue

`./coderunner` will install Docker if it is missing (`coderunner:36-99`), start
the daemon if it is stopped (`coderunner:101-143`), build the image if it is
absent (`coderunner:163-167`), start Ollama and pull both the chat model and the
embedding model (`coderunner:191-217`), run the session, and then stop the
Ollama sidecar so it releases RAM (`coderunner:222-231`). The app container
itself is still `--rm` (`coderunner:263`).

**The "zero residue" half of that claim is no longer true, and this document
does not soften it.** Solution memory defaults ON (C4, `docker-compose.yml:75`)
and persists every successful turn to the Docker named volume
`coderunner_app_data`, mounted at `/home/runner/.coderunner`
(`docker-compose.yml:67-68`, `:107-108`). What is written is the task text, the
model's reasoning, the executed script and its real stdout — unencrypted, on the
host, surviving the container.

| Residue | Measured |
| --- | --- |
| Volume at two records | 32.4 KB |
| Volume at the 100,000-record cap, typical | **≈0.9 GB** — 618 MB of FLAT vectors plus ~8 KB/record of text |
| Volume at the cap, worst case under C11 truncation | ≈1.4 GB (V4 §5) |
| Container image | **273 MB → 754 MB** — `pymilvus[milvus_lite]` and its transitive numpy |
| `coderunner_ollama_data`, additional | 274 MB for `nomic-embed-text:latest` |

The user's levers, all documented in `README.md`:

- `/memory` reports the store path, the record count and the recursive on-disk
  size; `/memory list` shows the content.
- `/memory clear --yes` empties the store; `docker volume rm
  coderunner_app_data` destroys it.
- `CODERUNNER_MEMORY=0` disables capture, retrieval and store creation, and the
  launcher then skips the 274 MB embedding-model pull (`coderunner:209-217`).
  It does **not** shrink the image — the dependency is baked in regardless.

---

## 3. Target audience

| Audience | Why it fits |
| --- | --- |
| Developers who want a local, offline-capable code interpreter | Whole stack runs on the machine; only the generated scripts touch the network |
| Engineers without (or unwilling to pay for) a hosted LLM API key | `README.md:5` — "without a paid API key" |
| Users on machines with no prior Docker/Ollama setup | Launcher performs the entire bootstrap (`coderunner:36-219`) |
| People who need a *verified* numeric/factual answer rather than a plausible one | Answers are produced only after real stdout is fed back (`main.py:492-508`) |
| Terminal-first users | Rich TUI with live streaming panels, no browser, no web server (`main.py:37-44`) |

**Not** the target audience: anyone needing to run untrusted or adversarial
prompts against a sensitive host. See Known Limitations (Section 6) and the
sandboxing note at `README.md:116`.

---

## 4. Core features

Twenty user-visible behaviors, each mapped to the code that implements it.

| # | Feature | Implementation | Location |
| --- | --- | --- | --- |
| 1 | **One-command launch** — `./coderunner` performs the full bootstrap and drops the user into the REPL | bootstrap sequence + `compose run --rm` | `coderunner:156-219`, `coderunner:263` |
| 2 | **Silent Docker install** — installs Docker Desktop (macOS, Homebrew cask then DMG fallback) or Docker Engine (Linux, `get.docker.com`) when the binary is missing | `install_docker_macos()`, `install_docker_linux()`, `ensure_docker_installed()` | `coderunner:37-71`, `coderunner:73-86`, `coderunner:88-99` |
| 3 | **Headless daemon start** — starts a stopped Docker daemon and polls until ready (default 180 s budget) | `wait_for_docker()`, `start_docker_macos()`, `start_docker_linux()`, `ensure_docker_running()` | `coderunner:104-143` |
| 4 | **Bundled model server + one-time model pull** — brings up the Ollama sidecar, waits for `healthy`, pulls the model only if absent from the volume | `ensure_ollama_service()`; `ollama` and `model-pull` services | `coderunner:191-217`, `docker-compose.yml:15-49` |
| 5 | **Diagnostic report** — `./coderunner --doctor` prints 12 fields (OS/arch, docker binary, docker version, compose command, daemon reachability, image presence, ollama service status, pulled models, ollama volume mountpoint, **app volume mountpoint**, **embedding model presence**, bootstrap log path) and exits 0 | `--doctor` branch | `coderunner:233-258` |
| 6 | **Automatic teardown** — on exit/INT/TERM, removes stray app containers and stops the Ollama sidecar to reclaim RAM while preserving the model volume | `cleanup()` + `trap ... EXIT INT TERM` | `coderunner:222-231` |
| 7 | **Session banner** — panel showing product name, active model, Ollama host, and execution timeout | `show_banner()` | `main.py:337-358` |
| 8 | **Interactive REPL** — rule-separated turn loop, blank input skipped, `/exit`, `/quit`, `:q` terminate | `repl()` | `main.py:623-667`, exit words at `main.py:649` |
| 9 | **Arrow-key prompt history** — readline wired for both GNU readline and macOS libedit, capped at 1000 entries, written back on exit via `atexit` | `_install_history()`, `_prompt_user()` | `main.py:585-612`, `main.py:615-620`, cap at `main.py:70` |
| 10 | **Live streaming reasoning** — the model's tokens render incrementally as Markdown inside a bordered `Thought · attempt N` panel at 24 fps | `stream_llm()`, `render_stream()` | `main.py:178-190`, `main.py:193-207`, invoked at `main.py:472-476` |
| 11 | **Dual protocol (CODE vs DIRECT)** — computational tasks produce a fenced Python block; conversational questions are answered directly with no execution | `SYSTEM_PROMPT` protocol spec; the "no code block" early return | `main.py:100-151`, branch at `main.py:479-482` |
| 12 | **Generated-script display** — the extracted code is shown in a Monokai syntax panel with line numbers before it runs | `show_code()` | `main.py:302-310`, called at `main.py:484` |
| 13 | **Sandboxed execution with wall-clock cap** — code is written to a fresh temp directory, run as a separate isolated-mode process, and the directory is destroyed unconditionally afterwards | `run_python()` | `main.py:244-286` |
| 14 | **Execution result panel** — green `Execution OK (rc=N)` with stdout, red `Execution FAILED (rc=N)` with stderr, or red `Execution TIMEOUT` | `show_exec_result()` | `main.py:313-334` |
| 15 | **Bounded agentic self-correction** — on failure, stderr+stdout are fed back and the model retries, up to `CODERUNNER_MAX_RETRIES` attempts per turn; on success a second LLM pass produces the grounded `Answer` | `agentic_turn()` | `main.py:427-541`; retry feedback `main.py:527-539`; grounded answer `main.py:492-508` |
| 16 | **Capture of successful turns** — task, reasoning, executed script and real stdout are persisted with an embedding of the task, deduplicated by task hash, truncated to ~8 KB per record, and pruned oldest-first at the 100,000-record cap | `_capture_turn()` → `vector_for_capture()` → `remember_success()` → `VectorStore.insert()` | `main.py:394-424` (called at `:515`), `recall.py:205-236`, `recall.py:239-270`, `vectorstore.py:362-422` |
| 17 | **Semantic recall and few-shot injection** — the new task is embedded, the most similar past task above a 0.65 cosine floor is retrieved, and the stored solution is inserted as one ephemeral `system` message before the user's message on attempt 1 only. **The stored code is never executed**; the block is framed as material to adapt or ignore | `recall_for_task()`, `format_recall_block()`, `inject_recall()` | `recall.py:109-169`, `memory.py:379-387`, `memory.py:390-404`; injection at `main.py:448`, `main.py:466-470` |
| 18 | **Zero-cost cold start** — on an empty store the embedding call is skipped entirely, so a fresh install pays no extra latency on its first turn | empty-store short-circuit in `recall_for_task()` | `recall.py:109-169` |
| 19 | **`/memory` command family** — `/memory` (path, counts, embed model, dimension, on-disk size, effective threshold/top-k/cap), `/memory list [n]`, `/memory forget <id>`, `/memory clear --yes`. Handled in the REPL; `agentic_turn()` is never invoked | `handle_memory_command()` and its `_emit_*` helpers | `memory.py:447-494`, `memory.py:497-567`; dispatch at `main.py:652` |
| 20 | **One-line degradation** — any memory fault (embedding backend down, store unopenable, volume unwritable, another session holding the store) produces exactly one status line and a turn otherwise identical to the pre-feature product | `retrieval_degraded()` classifier + the warning-suppression pair | `recall.py:172-202`, `main.py:384-391`, `main.py:444-446`, `main.py:515-523` |

### Supporting behaviors

- **Startup connectivity preflight** with a remediation panel listing the exact
  fix steps when Ollama is unreachable — `preflight()` (`main.py:573-582`),
  `_connection_help_panel()` (`main.py:553-570`). Exits with code 2 on failure
  (`main.py:628-629`).
- **Status ticker** — emoji + `[TAG]` + message lines that narrate each phase of
  the turn — `status()` (`main.py:294-299`).
- **Signal safety** — SIGTERM prints a panel and exits 0
  (`_install_signal_handlers()`, `main.py:670-676`); Ctrl+C at the prompt exits
  the REPL (`main.py:642-644`); Ctrl+C mid-turn aborts only that turn
  (`main.py:661-662`).

---

## 5. Use cases

### 5.1 Live data lookup (the README reference scenario)

Prompt: **"What's the current weather in Seoul in Celsius?"** (`README.md:61`)

Flow, as coded:

1. `agentic_turn()` appends the prompt (`main.py:433`) and streams the model's
   plan into the `Thought · attempt 1` panel (`main.py:472-476`).
2. The model follows the CODE protocol and is steered toward `wttr.in`'s JSON
   endpoint by the system prompt's explicit hint
   (`main.py:124-125`: `https://wttr.in/<city>?format=j1`).
3. The block is extracted (`main.py:479`), displayed (`main.py:484`), and
   executed (`main.py:487-488`).
4. stdout `Seoul is currently 4°C` is echoed in a green panel
   (`show_exec_result()`, `main.py:314-323`) and fed back
   (`main.py:495-499`).
5. The model returns the grounded `Answer` panel (`main.py:501-508`).

### 5.2 Factual lookup via Wikipedia

The system prompt directs the model at the Wikipedia REST summary API
(`main.py:126-127`) for factual questions, so "who/what/when" queries resolve
through a real HTTP fetch rather than model recall.

### 5.3 Open-ended web search fallback

When no structured API is known, the system prompt prescribes DuckDuckGo HTML
search parsed with BeautifulSoup — take the top `a.result__a` href, fetch that
page, extract the answer (`main.py:128-131`).

### 5.4 Deterministic computation on user-supplied data

The CODE protocol triggers whenever the task "requires computation on data the
user gave you, or logic/math you can execute" (`main.py:104-105`). Arithmetic,
parsing, text transforms, and date math are executed rather than guessed, and
the answer is derived from `print()`ed stdout (`main.py:134`).

### 5.5 Conversational / explanatory questions

"Explain X" style questions take the DIRECT protocol (`main.py:138-143`): the
model answers under an `Answer:` heading with no fenced block, `code` is `None`,
and the turn returns immediately after a `💬 [LLaMA] No code produced` status
line (`main.py:480-482`, `README.md:103`).

### 5.6 Self-correcting execution

If the first script raises, the red `Execution FAILED` panel is shown, stderr is
sent back, and attempt 2 begins from the model's diagnosis
(`main.py:527-539`, `README.md:101`).

---

## 6. Known limitations

These are verified against source. They are recorded deliberately and should not
be removed until the underlying code changes.

### 6.1 The `tools.py` helper is unreachable in practice

`run_python()` copies `tools.py` into every sandbox (`main.py:254-255`) and an
inline comment names the intended usage — *"`from tools import web_search`
resolves without PYTHONPATH"* (`main.py:257-258`). But `SYSTEM_PROMPT`
(`main.py:100-151`) **never mentions `tools.py` or `web_search`**. Its library
list is only "stdlib, requests, beautifulsoup4 (bs4), lxml" (`main.py:120`). The
model has no way to discover the helper, so all 99 lines of `tools.py` are
effectively dead code. This is the single most concrete disconnect in the
codebase.

### 6.2 Prompt history does not persist through the Docker path — **RESOLVED**

*Kept rather than deleted, because the gap was real and the fix is a single
independently-revertible line.*

The original defect: `_install_history()` reads, caps, and `atexit`-writes the
history file (`main.py:585-612`), defaulting to `~/.coderunner_history`
(`main.py:69`). In the container that resolved to
`/home/runner/.coderunner_history`, inside a `--rm` container
(`coderunner:263`) with no volume declared for the `coderunner` service.
History was discarded at the end of every session.

`docker-compose.yml:100` now sets
`CODERUNNER_HISTORY=/home/runner/.coderunner/history`, which lands the file
inside the `coderunner_app_data` volume, so arrow-key recall survives across
sessions. This was an **incidental** side effect of SPEC-MEMORY-001 — no
requirement, no acceptance criterion, no test — and the line carries a comment
saying so, precisely so it can be reverted on its own without touching solution
memory. Should it ever be reverted, this limitation returns exactly as written
above.

### 6.3 Stale-image hazard after editing source

`coderunner:163` builds only when `docker image inspect coderunner-ai:latest`
fails — i.e. only when the image is absent. Editing `main.py` or `tools.py` does
**not** trigger a rebuild; the launcher silently keeps running the old image
until the user manually runs `docker compose build coderunner`.

### 6.4 `--doctor` has heavy side effects

The `--doctor` branch sits at `coderunner:233`, *after* the entire bootstrap at
`coderunner:157-219`. Running `./coderunner --doctor` on a clean machine will
therefore install Docker, start the daemon, build the image, start the Ollama
sidecar, and pull a multi-GB model **before** printing a single diagnostic line.
It is not a read-only health check.

### 6.5 The sandbox is process-level, not privilege- or network-level

`README.md:116` states this plainly and the docs carry the same honesty.
Generated code runs as a separate non-root process with `-I` and a timeout, but
it retains full network egress (which the system prompt actively *encourages*,
`main.py:121-131`), can reach the `ollama` service directly on the compose
network, and can write to every source file in `/app` — `main.py`, `tools.py`,
`memory.py`, `recall.py`, `vectorstore.py` — because `/app` is chowned to
`runner` (`Dockerfile:42-45`). Since SPEC-MEMORY-001 it can also reach the
solution-memory volume; see §6.11. Do not run untrusted prompts.

### 6.6 Conversation history grows without bound

`Conversation.messages` (`main.py:161`) is appended on every assistant reply
(`main.py:477`, `main.py:508`) and on every synthetic feedback injection
(`main.py:499`, `main.py:539`). Nothing ever trims, summarizes, or windows it,
and there is no token counting anywhere in the codebase. Because each failed
attempt injects a full stderr+stdout dump, a few long turns can push a session
past the model's context window with no warning and no recovery path.

### 6.7 Retry exhaustion yields nothing at all

After `MAX_RETRIES` attempts, `agentic_turn()` prints
`❌ [System] Maximum retries exhausted — aborting turn.` and returns
(`main.py:541`). There is no partial answer, no fallback to the DIRECT protocol,
no summary of what was attempted. There is also no backoff, no distinction
between error classes, and no overall wall-clock cap on the turn — with the
defaults, three 30-second timeouts plus three streaming passes is the worst
case. Separately, there is **no retry around the LLM call itself**: an
`httpx.ConnectError` mid-stream is caught at the REPL level (`main.py:659-660`)
and aborts the whole turn.

### 6.8 Two launcher variables remain undocumented

*Narrowed at SPEC-MEMORY-001.* The README table previously documented only
`CODERUNNER_MODEL`, `CODERUNNER_TIMEOUT` and `CODERUNNER_MAX_RETRIES`. It now
also documents `OLLAMA_HOST` (`main.py:65`), `CODERUNNER_HISTORY`
(`main.py:69`) and the six memory variables. Still absent are the launcher-only
`CODERUNNER_DOCKER_BOOT_TIMEOUT` (`coderunner:17`) and
`CODERUNNER_BOOTSTRAP_LOG` (`coderunner:18`), which never reach the container.
See `tech.md` Section 4 for the complete table.

### 6.9 There is no command-line interface

`coderunner:263` forwards `"$@"` into the container, but `main.py` parses
nothing — there is no `argparse`, no `click`, no manual `sys.argv` inspection
anywhere. Any argument other than `--doctor` (which the launcher intercepts at
`coderunner:233`) is silently discarded. There is no `--help`, no `--version`,
and no `--model`; the only configuration surface is environment variables.

### 6.10 In-app troubleshooting text does not match the shipped compose file

`_connection_help_panel()` tells the user that `host.docker.internal` is
"mapped via compose extra_hosts" (`main.py:564-566`) and to "uncomment
`network_mode: host` in docker-compose.yml" (`main.py:567-569`).
`docker-compose.yml` contains **neither** an `extra_hosts` key nor a commented
`network_mode` line. Both instructions are stale relative to the current
two-service topology, where the app reaches Ollama at `http://ollama:11434`
(`docker-compose.yml:70`).

### 6.11 Solution memory is a persistent surface reachable by generated code

Until SPEC-MEMORY-001 nothing generated code wrote outlived the container. It
now shares the `runner` uid with the process that owns
`/home/runner/.coderunner`, so a model-written script can **read** the whole
task history, **poison** it with fabricated records, or **delete** the store —
and unlike a scribble on `/app/main.py` (§6.5), those effects persist into every
later session.

This is not a privilege escalation; the capability was already there, and only
the durability is new. The blast radius is bounded by design: stored content is
only ever *shown* to the model as text, never executed (constraint C2), so a
poisoned record can mislead the model's reasoning but cannot itself run.
`tech.md` §7.2 records the same finding from the security side.

### 6.12 Only one session at a time gets memory

Milvus Lite does not support concurrent access. Two genuinely simultaneous
clients on the same database file were measured (V5d): the loser fails **at
open**, not on some later operation.

The failure is handled, not fatal — `VectorStore.open()` returns `None`, the
second session prints one startup line and runs with memory disabled. In
practice `./coderunner` launches with `--name coderunner` (`coderunner:263`), so
a second *launcher* run collides on the container name first; the exposed path
is `docker compose run --rm coderunner`, which sets no name. There is no
queueing, no lock wait, and no `busy_timeout` equivalent — the SQLite design had
one, and this is a deliberate regression accepted with the substrate.

---

## 7. Non-goals (as evidenced by the code)

- **No GUI or web UI.** The only interface is the Rich terminal (`main.py:37-44`).
- **No multi-user or server mode.** A single blocking `input()` loop drives one
  conversation (`main.py:620`, `main.py:638`).
- **No conversation persistence.** `Conversation` lives only in process memory
  (`main.py:159-170`) and is never serialized. **This is no longer the same as
  "nothing is written to disk":** solution memory persists the task, reasoning,
  script and stdout of every *successful* turn to `coderunner_app_data`
  (§2.3). Failed turns, DIRECT-protocol turns, the streamed reasoning of
  attempts 2..N and the final grounded answer are all still discarded.
- **No tool/function-calling protocol.** The only channel between model and
  runtime is a fenced Markdown code block (`main.py:215`).
- **No cloud LLM provider.** `build_client()` constructs an Ollama client and
  nothing else (`main.py:549-550`).
