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
#  Author      : Chun Kang <ck@strpy.com>
#  License     : See LICENSE
#  Runtime     : Python 3.11+  |  Docker-only (ephemeral, --rm)
# ==============================================================================

from __future__ import annotations

import atexit
import getpass
import itertools
import os
import re
import readline
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field, replace
from pathlib import Path

import httpx
import ollama
from rich.cells import cell_len
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

import keychain
import params
import settings
from memory import (
    MemoryConfig,
    format_recall_block,
    handle_memory_command,
    inject_recall,
)
from recall import (
    recall_for_task,
    remember_success,
    retrieval_degraded,
    vector_for_capture,
)
from vectorstore import VectorStore

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

# ------------------------------------------------------------------------------
# Host-keychain secrets (SPEC-KEYCHAIN-001)
# ------------------------------------------------------------------------------
# READ AT IMPORT, AND THE TIMING IS THE REQUIREMENT (E3). `run_python()` passes
# no `env=` (main.py:496-503), so a child inherits whatever `os.environ` holds
# when it starts; deferring this to first use would leave the value readable by
# any script run earlier in the session with a one-line `print(os.environ)`.
# `keychain.load()` POPS each variable as it reads it, which closes that route
# for children (measured 2026-08-07) and closes NEITHER `/proc/self/environ` NOR
# `/proc/1/environ` (measured). It is a mitigation with a stated ceiling, not a
# fix — spec.md 4.1.
#
# The values arrive from the launcher, which fetched them from the host's own
# credential store before the container existed. Nothing here knows that: this is
# a dictionary, and every platform decision lives in bash (keychain.py's banner).
SECRETS = keychain.load(os.environ)

# ------------------------------------------------------------------------------
# Solution memory configuration (SPEC-MEMORY-001)
# ------------------------------------------------------------------------------
# Read once at import, matching the convention above, but parsed through
# validating helpers that catch ValueError, clamp to a documented range and fall
# back to the default.
#
# Deliberately NOT the pattern at :53-54. Those use a bare
# int(os.environ.get(...)) with no try/except: a non-numeric value raises at
# import time, before the banner and before preflight(), showing the user a raw
# traceback from a container that exits immediately. Retrofitting those two is
# out of scope for this SPEC.
MEMORY_CFG = MemoryConfig.from_env(MODEL_NAME)
MEMORY_ENABLED = MEMORY_CFG.enabled
# The `:latest` suffix is required, not cosmetic: coderunner:176 matches with
# `grep -qx` against `ollama list`, which prints fully-qualified tags, so a bare
# name would never match and would re-pull 274 MB on every launch.
EMBED_MODEL = MEMORY_CFG.embed_model
MEMORY_DB = MEMORY_CFG.db_path
MEMORY_TOP_K = MEMORY_CFG.top_k
MEMORY_MIN_SIM = MEMORY_CFG.min_sim
MEMORY_MAX_RECORDS = MEMORY_CFG.max_records

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
       - If you need a value only the user has (a city, an API key, a file
         path), do NOT call input(). Declare it as a comment INSIDE this same
         python block, before first use, then just use the name:

           # @param city: str = "Which city?"
           print(city)

         Types: str, int, float, secret. Use secret for keys and passwords —
         it is masked when typed. Never emit a second fenced block for these.
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


def stream_llm(client: ollama.Client, messages: list[dict]) -> Iterator[str]:
    """Stream one completion for an explicit message list.

    Takes the messages rather than the Conversation so that a caller can send a
    per-request list — specifically one carrying an ephemeral recall block —
    without mutating `Conversation.messages`. It also makes this function
    testable with a fake client, which it has never been.
    """
    stream = client.chat(model=MODEL_NAME, messages=messages, stream=True)
    for chunk in stream:
        piece = chunk.get("message", {}).get("content", "")
        if piece:
            yield piece


# Only the single in-flight line ever sits in the Live region below, so this
# repaints one line rather than a document. The old value was 24 against a
# whole growing panel.
STREAM_REFRESH_PER_SEC = 12

# Only the markdown constructs that OPEN AND CLOSE ON ONE LINE can be rendered
# by a renderer that never revisits a line. That is the whole constraint here,
# and it is not a limitation of the regex: a fenced block or a table is not
# renderable until its closing delimiter arrives, and waiting for that is what
# forces whole-document re-rendering and the flicker with it.
#
# Bold before italic, and the italic branch refuses a neighbouring asterisk, so
# `**x**` is never mistaken for an emphasised `*x*`.
_INLINE_MD_RE = re.compile(
    r"\*\*(?P<bold>[^*]+)\*\*"
    r"|(?<!\*)\*(?P<italic>[^*\s][^*]*)\*(?!\*)"
    r"|`(?P<code>[^`]+)`"
)

_FENCE_RE = re.compile(r"^\s*```")


