"""Model, paths, and limits for the Campus Customs agent team."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
HW5_DIR = BACKEND_DIR.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"
MCP_SERVER_DIR = HW5_DIR / "mcp_server"

load_dotenv(HW5_DIR / ".env")
load_dotenv(HW5_DIR.parent / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

# Every agent uses this one model. HW5 requires gpt-6-luna, so that's the default;
# OPENAI_MODEL in .env can override it (the course's AGENTS.md asks for a configurable model).
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-6-luna").strip() or "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# CAMPUS_AUDIT_PATH lets tests write somewhere other than the real audit trail.
AUDIT_PATH = Path(os.getenv("CAMPUS_AUDIT_PATH", HW5_DIR / "output" / "audit_trail.json"))

# --- Limits that keep token use (and runaway loops) in check -----------------
MAX_DELEGATION_DEPTH = 3          # boss -> A -> B -> C, and no further
MAX_DELEGATIONS_PER_TICKET = 8    # every hand-off in one ticket run, any agent
TICKET_TOKEN_BUDGET = 200_000     # input + output tokens across every agent on one ticket
BOSS_REQUEST_LIMIT = 12           # model calls in the boss's own loop
SPECIALIST_REQUEST_LIMIT = 8      # model calls in each specialist's loop
TOOL_CALLS_PER_AGENT = 16         # tool calls (MCP + delegate) in one agent's loop
MAX_OUTPUT_TOKENS = 8_000         # per model response
AUDIT_PREVIEW_CHARS = 1_500       # long tool results are cut to this in the audit trail


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to hw5/.env (see .env.example).")
    return key


@lru_cache(maxsize=1)
def build_model() -> OpenAIResponsesModel:
    key = require_api_key()
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key},
        timeout=120.0,
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def load_prompt(agent_name: str) -> str:
    return (PROMPTS_DIR / f"{agent_name}.md").read_text(encoding="utf-8").strip()
