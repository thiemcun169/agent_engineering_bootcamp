"""SQL tools over data/shop.db: the logic notebook 01 writes step by step, shared by both MCP servers.

Read tools: list_tables, describe_table, run_query (read-only). Write tool (server with API keys): update_order_status.
Errors are raised as ShopError with a message written for the model: what is wrong and how to fix the call.
Every tool call logs one line (logger "shop"): `run_query('SELECT ...') -> ok 3 ms`.
"""
import logging
import os
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Literal

logger = logging.getLogger("shop")

DB_PATH = Path(os.getenv("SHOP_DB") or Path(__file__).resolve().parents[1] / "data" / "shop.db")  # SHOP_DB: use a copy
MAX_ROWS = 50          # a query never returns more rows than this
BUDGET_SECONDS = 2.0   # a query is stopped after this time
Status = Literal["pending", "paid", "shipped", "delivered", "cancelled"]


class ShopError(Exception):
    """An error the model can act on."""


def log_call(tool: str, args: str, status: str, started: float) -> None:
    """The one log line of a tool call: tool(short args) -> ok|error <ms> ms."""
    args = " ".join(args.split())
    logger.info("%s(%s) -> %s %d ms", tool, args if len(args) <= 70 else args[:70] + "…", status,
                (time.monotonic() - started) * 1000)


def connect_readonly(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the file read-only (a wrong path fails instead of creating an empty file), and make the session refuse
    writes too. Close it with contextlib.closing: `with con:` only ends a transaction."""
    con = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    con.row_factory = sqlite3.Row
    return con


def _tables(con: sqlite3.Connection) -> list[str]:
    return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]


def list_tables(db_path: Path = DB_PATH) -> list[str]:
    started, status = time.monotonic(), "error"
    try:
        with closing(connect_readonly(db_path)) as con:
            tables = _tables(con)
        status = "ok"
        return tables
    finally:
        log_call("list_tables", "", status, started)


def describe_table(table: str, db_path: Path = DB_PATH) -> dict:
    started, status = time.monotonic(), "error"
    try:
        with closing(connect_readonly(db_path)) as con:
            if table not in _tables(con):
                raise ShopError(f"Unknown table '{table}'. Tables: {', '.join(_tables(con))}.")
            columns = [{"name": r["name"], "type": r["type"]} for r in con.execute(f"PRAGMA table_info({table})")]
            sample = [dict(r) for r in con.execute(f"SELECT * FROM {table} LIMIT 3")]
        status = "ok"
        return {"table": table, "columns": columns, "sample_rows": sample}
    finally:
        log_call("describe_table", repr(table), status, started)


def _read_only(action, arg1, arg2, db, source):
    """sqlite3 authorizer: allow reading, refuse everything else (INSERT, UPDATE, DELETE, ATTACH, PRAGMA ...)."""
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _select(query: str, db_path: Path) -> dict:
    """Four layers keep it read-only and small: SELECT-only check, read-only connection, authorizer,
    and a row cap plus a time budget."""
    if not re.match(r"(?is)^(select|with)\b", query):
        raise ShopError("Only SELECT queries are allowed (read-only). Rewrite it as SELECT ... FROM ...")
    with closing(connect_readonly(db_path)) as con:
        columns = {t: [r["name"] for r in con.execute(f"PRAGMA table_info({t})")] for t in _tables(con)}
        con.set_authorizer(_read_only)  # set after reading the schema: PRAGMA is refused from here on
        deadline = time.monotonic() + BUDGET_SECONDS
        con.set_progress_handler(lambda: time.monotonic() > deadline, 10_000)  # returning True stops the query
        try:
            # newline before ")": a trailing "-- comment" in the query must not swallow the LIMIT
            rows = [dict(r) for r in con.execute(f"SELECT * FROM ({query}\n) LIMIT {MAX_ROWS + 1}")]
        except sqlite3.Error as e:
            msg = str(e)
            if "no such column" in msg or "no such table" in msg:
                schema = "; ".join(f"{t}({', '.join(c)})" for t, c in columns.items())
                raise ShopError(f"{msg}. Valid columns: {schema}. Call describe_table to see sample rows.") from e
            if "interrupted" in msg:
                raise ShopError(f"The query took longer than {BUDGET_SECONDS:.0f} s. Add a WHERE clause or aggregate.") from e
            if "not authorized" in msg:
                raise ShopError("Only reading is allowed (read-only). Rewrite it as a single SELECT.") from e
            raise ShopError(f"SQL error: {msg}. Check the query against describe_table.") from e
    result = {"rows": rows[:MAX_ROWS], "row_count": min(len(rows), MAX_ROWS)}
    if len(rows) > MAX_ROWS:
        result["note"] = f"Only the first {MAX_ROWS} rows are shown. Aggregate (GROUP BY) or add a WHERE clause."
    return result


def run_query(sql: str, db_path: Path = DB_PATH) -> dict:
    """Run one SELECT and return at most MAX_ROWS rows."""
    started, status = time.monotonic(), "error"
    query = sql.strip().rstrip(";")
    try:
        result = _select(query, db_path)
        status = "ok"
        return result
    finally:
        log_call("run_query", repr(query), status, started)


def update_order_status(order_id: int, status: Status, db_path: Path = DB_PATH) -> dict:
    """The only write the shop allows: change the status of one order (needs the shop:write scope)."""
    started, outcome = time.monotonic(), "error"
    try:
        with closing(sqlite3.connect(db_path)) as con, con:  # closing: close the file; con: commit the transaction
            row = con.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
            if row is None:
                raise ShopError(f"Order {order_id} does not exist. Find the id with run_query first.")
            con.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        outcome = "ok"
        return {"order_id": order_id, "old_status": row[0], "new_status": status}
    finally:
        log_call("update_order_status", f"{order_id}, {status!r}", outcome, started)