def _render_markdown_line(line: str) -> Text:
    """Style the inline markdown in one line. Anything else is passed through."""
    out = Text()
    pos = 0
    for match in _INLINE_MD_RE.finditer(line):
        out.append(line[pos : match.start()])
        if match.group("bold") is not None:
            out.append(match.group("bold"), style="bold")
        elif match.group("italic") is not None:
            out.append(match.group("italic"), style="italic")
        else:
            out.append(match.group("code"), style="bold cyan")
        pos = match.end()
    out.append(line[pos:])
    return out


# `background_color="default"` is not cosmetic. Without it every highlighted
# line carries monokai's own dark background, which paints a ragged block behind
# each line as it arrives — the lines have different lengths, so the result
# looks like torn paper rather than a code listing.
_PY_HIGHLIGHTER = Syntax("", "python", theme="monokai", background_color="default")


# A left rail rather than a box. A box cannot be drawn around streaming output
# at all — its bottom edge is unknown until the closing fence arrives, so the
# block would have to be withheld until complete, which is exactly the
# "it shows at once" failure. A rail needs no knowledge of where the block ends:
# each line carries its own segment of it.
# U+2588 FULL BLOCK — a solid bar, not a rule. The rail is the only thing
# marking where a fenced block starts and stops, and it sits directly beside a
# line of syntax colours, so a line-drawing character loses that contest: the
# first attempt used a dim U+2502 and it disappeared, the second a bold U+2503
# and it still read as thin, and a third U+258C half block which was closer but
# still not solid. A block glyph is filled rather than stroked, which is what
# actually makes it thick — and the full block is the end of that ladder.
#
# The ladder, all cell_len 1 so any of them is layout-neutral:
#   │ U+2502 light   ┃ U+2503 heavy   ▎ U+258E quarter
#   ▌ U+258C half    ▊ U+258A three-quarter   █ U+2588 full
#
# Weight comes from the GLYPH, not the attribute: `bold` brightens a stroked
# character but does almost nothing to a filled one. The colour is what the
# attribute is for here.
#
# `bright_green` is a NAMED ANSI colour, deliberately, not a hex triple. A
# truecolor value degrades unpredictably — the colour system is resolved from
# the environment, and CI has already produced one failure that way (a runner
# with TERM unset renders in 16 colours). One of the sixteen standard colours
# renders as itself everywhere, including in the container, which sets
# TERM=xterm-256color at Dockerfile:11-23.
_CODE_RAIL = "  █ "
_CODE_RAIL_STYLE = "bold bright_green"


def _render_code_line(line: str, number: int) -> Text:
    """One line of the generated script, numbered and syntax-highlighted.

    Highlighting a line in isolation is imperfect by construction — a string
    literal or a bracket left open on a previous line is not visible from here,
    so pygments occasionally colours a continuation wrongly. That is accepted:
    the alternative is withholding the code until its closing fence arrives,
    which is precisely the "it appears all at once" complaint this replaced.
    """
    # Text() then append(style=...), NOT Text(..., style="dim"). The latter sets
    # a BASE style on the object, which applies to everything appended after it
    # too — the gutter's dim leaked onto every highlighted token and washed the
    # whole listing out.
    out = Text()
    out.append(_CODE_RAIL, style=_CODE_RAIL_STYLE)
    out.append(f"{number:>4} ", style="dim")
    highlighted = _PY_HIGHLIGHTER.highlight(line)
    highlighted.rstrip()  # highlight() appends the newline pygments emitted
    out.append_text(highlighted)
    return out


def _style_line(line: str, fence_depth: int, fence_lines: int, highlight_code: bool) -> Text:
    """Render one line exactly as it will finally appear.

    Used for BOTH the in-flight tail and the permanent print, and that is the
    whole reason it exists as a function. When the two differed — the tail plain
    and dim, the settled line numbered and coloured — every line visibly changed
    costume at the instant its newline arrived. Characters would flow in, then
    the finished line would blink into a different style. It read as stilted,
    line-at-a-time output rather than as a stream, which is what it is.

    Rendering the tail identically means nothing changes when a line completes.
    The text simply keeps flowing.
    """
    if not fence_depth:
        return _render_markdown_line(line)
    if highlight_code:
        return _render_code_line(line, fence_lines)
    # Unnumbered, but still railed: the reader still needs to see where the
    # block starts and stops.
    out = Text()
    out.append(_CODE_RAIL, style=_CODE_RAIL_STYLE)
    out.append(line, style="dim")
    return out


def _emit_line(
    line: str, fence_depth: int, fence_lines: int, highlight_code: bool
) -> tuple[int, int]:
    """Print one completed line, tracking fenced-block state. Returns the new state."""
    if _FENCE_RE.match(line):
        return (0, 0) if fence_depth else (1, 0)
    if fence_depth:
        fence_lines += 1
    console.print(_style_line(line, fence_depth, fence_lines, highlight_code))
    return fence_depth, fence_lines


