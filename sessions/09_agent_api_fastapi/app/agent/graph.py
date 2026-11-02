"""The Research Brief Agent: one Deep Agent with web search and an approval step before saving."""
from pathlib import Path

from deepagents import create_deep_agent
from langchain.agents.middleware import ToolCallLimitMiddleware

from app.agent.tools import Context, internet_search, save_brief

PROMPT = (Path(__file__).parent / "prompts" / "research_brief.md").read_text().strip()


def build_agent(model, checkpointer=None):
    """Built once at startup (lifespan); the checkpointer keeps every thread so interrupts can be resumed."""
    return create_deep_agent(
        model=model,
        tools=[internet_search, save_brief],
        system_prompt=PROMPT,
        context_schema=Context,
        interrupt_on={"save_brief": {"allowed_decisions": ["approve", "reject"]}},  # HumanInTheLoopMiddleware
        middleware=[ToolCallLimitMiddleware(tool_name="internet_search", run_limit=3, exit_behavior="continue")],
        checkpointer=checkpointer,
        name="research_brief",
    )
