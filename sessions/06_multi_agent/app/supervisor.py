"""The `supervisor` graph: launches `researcher` runs as background tasks. Both graphs are registered in the same
langgraph.json, so `AsyncSubAgent` needs no url: the SDK calls the researcher in-process (ASGI transport)."""
import os
from pathlib import Path

from deepagents import AsyncSubAgent, create_deep_agent
from dotenv import load_dotenv
from langchain.agents.middleware import ToolCallLimitMiddleware

SESSION_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SESSION_DIR / ".env")

researcher = AsyncSubAgent(
    name="researcher",
    description="Researches ONE question on the web in the background and returns cited bullets.",
    graph_id="researcher",  # the graph name in langgraph.json; no url -> same deployment (ASGI)
)

graph = create_deep_agent(
    name="supervisor",
    model=os.getenv("MODEL", "openai:gpt-6-luna"),
    subagents=[researcher],
    system_prompt=(SESSION_DIR / "prompts" / "async_supervisor.md").read_text(),
    middleware=[
        # Budget of the supervisor: at most 4 launches per thread, at most 2 status checks per turn.
        ToolCallLimitMiddleware(tool_name="start_async_task", thread_limit=4, exit_behavior="continue"),
        ToolCallLimitMiddleware(tool_name="check_async_task", run_limit=2, exit_behavior="continue"),
    ],
)
