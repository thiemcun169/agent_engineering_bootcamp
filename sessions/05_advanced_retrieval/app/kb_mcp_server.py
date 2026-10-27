"""Optional extension: serve the knowledge-base search over MCP, so any MCP host (Claude, Cursor, another agent) can use it.

    uv run app/kb_mcp_server.py                              # stdio: the host starts the server
    uv run app/kb_mcp_server.py --http                       # Streamable HTTP on http://localhost:8005/mcp
    uv run app/kb_mcp_server.py --http --groups public,finance
    uv run app/kb_mcp_server.py --http --public              # plus a public https URL from ngrok, API key required

The access groups are fixed when the server starts (one server per audience), never a tool argument the model fills.
With --public, every request needs `Authorization: Bearer <KB_READ_KEY>` (as Session 03's shop_server_auth.py):
the URL is reachable by anyone and each search costs an OpenAI embedding call. No key or a wrong key -> HTTP 401.
Needs the Qdrant server (`docker compose up -d`) and the collection built by `uv run app/ingest.py`.
"""
import argparse
import logging
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("FASTMCP_LOG_ENABLED", "false")  # plain log lines through basicConfig, no rich file links
sys.path.insert(0, str(Path(__file__).resolve().parent))  # app/, for kb

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # before `import kb`, which reads QDRANT_URL
import kb  # noqa: E402
logger = logging.getLogger("kb_mcp")
mcp = FastMCP("gia-dien-kb", instructions="Search Vietnamese electricity price decisions; passages come with citations.")
ACCESS_GROUPS = ["public"]  # replaced by --groups


@mcp.tool
def search_kb(query: str, effective_after: str | None = None) -> str:
    """Search the electricity price documents with hybrid search (meaning + keywords).

    Returns the best passages, each with a citation header [title | trang N | hiệu lực YYYY-MM-DD].

    Args:
        query: What to look for, in Vietnamese, e.g. "giá điện sinh hoạt bậc 1".
        effective_after: Optional date YYYY-MM-DD; only documents that took effect on or after that date.
    """
    started = time.monotonic()
    text = kb.search_text(query, ACCESS_GROUPS, effective_after)  # a bad date comes back as text
    logger.info("search_kb(%r, after=%s, groups=%s) %d ms", query[:70], effective_after, ",".join(ACCESS_GROUPS),
                (time.monotonic() - started) * 1000)
    return text


def public_url(port: int) -> str:
    """--public: open an ngrok tunnel to the local server with the ngrok Python SDK (no ngrok binary needed).
    Same helper as Session 03 (app/shop_mcp.py). The tunnel lives as long as this process."""
    import ngrok
    if not os.getenv("NGROK_AUTHTOKEN"):
        sys.exit("--public needs NGROK_AUTHTOKEN in .env: https://dashboard.ngrok.com/get-started/your-authtoken")
    logging.getLogger("ngrok").setLevel(logging.WARNING)  # one line below, not the SDK's session messages
    try:
        url = ngrok.forward(f"127.0.0.1:{port}", authtoken_from_env=True).url() + "/mcp"
    except Exception as e:  # wrong token, no network, free plan already has a tunnel open elsewhere ...
        sys.exit(f"ngrok did not start: {e}")
    logger.info("Public URL: %s", url)
    return url


def api_key_auth() -> StaticTokenVerifier:
    """--public: one static API key from .env, sent as `Authorization: Bearer <key>` (Session 03 pattern)."""
    key = os.getenv("KB_READ_KEY")
    if not key:
        sys.exit("--public needs KB_READ_KEY in .env (make one with: "
                 "uv run python -c \"import secrets; print(secrets.token_urlsafe(24))\").")
    return StaticTokenVerifier(tokens={key: {"client_id": "kb-reader", "scopes": ["kb:read"]}},
                               required_scopes=["kb:read"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="serve Streamable HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=8005)
    parser.add_argument("--groups", default="public", help="comma-separated access groups, e.g. public,finance")
    parser.add_argument("--public", action="store_true", help="with --http: also open a public https URL (ngrok)")
    args = parser.parse_args()
    if args.public and not args.http:
        parser.error("--public needs --http (stdio has no URL)")
    ACCESS_GROUPS[:] = args.groups.split(",")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")  # stderr: stdout is the protocol
    for noisy in ("httpx", "httpx2", "fastmcp", "mcp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    kb.check_server()
    if args.http:
        if args.public:
            mcp.auth = api_key_auth()  # before run(): the HTTP app is built with it, localhost included
        logger.info("MCP server gia-dien-kb: http://localhost:%d/mcp (groups: %s%s)", args.port, args.groups,
                    ", API key required" if args.public else "")
        if args.public:
            public_url(args.port)
        # 127.0.0.1: only this machine can connect; ngrok (--public) forwards from localhost too
        mcp.run(transport="http", host="127.0.0.1", port=args.port, show_banner=False,
                uvicorn_config={"log_level": "warning"})
    else:
        mcp.run(show_banner=False)