def render_stream(
    title: str, style: str, token_iter: Iterator[str], *, highlight_code: bool = False
) -> str:
    """Print the model's reply one completed line at a time, never repainting it.

    The predecessor wrapped a growing ``Panel(Markdown(...))`` in a ``Live`` and
    called ``live.update()`` on EVERY token at 24 fps. Rich therefore re-rendered
    the entire document — border, padding, markdown, syntax-highlighted fences —
    and repainted a region that grew with the text. On a long reply containing a
    code block that reads as continuous flicker, and it gets worse the more the
    model says, which is exactly backwards.

    Here a line is printed once, when its newline arrives, and is never touched
    again. What remains in the Live region is only the tail that has not yet
    ended in a newline — one line, so a repaint of it is invisible. Keeping that
    tail live matters: without it a model emitting a whole paragraph before its
    first newline would show nothing at all while producing it, which is the
    "it is doing something but showing nothing" complaint in another costume.

    Inline markdown IS rendered, per line, by ``_render_markdown_line``. The
    first version of this function printed lines verbatim on the reasoning that
    "little is lost in practice"; that was wrong, and the model's own replies
    disproved it immediately — it opens with ``**CODE protocol**`` and closes
    with ``**Stop here.**``, both of which reached the user as literal asterisks.

    ``highlight_code`` numbers and syntax-highlights the lines inside a fenced
    block as they arrive. Its predecessor did the opposite — suppressed the
    block behind a "… 15 lines of code, shown below …" placeholder, on the
    grounds that ``show_code()`` re-rendered it below and the duplication was
    waste. That removed the duplication and took the live view with it: writing
    the script is the LONGEST stretch of a turn, and it became the one stretch
    with nothing on screen, after which finished code appeared all at once.

    So the code streams and the separate panel is gone. What was two renderings
    of the same lines — one live and plain, one final and highlighted — is now
    one that is both.
    """
    # Text(), not the bare string: Rich's automatic highlighter picks numbers
    # out of a plain str, so "Thought · attempt 1" rendered its digit in a
    # different colour to the words beside it.
    console.print(Rule(Text(title), style=style, align="left"))

    buffer: list[str] = []
    pending = ""
    fence_depth = 0
    fence_lines = 0
    with Live(Text(""), console=console, refresh_per_second=STREAM_REFRESH_PER_SEC,
              transient=True) as live:
        for token in token_iter:
            buffer.append(token)
            pending += token
            # A token can carry several newlines, or none.
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                fence_depth, fence_lines = _emit_line(
                    line, fence_depth, fence_lines, highlight_code
                )
            # The tail is rendered EXACTLY as it will settle (see _style_line).
            # It is what makes this read as a stream rather than as lines being
            # posted one at a time: characters flow into a line that already
            # carries its gutter number and its colours, and completing it
            # changes nothing on screen.
            #
            # A fence marker is never shown, so a tail that is opening one stays
            # blank until its newline flips the state.
            live.update(
                Text("")
                if _FENCE_RE.match(pending)
                else _style_line(pending, fence_depth, fence_lines + 1, highlight_code)
            )

    # The stream can end mid-line; the Live region was transient, so that tail
    # has just been erased and has to be reprinted as permanent output.
    if pending:
        fence_depth, fence_lines = _emit_line(pending, fence_depth, fence_lines, highlight_code)
    console.print(Rule(style=style))
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
    #  Author   : Chun Kang <ck@strpy.com>
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


def run_python(code: str, timeout: int = EXEC_TIMEOUT_SEC, prelude: str = "") -> ExecResult:
    """Execute one generated script. ``prelude`` carries the user's declared values.

    THE PRELUDE IS MERGED HERE AND NOWHERE ELSE, and that is the single most
    consequential line in SPEC-INPUT-001. `agentic_turn()` passes `code` to
    `_capture_turn()` (main.py:860-869); if the combined string were built in the
    caller, the natural next edit is to pass the combined string, and user-typed
    secrets start persisting to coderunner_app_data in plaintext where any later
    generated script can read them (tech.md 7.2).

    Keeping the assembly here means there is NO VARIABLE IN THE CALLER'S SCOPE
    holding a user value alongside code. The property is enforced by the absence
    of a thing, which is the only kind of enforcement that survives refactoring.
    `code = prelude + code` is the tidy version, reads better, removes an
    argument — and is what AC-CAP asserts object identity to catch, because every
    other test in this repository stays green under it.

    stdin is untouched, deliberately (U2). `capture_output=True` below pipes
    stdout and stderr and says nothing about stdin, so the child inherits the
    parent's descriptor 0 — `EOFError` under pytest, and the REPL's own TTY in
    the container, where an `input()` in generated code would BLOCK and eat the
    user's keystrokes for the full timeout. That is why main.py:136 still forbids
    `input()` and why the `# @param` alternative exists at all.
    """
    workdir = tempfile.mkdtemp(prefix="coderunner_")
    script_path = os.path.join(workdir, "run.py")

    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(SCRIPT_HEADER + "\n" + params.splice_prelude(code, prelude) + "\n")

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


# The icon flips every PULSE_HALF_PERIOD_SEC, so a full bright/dim cycle takes
# twice that. Refresh has to be comfortably faster than the flip or the phase
# lands unevenly and the pulse looks like a stutter rather than a beat.
PULSE_HALF_PERIOD_SEC = 0.4
PULSE_REFRESH_PER_SEC = 12


