# CodeRunner.AI

An AI that doesn't just stop at coding without token worries, but takes responsibility all the way through to execution (Run).

Local, agentic Python code interpreter powered by LLaMA (via [Ollama](https://ollama.com)). Reasons about your task, writes Python, executes it in a sandboxed subprocess inside an ephemeral Docker container, and self-corrects on failure — all without a paid API key.

---

## Quickstart

```bash
./coderunner
```

The launcher will install Docker (if missing), pull the model on first run, and drop you into an interactive terminal. When you exit, the container and the bundled Ollama sidecar are shut down so the machine reclaims its RAM. Model weights persist in a Docker volume so subsequent launches are instant.

Configuration via environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CODERUNNER_MODEL` | `llama3.1:8b` | Ollama model tag |
| `CODERUNNER_TIMEOUT` | `30` | Per-execution wall-clock cap (seconds) |
| `CODERUNNER_MAX_RETRIES` | `3` | Self-correction attempts per turn |

Run `./coderunner --doctor` for a diagnostic report if anything misbehaves.

---

## Sample demo

A typical session looks like this:

```
╭──────────────────────────────────────────────────────────╮
│  CodeRunner.AI  — agentic Python interpreter powered by  │
│                   LLaMA                                  │
│  model: llama3.1:8b   host: http://ollama:11434          │
│  timeout: 30s                                            │
╰──────────────────────────────────────────────────────────╯
Type your task. Use /exit or Ctrl+C to quit.

you ➜ What's the current weather in Seoul in Celsius?

🔄 [LLaMA] Analyzing request and designing solution (attempt 1/3)…

╭─ Thought · attempt 1 ────────────────────────────────────╮
│  Task: fetch the current temperature in Seoul in °C.     │
│                                                          │
│  Thought: wttr.in exposes a JSON endpoint that returns   │
│  the current condition in a stable schema. I'll hit      │
│  https://wttr.in/Seoul?format=j1 with a short timeout    │
│  and a User-Agent, parse current_condition[0].temp_C,    │
│  and print it.                                           │
╰──────────────────────────────────────────────────────────╯

╭─ Generated Script ───────────────────────────────────────╮
│ 1  import requests                                       │
│ 2  r = requests.get(                                     │
│ 3      "https://wttr.in/Seoul?format=j1",                │
│ 4      headers={"User-Agent": "CodeRunner.AI/1.0"},      │
│ 5      timeout=10,                                       │
│ 6  )                                                     │
│ 7  r.raise_for_status()                                  │
│ 8  temp_c = r.json()["current_condition"][0]["temp_C"]   │
│ 9  print(f"Seoul is currently {temp_c}°C")               │
╰──────────────────────────────────────────────────────────╯

⚙️  [System] Running generated Python code…

╭─ Execution OK (rc=0) ────────────────────────────────────╮
│ Seoul is currently 4°C                                   │
╰──────────────────────────────────────────────────────────╯

📊 [System] Execution successful (Output: Seoul is currently 4°C)
💬 [LLaMA] Final response streaming…

╭─ Answer ─────────────────────────────────────────────────╮
│  It's currently **4 °C** in Seoul.                       │
╰──────────────────────────────────────────────────────────╯
```

If the first script fails, CodeRunner feeds the stderr back to the model, which diagnoses the problem and emits a corrected block — up to `CODERUNNER_MAX_RETRIES` attempts per turn.

For conversational questions that don't need computation ("explain X"), the model skips the code protocol and answers directly.

---

## How it works

1. **Launcher (`coderunner`)** — bootstraps Docker + Docker Compose, ensures the `ollama` sidecar is healthy, pulls the model on first run, and starts the app container ephemerally.
2. **App (`main.py`)** — Rich TUI that streams LLaMA's reasoning, extracts the last fenced Python block, and hands it to the executor.
3. **Executor** — writes the script to a scratch directory, runs it with `python -I` (isolated mode), captures stdout/stderr, and returns the result.
4. **Self-correction loop** — on non-zero exit, stderr is sent back to the model as feedback for the next attempt.
5. **Cleanup** — on exit, the launcher stops the Ollama container so RAM is reclaimed; the model volume is preserved for the next session.

Sandboxing note: execution runs inside the container as a non-root user, but the current sandbox is process-level, not network-level. Do not run untrusted prompts against sensitive hosts.

---

## Files

| File | Purpose |
| --- | --- |
| `coderunner` | Bash launcher — Docker bootstrap and session lifecycle |
| `main.py` | REPL, LLM streaming, code extraction, executor, retry loop |
| `tools.py` | Stdlib-only helpers importable from generated scripts (e.g. `web_search`) |
| `Dockerfile` | Slim Python 3.11 image running as unprivileged user |
| `docker-compose.yml` | Two-service stack: ephemeral `coderunner` + long-lived `ollama` |
| `requirements.txt` | Runtime dependencies: `ollama`, `rich`, `httpx`, `requests`, `beautifulsoup4`, `lxml` |

---

## License

See [LICENSE](LICENSE).
