"""Threads: one conversation each, owned by one user (records in services/threads.py, ownership check in
dependencies.py)."""
import logging
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.security import CurrentUser
from app.dependencies import Agent, OwnedThread, Running, Store
from app.schemas import Thread, ThreadDetail
from app.services import threads

router = APIRouter(tags=["threads"])
logger = logging.getLogger(__name__)


@router.post("/threads", status_code=201)
async def create_thread(user: CurrentUser, store: Store) -> Thread:
    thread = await threads.create_thread(store, user.user_id)
    logger.info("thread %s created for %s", thread.thread_id, user.user_id)
    return thread


@router.get("/threads")
async def list_threads(user: CurrentUser, store: Store, agent: Agent, running: Running,
                       limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[Thread]:
    """Newest first. `limit` is a query parameter: GET /threads?limit=5 (a non-integer gives 422)."""
    items = (await threads.list_threads(store, user.user_id))[:limit]
    for t in items:
        t.status, _ = await threads.thread_status(agent, running, t.thread_id)
    return items


@router.get("/threads/{thread_id}")
async def get_thread(thread: OwnedThread, agent: Agent, running: Running) -> ThreadDetail:
    status, interrupt = await threads.thread_status(agent, running, thread.thread_id)
    return ThreadDetail(**thread.model_dump(exclude={"status"}), status=status, interrupt=interrupt,
                        messages=await threads.thread_messages(agent, thread.thread_id))
