"""Tools of the Research Brief Agent (copied from Sessions 02 and 05).

- ``search_kb(query, product)``  keyword search in ``data/kb_mini.jsonl``, filtered by the team of the current user
  (``runtime.context``). The lookup is traced as a RETRIEVER observation with ``@observe``.
- ``search_docs(query)``  web search on the LangChain Python docs (Tavily).
- ``read_doc(url)``  reads one docs page (Tavily Extract), cached in ``data/read_doc_cache.jsonl`` so every run reads the same text.
"""
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langchain.tools import ToolRuntime, tool
from langfuse import observe
from tavily import TavilyClient

DATA = Path(__file__).resolve().parents[1] / "data"
DOCS_SITE = "https://docs.langchain.com/oss/python/"
TEAMS = {"alice": "research", "bob": "finance"}  # owned by the app, never set by the model
logger = logging.getLogger(__name__)
KB = [json.loads(line) for line in (DATA / "kb_mini.jsonl").read_text().splitlines() if line.strip()]
CACHE_PATH = DATA / "read_doc_cache.jsonl"
CACHE = {r["url"]: r["text"] for r in (json.loads(line) for line in CACHE_PATH.read_text().splitlines() if line.strip())}


@dataclass
class UserContext:
    """Passed with ``agent.invoke(..., context=UserContext("alice"))``."""

    user_id: str

    @property
    def team(self) -> str:
        return TEAMS.get(self.user_id, "public")


@observe(as_type="retriever", name="retrieve-kb-pages")
def retrieve(query: str, product: str | None, team: str, k: int = 3) -> list[dict]:
    """Keyword score over title, url and text; only pages the team may see."""
    words = {w for w in re.findall(r"[a-z0-9_]+", query.lower()) if len(w) > 2}
    scored = []
    for p in KB:
        if p["team"] not in ("public", "all-staff", team) or (product and p["product"] != product):
            continue
        score = sum(3 * (w in p["title"].lower()) + 2 * (w in p["url"]) + 0.2 * p["text"].lower().count(w) for w in words)
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [{"url": p["url"], "title": p["title"], "snippet": p["text"][:200]} for _, p in scored[:k]]


@tool
def search_kb(query: str, runtime: ToolRuntime[UserContext],
              product: Literal["langchain", "langgraph", "deepagents", "internal"] | None = None) -> list[dict]:
    """Search the knowledge base of LangChain, LangGraph and Deep Agents docs. Returns up to 3 pages (url, title, snippet). Write the query in English."""
    logger.info("search_kb(%r)", query)
    return retrieve(query, product, runtime.context.team)


@tool
def search_docs(query: str) -> list[dict]:
    """Search the official LangChain and LangGraph Python documentation on the web. Returns the title and url of the top pages."""
    logger.info("search_docs(%r)", query)
    try:
        hits = TavilyClient().search(query, include_domains=["docs.langchain.com"], max_results=5)["results"]
    except Exception as exc:  # quota, network: tell the model instead of crashing the run
        return [{"error": f"search failed: {exc}"}]
    return [{"title": h["title"], "url": h["url"]} for h in hits if h["url"].startswith(DOCS_SITE)][:3]


@tool
def read_doc(url: str) -> str:
    """Read one documentation page (first part of the page). Use a url returned by search_kb or search_docs."""
    logger.info("read_doc(%s)", url.removeprefix(DOCS_SITE))
    if not url.startswith(DOCS_SITE):
        return f"ERROR: only pages under {DOCS_SITE} can be read"
    if url not in CACHE:  # one Tavily Extract call, then the text is kept for every later run
        try:
            text = TavilyClient().extract(urls=[url])["results"][0]["raw_content"]
        except Exception as exc:
            return f"ERROR: could not read {url}: {exc}"
        CACHE[url] = text[text.find("\n# ") + 1:][:6000]  # drop the navigation above the page title
        with open(CACHE_PATH, "a") as f:
            f.write(json.dumps({"url": url, "text": CACHE[url]}, ensure_ascii=False) + "\n")
    return CACHE[url]


TOOLS = [search_kb, search_docs, read_doc]