def _status_line(
    icon: str, tag: str, message: str, style: str, icon_style: str = "bold"
) -> Text:
    line = Text()
    line.append(f"{icon} ", style=icon_style)
    line.append(f"[{tag}] ", style=f"bold {style}")
    line.append(message, style="white")
    return line


def status(icon: str, tag: str, message: str, style: str = "cyan") -> None:
    console.print(_status_line(icon, tag, message, style))


class _PulsingLine:
    """A status line whose icon blinks on and off while work is running.

    Rich re-invokes ``__rich__`` on every refresh of a Live region, so the phase
    is derived from the clock rather than from mutation — no timer thread, and
    no state to reset between uses.

    **The icon is blanked, not dimmed, and that is the entire point.** Every
    icon this program passes in is a colour emoji (``🔄``, ``🧠``, ``⚙️``,
    ``💬``), and a colour emoji draws its colour from the font's own glyph
    table. SGR 1 (bold) and SGR 2 (faint) adjust the *foreground colour
    intensity* of a text glyph, so against an emoji they are honoured and
    change nothing whatsoever.

    The first implementation of this class dimmed the icon. It emitted a
    flawless alternating stream of ``\\x1b[1m`` and ``\\x1b[2m``, passed a test
    asserting exactly that, and animated nothing on any terminal — the very
    failure the paragraph below was written to avoid, reached by a different
    route. It went unnoticed for a day. Presence and absence of a glyph is not
    an attribute a terminal can decline to honour, which is why the animation
    now lives in the text rather than in a style.

    Note also what the test for that bug must use: the ``*`` the original test
    passed as an icon is a *text* glyph, for which bold and dim work perfectly.
    A test of this class is only meaningful with a real emoji.

    Still deliberately not the ANSI blink attribute (``\\x1b[5m``, which Rich
    will happily emit as ``style="blink"``). iTerm2, VS Code's terminal and
    Windows Terminal all ignore that code, so on the machines this project
    actually runs on it would animate nothing at all.
    """

    def __init__(self, icon: str, tag: str, message: str, style: str) -> None:
        self.icon = icon
        self.tag = tag
        self.message = message
        self.style = style

    def __rich__(self) -> Text:
        lit = int(time.monotonic() / PULSE_HALF_PERIOD_SEC) % 2 == 0
        # cell_len, not len: an emoji occupies two terminal columns while being
        # one or two code points, and a single space would drag the rest of the
        # line leftwards on every dark frame.
        icon = self.icon if lit else " " * cell_len(self.icon)
        return _status_line(icon, self.tag, self.message, self.style)


@contextmanager
def processing(
    icon: str, tag: str, message: str, style: str = "cyan", *, settle: bool = True
) -> Iterator[None]:
    """Pulse ``icon`` on a transient line for as long as the block runs.

    Nothing pulses once the block is done: the Live region is transient, so it
    is erased on exit and the terminal is left holding only steady text.
    ``settle=True`` then prints the same line permanently; pass ``settle=False``
    where the outcome decides the wording and the caller emits its own line.

    The final line is printed from a ``finally``, so a phase that raises still
    leaves a record of what was being attempted -- matching the old behaviour of
    printing the line up front.
    """
    if not console.is_terminal:
        # Piped, redirected or captured under pytest: an animation would just be
        # escape-code noise in the log. Do the work, then report it.
        try:
            yield
        finally:
            if settle:
                status(icon, tag, message, style)
        return

    try:
        with Live(
            _PulsingLine(icon, tag, message, style),
            console=console,
            refresh_per_second=PULSE_REFRESH_PER_SEC,
            transient=True,
        ):
            yield
    finally:
        if settle:
            status(icon, tag, message, style)


def prime_stream(tokens: Iterator[str]) -> Iterator[str]:
    """Draw the first token, returning a stream that still yields it.

    Ollama emits nothing until it has loaded the model and evaluated the
    prompt, which is the longest silent stretch in a turn. Pulling one token
    inside a ``processing`` block puts the animation exactly over that wait and
    stops it the instant real output begins.
    """
    try:
        first = next(tokens)
    except StopIteration:
        return iter(())
    return itertools.chain((first,), tokens)


# `show_code()` stood here and rendered the extracted block in a bordered
# "Generated Script" panel after the reasoning had finished streaming. It is
# gone because render_stream(highlight_code=True) now numbers and highlights
# those same lines as they arrive, so the panel showed the reader nothing they
# had not just watched appear — twice the vertical space for one listing.
#
# Restoring it means the code is on screen twice again. If a static, complete,
# word-wrapped view is ever wanted back, it belongs behind an explicit choice
# rather than on every turn.


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
        title = (
            "Execution TIMEOUT"
            if result.timed_out
            else f"Execution FAILED (rc={result.returncode})"
        )
        console.print(
            Panel(
                Text(err, style="red"),
                title=title,
                border_style="red",
                padding=(0, 1),
            )
        )


