from __future__ import annotations

import hashlib
import hmac
from typing import Any

from . import config, store


def token_for(email: str) -> str:
    return hmac.new(config.SECRET.encode(), email.lower().encode(), hashlib.sha256).hexdigest()


def user_from_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    state = store.load()
    for user in state.get("users") or []:
        if token_for(user["email"]) == token:
            return _public(user)
    return None


def login(email: str, password: str) -> dict[str, Any]:
    email = email.strip().lower()
    state = store.load()
    users = state.get("users") or []
    if not users:
        from . import seed

        store.update(lambda s: s.__setitem__("users", seed.demo_users()))
        users = store.load()["users"]
    for user in users:
        if user["email"].lower() == email and user.get("password") == password:
            return {"token": token_for(user["email"]), "user": _public(user)}
    raise PermissionError("Unknown email or password.")


def _public(user: dict[str, Any]) -> dict[str, Any]:
    from . import config

    role = user["role"]
    class_ids = user.get("class_ids")
    if not class_ids:
        class_ids = [c["id"] for c in config.CLASSES] if role == "teacher" else [user.get("class_id") or config.DEFAULT_CLASS_ID]
    return {
        "email": user["email"],
        "name": user["name"],
        "role": role,
        "roll": user.get("roll"),
        "class_id": user.get("class_id") or config.DEFAULT_CLASS_ID,
        "class_ids": class_ids,
    }
