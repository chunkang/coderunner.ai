# ==============================================================================
#  ██████╗ ██████╗ ██████╗ ███████╗██████╗ ██╗   ██╗███╗   ██╗███╗   ██╗███████╗██████╗
# ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██║   ██║████╗  ██║████╗  ██║██╔════╝██╔══██╗
# ██║     ██║   ██║██║  ██║█████╗  ██████╔╝██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝
# ██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗
# ╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║╚██████╔╝██║ ╚████║██║ ╚████║███████╗██║  ██║
#  ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
# ------------------------------------------------------------------------------
#  File        : main.py
#  Project     : CodeRunner.AI
#  Description : Terminal-based Code Interpreter Chatbot powered by LLaMA.
#                Reasons through problems, generates Python code, executes it
#                in a sandboxed subprocess, and self-corrects on failure.
#  Author      : kurapa <kurapa@kurapa.com>
#  License     : See LICENSE
#  Runtime     : Python 3.11+  |  Docker-only (ephemeral, --rm)
# ==============================================================================

from __future__ import annotations

import atexit
import os
import re
import readline
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import httpx
import ollama
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.text import Text


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
MODEL_NAME = os.environ.get("CODERUNNER_MODEL", "llama3.1:8b")
EXEC_TIMEOUT_SEC = int(os.environ.get("CODERUNNER_TIMEOUT", "30"))
MAX_RETRIES = int(os.environ.get("CODERUNNER_MAX_RETRIES", "3"))
HISTORY_FILE = Path(os.environ.get("CODERUNNER_HISTORY", str(Path.home() / ".coderunner_history")))
HISTORY_MAX = 1000

TOOLS_MODULE = Path(__file__).with_name("tools.py")

console = Console()


SYSTEM_PROMPT = textwrap.dedent(
    """
    You are CodeRunner, an agentic Python code interpreter.

    Decide first: does this task require computation on data the user gave you,
    or logic/math you can execute? If YES, follow the CODE protocol. If NO (the
    question is conversational, opinion, general knowledge, or needs live data
    you don't have), follow the DIRECT protocol.

    CODE protocol:
    1. One-line task restatement.
    2. A "Thought:" section (2-4 lines) explaining your plan.
    3. Exactly ONE fenced Python 3 block:

       ```python
       # your code here
       print(final_answer)
       ```

       Rules:
       - Available libraries: stdlib, requests, beautifulsoup4 (bs4), lxml.
       - Network access IS allowed for scraping when the answer requires
         external / live data (weather, news, stock prices, definitions, etc.).
         Prefer:
           * direct JSON APIs when known (e.g. wttr.in for weather:
             https://wttr.in/<city>?format=j1)
           * Wikipedia REST API for factual lookups:
             https://en.wikipedia.org/api/rest_v1/page/summary/<Title>
           * DuckDuckGo HTML search as a general fallback:
             https://duckduckgo.com/html/?q=<url-encoded-query>
             — parse with BeautifulSoup, pick the top result href from
               a.result__a, then fetch that page and extract the answer.
       - Always set a short timeout (e.g. requests.get(url, timeout=10)).
       - Always set a User-Agent header when scraping (some sites 403 empty UA).
       - Must print the final answer to stdout.
       - No input(), no infinite loops. Deterministic and self-contained.
    4. Stop after the fenced block. Do not narrate results yet.

    DIRECT protocol (no code needed):
    - Use this ONLY for conversational replies, opinions, or explanations of
      general knowledge that clearly do not require live data.
    - Answer under an "Answer:" heading in concise Markdown.
    - Do NOT emit any fenced python block.
    - If in doubt, prefer the CODE protocol with a web lookup.

    After successful execution, the system will send you the stdout — reply
    with an "Answer:" heading in Markdown, referencing the computed value.

    On execution FAILURE, diagnose briefly in one paragraph, then emit a
    corrected fenced Python block (CODE protocol again).
    """
).strip()


