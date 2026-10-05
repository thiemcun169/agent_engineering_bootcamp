"""Helpers shared by the Session 04 notebooks: the web tools, a streaming loop, and a /context-style view of what
the model receives on each call. The notebooks keep only the parts each one teaches (prompt, skills, memory, backends)."""
import json
import logging
import time
from pathlib import Path

from langchain.messages import AIMessageChunk, ToolMessage
from langchain.tools import tool
import tiktoken
from langchain_core.callbacks import BaseCallbackHandler
from deepagents.middleware.skills import SKILLS_SYSTEM_PROMPT
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


# ── System prompt ────────────────────────────────────────────────────────────
SESSION_DIR = Path(__file__).resolve().parent.parent
PROMPT_FILE = SESSION_DIR / "prompts" / "system_prompt.md"
SKILLS_DIR = SESSION_DIR / "skills"


def system_prompt(layout: dict | None = None) -> str:
    """The shared system prompt (prompts/system_prompt.md) plus a <files> section built from the same table as the
    backend routes: {path: (backend, what the agent keeps there or None)}. Paths are written once, in the layout."""
    prompt = PROMPT_FILE.read_text().strip()
    files = [f"- {path} {purpose}" for path, (_, purpose) in (layout or {}).items() if purpose]
    return prompt + ("\n\n<files>\n" + "\n".join(files) + "\n</files>" if files else "")


def routes(layout: dict) -> dict:
    """Backend routes of a CompositeBackend from the same layout table."""
    return {path: backend for path, (backend, _) in layout.items()}


# ── Tools ────────────────────────────────────────────────────────────────────
@tool(parse_docstring=True)
def internet_search(query: str, max_results: int = 3) -> list[dict]:
    """Search the web and return title, url and a short snippet for each result.

    Run a few focused queries rather than one broad one.

    Args:
        query: What to search for, in a few keywords.
        max_results: Number of results, 1 to 5.
    """
    started, status = time.monotonic(), "error"
    try:
        results = tavily().search(query, max_results=min(max_results, 5))["results"]
        status = "ok"
        return [{"title": r["title"], "url": r["url"], "content": r["content"][:400]} for r in results]
    finally:
        log_call("internet_search", repr(query), status, started)


@tool(parse_docstring=True)
def read_page(url: str) -> str:
    """Read the full text of a web page.

    Args:
        url: Address of the page.
    """
    started, status = time.monotonic(), "error"
    try:
        results = tavily().extract(url)["results"]
        status = "ok" if results else "error"
        return results[0]["raw_content"] if results else f"Could not read {url}"
    finally:
        log_call("read_page", repr(url), status, started)


# ── What the model receives ──────────────────────────────────────────────────
ENCODING = tiktoken.get_encoding("o200k_base")  # tokenizer of current OpenAI models
SKILLS_MARKER = SKILLS_SYSTEM_PROMPT.splitlines()[0]  # "## Skills System", first line of the skills index


def compact(obj) -> str:
    """JSON without spaces, the way tool schemas and arguments are sent."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def tok(text: str) -> int:
    """Tokens of a piece of text with the model's tokenizer."""
    return len(ENCODING.encode(text, disallowed_special=())) if text else 0


