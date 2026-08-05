# ==============================================================================
#  CodeRunner.AI  ::  Runtime Tools Library (importable from generated scripts)
# ------------------------------------------------------------------------------
#  Author  : kurapa <kurapa@kurapa.com>
#  Purpose : Small helpers the model may import from generated code — currently
#            a stdlib-only web_search() using DuckDuckGo's Instant Answer API.
# ==============================================================================

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request

_UA = "Mozilla/5.0 (CodeRunner.AI/1.0 stdlib-agent)"
_TIMEOUT = 8


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _ddg_instant(query: str) -> list[dict]:
    url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
    )
    data = json.loads(_fetch(url))
    hits: list[dict] = []
    if data.get("AbstractText"):
        hits.append({
            "title": data.get("Heading") or query,
            "snippet": data["AbstractText"],
            "url": data.get("AbstractURL", ""),
            "source": data.get("AbstractSource", "DuckDuckGo"),
        })
    for topic in data.get("RelatedTopics", []) or []:
        if "Text" in topic and "FirstURL" in topic:
            hits.append({
                "title": topic.get("Text", "").split(" - ")[0],
                "snippet": topic.get("Text", ""),
                "url": topic.get("FirstURL", ""),
                "source": "DuckDuckGo",
            })
    return hits


_HTML_RESULT_RE = re.compile(
    r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
    r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
    re.DOTALL,
)


def _ddg_html(query: str, limit: int) -> list[dict]:
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    body = _fetch(url)
    hits: list[dict] = []
    for m in _HTML_RESULT_RE.finditer(body):
        raw_url, raw_title, raw_snip = m.groups()
        parsed = urllib.parse.urlparse(raw_url)
        real = urllib.parse.parse_qs(parsed.query).get("uddg", [raw_url])[0]
        hits.append({
            "title": html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip(),
            "snippet": html.unescape(re.sub(r"<[^>]+>", "", raw_snip)).strip(),
            "url": real,
            "source": "DuckDuckGo",
        })
        if len(hits) >= limit:
            break
    return hits


def web_search(query: str, limit: int = 5) -> list[dict]:
    """Return up to ``limit`` search hits as [{title, snippet, url, source}, …].

    Uses DuckDuckGo's Instant Answer API first (fast, structured), then falls
    back to scraping the HTML endpoint if no instant answer is available.
    Stdlib-only — safe to call from generated scripts.
    """
    if not query or not query.strip():
        return []
    try:
        hits = _ddg_instant(query)
        if hits:
            return hits[:limit]
    except Exception:
        pass
    try:
        return _ddg_html(query, limit)
    except Exception as err:
        return [{"title": "search_error", "snippet": str(err), "url": "", "source": "local"}]


__all__ = ["web_search"]