# ------------------------------------------------------------------------------
# Data model
# ------------------------------------------------------------------------------


@dataclass
class Conversation:
    messages: list[dict] = field(default_factory=list)

    def system(self, content: str) -> None:
        self.messages.append({"role": "system", "content": content})

    def user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})


# ------------------------------------------------------------------------------
# LLM streaming
# ------------------------------------------------------------------------------


def stream_llm(client: ollama.Client, conv: Conversation) -> Iterator[str]:
    stream = client.chat(model=MODEL_NAME, messages=conv.messages, stream=True)
    for chunk in stream:
        piece = chunk.get("message", {}).get("content", "")
        if piece:
            yield piece


def render_stream(title: str, style: str, token_iter: Iterator[str]) -> str:
    buffer: list[str] = []
    with Live(console=console, refresh_per_second=24, transient=False) as live:
        for token in token_iter:
            buffer.append(token)
            text = "".join(buffer)
            live.update(
                Panel(
                    Markdown(text or "…"),
                    title=title,
                    border_style=style,
                    padding=(1, 2),
                )
            )
    return "".join(buffer)


# ------------------------------------------------------------------------------
# Code extraction & execution
# ------------------------------------------------------------------------------


CODE_BLOCK_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_last_python_block(text: str) -> str | None:
    matches = CODE_BLOCK_RE.findall(text)
    return matches[-1].strip() if matches else None


SCRIPT_HEADER = textwrap.dedent(
    '''\
    # ==============================================================================
    #  CodeRunner.AI  ::  Auto-Generated Execution Script
    # ------------------------------------------------------------------------------
    #  Author   : kurapa <kurapa@kurapa.com>
    #  Notice   : Ephemeral script, executed inside sandboxed subprocess and removed.
    # ==============================================================================
    '''
)


@dataclass
class ExecResult:
    ok: bool
    stdout: str
    stderr: str
    timed_out: bool
    returncode: int