class ContextLog(BaseCallbackHandler):
    """Everything the model receives on each call, i.e. the final request after every middleware ran, shown like
    /context in Claude Code. The total of a call is the input token count the provider reports. System prompt and
    messages are counted with the tokenizer. The provider encodes tool schemas in its own compact format, so their size
    is measured once, on the first call (provider total minus system prompt and message), and split between tools in
    proportion to their JSON schema; on later calls the rest is shown as message overhead (roles, ids, separators)."""

    def __init__(self, window: int):
        self.window, self.calls, self.tool_share = window, [], None

    def on_chat_model_start(self, serialized, messages, *, run_id=None, metadata=None, **kwargs):
        if (metadata or {}).get("lc_source") == "summarization":
            return  # the summarization call is not an agent step
        msgs = messages[0]
        system = msgs[0].text if msgs and msgs[0].type == "system" else ""
        self.calls.append({"run_id": run_id, "system": system, "messages": msgs[1:] if system else msgs,
                           "reported": None, "tools": kwargs.get("invocation_params", {}).get("tools", [])})

    def on_llm_end(self, response, *, run_id=None, **kwargs):
        usage = getattr(getattr(response.generations[0][0], "message", None), "usage_metadata", None) or {}
        for call in self.calls:
            if call["run_id"] == run_id:
                call["reported"] = usage.get("input_tokens")

    @property
    def system(self) -> str:  # system prompt of the last call
        return self.calls[-1]["system"] if self.calls else ""

    @property
    def messages(self) -> list:  # messages of the last call
        return self.calls[-1]["messages"] if self.calls else []

    @staticmethod
    def system_parts(system: str) -> dict:
        """Split the system prompt into our prompt and the parts Deep Agents appends after it, in this order:
        the skills index (SkillsMiddleware) and the memory block (MemoryMiddleware, last)."""
        rest, memory = (system.split("<agent_memory>", 1) + [""])[:2]
        rest, skills = (rest.split(SKILLS_MARKER, 1) + [""])[:2]
        file_text, guidelines = (memory.split("</agent_memory>", 1) + [""])[:2]
        return {"your system_prompt": rest, "skills index": skills and SKILLS_MARKER + skills,
                "memory: AGENTS.md content": file_text, "memory: guidelines": guidelines}

    @staticmethod
    def message_groups(messages) -> dict:
        groups = {}

        def add(key, text, count=1):
            g = groups.setdefault(key, [0, 0])
            g[0] += count
            g[1] += tok(text)

        for m in messages:
            if m.type == "ai":
                if m.tool_calls:
                    add("ai: tool calls", compact([{"name": c["name"], "id": c["id"], "args": c["args"]} for c in m.tool_calls]),
                        len(m.tool_calls))
                if m.text:
                    add("ai: text", m.text)
            elif m.type == "tool":
                add(f"tool result: {m.name}", m.text)
            else:
                add(m.type, m.text)  # human, or the summary injected by summarization
        return groups

    def sizes(self, i: int = -1) -> dict:
        c = self.calls[i]
        system = {k: tok(v) for k, v in self.system_parts(c["system"]).items() if v.strip()}
        groups = self.message_groups(c["messages"])
        counted = sum(system.values()) + sum(v for _, v in groups.values())
        raw = {(t.get("name") or t.get("function", {}).get("name")): tok(compact(t)) for t in c["tools"]}
        if self.tool_share is None and c["reported"]:  # first call with a provider count: measure the tools once
            scale = max(c["reported"] - counted, 0) / max(sum(raw.values()), 1)
            self.tool_share = {k: round(v * scale) for k, v in raw.items()}
        tools = {k: (self.tool_share or raw).get(k, v) for k, v in raw.items()}
        total = c["reported"] or counted + sum(tools.values())
        return {"system": system, "tools": tools, "messages": groups, "total": total, "estimated": not c["reported"],
                "overhead": total - counted - sum(tools.values())}

    def notes(self, i: int) -> str:
        """What is special in the request of call i: parts appended to the system prompt, a summary of older
        messages, tool results replaced by a file path (offloaded)."""
        c = self.calls[i]
        items = list(dict.fromkeys(k.split(":")[0] for k in self.sizes(i)["system"] if k != "your system_prompt"))
        if any(m.additional_kwargs.get("lc_source") == "summarization" for m in c["messages"]):
            items.append("summary")
        offloaded = sum(m.type == "tool" and "/large_tool_results/" in m.text[:300] for m in c["messages"])
        if offloaded:
            items.append(f"{offloaded} offloaded")
        return ", ".join(items) or "-"

    def table(self):
        """One row per model call; tokens = the provider's input count."""
        print(f"{'call':>4} {'messages':>8} {'tokens':>8}  in this call")
        for n, c in enumerate(self.calls):
            s = self.sizes(n)
            print(f"{n + 1:>4} {len(c['messages']):>8} {s['total']:>8,}{'*' if s['estimated'] else ''}  {self.notes(n)}")

    def show(self, i: int = -1):
        """Breakdown of one call, like /context in Claude Code: a bar, then every part of the request."""
        s, c, n = self.sizes(i), self.calls[i], (i if i >= 0 else len(self.calls) + i) + 1
        cats = [("system prompt", sum(s["system"].values()), "█"), ("tool schemas", sum(s["tools"].values()), "▓"),
                ("messages", sum(v for _, v in s["messages"].values()) + max(s["overhead"], 0), "▒")]  # tokenizer rounding can make overhead slightly negative
        source = "estimated, no usage reported" if s["estimated"] else "provider count"
        print(f"Call {n}/{len(self.calls)}: {s['total']:,} of {self.window:,} tokens ({s['total'] / self.window:.2%}, {source})")
        bar = "".join(ch * round(40 * v / max(s["total"], 1)) for _, v, ch in cats)
        print(f"  [{bar:<40}]  " + "  ".join(f"{ch} {name}" for name, _, ch in cats))
        print(f"  {'System prompt':<34}{cats[0][1]:>7,}")
        for k, v in s["system"].items():
            print(f"    {k:<32}{v:>7,}")
        print(f"  {'Tool schemas (' + str(len(s['tools'])) + ')':<34}{cats[1][1]:>7,}")
        print("    " + " · ".join(f"{k} {v}" for k, v in s["tools"].items()))
        print(f"  {'Messages (' + str(len(c['messages'])) + ')':<34}{cats[2][1]:>7,}")
        for k, (count, v) in s["messages"].items():
            print(f"    {k + ' x' + str(count):<32}{v:>7,}")
        if s["overhead"] > 0:  # roles, ids, separators the provider adds around messages
            print(f"    {'message overhead':<32}{s['overhead']:>7,}")
        print(f"  {'Free':<34}{self.window - s['total']:>9,}")


