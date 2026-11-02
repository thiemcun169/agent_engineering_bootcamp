"""Run the agent and turn its LangGraph stream into the API's Server-Sent Events.

stream_mode "updates" -> step, tool_call, tool_result, interrupt · "messages" -> token · "custom" -> progress.
Every stream starts with `metadata` and ends with `done` or `error`."""
import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator

from fastapi.sse import ServerSentEvent
from langchain.messages import AIMessage, AIMessageChunk, ToolMessage

from app.agent.tools import Context
from app.core.errors import problem

logger = logging.getLogger(__name__)


def short(value, n: int = 200) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= n else text[:n] + "…"


def to_events(mode: str, chunk) -> list[tuple[str, dict]]:
    """One LangGraph stream chunk -> zero or more (event name, data) pairs."""
    if mode == "messages":  # (message chunk, metadata): only text tokens of the agent's own model node
        token, meta = chunk
        ok = isinstance(token, AIMessageChunk) and token.text and meta.get("langgraph_node") == "model"
        return [("token", {"text": token.text})] if ok else []
    if mode == "custom":  # whatever a tool wrote with get_stream_writer()
        return [("progress", chunk)]
    events = []  # updates: {node name: what the node returned}
    for node, update in chunk.items():
        if node == "__interrupt__":
            events.append(("interrupt", {"id": update[0].id, **update[0].value}))
            continue
        if not isinstance(update, dict):
            continue
        if node in ("model", "tools"):
            events.append(("step", {"node": node}))
        for m in update.get("messages", []):  # model, tools, or a middleware hook such as a call limit
            for c in getattr(m, "tool_calls", []) or []:
                events.append(("tool_call", {"id": c["id"], "name": c["name"], "args": c["args"]}))
            if isinstance(m, ToolMessage):
                events.append(("tool_result", {"id": m.tool_call_id, "name": m.name, "status": m.status,
                                               "preview": short(m.text)}))
    return events


async def run_events(agent, running: dict[str, str], user_id: str, thread_id: str, payload,
                     timeout_s: int = 180) -> AsyncIterator[ServerSentEvent]:
    """Stream one run. `running` maps thread_id -> run_id so a thread never has two runs at once."""
    run_id, seq, started = uuid.uuid4().hex[:8], 0, time.monotonic()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}

    def event(name: str, data: dict) -> ServerSentEvent:
        nonlocal seq
        seq += 1
        return ServerSentEvent(event=name, data=data, id=f"{run_id}-{seq}")

    if thread_id in running:  # a second request passed the 409 check at the same moment
        yield event("error", problem(409, "A run is already streaming on this thread", f"/threads/{thread_id}"))
        return
    running[thread_id] = run_id  # claimed with no await since the check above
    logger.info("run %s started: user=%s thread=%s", run_id, user_id, thread_id)
    stream = agent.astream(payload, config, context=Context(user_id=user_id),
                           stream_mode=["updates", "messages", "custom"])
    try:
        yield event("metadata", {"run_id": run_id, "thread_id": thread_id})
        while True:
            try:  # the deadline covers the whole run, not each chunk
                mode, chunk = await asyncio.wait_for(anext(stream), timeout_s - (time.monotonic() - started))
            except StopAsyncIteration:
                break
            for name, data in to_events(mode, chunk):
                yield event(name, data)
        state = await agent.aget_state(config)
        last = state.values["messages"][-1]
        done = {"status": "interrupted" if state.interrupts else "completed",
                "answer": last.text if isinstance(last, AIMessage) and not state.interrupts else None,
                "seconds": round(time.monotonic() - started, 1)}
        logger.info("run %s %s in %.0f s", run_id, done["status"], done["seconds"])
        yield event("done", done)
    except asyncio.CancelledError:  # the client closed the connection: stop the agent, no new model/tool calls
        logger.warning("run %s cancelled: client disconnected", run_id)
        raise
    except TimeoutError:
        logger.warning("run %s timed out after %d s", run_id, timeout_s)
        yield event("error", problem(504, f"The run took longer than {timeout_s} s.", f"/threads/{thread_id}"))
    except Exception as exc:  # status 200 was sent with the first byte: report the failure as an event
        logger.error("run %s failed: %r", run_id, exc)
        yield event("error", problem(500, f"The run stopped ({type(exc).__name__}); see the server log, run {run_id}.",
                                     f"/threads/{thread_id}"))
    finally:
        await stream.aclose()
        if running.get(thread_id) == run_id:
            del running[thread_id]
