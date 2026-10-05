"""The parts both MCP servers share: the 3 read tools of shop_sql, the /healthz route and the --public tunnel."""
import logging
import os
import sys

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from starlette.responses import JSONResponse

import shop_sql


def call(fn, *args):
    """Run a shop_sql function; an error the model can act on goes back as isError (ToolError), not a crash."""
    try:
        return fn(*args)
    except shop_sql.ShopError as e:
        raise ToolError(str(e)) from e


def add_read_tools(mcp: FastMCP) -> FastMCP:
    """Register list_tables, describe_table, run_query and GET /healthz on `mcp`."""

    @mcp.tool(annotations={"readOnlyHint": True})
    def list_tables() -> list[str]:
        """List the tables of the shop database. Call it first, then describe_table."""
        return call(shop_sql.list_tables)

    @mcp.tool(annotations={"readOnlyHint": True})
    def describe_table(table: str) -> dict:
        """Show the columns of one table and 3 sample rows. Call it before writing SQL on that table."""
        return call(shop_sql.describe_table, table)

    @mcp.tool(annotations={"readOnlyHint": True})
    def run_query(sql: str) -> dict:
        """Run one read-only SQLite SELECT on the shop database and return at most 50 rows.
        Prices are in VND; orders.created_at is an ISO timestamp. Aggregate with GROUP BY instead of reading many rows."""
        return call(shop_sql.run_query, sql)

    @mcp.custom_route("/healthz", methods=["GET"])  # no key needed: for `curl` and the notebooks
    async def healthz(request):
        return JSONResponse({"status": "ok", "server": mcp.name})

    return mcp


def public_url(port: int) -> str:
    """--public: open an ngrok tunnel to the local server with the ngrok Python SDK (no ngrok binary needed).
    The tunnel lives as long as this process; Claude (claude.ai / Desktop) connects to the https URL."""
    import ngrok
    if not os.getenv("NGROK_AUTHTOKEN"):
        sys.exit("--public needs NGROK_AUTHTOKEN in .env: https://dashboard.ngrok.com/get-started/your-authtoken")
    logging.getLogger("ngrok").setLevel(logging.WARNING)  # one line below, not the SDK's session messages
    try:
        url = ngrok.forward(f"127.0.0.1:{port}", authtoken_from_env=True).url() + "/mcp"
    except Exception as e:  # wrong token, no network, free plan already has a tunnel open elsewhere ...
        sys.exit(f"ngrok did not start: {e}")
    logging.getLogger("shop").info("Public URL: %s", url)
    return url
