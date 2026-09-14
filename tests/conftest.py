from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from markmap import config, seed, store


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    path = tmp_path / "markmap.json"
    monkeypatch.setattr(config, "STORE_PATH", path)
    monkeypatch.setenv("MARKMAP_DISABLE_BEDROCK", "1")
    monkeypatch.setenv("MARKMAP_DESK_MODEL", "desk")
    monkeypatch.setattr(config, "bedrock_disabled", lambda: True)
    monkeypatch.setattr(config, "model_backend", lambda: "desk")
    seed.reset_store()
    from markmap import workspace

    workspace.seed_defaults()
    return path


@pytest.fixture
def client(tmp_store):
    from markmap.main import app

    return TestClient(app)


def login(client: TestClient, email: str = "teacher@markmap.demo") -> None:
    res = client.post("/api/login", json={"email": email, "password": "demo"})
    assert res.status_code == 200, res.text
