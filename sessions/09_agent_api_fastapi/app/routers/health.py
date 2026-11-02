"""Liveness (/health: the process answers) and readiness (/ready: it can serve a run now). No token: a load balancer
or an orchestrator calls them. Neither calls the LLM."""
import logging

from fastapi import APIRouter, HTTPException

from app.dependencies import Store

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(store: Store) -> dict:
    try:
        await store.conn.execute("SELECT 1")  # the database answers
    except Exception as exc:
        logger.error("readiness check failed: %r", exc)
        raise HTTPException(503, "storage not ready")  # details stay in the log
    return {"status": "ready", "checks": {"store": "ok"}}