# The wordmark, 5 rows and 61 columns. 61 rather than the 86-column block art in
# this file's own header for one measured reason: the header art does not fit an
# 80-column terminal, which is still the default width of Terminal.app, and a
# logo that wraps is worse than no logo. LOGO_MIN_WIDTH leaves two columns of
# slack so a logo is never printed into a terminal that would fold it.
LOGO = """\
████ ████ ███  ████ ███  █  █ █  █ █  █ ████ ███     ████ ███
█    █  █ █  █ █    █  █ █  █ ██ █ ██ █ █    █  █    █  █  █
█    █  █ █  █ ███  ███  █  █ █ ██ █ ██ ███  ███     ████  █
█    █  █ █  █ █    █ █  █  █ █  █ █  █ █    █ █     █  █  █
████ ████ ███  ████ █  █ ████ █  █ █  █ ████ █  █ █  █  █ ███"""
LOGO_MIN_WIDTH = 63


def _clear_is_safe() -> bool:
    """Whether wiping the terminal would destroy something the user needs.

    Two ways it would. Redirected output is the obvious one: clear codes in a
    pipe or a log corrupt it, so this is gated on an actual terminal.

    The second is not obvious and is the reason this function exists rather than
    a bare `console.clear()`. Every `warn()` in the launcher fires BEFORE the
    container starts, and five of the six are SPEC-KEYCHAIN-001 U4 degradation
    lines — "'api_key' is registered but could not be read — it will be
    prompted." Their whole purpose is to tell the user that a declared secret
    will be typed rather than sourced. Clearing the screen at startup erases
    them in the instant before they are read, and the user then meets a getpass
    prompt with no idea why. The launcher sets CODERUNNER_LAUNCH_WARNED when it
    has said anything, and a clean screen loses to a line worth reading.
    """
    return console.is_terminal and not os.environ.get("CODERUNNER_LAUNCH_WARNED")


def show_banner() -> None:
    if _clear_is_safe():
        console.clear()

    if console.width >= LOGO_MIN_WIDTH:
        console.print(Text(LOGO, style="bold magenta"))
        console.print()

    banner = Text()
    banner.append("CodeRunner", style="bold magenta")
    banner.append(".AI  ", style="bold white")
    banner.append("— agentic Python interpreter powered by LLaMA", style="dim")
    subtitle = Text()
    subtitle.append("model: ", style="dim")
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


def _open_memory_store() -> VectorStore | None:
    """Open the solution store once per session, or degrade to None (M5)."""
    if not MEMORY_ENABLED:
        return None
    store = VectorStore.open(MEMORY_DB)
    if store is None:
        status(
            "🧠",
            "Memory",
            f"Solution memory unavailable at {MEMORY_DB} — continuing without it.",
            "yellow",
        )
    return store


# M5 requires exactly ONE status line per turn when the subsystem degrades. On a
# degraded session both retrieval and capture fail every turn, so reporting each
# separately would double the noise forever. The single wording covers both.
MEMORY_DEGRADED_MSG = "Unavailable this turn (embedding backend); continuing without memory."
MEMORY_UNWRITABLE_MSG = (
    "Could not save this solution (store unwritable); continuing without memory."
)


def _warn_memory(message: str) -> bool:
    """Emit the one degradation line for this turn. Always returns True."""
    status("🧠", "Memory", message, "yellow")
    return True


def _capture_turn(
    client: ollama.Client,
    store: VectorStore | None,
    task: str,
    thought: str,
    code: str,
    stdout: str,
    recall_result,
    already_warned: bool,
) -> bool:
    """Persist one successful turn. Returns True if a warning was emitted here.

    ``already_warned`` carries the retrieval outcome forward so a turn in which
    BOTH retrieval and capture fail reports once, not twice.
    """
    if store is None or not MEMORY_ENABLED:
        return False  # deliberately off, or reported once at startup

    # settle=False: the embed and the write share one animation, but which line
    # follows depends on how they went, so the outcome branches below print it.
    with processing("🧠", "Memory", "Saving this solution…", "green", settle=False):
        vector = vector_for_capture(client, store, task, MEMORY_CFG, recall_result)
        # `and` short-circuits, so a failed embed still skips the write exactly
        # as the sequential form did.
        written = bool(vector) and remember_success(
            store, task, thought, code, stdout, vector, MEMORY_CFG
        )

    if not vector:
        # Either retrieval's embed already failed (and was reported), or the
        # cold-start embed just failed here.
        return False if already_warned else _warn_memory(MEMORY_DEGRADED_MSG)

    if written:
        status("🧠", "Memory", "Captured this solution for future turns.", "green")
        return False

    # The store rejected the write — unwritable, locked, or corrupt. Silent
    # until the smoke run caught it.
    return False if already_warned else _warn_memory(MEMORY_UNWRITABLE_MSG)


