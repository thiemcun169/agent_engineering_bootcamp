"""Helpers shared by the Session 06 notebooks: prompts, streaming with one line per agent step, and a usage table
(model calls and tokens per agent). The notebooks keep only what each part teaches."""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from langchain.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.callbacks import BaseCallbackHandler

SESSION_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SESSION_DIR))  # so `from app.tools import internet_search` works (shared with langgraph dev)
from app.tools import internet_search, log_call  # noqa: E402,F401


def prompt(name: str) -> str:
    """A system prompt from prompts/<name>.md."""
    return (SESSION_DIR / "prompts" / f"{name}.md").read_text().strip()


def short(text, n: int = 100) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + "…"


# ── Usage: model calls and tokens per agent ──────────────────────────────────
class Usage(BaseCallbackHandler):
    """Counts model calls and provider-reported tokens per agent (`lc_agent_name`, set by create_agent(name=…))."""

    def __init__(self):
        self.agent_of_run, self.rows = {}, defaultdict(lambda: {"calls": 0, "input": 0, "output": 0})

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        meta = metadata or {}
        self.agent_of_run[run_id] = meta.get("lc_agent_name") or meta.get("langgraph_node") or "model"

    def on_llm_end(self, response, *, run_id, **kwargs):
        row = self.rows[self.agent_of_run.pop(run_id, "model")]
        usage = getattr(response.generations[0][0].message, "usage_metadata", None) or {}
        row["calls"] += 1
        row["input"] += usage.get("input_tokens", 0)
        row["output"] += usage.get("output_tokens", 0)

    def total(self) -> dict:
        return {k: sum(r[k] for r in self.rows.values()) for k in ("calls", "input", "output")}

    def table(self, title: str = ""):
        print(f"\n{title}\n{'agent':<24}{'model calls':>12}{'input tok':>11}{'output tok':>11}")
        for agent, r in self.rows.items():
            print(f"{agent:<24}{r['calls']:>12}{r['input']:>11,}{r['output']:>11,}")
        t = self.total()
        print(f"{'total':<24}{t['calls']:>12}{t['input']:>11,}{t['output']:>11,}")


# ── Streaming: tokens of the main agent, one line per tool call of every agent ──
def _key(m) -> str:
    return m.id or f"{type(m).__name__}-{getattr(m, 'tool_call_id', '')}-{hash(m.text)}"


async def stream(agent, question: str, config: dict | None = None, *, context=None, main: str = "main",
                 show_tokens: bool = True) -> tuple[dict, Usage, float]:
    """Stream one turn with stream_mode=["updates", "messages", "values"] and subgraphs=True, so the steps of
    subagents show too: `[agent] → tool(args)` for a call, `[agent] ← tool: result` for its result, the main agent's
    answer token by token. Returns (final state values, Usage, seconds)."""
    usage, started, mid_line, final = Usage(), time.monotonic(), False, {}
    agent_of_ns, seen = {(): main}, set()  # namespace of a (sub)graph -> agent name; messages already printed
    if getattr(agent, "checkpointer", None) and (config or {}).get("configurable", {}).get("thread_id"):
        before = await agent.aget_state(config)  # earlier turns of this thread are not printed again
        seen = {_key(m) for m in before.values.get("messages", [])}
    config = {**(config or {}), "callbacks": [usage]}
    async for ns, mode, data in agent.astream({"messages": [{"role": "user", "content": question}]}, config,
                                              context=context, stream_mode=["updates", "messages", "values"],
                                              subgraphs=True):
        if mode == "values":  # full state after each step; the last one of the main graph is the result
            final = data if not ns else final
            continue
        if mode == "messages":
            token, meta = data
            if (show_tokens and not ns and isinstance(token, AIMessageChunk) and token.text
                    and meta.get("langgraph_node") == "model"):
                print(token.text, end="", flush=True)
                mid_line = True
            continue
        for update in data.values():
            for m in (update or {}).get("messages", []) if isinstance(update, dict) else []:
                if _key(m) in seen:  # a parent graph re-emits the messages of its child
                    continue
                seen.add(_key(m))
                if isinstance(m, AIMessage) and m.name:
                    agent_of_ns[ns] = m.name  # AI messages carry the name given to create_agent / create_deep_agent
                who, lines = agent_of_ns.get(ns, "subagent"), []
                for c in getattr(m, "tool_calls", []) or []:
                    lines.append(f"[{who}] → {c['name']}({short(json.dumps(c['args'], ensure_ascii=False), 90)})")
                if isinstance(m, ToolMessage):
                    lines.append(f"[{who}] ← {m.name}: {short(m.text, 90)}")
                if lines:
                    print(("\n" if mid_line else "") + "\n".join(lines), flush=True)
                    mid_line = False
    print()
    return final, usage, time.monotonic() - started
