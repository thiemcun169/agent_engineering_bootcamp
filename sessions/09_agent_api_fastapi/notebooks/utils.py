"""Helpers for the Session 09 notebooks: call the running API with a user's token. The notebooks explain the service; the service itself lives in app/ and runs with `uv run fastapi run`."""
import json
import os
import sys
from pathlib import Path

import httpx

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))  # so `import app...` works from the notebooks folder
BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
# Two demo accounts the notebooks create through the API (POST /auth/signup), like users of the app would.
DEMO_USERS = {"alice": ("Alice", "alice-pass-2026"), "bob": ("Bob", "bob-pass-2026"), "carol": ("Carol", "carol-pass-2026")}
_tokens: dict[str, str] = {}


# ── Calling the API ───────────────────────────────────────────────────────────
def sign_up_and_login(username: str) -> str:
    """Create the demo account if needed (409 = it exists already), then log in: the OAuth2 password form returns a
    JWT access token. Cached per notebook run."""
    if username not in _tokens:
        name, password = DEMO_USERS[username]
        httpx.post(f"{BASE_URL}/auth/signup", json={"username": username, "password": password, "name": name})
        r = httpx.post(f"{BASE_URL}/auth/token", data={"username": username, "password": password})
        r.raise_for_status()
        _tokens[username] = r.json()["access_token"]
    return _tokens[username]


def client(user: str | None) -> httpx.Client:
    """An HTTP client that sends `Authorization: Bearer <JWT>` for a demo user (None = no token)."""
    headers = {"Authorization": f"Bearer {sign_up_and_login(user)}"} if user else {}
    return httpx.Client(base_url=BASE_URL, headers=headers, timeout=httpx.Timeout(10, read=200))


def short_token(token: str) -> str:
    """Never print a whole token: it is a password for the next 30 minutes."""
    return token[:20] + "…"


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
