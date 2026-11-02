"""Thread records in the LangGraph store, one namespace per user: a lookup can never see another user's threads."""
import uuid
from datetime import datetime, timezone

from langgraph.store.base import BaseStore

from app.schemas import Message, Thread


def namespace(user_id: str) -> tuple[str, ...]:
    return ("users", user_id, "threads")


async def create_thread(store: BaseStore, user_id: str) -> Thread:
    thread = Thread(thread_id=uuid.uuid4().hex[:12], title="New brief",
                    created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    await store.aput(namespace(user_id), thread.thread_id, thread.model_dump(include={"title", "created_at"}))
    return thread


async def get_thread(store: BaseStore, user_id: str, thread_id: str) -> Thread | None:
    item = await store.aget(namespace(user_id), thread_id)
    return Thread(thread_id=thread_id, **item.value) if item else None


async def list_threads(store: BaseStore, user_id: str) -> list[Thread]:
    items = await store.asearch(namespace(user_id), limit=50)
    return sorted((Thread(thread_id=i.key, **i.value) for i in items), key=lambda t: t.created_at, reverse=True)


async def set_title(store: BaseStore, user_id: str, thread: Thread, title: str) -> None:
    await store.aput(namespace(user_id), thread.thread_id, {"title": title, "created_at": thread.created_at})


async def thread_status(agent, running: dict, thread_id: str) -> tuple[str, dict | None]:
    """busy (a run is streaming), interrupted (waits for a decision, with its payload) or idle."""
    if thread_id in running:
        return "busy", None
    state = await agent.aget_state({"configurable": {"thread_id": thread_id}})
    if state.interrupts:
        return "interrupted", {"id": state.interrupts[0].id, **state.interrupts[0].value}
    return "idle", None


async def thread_messages(agent, thread_id: str) -> list[Message]:
    """The saved conversation, without internal state (tool results shortened)."""
    state = await agent.aget_state({"configurable": {"thread_id": thread_id}})
    out = []
    for m in state.values.get("messages", []):
        if m.type == "human":
            out.append(Message(role="user", content=m.text))
        elif m.type == "ai":
            out.append(Message(role="assistant", content=m.text,
                               tool_calls=[{"name": c["name"], "args": c["args"]} for c in m.tool_calls]))
        elif m.type == "tool":
            out.append(Message(role="tool", name=m.name, content=m.text[:300]))
    return out
