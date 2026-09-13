from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass
DATA_DIR = ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
STATIC_DIR = ROOT / "static"
STORE_PATH = Path(os.getenv("MARKMAP_STORE", DATA_DIR / "markmap.json"))
DEFAULT_SECRET = "markmap-demo-secret"
SECRET = os.getenv("MARKMAP_SECRET", DEFAULT_SECRET)
COOKIE_NAME = "markmap_session"
CLASS_COOKIE = "markmap_class"

AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-west-2"
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL_ID = os.getenv("MARKMAP_OLLAMA_MODEL", "llama3.2")
MLX_BASE_URL = os.getenv("MARKMAP_MLX_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
MLX_MODEL_ID = os.getenv("MARKMAP_MLX_MODEL", "llama-3.2-3b-instruct")

DEMO_PASSWORD = "demo"

SCHOOL = {
    "name": "Greenfield Public School",
    "class_name": "10-B",
    "subject": "Mathematics",
    "teacher": "Kavita Sharma",
}

CLASSES = (
    {
        "id": "10-B",
        "label": "10-B",
        "grade": "10",
        "section": "B",
        "subject": "Mathematics",
        "teacher": "Kavita Sharma",
    },
    {
        "id": "10-A",
        "label": "10-A",
        "grade": "10",
        "section": "A",
        "subject": "Mathematics",
        "teacher": "Kavita Sharma",
    },
    {
        "id": "9-C",
        "label": "9-C",
        "grade": "9",
        "section": "C",
        "subject": "Science",
        "teacher": "Kavita Sharma",
    },
)
DEFAULT_CLASS_ID = "10-B"

SECTIONS = (
    {"id": "term-1", "title": "Term 1", "paper_id": "term-1"},
    {"id": "midterm", "title": "Midterm", "paper_id": "midterm"},
)
PAPER_ALIASES = {
    "midterm-1": "term-1",
    "midterm-2": "midterm",
    "midterm2": "midterm",
    "term1": "term-1",
    "term_1": "term-1",
}


def resolve_paper_id(paper_id: str) -> str:
    return PAPER_ALIASES.get(paper_id, paper_id)

STRONG_AT = 0.75
OK_AT = 0.50


def bedrock_disabled() -> bool:
    return os.getenv("MARKMAP_DISABLE_BEDROCK", "0") == "1"


def aws_credentials_present() -> bool:
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        return True
    if os.getenv("AWS_PROFILE"):
        return True
    cred = Path.home() / ".aws" / "credentials"
    return cred.exists()


def ollama_available() -> bool:
    try:
        from urllib.request import urlopen

        with urlopen(OLLAMA_HOST.rstrip("/") + "/api/tags", timeout=0.4) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:
        return False


def omlx_endpoint_up() -> bool:
    if not MLX_BASE_URL:
        return False
    try:
        from urllib.request import Request, urlopen

        req = Request(MLX_BASE_URL + "/models", headers={"Authorization": "Bearer local"})
        with urlopen(req, timeout=0.4) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:
        return False


def mlx_available() -> bool:
    return omlx_endpoint_up() or ollama_available()


def requested_backend() -> str:
    forced = (os.getenv("MARKMAP_DESK_MODEL") or "").strip().lower()
    if forced == "local":
        return "ollama" if ollama_available() else ("mlx" if mlx_available() else "scripted")
    if forced in {"scripted", "bedrock", "ollama", "mlx"}:
        return forced
    if ollama_available() and os.getenv("MARKMAP_PREFER_LOCAL", "0") == "1":
        return "ollama"
    if mlx_available() and os.getenv("MARKMAP_PREFER_LOCAL", "0") == "1":
        return "mlx"
    if bedrock_disabled() or not aws_credentials_present():
        return "scripted"
    return "bedrock"


def model_backend() -> str:
    wanted = requested_backend()
    if wanted == "ollama" and not ollama_available():
        return "scripted"
    if wanted == "mlx" and not mlx_available():
        return "scripted"
    return wanted


def desk_model_id(backend: str | None = None) -> str:
    backend = backend or model_backend()
    if backend == "bedrock":
        return BEDROCK_MODEL_ID
    if backend == "ollama":
        return OLLAMA_MODEL_ID
    if backend == "mlx":
        return MLX_MODEL_ID if omlx_endpoint_up() else OLLAMA_MODEL_ID
    return "scripted-desk"


def require_production_secret() -> None:
    if os.getenv("MARKMAP_ENV") != "production":
        return
    if SECRET == DEFAULT_SECRET:
        raise SystemExit("Set MARKMAP_SECRET before listening in production.")


def strands_enabled() -> bool:
    try:
        import strands  # noqa: F401

        return True
    except ImportError:
        return False
