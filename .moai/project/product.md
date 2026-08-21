# CodeRunner.AI — Product Overview

> Scope note: this document describes the CodeRunner.AI product only — the files
> `coderunner`, `install.sh`, `main.py`, `tools.py`, `Dockerfile`, `docker-compose.yml`,
> `requirements.txt`, `README.md`, `LICENSE`. The `.claude/` and `.moai/`
> directories (including `CLAUDE.md`) are AI-agent tooling checked into the same
> repository and are **not** part of the product.

---

## 1. Identity

| Field | Value |
| --- | --- |
| Project name | CodeRunner.AI (`main.py:10`) |
| Author | Chun Kang \<ck@strpy.com\> (`main.py:14`) |
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
sandboxing note at `README.md:178`.

---

## 4. Core features

Twenty-one user-visible behaviors, each mapped to the code that implements it.

| # | Feature | Implementation | Location |
| --- | --- | --- | --- |
| 1 | **One-command launch** — `./coderunner` performs the full bootstrap and drops the user into the REPL | bootstrap sequence + `compose run --rm` | `coderunner:156-219`, `coderunner:263` |
| 2 | **Silent Docker install** — installs Docker Desktop (macOS, Homebrew cask then DMG fallback) or Docker Engine (Linux, `get.docker.com`) when the binary is missing | `install_docker_macos()`, `install_docker_linux()`, `ensure_docker_installed()` | `coderunner:37-71`, `coderunner:73-86`, `coderunner:88-99` |
| 3 | **Headless daemon start** — starts a stopped Docker daemon and polls until ready (default 180 s budget) | `wait_for_docker()`, `start_docker_macos()`, `start_docker_linux()`, `ensure_docker_running()` | `coderunner:104-143` |
| 4 | **Bundled model server + one-time model pull** — brings up the Ollama sidecar, waits for `healthy`, pulls the model only if absent from the volume | `ensure_ollama_service()`; `ollama` and `model-pull` services | `coderunner:191-217`, `docker-compose.yml:15-49` |
| 5 | **Diagnostic report** — `./coderunner --doctor` prints 14 fields (OS/arch, docker binary, docker version, compose command, daemon reachability, image presence, ollama service status, pulled models, ollama volume mountpoint, **app volume mountpoint**, **embedding model presence**, bootstrap log path, **keychain backend**, **stored secret names and count**) and exits 0. The last two report names only, never a value | `--doctor` branch | `coderunner:233-258` |
| 6 | **Automatic teardown** — on exit/INT/TERM, removes stray app containers and stops the Ollama sidecar to reclaim RAM while preserving the model volume | `cleanup()` + `trap ... EXIT INT TERM` | `coderunner:222-231` |
| 7 | **Session banner** — panel showing product name, active model, Ollama host, and execution timeout | `show_banner()` | `main.py:337-358` |
| 8 | **Interactive REPL** — rule-separated turn loop, blank input skipped, `/exit`, `/quit`, `:q` terminate | `repl()` | `main.py:623-667`, exit words at `main.py:649` |
| 9 | **Arrow-key prompt history** — readline wired for both GNU readline and macOS libedit, capped at 1000 entries, written back on exit via `atexit` | `_install_history()`, `_prompt_user()` | `main.py:585-612`, `main.py:615-620`, cap at `main.py:70` |
| 10 | **Live streaming reasoning** — tokens are printed one completed line at a time under a `Thought · attempt N` rule, never repainted; only the unfinished tail line stays in a `Live` region. Inline markdown (bold, italic, inline code) is rendered per line | `stream_llm()`, `render_stream()`, `_render_markdown_line()` | `main.py:179-192`, `main.py:323-`, `main.py:216-` |
| 11 | **Dual protocol (CODE vs DIRECT)** — computational tasks produce a fenced Python block; conversational questions are answered directly with no execution | `SYSTEM_PROMPT` protocol spec; the "no code block" early return | `main.py:100-151`, branch at `main.py:479-482` |
| 12 | **Live script display** — fenced code is numbered, Monokai-highlighted and marked with a solid left rail **as it is written**, inside the reasoning stream. There is no separate panel afterwards: `show_code()` was removed once the code streamed, because it re-showed lines the reader had just watched appear | `_render_code_line()`, `_CODE_RAIL` | `main.py:264-`, `main.py:260` |
| 13 | **Sandboxed execution with wall-clock cap** — code is written to a fresh temp directory, run as a separate isolated-mode process, and the directory is destroyed unconditionally afterwards | `run_python()` | `main.py:244-286` |
| 14 | **Execution result panel** — green `Execution OK (rc=N)` with stdout, red `Execution FAILED (rc=N)` with stderr, or red `Execution TIMEOUT` | `show_exec_result()` | `main.py:313-334` |
| 15 | **Bounded agentic self-correction** — on failure, stderr+stdout are fed back and the model retries, up to `CODERUNNER_MAX_RETRIES` attempts per turn; on success a second LLM pass produces the grounded `Answer` | `agentic_turn()` | `main.py:427-541`; retry feedback `main.py:527-539`; grounded answer `main.py:492-508` |
| 16 | **Capture of successful turns** — task, reasoning, executed script and real stdout are persisted with an embedding of the task, deduplicated by task hash, truncated to ~8 KB per record, and pruned oldest-first at the 100,000-record cap | `_capture_turn()` → `vector_for_capture()` → `remember_success()` → `VectorStore.insert()` | `main.py:394-424` (called at `:515`), `recall.py:205-236`, `recall.py:239-270`, `vectorstore.py:362-422` |
| 17 | **Semantic recall and few-shot injection** — the new task is embedded, the most similar past task above a 0.65 cosine floor is retrieved, and the stored solution is inserted as one ephemeral `system` message before the user's message on attempt 1 only. **The stored code is never executed**; the block is framed as material to adapt or ignore | `recall_for_task()`, `format_recall_block()`, `inject_recall()` | `recall.py:109-169`, `memory.py:379-387`, `memory.py:390-404`; injection at `main.py:448`, `main.py:466-470` |
| 18 | **Zero-cost cold start** — on an empty store the embedding call is skipped entirely, so a fresh install pays no extra latency on its first turn | empty-store short-circuit in `recall_for_task()` | `recall.py:109-169` |
| 19 | **`/memory` command family** — `/memory` (path, counts, embed model, dimension, on-disk size, effective threshold/top-k/cap), `/memory list [n]`, `/memory forget <id>`, `/memory clear --yes`. Handled in the REPL; `agentic_turn()` is never invoked | `handle_memory_command()` and its `_emit_*` helpers | `memory.py:447-494`, `memory.py:497-567`; dispatch at `main.py:652` |
| 20 | **One-line degradation** — any memory fault (embedding backend down, store unopenable, volume unwritable, another session holding the store) produces exactly one status line and a turn otherwise identical to the pre-feature product | `retrieval_degraded()` classifier + the warning-suppression pair | `recall.py:172-202`, `main.py:384-391`, `main.py:444-446`, `main.py:515-523` |
| 21 | **Host-keychain secrets for declared parameters** — `--set-secret NAME` keeps a value in the macOS keychain or the Linux Secret Service; the launcher fetches every registered name before the container starts and passes it as `-e CODERUNNER_SECRET_<NAME>` (name only), and a `# @param NAME : secret` is filled without prompting. `--list-secrets` and `--forget-secret` manage the set; all three run before the bootstrap, so storing a password does not install Docker. Eligibility is `type == secret` only, the turn's own cache always wins, and every fault degrades to a prompt with one yellow line. **This moves the exposure rather than removing it — see 6.13** | `keychain.load()`/`keychain.prefill()`; the launcher's keychain section and `keychain_collect_env()` | `keychain.py`, `main.py:_collect_params()`, `coderunner:36-…`, `coderunner:263` |

