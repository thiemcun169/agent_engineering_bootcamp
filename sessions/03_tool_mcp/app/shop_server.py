"""MCP server `shop`: the read-only SQL tools of notebook 01, served over MCP. No authentication.

    uv run app/shop_server.py                  # stdio: a host (Claude Desktop, Cursor, Claude Code) starts it
    uv run app/shop_server.py --http           # Streamable HTTP on http://localhost:$SHOP_PORT/mcp (default 8000)
    uv run app/shop_server.py --http --public  # plus a public https URL from ngrok (for Claude)

Anyone who knows the URL can read the shop data: demo data only. shop_server_auth.py adds API keys.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # app/, for shop_sql and shop_mcp

from dotenv import load_dotenv
from fastmcp import FastMCP

from shop_mcp import add_read_tools, public_url

load_dotenv()  # SHOP_PORT, NGROK_AUTHTOKEN from the .env of this session
mcp = add_read_tools(FastMCP("shop", instructions="Read-only SQL access to a small online store (customers, products, orders)."))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="serve Streamable HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=int(os.getenv("SHOP_PORT", "8000")))
    parser.add_argument("--public", action="store_true", help="with --http: also open a public https URL (ngrok)")
    args = parser.parse_args()
    if args.public and not args.http:
        parser.error("--public needs --http (stdio has no URL)")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")  # stderr: stdout is the protocol
    for noisy in ("fastmcp", "mcp"):  # one line per tool call is enough
        logging.getLogger(noisy).setLevel(logging.WARNING)
    if args.http:
        logging.getLogger("shop").info("MCP server shop: http://localhost:%d/mcp", args.port)
        if args.public:
            public_url(args.port)
        # 127.0.0.1: only this machine can connect; ngrok (--public) forwards from localhost too
        mcp.run(transport="http", host="127.0.0.1", port=args.port, show_banner=False,
                uvicorn_config={"log_level": "warning"})
    else:
        mcp.run(show_banner=False)
