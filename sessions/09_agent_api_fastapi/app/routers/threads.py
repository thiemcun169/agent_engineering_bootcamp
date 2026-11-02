"""Threads: one conversation each, owned by one user."""
import logging

from fastapi import APIRouter

from app.core.security import CurrentUser
from app.dependencies import Agent, OwnedThread, Running, Store
from app.schemas import Thread, ThreadDetail, User
from app.services import threads

router = APIRouter(tags=["threads"])
logger = logging.getLogger(__name__)


@router.get("/me")
async def me(user: CurrentUser) -> User:
    return user


@router.post("/threads", status_code=201)
async def create_thread(user: CurrentUser, store: Store) -> Thread:
    thread = await threads.create_thread(store, user.user_id)
    logger.info("thread %s created for %s", thread.thread_id, user.user_id)
    return thread


@router.get("/threads")
async def list_threads(user: CurrentUser, store: Store, agent: Agent, running: Running) -> list[Thread]:
    items = await threads.list_threads(store, user.user_id)
    for t in items:
        t.status, _ = await threads.thread_status(agent, running, t.thread_id)
    return items


@router.get("/threads/{thread_id}")
async def get_thread(thread: OwnedThread, agent: Agent, running: Running) -> ThreadDetail:
    status, interrupt = await threads.thread_status(agent, running, thread.thread_id)
    return ThreadDetail(**thread.model_dump(exclude={"status"}), status=status, interrupt=interrupt,
                        messages=await threads.thread_messages(agent, thread.thread_id))