### Supporting behaviors

- **Startup connectivity preflight** with a remediation panel listing the exact
  fix steps when Ollama is unreachable — `preflight()` (`main.py:573-582`),
  `_connection_help_panel()` (`main.py:553-570`). Exits with code 2 on failure
  (`main.py:628-629`).
- **Status ticker** — emoji + `[TAG]` + message lines that narrate each phase of
  the turn — `status()` (`main.py:503`).
- **Pulsing status icon** — while a phase is running its icon blinks on and off,
  then the line settles and stays steady; the animation lives in a transient
  `Live` region that is erased on exit — `_PulsingLine` (`main.py:507`),
  `processing()` (`main.py:555`). Applied to all five phases: memory search,
  both model warm-ups, execution and capture.

  The icon is **blanked**, not dimmed, and that is the whole mechanism. Every
  icon is a colour emoji, which draws its colour from the font's own glyph
  table and therefore ignores SGR 1 and SGR 2 entirely. The first
  implementation alternated `bold` and `dim`, emitted a flawless alternating
  escape stream, and animated nothing on any terminal — for the same reason its
  own docstring rejected `\x1b[5m`. Presence and absence of a glyph is not an
  attribute a terminal can decline to honour.
- **Streaming that never repaints** — `prime_stream()` (`main.py:592`) draws
  exactly one token inside the pulse so the animation covers the longest silence
  in a turn (model load plus prompt evaluation) and ends when real output
  starts.
