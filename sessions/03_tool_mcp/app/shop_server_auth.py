"""MCP server `shop` with API keys: shop_server.py plus authentication, a write tool and an audit log.

    uv run app/shop_server_auth.py            # http://localhost:$SHOP_AUTH_PORT/mcp (default 8001), keys from .env
    uv run app/shop_server_auth.py --public   # plus a public https URL from ngrok
    uv run app/shop_server_auth.py --reset    # start again from a fresh copy of data/shop.db

Writes (update_order_status) go to output/shop.db, a copy of data/shop.db made on the first start (or --reset).

Every request sends `Authorization: Bearer <key>`. The key decides the scopes:
    SHOP_READ_KEY  -> client "analyst",  scopes shop:read              (list_tables, describe_table, run_query)
    SHOP_WRITE_KEY -> client "operator", scopes shop:read shop:write   (+ update_order_status)
No key or an unknown key -> HTTP 401. A tool the key has no scope for is not listed and cannot be called.

Two loggers: `shop` prints diagnostics to the terminal; `shop.audit` is the security record (who called which tool,
with what, the outcome), one JSON line per tool call or refused request in output/audit.jsonl.
"""
import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "app"))  # for shop_sql and shop_mcp
# Before shop_sql is imported (it reads SHOP_DB once): this server works on a copy, never on data/shop.db
os.environ.setdefault("SHOP_DB", str(LAB / "output" / "shop.db"))

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import NotFoundError
from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from starlette.middleware import Middleware as ASGIMiddleware

import shop_sql
from shop_mcp import add_read_tools, call, public_url

load_dotenv()  # SHOP_READ_KEY, SHOP_WRITE_KEY from the .env of this session
logger = logging.getLogger("shop")

AUDIT_PATH = Path(os.getenv("SHOP_AUDIT") or LAB / "output" / "audit.jsonl")


def api_keys() -> dict:
    """Map each API key to the client name and scopes it grants (read from the environment, never from code)."""
    read_key, write_key = os.getenv("SHOP_READ_KEY"), os.getenv("SHOP_WRITE_KEY")
    if not read_key or not write_key:
        sys.exit("Set SHOP_READ_KEY and SHOP_WRITE_KEY in .env (e.g. uv run python -c \"import secrets; print(secrets.token_urlsafe(24))\").")
    if read_key == write_key:  # the dict below would keep only the write entry: the "read" key could write
        sys.exit("SHOP_READ_KEY and SHOP_WRITE_KEY must be different keys (.env).")
    return {read_key: {"client_id": "analyst", "scopes": ["shop:read"]},
            write_key: {"client_id": "operator", "scopes": ["shop:read", "shop:write"]}}


# ------------------------------------------------------------------ audit log: a second logger with its own file
audit = logging.getLogger("shop.audit")


class JsonLine(logging.Formatter):
    """One JSON object per line: the dict passed to audit.info(...), plus a UTC timestamp."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="seconds")
        return json.dumps({"ts": ts, **record.msg}, ensure_ascii=False)


def setup_audit(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(JsonLine())
    audit.addHandler(handler)
    audit.setLevel(logging.INFO)
    audit.propagate = False  # the audit file only, not the terminal


class AuditMiddleware(Middleware):
    """One line per tool call, written where the permission is checked (the server)."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        token, started = get_access_token(), time.monotonic()
        record = {"client_id": token.client_id if token else None, "tool": context.message.name,
                  "args": context.message.arguments}
        try:
            result = await call_next(context)
        except NotFoundError as e:
            # FastMCP hides a tool the key has no scope for: calling it raises NotFoundError("Unknown tool"),
            # the same as a tool that does not exist. Both are refused calls.
            logger.warning("denied: %s calls %s", record["client_id"], record["tool"])
            audit.info({**record, "status": "denied", "reason": str(e)[:120],
                        "ms": round((time.monotonic() - started) * 1000)})
            raise
        except Exception as e:
            audit.info({**record, "status": "error", "reason": str(e)[:120],
                        "ms": round((time.monotonic() - started) * 1000)})
            raise
        audit.info({**record, "status": "ok", "ms": round((time.monotonic() - started) * 1000)})
        return result


class AuditRejected:
    """ASGI layer: a request refused at the door (401 / 403) never reaches a tool, so log it here."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_and_log(message):
            if message["type"] == "http.response.start" and message["status"] in (401, 403):
                logger.warning("denied: HTTP %s on %s (no or unknown key)", message["status"], scope["path"])
                audit.info({"client_id": None, "status": "denied", "http": message["status"], "path": scope["path"]})
            await send(message)

        await self.app(scope, receive, send_and_log if scope["type"] == "http" else send)


# ------------------------------------------------------------------ server
mcp = FastMCP("shop", auth=StaticTokenVerifier(tokens=api_keys(), required_scopes=["shop:read"]),
              middleware=[AuditMiddleware()],
              instructions="SQL access to a small online store. Reading needs shop:read, changing an order needs shop:write.")
add_read_tools(mcp)  # list_tables, describe_table, run_query, /healthz: the same as shop_server.py


@mcp.tool(auth=require_scopes("shop:write"),
          annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
def update_order_status(order_id: int, status: shop_sql.Status) -> dict:
    """Change the status of one order, e.g. mark a paid order as shipped. Returns the old and new status."""
    return call(shop_sql.update_order_status, order_id, status)


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--port", type=int, default=int(os.getenv("SHOP_AUTH_PORT", "8001")))
    args.add_argument("--public", action="store_true", help="also open a public https URL (ngrok)")
    args.add_argument("--reset", action="store_true", help="start again from a fresh copy of data/shop.db")
    args = args.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")  # logger "shop": the terminal
    setup_audit(AUDIT_PATH)                                                          # logger "shop.audit": the file
    for noisy in ("fastmcp", "mcp"):  # one line per tool call is enough
        logging.getLogger(noisy).setLevel(logging.WARNING)
    if args.reset or not shop_sql.DB_PATH.exists():
        shop_sql.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(LAB / "data" / "shop.db", shop_sql.DB_PATH)
        logger.info("Fresh copy of data/shop.db in %s", shop_sql.DB_PATH)
    logger.info("MCP server shop (API keys): http://localhost:%d/mcp, audit log in %s", args.port, AUDIT_PATH)
    if args.public:
        public_url(args.port)
    # 127.0.0.1: only this machine can connect; ngrok (--public) forwards from localhost too
    mcp.run(transport="http", host="127.0.0.1", port=args.port, show_banner=False,
            uvicorn_config={"log_level": "warning"}, middleware=[ASGIMiddleware(AuditRejected)])
