from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config

_lock = threading.Lock()

EMPTY: dict[str, Any] = {
    "school": dict(config.SCHOOL),
    "users": [],
    "papers": {},
    "rows": {},
    "alerts": [],
    "audit": [],
    "ptm_at": None,
    "agent_log": [],
    "tasks": [],
    "broadcasts": [],
    "calendar": [],
    "queries": [],
    "interventions": [],
    "classes": {},
    "threads": [],
    "desk_cycles": [],
    "desk_snapshot": {},
    "last_desk_run": None,
}


def _path() -> Path:
    return Path(config.STORE_PATH)


def default_state() -> dict[str, Any]:
    return deepcopy(EMPTY)


def load() -> dict[str, Any]:
    path = _path()
    if not path.exists():
        return default_state()
    with _lock:
        data = json.loads(path.read_text(encoding="utf-8"))
    for key, value in EMPTY.items():
        data.setdefault(key, deepcopy(value))
    return data


def save(state: dict[str, Any]) -> dict[str, Any]:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, ensure_ascii=False)
    tmp = path.with_name(path.name + ".tmp")
    with _lock:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    return state


def update(mutator) -> dict[str, Any]:
    state = load()
    mutator(state)
    return save(state)


def audit(action: str, detail: dict[str, Any] | None = None) -> None:
    def _add(state: dict[str, Any]) -> None:
        state["audit"].append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "detail": detail or {},
            }
        )
        state["audit"] = state["audit"][-80:]

    update(_add)


def agent_log(kind: str, text: str, extra: dict[str, Any] | None = None) -> None:
    def _add(state: dict[str, Any]) -> None:
        state["agent_log"].append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "kind": kind,
                "text": text,
                "extra": extra or {},
            }
        )
        state["agent_log"] = state["agent_log"][-40:]

    update(_add)
