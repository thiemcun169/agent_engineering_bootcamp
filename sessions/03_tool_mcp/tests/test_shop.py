"""Checks of the Session 03 tools and servers. Run from this session folder: uv run pytest -q"""
import asyncio
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "app"))  # shop_sql

import shop_sql  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed = load(LAB / "data" / "seed_shop.py", "seed_shop")


@pytest.fixture(scope="session")
def db(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("shop") / "shop.db"
    seed.build(path)
    return path


# ------------------------------------------------------------------ data
def test_seed_is_deterministic(tmp_path, db):
    other = tmp_path / "again.db"
    counts = seed.build(other)
    assert counts == {"customers": 200, "products": 40, "orders": 1500, "order_items": 2565}
    dump = lambda p: hashlib.md5("\n".join(sqlite3.connect(p).iterdump()).encode()).hexdigest()
    assert dump(other) == dump(db)


# ------------------------------------------------------------------ read tools (notebook 01 logic)
def test_list_and_describe(db):
    assert shop_sql.list_tables(db) == ["customers", "order_items", "orders", "products"]
    d = shop_sql.describe_table("orders", db)
    assert [c["name"] for c in d["columns"]] == ["id", "customer_id", "status", "created_at"]
    assert len(d["sample_rows"]) == 3
    with pytest.raises(shop_sql.ShopError, match="Unknown table 'order'. Tables: customers"):
        shop_sql.describe_table("order", db)


@pytest.mark.parametrize("sql, message", [
    ("DELETE FROM orders", "Only SELECT queries are allowed"),
    ("UPDATE orders SET status = 'paid'", "Only SELECT queries are allowed"),
    ("ATTACH DATABASE 'x.db' AS x", "Only SELECT queries are allowed"),
    ("SELECT * FROM pragma_table_info('orders')", "Only reading is allowed"),  # passes layer 1, stopped by the authorizer
    ("SELECT 1; DELETE FROM orders", "SQL error"),                             # one statement only
])
def test_writes_are_blocked(db, sql, message):
    with pytest.raises(shop_sql.ShopError, match=message):
        shop_sql.run_query(sql, db)
    assert sqlite3.connect(db).execute("SELECT count(*) FROM orders").fetchone()[0] == 1500


def test_readonly_connection_refuses_writes(db):
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        shop_sql.connect_readonly(db).execute("DELETE FROM orders")


def test_bad_column_lists_valid_columns(db):
    with pytest.raises(shop_sql.ShopError) as e:
        shop_sql.run_query("SELECT total_amount FROM orders", db)
    assert "no such column: total_amount" in str(e.value)
    assert "orders(id, customer_id, status, created_at)" in str(e.value)
    assert "describe_table" in str(e.value)


def test_trailing_comment(db):  # the LIMIT wrapper must survive a "-- comment" at the end of the query
    assert shop_sql.run_query("SELECT count(*) AS n FROM orders -- all orders", db)["rows"] == [{"n": 1500}]


def test_wrong_path_is_not_created(tmp_path):
    with pytest.raises(sqlite3.OperationalError):
        shop_sql.list_tables(tmp_path / "missing.db")
    assert not (tmp_path / "missing.db").exists()


def test_one_log_line_per_call(db, caplog):
    with caplog.at_level("INFO", logger="shop"):
        shop_sql.run_query("SELECT 1 AS x", db)
        with pytest.raises(shop_sql.ShopError):
            shop_sql.describe_table("nope", db)
    assert [r.getMessage().rsplit(" ", 2)[0] for r in caplog.records] == [
        "run_query('SELECT 1 AS x') -> ok", "describe_table('nope') -> error"]


def test_row_cap(db):
    r = shop_sql.run_query("SELECT * FROM orders", db)
    assert r["row_count"] == shop_sql.MAX_ROWS == 50 and "note" in r
    assert "note" not in shop_sql.run_query("SELECT * FROM products LIMIT 5", db)


def test_update_order_status(db, tmp_path):
    copy = tmp_path / "shop.db"
    shutil.copy(db, copy)
    assert shop_sql.update_order_status(1500, "paid", copy) == {"order_id": 1500, "old_status": "pending", "new_status": "paid"}
    with pytest.raises(shop_sql.ShopError, match="does not exist"):
        shop_sql.update_order_status(99999, "paid", copy)


# ------------------------------------------------------------------ server without auth (in process)
def test_server_tools():
    server = load(LAB / "app" / "shop_server.py", "shop_server")

    async def run():
        async with Client(server.mcp) as c:
            assert [t.name for t in await c.list_tools()] == ["list_tables", "describe_table", "run_query"]
            bad = await c.call_tool("run_query", {"sql": "SELECT revenue FROM orders"}, raise_on_error=False)
            assert bad.is_error and "Valid columns" in bad.content[0].text

    asyncio.run(run())


# ------------------------------------------------------------------ server with API keys, over HTTP
@pytest.fixture(scope="module")
def auth_server(tmp_path_factory, db):
    tmp = tmp_path_factory.mktemp("auth_server")
    shutil.copy(db, tmp / "shop.db")
    with socket.socket() as s:
        s.bind(("", 0))
        port = s.getsockname()[1]
    env = {**os.environ, "SHOP_DB": str(tmp / "shop.db"), "SHOP_AUDIT": str(tmp / "audit.jsonl"),
           "SHOP_READ_KEY": "test-read", "SHOP_WRITE_KEY": "test-write"}
    log = tmp / "server.log"
    proc = subprocess.Popen([sys.executable, str(LAB / "app" / "shop_server_auth.py"), "--port", str(port)], env=env,
                            stdout=subprocess.DEVNULL, stderr=log.open("w"))
    url = f"http://localhost:{port}/mcp"
    for _ in range(100):
        if proc.poll() is not None:
            pytest.fail(f"shop_server_auth.py exited with code {proc.returncode}:\n{log.read_text()}")
        try:
            httpx.get(f"http://localhost:{port}/healthz", timeout=1)
            break
        except httpx.TransportError:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.fail(f"shop_server_auth.py did not answer on port {port} within 20 s:\n{log.read_text()}")
    yield url, tmp / "audit.jsonl"
    proc.terminate()
    proc.wait()


def test_same_key_twice_is_refused():
    env = {**os.environ, "SHOP_READ_KEY": "same", "SHOP_WRITE_KEY": "same"}
    r = subprocess.run([sys.executable, str(LAB / "app" / "shop_server_auth.py"), "--port", "1"], env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and "must be different" in r.stderr


def test_no_key_is_401(auth_server):
    url, audit = auth_server
    r = httpx.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                   headers={"Accept": "application/json, text/event-stream"})
    assert r.status_code == 401 and 'scope="shop:read"' in r.headers["www-authenticate"]
    assert any(json.loads(l).get("http") == 401 for l in audit.read_text().splitlines())


def test_read_key_cannot_write(auth_server):
    url, audit = auth_server

    async def run():
        async with Client(url, auth="test-read") as c:
            assert "update_order_status" not in [t.name for t in await c.list_tools()]
            with pytest.raises(ToolError, match="Unknown tool"):
                await c.call_tool("update_order_status", {"order_id": 1, "status": "paid"})

    asyncio.run(run())
    last = json.loads(audit.read_text().splitlines()[-1])
    assert last["client_id"] == "analyst" and last["status"] == "denied"


def test_write_key_can_write(auth_server):
    url, audit = auth_server

    async def run():
        async with Client(url, auth="test-write") as c:
            r = await c.call_tool("update_order_status", {"order_id": 1499, "status": "shipped"})
            assert r.data["new_status"] == "shipped"

    asyncio.run(run())
    last = json.loads(audit.read_text().splitlines()[-1])
    assert last["client_id"] == "operator" and last["tool"] == "update_order_status" and last["status"] == "ok"