# ── Streaming ────────────────────────────────────────────────────────────────
def short(text: str, n: int = 110) -> str:
    return text if len(text) <= n else text[:n] + "…"


def stream(agent, question: str, thread_id: str, *, window: int, context=None):
    """Stream one turn with stream_mode=["updates", "messages"]: a line per tool call (→) and tool result (←),
    the answer token by token. Sync on purpose: the SqliteStore of Part 2 has no async methods.
    Returns ({"messages": what the turn added}, ContextLog of its model calls)."""
    log, added, mid_line = ContextLog(window), [], False
    config = {"configurable": {"thread_id": thread_id}, "callbacks": [log]}
    for mode, data in agent.stream({"messages": [{"role": "user", "content": question}]}, config, context=context,
                                   stream_mode=["updates", "messages"]):
        if mode == "messages":  # (token, metadata): the model's text as it is generated
            token, meta = data
            if (isinstance(token, AIMessageChunk) and meta.get("langgraph_node") == "model"
                    and meta.get("lc_source") != "summarization" and token.text):
                print(token.text, end="", flush=True)
                mid_line = True
            continue
        for update in data.values():  # updates: {node: what the node added to the state}
            for m in update.get("messages", []) if isinstance(update, dict) else []:
                added.append(m)
                lines = [f"→ {c['name']}({short(json.dumps(c['args'], ensure_ascii=False))})"
                         for c in getattr(m, "tool_calls", [])]
                if isinstance(m, ToolMessage):
                    lines.append(f"← {m.name} {m.status}: {short(m.text)}")
                if lines:
                    print(("\n" if mid_line else "") + "\n".join(lines), flush=True)
                    mid_line = False
    print()
    return {"messages": added}, log


def ask(agent, question: str, thread_id: str, *, window: int, context=None):
    """Stream one turn, then print one row per model call."""
    result, log = stream(agent, question, thread_id, window=window, context=context)
    log.table()
    return result, log


def context_window(model, default: int = 128_000) -> int:
    """Max input tokens from the model's LangChain profile (default when the model has no profile)."""
    window = (getattr(model, "profile", None) or {}).get("max_input_tokens")
    if not window:
        logger.warning("No context window in the profile of %s; using %s", model, default)
    return window or default


def tool_calls(result) -> list[str]:
    """Names of the tools the agent called in this turn, in order."""
    return [tc["name"] for m in result["messages"] if m.type == "ai" for tc in m.tool_calls]