# ------------------------------------------------------------------------------
# Declared parameters (SPEC-INPUT-001)
# ------------------------------------------------------------------------------
# Wiring only. Every decision — what counts as a declaration, how a literal is
# rendered, what a malformed settings file means, what gets redacted — lives in
# params.py or settings.py, both gated at 100%. main.py is under no coverage
# floor (spec.md 5.3), so the rule holding the line is: if a change here would
# need a new test to be trusted, it is in the wrong file.


def _ask_param(decl: params.Declaration, retry: bool) -> str:
    """Read one declared value. Two prompt paths, and they must stay different.

    A `secret` NEVER goes through `input()` (N3). `_install_history()`
    (main.py:930-957) wires readline and registers an `atexit` writer, so any
    line read through `input()` while readline is loaded enters the history
    buffer and is written to CODERUNNER_HISTORY — pinned by compose to
    /home/runner/.coderunner/history (docker-compose.yml:107), on the volume that
    survives `--rm`. A secret typed at an `input()` prompt would therefore be
    persisted in plaintext next to the memory store, by a mechanism NO capture
    policy in this SPEC inspects: every policy, including `never`, would report
    that nothing was stored and would be telling the truth about the only store
    it knows about.

    `getpass` is also not readline, which is why its prompt carries no
    \\001/\\002 bracketing — it writes the prompt raw and would emit those as
    literal control bytes. The two paths therefore look gratuitously
    inconsistent, one coloured and bracketed and one plain, and that is exactly
    what invites a later cleanup to unify them. Do not.
    """
    # Flushed for both paths, matching _prompt_user() (main.py:977-981): Rich
    # buffers its own writes, and neither input() nor getpass goes through it, so
    # without this the prompt can be drawn before the line that explains it.
    console.file.flush()
    if decl.type == params.TYPE_SECRET:
        return getpass.getpass(params.secret_prompt(decl, retry))
    return input(params.plain_prompt(decl, retry))


def _ask_policy(prompt: str) -> str:
    console.file.flush()
    return input(prompt)


def _resolve_param_policy(session: settings.PolicySession) -> settings.Policy:
    """The capture policy for this session, asked once on the first parameterised
    turn and never at startup (spec.md 4.5).

    `ask=None` when stdin is not interactive — a piped session or a test. The
    question then cannot be asked, so the policy falls back to `never`, one line
    says so, and no file is written.
    """
    return settings.ensure_policy(
        session,
        _ask_policy if sys.stdin.isatty() else None,
        lambda line: console.print(Text(f"     {line}", style="dim")),
        lambda line: status("⚙️", "Params", line, "yellow"),
    )


def _collect_params(
    declarations: list[params.Declaration],
    values: dict[str, object],
    session: settings.PolicySession,
) -> list[params.Declaration]:
    """Source what the keychain has, prompt for the rest, return everything.

    Returns the declarations newly collected here — SOURCED ONES INCLUDED — so
    the caller can accumulate them across attempts. Nothing is prompted twice in
    a turn (E4), and the assembled prelude is never printed, for any value,
    secret or not (N2).

    THREE THINGS HERE ARE LOAD-BEARING AND ALL THREE ARE INVISIBLE WHEN WRONG.

    **(a) `_resolve_param_policy()` is unconditional on `pending` and MUST NOT
    become conditional on `asked`** (S1, AC-POLICY). Before SPEC-KEYCHAIN-001 the
    two were the same set, so the call could live inside the block that prompts
    and nobody could tell. They are no longer the same set: a turn whose values
    all came from the keychain prompts nothing and still holds a secret. Move
    this line and the chain is:

        param_session.policy stays None
          -> main.py:981   reads the policy as ""
          -> main.py:988   `policy == POLICY_SENSITIVE` is False -> no redaction
          -> main.py:1026  `policy == POLICY_NEVER`     is False -> capture runs
          -> _capture_turn() persists stdout containing the secret, in plaintext,
             to coderunner_app_data, which tech.md 7.2 states any later generated
             script can read

    Nothing in it raises, warns or prints. The script runs, the panel is green,
    the answer streams, the turn is captured as solved.

    The cost is real and is accepted rather than designed around (R8): the
    first-run capture-policy question can now fire on a turn where the user typed
    nothing at all. That is correct — the policy governs capture, not prompting —
    and it is surprising. Do not "fix" it by making resolution conditional again.

    **(b) `pending` is returned, not `asked`.** main.py:974 accumulates the
    return value into `param_declared`, which main.py:987 feeds to
    `params.secret_values()` to build the redaction set. A sourced declaration
    dropped from the return value is a secret redaction never sees.

    **(c) The prefill goes THROUGH the collection seam, not around it.**
    `keychain.prefill()` writes into `values`; `collect_values()`'s existing skip
    (params.py:201-203) is then what suppresses the prompt. So `ask` is never
    invoked for a sourced name, `_ask_param()` never runs, `getpass` never runs,
    and no branch was added to a module gated at 100%. The absence of a call is
    easier to verify than the presence of a guard.
    """
    pending = params.pending_declarations(declarations, values)
    if not pending:
        return pending

    sourced = keychain.prefill(pending, values, SECRETS)
    asked = params.pending_declarations(pending, values)

    if asked:
        status("⚙️", "Params", params.announcement(asked), "cyan")
    _resolve_param_policy(session)  # UNCONDITIONAL — see (a) above
    for name in sourced:
        status("⚙️", "Params", PARAM_SOURCED_MSG.format(name=name), "cyan")
    if asked:
        params.collect_values(asked, _ask_param, values)
    # E5: the masked confirmation is emitted for the whole of `pending`, so a
    # sourced secret is exactly as visible in the transcript as a typed one.
    for line in params.confirmations(pending, values):
        status("⚙️", "Params", line, "cyan")
    return pending


