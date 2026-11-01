import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
import app  # noqa: E402,F401  (loads .env, puts the lab on sys.path)

from app import guards  # noqa: E402
from app.guards import SecContext  # noqa: E402


@pytest.fixture(autouse=True)
def out_dir(tmp_path, monkeypatch):
    """audit.jsonl and outbox.jsonl of every test go to a temp folder, never to output/."""
    monkeypatch.setattr(guards, "OUTPUT", tmp_path)
    return tmp_path


@pytest.fixture
def runtime():
    """A fake ToolRuntime: tools only read ``runtime.context`` (like the fake runtime of Session 04)."""
    return lambda user_id: SimpleNamespace(context=SecContext(user_id=user_id))


def read_jsonl(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
