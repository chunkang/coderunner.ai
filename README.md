# CodeRunner.AI

An AI that doesn't just stop at coding without token worries, but takes responsibility all the way through to execution (Run).

Local, agentic Python code interpreter powered by LLaMA (via [Ollama](https://ollama.com)). Reasons about your task, writes Python, executes it in a sandboxed subprocess inside an ephemeral Docker container, and self-corrects on failure — all without a paid API key.

---

## Quickstart

```bash
./coderunner
```

The launcher will install Docker (if missing), pull the model on first run, and drop you into an interactive terminal. When you exit, the container and the bundled Ollama sidecar are shut down so the machine reclaims its RAM. Model weights persist in a Docker volume so subsequent launches are instant.

### Running it from anywhere

```bash
./install.sh                        # put a `coderunner` command in ~/bin
./install.sh --dir /usr/local/bin   # somewhere else
./install.sh --uninstall            # remove it
```

This puts a command on your `PATH` and nothing more — same launcher, same container, same behaviour. It writes a small wrapper that runs the launcher from wherever the repository lives, so the repository is neither moved nor copied and `git pull` updates the installed command too. A symlink would not work: the launcher resolves its own directory without following symlinks, so through one it would look for `docker-compose.yml` in `~/bin`.

If `~/bin` is not on your `PATH`, the installer says so and prints the line to add. It does not edit your shell startup file.

**The app container is ephemeral, but the machine is no longer left untouched.** Solution memory is **on by default**, and it writes every successful turn — your task, the model's reasoning, the script it ran, the real stdout, and a 768-dimension embedding of the task — to the Docker named volume `coderunner_app_data`. That volume is real, persistent, unencrypted host storage:

- **How big.** About 32 KB with a couple of records. At the default 100,000-record cap, roughly **0.9 GB** — 618 MB of vectors plus around 8 KB of text per record.
- **How to see it.** `/memory` in the REPL reports the store path, record count and the recursive on-disk size. `/memory list` shows what is in it.
- **How to erase it.** `/memory clear --yes` empties the store; `docker volume rm coderunner_app_data` destroys the volume outright.
- **How to switch it off.** `CODERUNNER_MEMORY=0` disables capture, retrieval and store creation, and makes the launcher skip the 274 MB embedding-model download.

The vector store also roughly **tripled the image**, from 273 MB to 754 MB — `pymilvus[milvus_lite]` and the numpy it pulls in transitively. See [Solution memory](#solution-memory) below.

Configuration via environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CODERUNNER_MODEL` | `llama3.1:8b` | Ollama chat model tag |
| `CODERUNNER_TIMEOUT` | `30` | Per-execution wall-clock cap (seconds) |
| `CODERUNNER_MAX_RETRIES` | `3` | Self-correction attempts per turn |
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama base URL. Set unconditionally by compose (`docker-compose.yml:70`); `main.py:65` falls back to `http://host.docker.internal:11434` outside compose |
| `CODERUNNER_HISTORY` | `/home/runner/.coderunner/history` | Readline history file. Set unconditionally by compose (`docker-compose.yml:100`), on the volume, so arrow-key history now survives a session; `main.py:69` falls back to `~/.coderunner_history` |
| `CODERUNNER_MEMORY` | `1` | Solution memory master switch. `0` disables capture, retrieval and store creation, and skips the embedding-model pull |
| `CODERUNNER_EMBED_MODEL` | `nomic-embed-text:latest` | Embedding model used for retrieval. The `:latest` suffix is load-bearing — the launcher matches `ollama list` output with `grep -qx`, and a bare name would re-pull 274 MB every launch |
| `CODERUNNER_MEMORY_DB` | `/home/runner/.coderunner/memory.milvus.db` | Store path. Must end in `.db` (Milvus Lite rejects anything else), even though what it creates there is a directory |
| `CODERUNNER_MEMORY_TOP_K` | `1` | Past solutions retrieved per turn, clamped to 1–5 |
| `CODERUNNER_MEMORY_MIN_SIMILARITY` | `0.65` | Cosine similarity floor for a hit, clamped to 0.0–1.0 |
| `CODERUNNER_MEMORY_MAX_RECORDS` | `100000` | Record cap; oldest records are pruned first. Clamped to 10–200000 |

Everything except `OLLAMA_HOST` and `CODERUNNER_HISTORY` passes through from your shell (`docker-compose.yml:69-101`); compose sets those two unconditionally, so exporting them on the host has no effect under `./coderunner`.

The six memory variables are parsed defensively: a malformed value falls back to the default or clamps into range. `CODERUNNER_TIMEOUT` and `CODERUNNER_MAX_RETRIES` are not — a non-numeric value there raises at import, before anything is rendered.

Run `./coderunner --doctor` for a diagnostic report if anything misbehaves.

---

## Sample demo

A typical session looks like this:

```
╭────────────────────────────────────────────────────────────────────╮
│                                                                    │
│  CodeRunner.AI  — agentic Python interpreter powered by LLaMA      │
│  model: llama3.1:8b   host: http://ollama:11434      timeout: 30s  │
│                                                                    │
╰────────────────────────────────────────────────────────────────────╯
Type your task. Use /exit or Ctrl+C to quit.

you ➜ What's the current weather in Seoul in Celsius?

🔄 [LLaMA] Analyzing request and designing solution (attempt 1/3)…
Thought · attempt 1 ──────────────────────────────────────────────────
Task: fetch the current temperature in Seoul in °C.

Thought: wttr.in exposes a JSON endpoint with a stable
schema. I'll hit it with a short timeout and a User-Agent,
parse current_condition[0].temp_C, and print it.

  █    1 import requests
  █    2 
  █    3 r = requests.get(
  █    4     "https://wttr.in/Seoul?format=j1",
  █    5     headers={"User-Agent": "CodeRunner.AI/1.0"},
  █    6     timeout=10,
  █    7 )
  █    8 r.raise_for_status()
  █    9 temp_c = r.json()["current_condition"][0]["temp_C"]
  █   10 print(f"Seoul is currently {temp_c}°C")
──────────────────────────────────────────────────────────────────────
⚙️ [System] Running generated Python code…
╭─────────────────────── Execution OK (rc=0) ────────────────────────╮
│ Seoul is currently 4°C                                             │
╰────────────────────────────────────────────────────────────────────╯
📊 [System] Execution successful (Output: Seoul is currently 4°C)
💬 [LLaMA] Final response streaming…
Answer ───────────────────────────────────────────────────────────────
Answer: it's currently 4 °C in Seoul.
──────────────────────────────────────────────────────────────────────
```

If the first script fails, CodeRunner feeds the stderr back to the model, which diagnoses the problem and emits a corrected block — up to `CODERUNNER_MAX_RETRIES` attempts per turn.

For conversational questions that don't need computation ("explain X"), the model skips the code protocol and answers directly.

---

## How it works

1. **Launcher (`coderunner`)** — bootstraps Docker + Docker Compose, ensures the `ollama` sidecar is healthy, pulls the model on first run, and starts the app container ephemerally.
2. **App (`main.py`)** — Rich TUI that streams LLaMA's reasoning, extracts the last fenced Python block, and hands it to the executor.
3. **Executor** — writes the script to a scratch directory, runs it with `python -I` (isolated mode), captures stdout/stderr, and returns the result.
4. **Self-correction loop** — on non-zero exit, stderr is sent back to the model as feedback for the next attempt.
5. **Solution memory** — wraps steps 2–4: one retrieval before the first LLM call, one capture after a turn succeeds. See the next section.
6. **Cleanup** — on exit, the launcher stops the Ollama container so RAM is reclaimed; the model volume is preserved for the next session.

Sandboxing note: execution runs inside the container as a non-root user, but the current sandbox is process-level, not network-level. Do not run untrusted prompts against sensitive hosts. Note that generated code runs as the same `runner` user that owns the memory volume, and can therefore read, corrupt or delete the store.

---

## Solution memory

When a turn succeeds, CodeRunner stores the task, the model's reasoning, the script that ran and the real stdout, together with an embedding of the task text. On a later turn it embeds your new task, searches the store for the single most similar past task, and — if the cosine similarity is at least `0.65` — injects that prior solution as one `system` message placed immediately before your message.

**Stored code is never replayed.** It enters the prompt as reference material the model is explicitly told to adapt or ignore, and every script that executes is the one the model emits in that turn. The injected block is ephemeral: it is not appended to the conversation, it goes only into attempt 1, and retries and the final grounded-answer pass never see it.

Retrieval is semantic, not keyword-based. Asking *"tell me the temperature in Busan right now"* after a Seoul weather task scores 0.76 and fires; unrelated task pairs measure 0.30–0.40, so the 0.65 floor has clear air on both sides.

### Commands

| Command | Effect |
| --- | --- |
| `/memory` | Store path, record count, eligible count, embedding model, vector dimension, on-disk size, and the effective threshold, top-k and cap |
| `/memory list [n]` | The *n* most recent records, newest first. Default 10, clamped to 1–100 |
| `/memory forget <id>` | Delete one record by the id shown in `/memory list` |
| `/memory clear --yes` | Delete every record. Without `--yes` nothing is deleted and the required form is printed |

These are handled in the REPL and never reach the model.

### Where it lives

An embedded [Milvus Lite](https://milvus.io/docs/milvus_lite.md) collection at `/home/runner/.coderunner/memory.milvus.db`, inside the Docker named volume `coderunner_app_data`. No extra services, no ports, no daemon — it is a library writing a directory tree. Records survive the container's `--rm` lifecycle; that is the point.

The store is capped at 100,000 records and prunes oldest-first when it goes over. Identical tasks deduplicate in place: re-asking updates the stored record and keeps its id and its original timestamp, so `/memory forget <id>` keeps addressing the same thing. Long fields are truncated on the way in — task 2,000 characters, thought 1,000, code 4,000, stdout 1,000 — which bounds a record to about 8 KB and does not affect retrieval, since only the task text is embedded.

Two records occupy about 32 KB; at the cap the volume reaches roughly 0.9 GB, of which 618 MB is the vectors. Search on a freshly started container measures about 298 ms, and cold startup to first result about 1.18 s.

Adding all this roughly tripled the container image, from **273 MB to 754 MB** — `pymilvus[milvus_lite]` plus the numpy it drags in transitively and that no CodeRunner module imports. That is the honest price of the feature; `CODERUNNER_MEMORY=0` does not reclaim it, because the dependency is baked into the image either way.

### When it breaks

Solution memory is an enhancement, never a dependency. If the embedding model is absent, the store cannot be opened, the volume is unwritable, or anything else in the subsystem fails, you get **exactly one status line** for that turn and the turn then proceeds identically to a build without the feature. Nothing raises and nothing exits non-zero.

One case worth naming: Milvus Lite does not support concurrent access. A second simultaneous session fails to open the store, says so once, and runs with memory disabled.

---

## Host-keychain secrets

When the model needs a value only you have, it declares it — `# @param api_key: secret = "API key"` — and CodeRunner asks you for it. If you use the same API key every session, you can keep it in your operating system's credential store instead and stop retyping it.

```bash
./coderunner --set-secret api_key      # the OS prompts for the value and masks it
./coderunner --list-secrets            # names and a count, never a value
./coderunner --forget-secret api_key   # remove it
```

At the next launch the launcher fetches every registered name and passes it into the container. A `# @param NAME : secret = "…"` whose name matches is filled without prompting; every other declaration prompts exactly as it does today. Only `secret` declarations are eligible — store `city` and you will still be asked for it, because the model declared it `str`.

The store is `security` on macOS and `secret-tool` (libsecret) on Linux. **No Python dependency is added** — the launcher is bash, and those commands ship with the operating system. The value never appears in a command line on the way in: `security` and `secret-tool` read it themselves, so it does not pass through the launcher at all.

The three subcommands run before the Docker bootstrap, so storing a password does not install Docker. `CODERUNNER_KEYCHAIN=0` disables the feature for one launch without deleting anything. `./coderunner --doctor` reports which backend is in use and which names are registered.

### What this does and does not buy you

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
> prompt, where CodeRunner already routes it through `getpass` and keeps it out of readline
> history, out of the rendered script, and — under the `sensitive_excluded` or `never` capture
> policies — out of solution memory.

One consequence deserves stating on its own, because it changes what an existing promise means. `never` — the capture policy for people who want a guarantee rather than a reduction — is still the strongest policy available, and for a keychain-sourced value **it no longer bounds the exposure**: the value is in the container's `Config.Env` for the whole session regardless of which policy you chose, because that is outside the store any capture policy governs. "This turn was not stored" remains true. It is no longer complete.

### When it breaks

Every keychain fault ends in a prompt and never in a failure. No keychain client on `PATH`, a locked keychain, a name you registered whose item has since been deleted, a cancelled unlock dialog, an item that exists but is empty — each produces **one yellow line at launch** and then behaves exactly as CodeRunner did before this feature: you are asked for the value. One unreadable name does not stop the others.

A user who has never run `--set-secret` gets no line at all. That is a state, not a fault.

---

## Files

| File | Purpose |
| --- | --- |
| `coderunner` | Bash launcher — Docker bootstrap and session lifecycle |
| `install.sh` | Puts a `coderunner` command on `PATH` by writing a wrapper that execs the launcher in place. Bash 3.2 compatible; edits no shell startup file |
| `main.py` | REPL, LLM streaming, code extraction, executor, retry loop |
| `memory.py` | Solution memory core — record model, truncation, config parsing, `/memory` commands, prompt-block formatting. Stdlib only |
| `recall.py` | The embedding seam — the only module that touches `ollama` for embeddings |
| `vectorstore.py` | The storage seam — the only module that touches `pymilvus` |
| `params.py` | Declared-parameter grammar, collection and literal safety. Stdlib only |
| `settings.py` | `settings.json` and the parameter capture policy. Stdlib only |
| `keychain.py` | Reads the values the launcher fetched from the host keychain. Stdlib only, and it contains no platform knowledge at all — that lives in the launcher |
| `tools.py` | Stdlib-only helpers importable from generated scripts (e.g. `web_search`) |
| `Dockerfile` | Slim Python 3.11 image running as unprivileged user |
| `docker-compose.yml` | Three-service stack: ephemeral `coderunner`, long-lived `ollama`, and the one-shot `model-pull` helper, plus the `coderunner_app_data` and `coderunner_ollama_data` volumes |
| `requirements.txt` | Runtime dependencies: `ollama`, `rich`, `httpx`, `requests`, `beautifulsoup4`, `lxml`, `pymilvus[milvus_lite]` |

---

## License

See [LICENSE](LICENSE).
