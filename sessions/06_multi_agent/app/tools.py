"""Tools shared by the notebooks and by the async researcher graph (app/researcher.py)."""
import logging
import time

from langchain.tools import tool
from tavily import TavilyClient

logger = logging.getLogger(__name__)
_tavily = None


def tavily() -> TavilyClient:
    global _tavily
    _tavily = _tavily or TavilyClient()  # reads TAVILY_API_KEY from the environment (.env)
    return _tavily


def log_call(tool_name: str, args: str, status: str, started: float) -> None:
    """The one log line of a tool call: tool(short args) -> ok|error <ms> ms."""
    args = " ".join(args.split())
    logger.info("%s(%s) -> %s %d ms", tool_name, args if len(args) <= 70 else args[:70] + "…", status,
                (time.monotonic() - started) * 1000)


@tool(parse_docstring=True)
def internet_search(query: str) -> list[dict]:
    """Search the web and return title, url and a short snippet for the 3 best results.

    Run one or two focused queries rather than many broad ones.

    Args:
        query: What to search for, in a few keywords.
    """
    started, status = time.monotonic(), "error"
    try:
        results = tavily().search(query, max_results=3)["results"]  # 3 results keep each call small and cheap
        status = "ok"
        return [{"title": r["title"], "url": r["url"], "content": r["content"][:500]} for r in results]
    except Exception as exc:  # quota, network, bad key: tell the model instead of crashing the whole run
        return [{"error": f"search failed: {exc}"}]
    finally:
        log_call("internet_search", repr(query), status, started)
