"""Helpers shared by the Session 05 notebooks: the tool log line, a result table, the system prompt and a streaming
loop. The notebooks keep only what each part teaches (chunking, embeddings, search, Qdrant, the agent)."""
import json
import logging
import sys
import time
from pathlib import Path

from langchain.messages import AIMessageChunk, ToolMessage

SESSION_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SESSION_DIR / "app"))  # notebooks import the lab code as `import kb, ingest`
PROMPT_FILE = SESSION_DIR / "prompts" / "system_prompt.md"
logger = logging.getLogger(__name__)


def log_call(tool_name: str, args: str, status: str, started: float) -> None:
    """The one log line of a tool call: tool(short args) -> ok|error <ms> ms."""
    args = " ".join(args.split())
    logger.info("%s(%s) -> %s %d ms", tool_name, args if len(args) <= 80 else args[:80] + "…", status,
                (time.monotonic() - started) * 1000)


def system_prompt() -> str:
    """The shared system prompt of the agents (prompts/system_prompt.md)."""
    return PROMPT_FILE.read_text(encoding="utf-8").strip()


def short(text: str, n: int = 110) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n] + "…"


def table(rows: list[list], header: list[str]) -> None:
    """Print rows as an aligned text table."""
    rows = [[str(c) for c in r] for r in rows]
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(header)]
    print("  ".join(h.ljust(w) for h, w in zip(header, widths)))
    for r in rows:
        print("  ".join(c.ljust(w) for c, w in zip(r, widths)))


def stream(agent, question: str, *, context=None) -> str:
    """Stream one turn with stream_mode=["updates", "messages"]: a line per tool call (→) and tool result (←),
    the answer token by token. Returns the final answer text."""
    print(f"Q: {question}")
    answer, mid_line = "", False
    for mode, data in agent.stream({"messages": [{"role": "user", "content": question}]}, context=context,
                                   stream_mode=["updates", "messages"]):
        if mode == "messages":  # (token, metadata): the model's text as it is generated
            token, meta = data
            if isinstance(token, AIMessageChunk) and meta.get("langgraph_node") == "model" and token.text:
                print(token.text, end="", flush=True)
                mid_line = True
            continue
        for update in data.values():  # updates: {node: what the node added to the state}
            for m in update.get("messages", []) if isinstance(update, dict) else []:
                lines = [f"→ {c['name']}({short(json.dumps(c['args'], ensure_ascii=False))})"
                         for c in getattr(m, "tool_calls", [])]
                if isinstance(m, ToolMessage):
                    lines.append(f"← {m.name} {m.status}: {short(m.text)}")
                elif m.type == "ai" and m.text:
                    answer = m.text
                if lines:
                    print(("\n" if mid_line else "") + "\n".join(lines), flush=True)
                    mid_line = False
    print()
    return answer
