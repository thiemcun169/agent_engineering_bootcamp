"""Helpers for the Session 09 notebooks: read the code of the app/ package, and call the running API with a user's
token. The notebooks explain the service; the service itself lives in app/ and runs with `uv run fastapi run`."""
import inspect
import json
import os
import sys
from pathlib import Path

import httpx
from IPython.display import Code

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))  # so `import app...` works from the notebooks folder
BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
TOKENS = {u["user_id"]: u["token"] for u in json.loads((PROJECT_DIR / "data" / "users.json").read_text())["users"]}


# ── Reading the code ──────────────────────────────────────────────────────────
def source(obj) -> Code:
    """The source of a function, class, module or LangChain tool, shown with syntax colours."""
    obj = getattr(obj, "func", None) or obj  # a @tool wraps the function in a StructuredTool
    return Code(inspect.getsource(obj), language="python")


def tree() -> None:
    """The app/ package: one line per file with the first line of its docstring."""
    import ast
    for path in sorted((PROJECT_DIR / "app").rglob("*")):
        if "__pycache__" in path.parts or path.name == "__init__.py" or path.is_dir():
            continue
        rel = path.relative_to(PROJECT_DIR)
        doc = ""
        if path.suffix == ".py":
            doc = (ast.get_docstring(ast.parse(path.read_text())) or "").split("\n")[0]
        print(f"{str(rel):<32} {doc[:80]}")


# ── Calling the API ───────────────────────────────────────────────────────────
def client(user: str | None) -> httpx.Client:
    """An HTTP client that sends `Authorization: Bearer <token>` for a demo user (None = no token)."""
    headers = {"Authorization": f"Bearer {TOKENS[user]}"} if user else {}
    return httpx.Client(base_url=BASE_URL, headers=headers, timeout=httpx.Timeout(10, read=200))


def check_server() -> None:
    """Fail fast with the start command when the API is not running."""
    try:
        httpx.get(f"{BASE_URL}/health", timeout=3).raise_for_status()
    except httpx.HTTPError:
        raise RuntimeError("The API is not running. In a terminal in the session folder: "
                           "uv run fastapi run --host 127.0.0.1") from None
    print("server: ok")


def sse_events(response: httpx.Response):
    """Parse a text/event-stream body: blocks separated by a blank line, one `field: value` per line."""
    event = {}
    for line in response.iter_lines():
        if line == "":  # a blank line ends the event
            if "data" in event:
                yield {"event": event.get("event", "message"), "id": event.get("id"), "data": json.loads(event["data"])}
            event = {}
        elif not line.startswith(":"):  # ": ping" lines are keep-alive comments
            field, _, value = line.partition(":")
            value = value.removeprefix(" ")
            event[field] = event[field] + "\n" + value if field in event else value


_mid_line = False  # True while tokens are being printed on one line


def show(name: str, d: dict) -> None:
    """One line per event; tokens are printed inline, as a chat UI shows them."""
    global _mid_line
    if name == "token":
        print(("[token] " if not _mid_line else "") + d["text"], end="", flush=True)
        _mid_line = True
        return
    text = {
        "metadata": lambda: f"run {d['run_id']} on thread {d['thread_id']}",
        "step": lambda: d["node"],
        "progress": lambda: f"{d['stage']}: {d['query']}",
        "tool_call": lambda: f"{d['name']}({short(json.dumps(d['args'], ensure_ascii=False), 90)})",
        "tool_result": lambda: f"{d['name']} -> {d['status']}: {short(d['preview'], 80)}",
        "interrupt": lambda: f"waiting for a decision on {d['action_requests'][0]['name']}"
                             f"(title={d['action_requests'][0]['args'].get('title')!r})",
        "done": lambda: f"{d['status']} in {d['seconds']} s",
        "error": lambda: f"{d['status']} {d['title']}: {d['detail']}",
    }.get(name, lambda: json.dumps(d))()
    print(("\n" if _mid_line else "") + f"[{name}] {text}")
    _mid_line = False


def stream_run(user: str, path: str, body: dict, *, quiet: bool = False) -> list[dict]:
    """POST to a streaming endpoint, print each event as it arrives, return all events."""
    events = []
    with client(user) as c, c.stream("POST", path, json=body) as r:
        if r.status_code != 200:  # errors before the stream starts are normal JSON problem responses
            r.read()
            print(r.status_code, r.json())
            return events
        for e in sse_events(r):
            events.append(e)
            if not quiet:
                show(e["event"], e["data"])
    return events


def short(text, n: int = 100) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + "…"
