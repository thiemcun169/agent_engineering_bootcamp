"""Tools of the Research Brief Agent (copied from Session 06 and trimmed). Tools read the signed-in user from the run
context, never from the model's arguments."""
import logging
import re
import time
from dataclasses import dataclass

from langchain.tools import ToolRuntime, tool
from langgraph.config import get_stream_writer
from tavily import TavilyClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_tavily: TavilyClient | None = None


@dataclass
class Context:
    """Run context filled by the API from the bearer token (LangChain runtime context)."""
    user_id: str


def log_call(tool_name: str, args: str, status: str, started: float) -> None:
    """The one log line of a tool call: tool(short args) -> ok|error <ms> ms."""
    args = " ".join(args.split())
    logger.info("%s(%s) -> %s %d ms", tool_name, args if len(args) <= 70 else args[:70] + "…", status,
                (time.monotonic() - started) * 1000)


@tool(parse_docstring=True)
def internet_search(query: str) -> list[dict]:
    """Search the web and return title, url and a short snippet for the 3 best results.

    Args:
        query: What to search for, in a few keywords.
    """
    global _tavily
    started, status = time.monotonic(), "error"
    get_stream_writer()({"stage": "searching", "query": query})  # stream_mode="custom": progress for the UI
    try:
        _tavily = _tavily or TavilyClient(api_key=get_settings().tavily_api_key.get_secret_value())
        results = _tavily.search(query, max_results=3)["results"]  # 3 results keep each call small and cheap
        status = "ok"
        return [{"title": r["title"], "url": r["url"], "content": r["content"][:500]} for r in results]
    except Exception as exc:  # quota, network, bad key: tell the model instead of crashing the whole run
        return [{"error": f"search failed: {exc}"}]
    finally:
        log_call("internet_search", repr(query), status, started)


@tool(parse_docstring=True)
def save_brief(title: str, content: str, runtime: ToolRuntime[Context]) -> str:
    """Save the finished brief to the user's brief folder. A person approves the save first.

    Args:
        title: A short title, a few words.
        content: The full brief in Markdown.
    """
    started = time.monotonic()
    user_id = runtime.context.user_id  # from the API's token check, not from the model
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50] or "brief"
    path = get_settings().data_dir / "briefs" / user_id / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log_call("save_brief", f"{user_id}/{slug}.md", "ok", started)
    return f"saved: briefs/{user_id}/{slug}.md"
