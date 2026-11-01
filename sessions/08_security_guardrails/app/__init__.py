"""Session 08 application code: the Research Brief Agent with deliberate flaws (baseline) and controls (defended).

Layout: ``guards.py`` (UserContext, authorize, scope guard, PII, egress, HITL, audit, verify_tools) ·
``agent_lib.py`` (fake tools, two prompts, ``build_model``) · ``cases.py`` (the 14 security cases as a literal list).
Everything here talks to FAKE data in ``data/``. Never point these techniques at real systems.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

LAB_DIR = Path(__file__).resolve().parents[1]

if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))

load_dotenv(LAB_DIR / ".env")  # OPENAI_API_KEY, MODEL