def run_python(code: str, timeout: int = EXEC_TIMEOUT_SEC) -> ExecResult:
    workdir = tempfile.mkdtemp(prefix="coderunner_")
    script_path = os.path.join(workdir, "run.py")

    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(SCRIPT_HEADER + "\n" + code + "\n")

    # Make the tools helper importable from the generated script without
    # exposing the rest of the app. Copy, don't symlink, so the sandbox is
    # self-contained and cleanup is trivial.
    if TOOLS_MODULE.exists():
        shutil.copy2(TOOLS_MODULE, os.path.join(workdir, "tools.py"))

    # Running `python run.py` prepends the script's directory to sys.path, so
    # `from tools import web_search` resolves without PYTHONPATH. `-I` strips
    # PYTHON* env vars anyway, so an override wouldn't help. Site-packages
    # (requests, bs4, lxml) remain available under `-I`.
    try:
        proc = subprocess.run(
            [sys.executable, "-I", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=workdir,
        )
        return ExecResult(
            ok=proc.returncode == 0,
            stdout=proc.stdout,
            stderr=proc.stderr,
            timed_out=False,
            returncode=proc.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        return ExecResult(
            ok=False,
            stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=f"TimeoutExpired: exceeded {timeout}s",
            timed_out=True,
            returncode=-1,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ------------------------------------------------------------------------------
# Status renderers
# ------------------------------------------------------------------------------


def status(icon: str, tag: str, message: str, style: str = "cyan") -> None:
    line = Text()
    line.append(f"{icon} ", style="bold")
    line.append(f"[{tag}] ", style=f"bold {style}")
    line.append(message, style="white")
    console.print(line)


def show_code(code: str) -> None:
    console.print(
        Panel(
            Syntax(code, "python", theme="monokai", line_numbers=True, word_wrap=True),
            title="Generated Script",
            border_style="magenta",
            padding=(0, 1),
        )
    )


def show_exec_result(result: ExecResult) -> None:
    if result.ok:
        body = result.stdout.strip() or "(no stdout)"
        console.print(
            Panel(
                Text(body, style="green"),
                title=f"Execution OK (rc={result.returncode})",
                border_style="green",
                padding=(0, 1),
            )
        )
    else:
        err = result.stderr.strip() or "(no stderr)"
        title = "Execution TIMEOUT" if result.timed_out else f"Execution FAILED (rc={result.returncode})"
        console.print(
            Panel(
                Text(err, style="red"),
                title=title,
                border_style="red",
                padding=(0, 1),
            )
        )


def show_banner() -> None:
    banner = Text()
    banner.append("CodeRunner", style="bold magenta")
    banner.append(".AI  ", style="bold white")
    banner.append("— agentic Python interpreter powered by LLaMA", style="dim")
    subtitle = Text()
    subtitle.append(f"model: ", style="dim")
    subtitle.append(MODEL_NAME, style="bold cyan")
    subtitle.append("   host: ", style="dim")
    subtitle.append(OLLAMA_HOST, style="cyan")
    subtitle.append("   timeout: ", style="dim")
    subtitle.append(f"{EXEC_TIMEOUT_SEC}s", style="cyan")
    console.print(
        Panel(
            Group(banner, subtitle),
            border_style="magenta",
            padding=(1, 2),
        )
    )
    console.print(
        Text("Type your task. Use /exit or Ctrl+C to quit.", style="dim italic")
    )


# ------------------------------------------------------------------------------
# Agentic loop
# ------------------------------------------------------------------------------


def agentic_turn(client: ollama.Client, conv: Conversation, user_input: str) -> None:
    conv.user(user_input)

    for attempt in range(1, MAX_RETRIES + 1):
        status("🔄", "LLaMA", f"Analyzing request and designing solution (attempt {attempt}/{MAX_RETRIES})…", "cyan")
        thought = render_stream(
            title=f"Thought · attempt {attempt}",
            style="cyan",
            token_iter=stream_llm(client, conv),
        )
        conv.assistant(thought)

        code = extract_last_python_block(thought)
        if not code:
            status("💬", "LLaMA", "No code produced — returning direct answer.", "yellow")
            return

        show_code(code)
        status("⚙️", "System", "Running generated Python code…", "yellow")

        with console.status("[bold yellow]Executing sandboxed script…", spinner="dots"):
            result = run_python(code)

        show_exec_result(result)

        if result.ok:
            preview = (result.stdout.strip().splitlines() or [""])[-1][:120]
            status("📊", "System", f"Execution successful (Output: {preview or 'n/a'})", "green")
            feedback = (
                f"Execution succeeded.\n\nSTDOUT:\n```\n{result.stdout.strip()}\n```\n"
                "Please provide the final Answer to the user in Markdown."
            )
            conv.user(feedback)

            status("💬", "LLaMA", "Final response streaming…", "magenta")
            answer = render_stream(
                title="Answer",
                style="magenta",
                token_iter=stream_llm(client, conv),
            )
            conv.assistant(answer)
            return

        status(
            "⚠️",
            "System",
            "Execution failed — asking the model to self-correct…",
            "red",
        )
        feedback = (
            "Execution FAILED.\n\n"
            f"STDERR:\n```\n{result.stderr.strip()}\n```\n"
            f"STDOUT:\n```\n{result.stdout.strip()}\n```\n"
            "Diagnose briefly, then emit a corrected Python block."
        )
        conv.user(feedback)

    status("❌", "System", "Maximum retries exhausted — aborting turn.", "red")


# ------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------


def build_client() -> ollama.Client:
    return ollama.Client(host=OLLAMA_HOST)


def _connection_help_panel(err: Exception) -> Panel:
    body = Text()
    body.append("Cannot reach the Ollama server.\n\n", style="bold red")
    body.append(f"OLLAMA_HOST = {OLLAMA_HOST}\n", style="yellow")
    body.append(f"Error: {err.__class__.__name__}: {err}\n\n", style="dim")
    body.append("Fix on the host machine:\n", style="bold white")
    body.append("  1. Install & start Ollama:  ", style="white")
    body.append("https://ollama.com/download\n", style="cyan")
    body.append("  2. Bind on all interfaces so the container can reach it:\n", style="white")
    body.append("     OLLAMA_HOST=0.0.0.0:11434 ollama serve\n", style="cyan")
    body.append(f"  3. Pull the model:  ollama pull {MODEL_NAME}\n", style="white")
    body.append("  4. From inside the container, host is ", style="white")
    body.append("host.docker.internal", style="cyan")
    body.append(" (mapped via compose extra_hosts).\n", style="white")
    body.append("     If on Linux without Docker Desktop, uncomment ", style="white")
    body.append("network_mode: host", style="cyan")
    body.append(" in docker-compose.yml.\n", style="white")
    return Panel(body, title="Ollama unreachable", border_style="red", padding=(1, 2))


def preflight(client: ollama.Client) -> bool:
    try:
        client.list()
        return True
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, ConnectionError) as err:
        console.print(_connection_help_panel(err))
        return False
    except ollama.ResponseError as err:
        status("⚠️", "Ollama", f"Server responded with error: {err}", "yellow")
        return True  # server is up, model may just be missing — let the turn surface it


def _install_history() -> None:
    """Wire up readline so ↑/↓ navigate prior prompts and history persists."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if HISTORY_FILE.exists():
            readline.read_history_file(str(HISTORY_FILE))
    except OSError:
        pass
    readline.set_history_length(HISTORY_MAX)
    # libedit (macOS default) vs GNU readline: emacs-style bindings for both.
    try:
        if "libedit" in getattr(readline, "__doc__", "") or "":
            readline.parse_and_bind("bind ^I rl_complete")
            readline.parse_and_bind("bind '\\e[A' ed-search-prev-history")
            readline.parse_and_bind("bind '\\e[B' ed-search-next-history")
        else:
            readline.parse_and_bind(r'"\e[A": previous-history')
            readline.parse_and_bind(r'"\e[B": next-history')
    except Exception:
        pass

    def _save():
        try:
            readline.write_history_file(str(HISTORY_FILE))
        except OSError:
            pass

    atexit.register(_save)


def _prompt_user() -> str:
    """Read a line with arrow-key history. Rich handles the banner/rendering;
    the actual input() call is what gives us readline's line-editing."""
    console.file.flush()
    # Bright-green prompt, ANSI directly so readline sees a clean terminal.
    return input("\033[1;32myou\033[0m ➜ ")


def repl() -> None:
    show_banner()
    _install_history()
    client = build_client()
    if not preflight(client):
        status("ℹ", "System", "Fix the host, then re-run ./coderunner.", "yellow")
        sys.exit(2)

    conv = Conversation()
    conv.system(SYSTEM_PROMPT)

    while True:
        console.print(Rule(style="dim"))
        try:
            user_input = _prompt_user()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        stripped = user_input.strip()
        if not stripped:
            continue
        if stripped.lower() in {"/exit", "/quit", ":q"}:
            break

        try:
            agentic_turn(client, conv, stripped)
        except ollama.ResponseError as err:
            status("❌", "LLaMA", f"API error: {err}", "red")
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as err:
            console.print(_connection_help_panel(err))
        except KeyboardInterrupt:
            status("⏹", "System", "Turn interrupted.", "yellow")

    console.print(Panel(Text("Goodbye.", style="bold magenta"), border_style="magenta"))


def _install_signal_handlers() -> None:
    def _graceful(_signum, _frame):
        console.print()
        console.print(Panel(Text("Interrupted. Exiting.", style="bold red"), border_style="red"))
        sys.exit(0)

    signal.signal(signal.SIGTERM, _graceful)


if __name__ == "__main__":
    _install_signal_handlers()
    try:
        repl()
    except KeyboardInterrupt:
        console.print()
