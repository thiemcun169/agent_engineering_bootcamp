"""The `researcher` graph: one background research task. Served by `langgraph dev` together with `supervisor`
(langgraph.json), so the supervisor reaches it in-process (ASGI transport)."""
import asyncio
import os
from pathlib import Path

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain.tools import tool

from app.tools import internet_search as web_search

SESSION_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SESSION_DIR / ".env")

RESEARCH_DELAY_S = 15  # pause before each search, so a task stays "running" long enough to watch it; set 0 to disable


@tool(description=web_search.description, args_schema=web_search.args_schema)
async def internet_search(query: str) -> list[dict]:
    await asyncio.sleep(RESEARCH_DELAY_S)
    return await web_search.ainvoke({"query": query})


graph = create_deep_agent(
    name="researcher",
    model=os.getenv("MODEL", "openai:gpt-6-luna"),
    tools=[internet_search],
    system_prompt=(SESSION_DIR / "prompts" / "researcher.md").read_text(),
    middleware=[
        # Budget of ONE background task: at most 4 model calls and 2 searches, then it ends with what it has.
        ModelCallLimitMiddleware(run_limit=4, exit_behavior="end"),
        ToolCallLimitMiddleware(tool_name="internet_search", run_limit=2, exit_behavior="continue"),
    ],
)
