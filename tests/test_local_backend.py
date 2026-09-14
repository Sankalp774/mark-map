from markmap import config


def test_forced_ollama_falls_back_when_daemon_down(monkeypatch):
    monkeypatch.setenv("MARKMAP_DESK_MODEL", "ollama")
    monkeypatch.setattr(config, "ollama_available", lambda: False)
    assert config.model_backend() == "desk"
    assert config.desk_model_id("desk") == "desk"


def test_forced_ollama_when_up(monkeypatch):
    monkeypatch.setenv("MARKMAP_DESK_MODEL", "ollama")
    monkeypatch.setenv("MARKMAP_OLLAMA_MODEL", "llama3.2")
    monkeypatch.setattr(config, "OLLAMA_MODEL_ID", "llama3.2")
    monkeypatch.setattr(config, "ollama_available", lambda: True)
    assert config.requested_backend() == "ollama"
    assert config.model_backend() == "ollama"
    assert config.desk_model_id("ollama") == "llama3.2"


def test_mlx_alias_without_server_falls_back(monkeypatch):
    monkeypatch.setenv("MARKMAP_DESK_MODEL", "mlx")
    monkeypatch.setattr(config, "mlx_available", lambda: False)
    monkeypatch.setattr(config, "ollama_available", lambda: False)
    assert config.model_backend() == "desk"
