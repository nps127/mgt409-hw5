"""Append-only audit trail at output/audit_trail.json.

The file is a JSON array. Each agent-loop step adds one row. Existing rows are
never removed: every write reads the array, appends, and swaps the file in
atomically. If the file can't be parsed, it is set aside (never deleted) and a
new array is started.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from pydantic_core import to_jsonable_python

from config import AUDIT_PATH, AUDIT_PREVIEW_CHARS
from models import AuditStep

_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def preview(value: Any, limit: int = AUDIT_PREVIEW_CHARS) -> Any:
    """Keep structured values as-is when short, otherwise a trimmed JSON string."""
    plain = to_jsonable_python(value, fallback=str)
    text = plain if isinstance(plain, str) else json.dumps(plain, ensure_ascii=False)
    if len(text) <= limit:
        return plain
    return text[: limit - 1] + "…"


def append_step(step: AuditStep) -> None:
    row = step.model_dump(mode="json", exclude_none=True)
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        rows: list[Any] = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
            try:
                loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
                rows = loaded if isinstance(loaded, list) else [loaded]
            except json.JSONDecodeError:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                AUDIT_PATH.replace(AUDIT_PATH.with_name(f"audit_trail.corrupt-{stamp}.json"))
        rows.append(row)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(AUDIT_PATH)