- **Signal safety** — SIGTERM prints a panel and exits 0
  (`_install_signal_handlers()`, `main.py:670-676`); Ctrl+C at the prompt exits
  the REPL (`main.py:642-644`); Ctrl+C mid-turn aborts only that turn
  (`main.py:661-662`).

---

## 5. Use cases

### 5.1 Live data lookup (the README reference scenario)

Prompt: **"What's the current weather in Seoul in Celsius?"** (`README.md:88`)

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

### 5.5 Conversational / explanatory questions — the DIRECT protocol does not fire

*Corrected 2026-08-18. The previous text asserted the behaviour below as fact;
it is measured at 0/30 and has been false for as long as it has been written.*

`SYSTEM_PROMPT` does offer a DIRECT protocol for questions needing no
computation (`main.py:169-174`): answer under an `Answer:` heading, emit no
fenced block. `agentic_turn()` honours it — the extractor returning nothing is
the one branch that skips execution, and it prints `💬 [LLaMA] No code
produced — returning direct answer.` (`main.py:1072-1074`).

**That branch is not reached on the shipped model.** Measured 2026-08-10,
`llama3.1:8b` (Q4_K_M) via the compose sidecar, N=30 on *"explain what a Python
closure is, with a short example"*: **CODE 30/30, DIRECT 0/30**, 95 % Wilson
**[0.000, 0.114]**. `fence_matches == 1` in all thirty, so this is not the
two-block trap; all thirty parsed, defined a function and printed a computed
value. Source `v0-c4-general-knowledge.jsonl` on `feature/SPEC-PROMPT-001`,
re-derived 2026-08-12 (`SPEC-ILLUSTRATE-001` §2.2).

What happens instead is §5.4's path applied to an illustration. `README.md:124`
documents it for the user, with a transcript of one of the thirty. See §6.15.

### 5.6 Self-correcting execution

If the first script raises, the red `Execution FAILED` panel is shown, stderr is
sent back, and attempt 2 begins from the model's diagnosis
(`main.py:527-539`, `README.md:122`).

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

### 6.3 Stale-image hazard after editing source — **RESOLVED**

*Kept rather than deleted, following §6.2: the gap was real, it was invisible by
construction, and the fix is one gate that can be reverted on its own.*

The original defect: the launcher built only when `docker image inspect
coderunner-ai:latest` failed — i.e. only when the image was absent. Since the
`.py` files are baked in by the Dockerfile's `COPY` lines, editing `main.py` or
`tools.py` did **not** trigger a rebuild; the launcher silently kept running the
old image until the user ran `docker compose build coderunner` by hand. Nothing
reported it, so the symptom was an edit that appeared to do nothing at all.

`coderunner:567-579` now branches three ways: build when the image is absent,
rebuild when `image_is_stale()` (`coderunner:542-565`) is true, and otherwise do
nothing. Staleness compares each baked-in file's mtime — `image_sources()`
(`coderunner:533-536`) reads that list from the Dockerfile's own `COPY` lines
rather than restating it — against the image's `LastTagTime` (`image_epoch()`,
`coderunner:518-525`). **Unreadable is stale:** a date that will not parse or a
file that will not stat returns 0 and rebuilds. `README.md:17` documents the
behaviour and its price — 0.375 s for a rebuild with nothing to do, because the
layer cache does the real work.

What the gate cannot see is **content** (`coderunner:482-486`). `git checkout`
writes a fresh mtime onto an identical file and buys one rebuild that changes
nothing, and a file restored with an *older* mtime is missed entirely. The gate
decides only "might this differ", never "does this differ".

### 6.4 `--doctor` has heavy side effects

The `--doctor` branch sits at `coderunner:233`, *after* the entire bootstrap at
`coderunner:157-219`. Running `./coderunner --doctor` on a clean machine will
therefore install Docker, start the daemon, build the image, start the Ollama
sidecar, and pull a multi-GB model **before** printing a single diagnostic line.
It is not a read-only health check.

### 6.5 The sandbox is process-level, not privilege- or network-level

`README.md:178` states this plainly and the docs carry the same honesty.
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

### 6.13 A keychain-stored secret is readable by anyone who can query the Docker daemon

Feature 21 stores a value in the host's credential store so the user stops
retyping it, and the launcher then passes it into the container's environment.
**That does not make the value private. It moves the exposure**, and this section
exists so the move is stated rather than implied.