PARAMS_NOT_STORED_MSG = (
    "This turn used parameters — not stored, per the capture policy (/params)."
)

#: E5. One line per sourced parameter, naming it and its source, so a value the
#: user was not asked for is still something they were told about. The launcher
#: reports its own faults in its own output, before the banner; this is the only
#: per-turn line the feature has, and it is emitted on the SUCCESS path only —
#: a line on every parameterised turn is how a warning becomes furniture
#: (spec.md 3.8).
PARAM_SOURCED_MSG = "{name} supplied from the host keychain (not asked)."


def agentic_turn(
    client: ollama.Client,
    conv: Conversation,
    user_input: str,
    store: VectorStore | None = None,
    param_session: settings.PolicySession | None = None,
) -> None:
    conv.user(user_input)

    # Values are collected once per turn and held here for the life of it. A
    # mistyped value therefore cannot be corrected within the turn; the escape is
    # Ctrl+C, already handled as "abort this turn only" at main.py:1022-1023. The
    # alternative — re-prompting on every attempt — means typing an API key three
    # times to watch a script fail three times (spec.md 3.4).
    param_values: dict[str, object] = {}
    param_declared: list[params.Declaration] = []
    param_session = settings.PolicySession() if param_session is None else param_session

    # Retrieval runs ONCE per turn, before the loop, so the embedding round trip
    # is not paid per attempt. The resulting vector is cached and reused by the
    # capture below, so a turn costs exactly one embed call, not two (M2).
    # Only animate when there is actually a store to search: with memory off,
    # recall_for_task returns immediately and a flashed "Searching…" would claim
    # work that never happened.
    searching = (
        processing("🧠", "Memory", "Searching past solutions…", "green", settle=False)
        if store is not None and MEMORY_ENABLED
        else nullcontext()
    )
    with searching:
        recall_result = recall_for_task(client, store, user_input, MEMORY_CFG)
    recall_block: str | None = None

    # At most one degradation line per turn, tracked from here through capture.
    # Silent degradation is risk R7: without this the user has no way to learn
    # that memory has stopped working, because every turn still looks correct.
    memory_warned = retrieval_degraded(store, user_input, MEMORY_CFG, recall_result)
    if memory_warned:
        _warn_memory(MEMORY_DEGRADED_MSG)
    elif recall_result is not None and recall_result.record is not None:
        recall_block = format_recall_block(recall_result.record)
        status(
            "🧠",
            "Memory",
            f"Recalled a similar solved task (similarity {recall_result.similarity:.2f}).",
            "green",
        )

    for attempt in range(1, MAX_RETRIES + 1):
        # Attempt 1 only (C8). On a retry the conversation already contains the
        # failed attempt, and re-injecting the same example risks re-anchoring
        # the model on an approach that has just been shown not to work.
        #
        # inject_recall returns a NEW list; conv.messages is never mutated, so
        # the block is ephemeral to this one request and cannot accumulate
        # across turns.
        request_messages = (
            inject_recall(conv.messages, recall_block)
            if attempt == 1 and recall_block is not None
            else conv.messages
        )

        with processing(
            "🔄",
            "LLaMA",
            f"Analyzing request and designing solution (attempt {attempt}/{MAX_RETRIES})…",
            "cyan",
        ):
            thought_tokens = prime_stream(stream_llm(client, request_messages))

        thought = render_stream(
            title=f"Thought · attempt {attempt}",
            style="cyan",
            token_iter=thought_tokens,
            # The script is numbered and highlighted AS IT ARRIVES, which is
            # why no Generated Script panel follows: the reader has already
            # watched these lines being written.
            highlight_code=True,
        )
        conv.assistant(thought)

        code = extract_last_python_block(thought)
        if not code:
            status("💬", "LLaMA", "No code produced — returning direct answer.", "yellow")
            return

        # `code` IS NEVER REASSIGNED past this point. It is the object handed to
        # _capture_turn() below, and the prelude is merged inside run_python()
        # instead, so an injected value is absent from the store by construction
        # rather than by filtering (U3, N4, AC-CAP).
        #
        # Collection sits HERE, after render_stream() has returned and before the
        # processing() block below: processing() opens a transient Rich Live
        # region (main.py:562-596), and a prompt inside one fights the renderer
        # for the terminal. There is exactly one point in the turn that satisfies
        # S5 and this is it.
        declarations = params.parse_declarations(code)
        param_declared.extend(_collect_params(declarations, param_values, param_session))

        with processing("⚙️", "System", "Running generated Python code…", "yellow"):
            result = run_python(code, prelude=params.render_prelude(declarations, param_values))

        # Empty until the first parameterised turn resolves it, which is what
        # keeps a turn that declared nothing byte-for-byte the pre-feature turn.
        policy = param_session.policy.value if param_session.policy is not None else ""

        # ONE redaction point, not three. E6 names three sinks — the panel below,
        # the feedback splices at :838-842 and :878-884, and the capture call —
        # and redacting the RESULT itself closes all three at once, structurally.
        # Three helpers would be three chances to update two of them.
        secrets = params.secret_values(param_declared, param_values)
        if secrets and policy == settings.POLICY_SENSITIVE:
            result = replace(
                result,
                stdout=params.redact(result.stdout, secrets),
                stderr=params.redact(result.stderr, secrets),
            )

        show_exec_result(result)

        if result.ok:
            preview = (result.stdout.strip().splitlines() or [""])[-1][:120]
            status("📊", "System", f"Execution successful (Output: {preview or 'n/a'})", "green")
            feedback = (
                f"Execution succeeded.\n\nSTDOUT:\n```\n{result.stdout.strip()}\n```\n"
                "Please provide the final Answer to the user in Markdown."
            )
            conv.user(feedback)

            with processing("💬", "LLaMA", "Final response streaming…", "magenta"):
                # No recall block on the grounded pass: it only needs the stdout.
                answer_tokens = prime_stream(stream_llm(client, conv.messages))

            answer = render_stream(
                title="Answer",
                style="magenta",
                token_iter=answer_tokens,
            )
            conv.assistant(answer)

            # Capture last, after the answer has streamed, so the embed/write
            # latency lands at the end of the turn rather than stalling
            # mid-flow. Captured on a retrieval MISS too — a miss is exactly
            # what a new task looks like, and skipping it would freeze the
            # store at its first record (M3).
            #
            # S1: under `never`, a parameterised turn is not captured at all —
            # and one line says so, because silence here is indistinguishable
            # from a successful capture.
            if param_declared and policy == settings.POLICY_NEVER:
                status("⚙️", "Params", PARAMS_NOT_STORED_MSG, "yellow")
                return

            _capture_turn(
                client,
                store,
                user_input,
                thought,
                code,
                result.stdout,
                recall_result,
                memory_warned,
            )
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


