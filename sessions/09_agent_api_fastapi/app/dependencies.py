"""Dependencies shared by the routers: the objects created at startup, and the thread checks that must pass before a
route runs (and before a stream sends its first byte)."""
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from langgraph.store.base import BaseStore

from app.core.security import CurrentUser
from app.schemas import Thread
from app.services import threads


def get_agent(request: Request):
    return request.app.state.agent


def get_store(request: Request) -> BaseStore:
    return request.app.state.store


def get_running(request: Request) -> dict[str, str]:
    return request.app.state.running


Agent = Annotated[object, Depends(get_agent)]
Store = Annotated[BaseStore, Depends(get_store)]
Running = Annotated[dict, Depends(get_running)]


async def owned_thread(thread_id: str, user: CurrentUser, store: Store) -> Thread:
    thread = await threads.get_thread(store, user.user_id, thread_id)
    if thread is None:  # same answer for "does not exist" and "belongs to someone else": ids are not revealed
        raise HTTPException(404, f"Thread {thread_id} not found")
    return thread


OwnedThread = Annotated[Thread, Depends(owned_thread)]


async def idle_thread(thread: OwnedThread, agent: Agent, running: Running) -> Thread:
    status, _ = await threads.thread_status(agent, running, thread.thread_id)
    if status == "busy":
        raise HTTPException(409, "A run is already streaming on this thread")
    if status == "interrupted":
        raise HTTPException(409, "The thread is waiting for a decision: POST /threads/{id}/resume")
    return thread


async def interrupted_thread(thread: OwnedThread, agent: Agent, running: Running) -> Thread:
    status, _ = await threads.thread_status(agent, running, thread.thread_id)
    if status != "interrupted":
        raise HTTPException(409, f"Nothing to resume: the thread is {status}")
    return thread


IdleThread = Annotated[Thread, Depends(idle_thread)]
InterruptedThread = Annotated[Thread, Depends(interrupted_thread)]