Measured 2026-08-07:

```
$ docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' <id> | grep -i secret
MY_SECRET=hunter2

$ docker exec <id> sh -c 'tr "\0" "\n" < /proc/1/environ | grep -i secret; id'
MY_SECRET=hunter2
uid=1000(runner) gid=1000(runner) groups=1000(runner)
```

Neither route is a property of *how* the value is passed — `-e NAME`,
`-e NAME=value` and `--env-from-file` all produce the same `Config.Env` record.
It is a property of the container having an environment. `main.py` pops every
`CODERUNNER_SECRET_*` variable out of `os.environ` at import, which was measured
to close the `os.environ` route for scripts started by `run_python()` and
measured **not** to close either `/proc` route. That is a mitigation with a
stated ceiling, not a fix.

What this removes, retained and adds:

- **Removed** — the repetition. The value is typed once, into the operating
  system, rather than once per session into a terminal in front of whoever is
  looking at it.
- **Retained** — generated code can read it, and must: it is the value the script
  was written to use. That was already true of a typed value.
- **Added** — the Docker daemon. Access to it is already root-equivalent on the
  host and this project grants that access itself (`coderunner:83-84` adds the
  invoking user to the `docker` group), so the marginal exposure is small. It is
  not zero, and on a shared Linux machine the `docker` group can be wider than
  the person who stored the key. Also added: the host keychain itself, which is a
  store no capture policy inspects — that one is intentional and is the entire
  point, listed so that "nothing was stored" is never said about a session that
  used this feature.

The container is `--rm`, so the `Config.Env` record is destroyed with the
container. It is transient. It is not absent.

**And one existing promise changes meaning.** The `never` capture policy is still
the strongest available, and for a keychain-sourced value it no longer bounds the
exposure: "this turn was not stored" stays true and stops being complete. A user
who chose `never` is told so, in `README.md` and in `tech.md` §7.2.

A user who needs a secret the Docker daemon cannot see should not use this
feature. Typing it at the prompt still routes it through `getpass`, keeps it out
of readline history, out of the rendered script and — under `sensitive_excluded`
or `never` — out of solution memory.

### 6.14 The launcher has no tests, and it just grew

Feature 21 adds roughly forty lines of bash to a file that has never had a test
of any kind, and two of its sharpest edges live there: the empty-array expansion
that is fatal under `set -u` on stock macOS `/bin/bash` 3.2.57, and the
"rc 0 **and** non-empty" predicate that decides whether a value is trusted.

`tests/test_launcher_source.py` asserts what can be asserted about the text —
that `--env-from-file` is absent, that every `-e` carries a bare name, that the
array expansion is guarded, that the subcommands are dispatched before the
bootstrap, and that `--doctor` prints no stored value. It cannot assert
behaviour. A harness is deliberately out of scope: a test framework introduced
as a rider on a `LOW`-priority feature is a framework nobody maintains. If the
launcher grows again, it should be its own piece of work.

### 6.15 Illustrative code is executed, narrated and stored as a solution

`extract_last_python_block()` (`main.py:447-449`) is a regex, and the only
branch that avoids execution (`main.py:1072-1074`) is taken solely when it
finds nothing. Nothing in the path distinguishes a block meant to *illustrate*
from one meant to *run*, because the distinction is not in the block — it is in
the request. §5.5 records how often that matters: **30/30**.

So an "explain X" turn writes the illustration to a scratch directory, runs it
under `python -I`, renders an `Execution OK` panel, pays a second LLM round
trip to narrate a result nobody asked for, and captures the turn into solution
memory (`main.py:1143-1152`). `format_recall_block()` (`memory.py:383-391`)
later re-injects it under `PRIOR SUCCESSFUL SOLUTION — reference only` into a
similar question, and a second "explain X" is exactly the shape that clears the
0.65 similarity floor. **The defect feeds itself.**

Nothing raises, nothing exits non-zero, and `main.py` imports no logging module,
so there is no line for a bug report to quote — the turn is byte-for-byte what a
correct computation turn looks like. That is worse than an error. The cost is
one extra model round trip per turn, up to three when the illustration fails,
plus one subprocess and one persistent write.

`SPEC-ILLUSTRATE-001` specifies a structural screen — the block parses, imports
nothing, and references no name it does not itself bind — and it is **not
shipped**. Whether it ships at all is gated on a false-positive measurement
(T2/T3) that has not been taken, and **I-b, "measured unusable", is admitted in
advance as a real outcome.**

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
