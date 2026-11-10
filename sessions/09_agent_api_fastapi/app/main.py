"""The FastAPI application: startup (lifespan), routers, error handlers and the demo UI.

Run:  uv run fastapi dev      (development: auto-reload)
      uv run fastapi run      (serving: no reload; entrypoint app.main:app is set in pyproject.toml)"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.sqlite.aio import AsyncSqliteStore

from app.agent.graph import build_agent
from app.core.config import get_settings
from app.core.errors import add_error_handlers
from app.routers import auth, health, runs, threads

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
for noisy in ("httpx", "httpx2"):  # HTTP clients log every request at INFO
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger("app")
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Created once before the first request, closed after the last one."""
    settings = get_settings()  # fails fast if a required key is missing
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key.get_secret_value())  # read by init_chat_model
    settings.data_dir.mkdir(exist_ok=True)
    # one database file, two connections: the checkpointer (conversation state per thread) and the store
    # (thread and user records); SQLite's WAL mode lets both write to the same file
    async with (AsyncSqliteSaver.from_conn_string(str(settings.db_path)) as checkpointer,
                AsyncSqliteStore.from_conn_string(str(settings.db_path)) as store):
        await checkpointer.setup()  # tables, and WAL mode for the file
        await store.setup()
        app.state.agent = build_agent(init_chat_model(settings.model), checkpointer)
        app.state.store = store
        app.state.running = {}  # thread_id -> run_id; in memory, so serve with ONE worker process
        logger.info("model %s · agent ready", settings.model)
        yield
    logger.info("shutdown: checkpointer and store closed")


app = FastAPI(title="Research Brief Agent API", version="1.0.0", lifespan=lifespan,
              description="Runs the Research Brief Agent per user and streams each run as Server-Sent Events.")
add_error_handlers(app)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(threads.router)
app.include_router(runs.router)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
async def ui() -> FileResponse:
    return FileResponse(STATIC / "index.html")