# readline counts EVERY byte of the prompt as one visible column unless it is
# bracketed by \001 (RL_PROMPT_START_IGNORE) and \002 (RL_PROMPT_END_IGNORE).
#
# Unbracketed, the eleven bytes of colour escape here are counted as eleven
# columns, so readline believes the cursor sits eleven columns to the right of
# where it is. Every redraw is then computed from a wrong origin — and a redraw
# is exactly what Up and Down do. Recalling an entry erases the wrong span, so
# the recalled text appears appended to whatever was already on the line
# instead of replacing it. The bug is invisible until the user presses an arrow
# key, which is why a prompt that looks perfect can still be wrong.
#
# The brackets are the fix and they are not decoration: remove them and the
# history navigation breaks again, silently, while the prompt still renders
# correctly.
PROMPT = "\001\033[1;32m\002you\001\033[0m\002 ➜ "


def _prompt_user() -> str:
    """Read a line with arrow-key history. Rich handles the banner/rendering;
    the actual input() call is what gives us readline's line-editing."""
    console.file.flush()
    return input(PROMPT)


def repl() -> None:
    show_banner()
    _install_history()
    client = build_client()
    if not preflight(client):
        status("ℹ", "System", "Fix the host, then re-run ./coderunner.", "yellow")
        sys.exit(2)

    conv = Conversation()
    conv.system(SYSTEM_PROMPT)

    # Opened once for the session and threaded into every turn. None means the
    # feature is off or unavailable, and every downstream call handles that.
    store = _open_memory_store()

    # Empty until the first turn that declares a parameter. Nothing is read from
    # disk and nothing is written here: a user who never uses the feature is
    # never asked and settings.json is never created for them (spec.md 4.5).
    param_session = settings.PolicySession()

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
        # Handled locally, beside the exit words: /memory never reaches the model.
        if handle_memory_command(store, stripped, lambda line: console.print(line), MEMORY_CFG):
            continue
        params_handled, chosen = settings.handle_params_command(
            stripped, lambda line: console.print(line), param_session.policy
        )
        if params_handled:
            if chosen is not None:
                param_session.policy = chosen
            continue

        try:
            agentic_turn(client, conv, stripped, store, param_session)
        except ollama.ResponseError as err:
            status("❌", "LLaMA", f"API error: {err}", "red")
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as err:
            console.print(_connection_help_panel(err))
        except KeyboardInterrupt:
            status("⏹", "System", "Turn interrupted.", "yellow")

    if store is not None:
        store.close()

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
