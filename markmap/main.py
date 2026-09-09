from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import analyser, auth, briefs, config, desk, query, seed, store, tools, workspace
from . import agents as agent_runtime

@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not Path(config.STORE_PATH).exists():
        seed.reset_store()
    else:
        state = store.load()
        if not state.get("users"):
            store.update(lambda s: s.__setitem__("users", seed.demo_users()))
        store.update(seed.migrate_legacy_ids)
    workspace.seed_defaults()
    yield


app = FastAPI(title="Mark Map", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
if config.SAMPLES_DIR.exists():
    app.mount("/samples", StaticFiles(directory=config.SAMPLES_DIR), name="samples")


class LoginBody(BaseModel):
    email: str
    password: str


class ChapterBody(BaseModel):
    chapter: str


class DeskBody(BaseModel):
    prompt: str | None = None


class BroadcastBody(BaseModel):
    audience: str
    title: str
    body: str


class TaskBody(BaseModel):
    roll: str
    title: str
    body: str
    due: str | None = None


class CalendarBody(BaseModel):
    title: str
    date: str
    syllabus: str


class BonusBody(BaseModel):
    paper_id: str = "midterm"
    roll: str
    question_id: str
    extra: float = 1


class AddressBody(BaseModel):
    paper_id: str = "midterm"
    roll: str
    question_id: str
    note: str = ""


class QueryBody(BaseModel):
    question: str = ""
    faq_id: str | None = None


def _user(request: Request) -> dict[str, Any]:
    token = request.cookies.get(config.COOKIE_NAME)
    user = auth.user_from_token(token)
    if not user:
        raise HTTPException(401, "Sign in.")
    return user


def _teacher(request: Request) -> dict[str, Any]:
    user = _user(request)
    if user["role"] != "teacher":
        raise HTTPException(403, "Teacher only.")
    return user


def _can_see(user: dict[str, Any], roll: str) -> bool:
    if user["role"] == "teacher":
        return True
    return user.get("roll") == roll


@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, **tools.health()}


@app.post("/api/login")
def login(body: LoginBody) -> JSONResponse:
    try:
        payload = auth.login(body.email, body.password)
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    response = JSONResponse({"user": payload["user"]})
    response.set_cookie(
        config.COOKIE_NAME,
        payload["token"],
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@app.post("/api/logout")
def logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.delete_cookie(config.COOKIE_NAME)
    return response


@app.get("/api/me")
def me(request: Request) -> dict[str, Any]:
    user = _user(request)
    state = store.load()
    papers = [
        {
            "id": p["id"],
            "title": p.get("title"),
            "section": p.get("section") or p["id"],
            "date": p.get("date"),
        }
        for p in sorted(state["papers"].values(), key=lambda x: x.get("date") or "")
    ]
    kpis = _kpis(state)
    return {
        "user": user,
        "school": state.get("school") or config.SCHOOL,
        "papers": papers,
        "alerts": state.get("alerts") or [],
        "agent_log": state.get("agent_log") or [],
        "health": tools.health(),
        "ptm_hours": desk.hours_until_ptm(state),
        "workspace": workspace.snapshot(user),
        "kpis": kpis,
        "roster_lite": kpis.get("roster_lite") or [],
    }


@app.post("/api/demo/midterm2")
def demo_midterm2(request: Request) -> dict[str, Any]:
    _teacher(request)
    result = seed.load_demo_midterm_2()
    store.agent_log("ingest_clerk", "Teacher loaded demo Term 1 + Midterm.")
    return {"ok": True, **result, "class": analyser.class_bundle("midterm")}


@app.post("/api/demo/ravi-q9-blank")
def demo_blank(request: Request) -> dict[str, Any]:
    _teacher(request)
    seed.load_ravi_q9_blank()
    bundle = analyser.student_bundle("midterm", "17")
    return {
        **bundle,
        "briefs": briefs.write_briefs(bundle["analysis"], bundle["year"]),
    }


@app.post("/api/demo/reset")
def demo_reset(request: Request) -> dict[str, Any]:
    _teacher(request)
    seed.reset_store()
    return {"ok": True}


@app.post("/api/ingest")
async def ingest(
    request: Request,
    title: str = Form("Uploaded paper"),
    paper_text: str = Form(""),
    paper: UploadFile | None = File(None),
    marks: UploadFile | None = File(None),
) -> dict[str, Any]:
    _teacher(request)
    text = paper_text.strip()
    if paper is not None and paper.filename:
        raw = await paper.read()
        name = (paper.filename or "").lower()
        if name.endswith(".pdf"):
            text = _pdf_text(raw)
        else:
            text = raw.decode("utf-8", errors="replace")
    if marks is None:
        raise HTTPException(400, "Marks CSV is required.")
    csv_text = (await marks.read()).decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(400, "Paper text is empty.")
    try:
        section = "term-1" if "term 1" in title.lower() or "term-1" in title.lower() else "midterm"
        result = seed.ingest_paper(
            paper_id=title.lower().replace(" ", "-")[:40],
            title=title,
            date="2026-09-04",
            paper_text=text,
            csv_text=csv_text,
            section=section,
            source="upload",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    desk.run_desk()
    return result


@app.get("/api/papers/{paper_id}")
def get_paper(paper_id: str, request: Request) -> dict[str, Any]:
    _user(request)
    try:
        return analyser.class_bundle(paper_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.patch("/api/papers/{paper_id}/questions/{question_id}")
def patch_chapter(paper_id: str, question_id: str, body: ChapterBody, request: Request) -> dict[str, Any]:
    _teacher(request)
    try:
        analyser.set_question_chapter(paper_id, question_id, body.chapter)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return analyser.class_bundle(paper_id)


@app.get("/api/papers/{paper_id}/students/{roll}")
def get_student(paper_id: str, roll: str, request: Request) -> dict[str, Any]:
    user = _user(request)
    if not _can_see(user, roll):
        raise HTTPException(403, "Not your map.")
    try:
        bundle = analyser.student_bundle(paper_id, roll)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    payload = briefs.write_briefs(bundle["analysis"], bundle["year"])
    if user["role"] != "teacher":
        payload = {
            "blocked": payload["blocked"],
            "reason": payload["reason"],
            "family": payload["family"],
            "teacher": None,
        }
        bundle["row"] = {
            "roll": bundle["row"]["roll"],
            "name": bundle["row"]["name"],
            "complete": bundle["row"]["complete"],
            "missing": bundle["row"]["missing"],
            "cells": bundle["row"]["cells"],
            "bonus": bundle["row"].get("bonus") or {},
            "addressed": bundle["row"].get("addressed") or [],
        }
    return {**bundle, "briefs": payload}


@app.get("/api/students/{roll}/year")
def get_year(roll: str, request: Request) -> dict[str, Any]:
    user = _user(request)
    if not _can_see(user, roll):
        raise HTTPException(403, "Not your map.")
    return {"roll": roll, "year": analyser.year_line(roll)}


@app.get("/api/students/{roll}/sections")
def get_sections(roll: str, request: Request) -> dict[str, Any]:
    user = _user(request)
    if not _can_see(user, roll):
        raise HTTPException(403, "Not your map.")
    blocks = analyser.student_sections(roll)
    if user["role"] != "teacher":
        for block in blocks:
            briefs_payload = block.get("briefs") or {}
            block["briefs"] = {
                "blocked": briefs_payload.get("blocked"),
                "reason": briefs_payload.get("reason"),
                "family": briefs_payload.get("family"),
                "teacher": None,
            }
    return {"roll": roll, "sections": blocks}


@app.post("/api/ingest/screenshot")
async def ingest_screenshot(request: Request, shot: UploadFile = File(...)) -> dict[str, Any]:
    _teacher(request)
    raw = await shot.read()
    if not raw:
        raise HTTPException(400, "Empty screenshot.")
    from . import ocr

    result = ocr.read_and_maybe_ingest(raw)
    store.agent_log("ingest_clerk", f"Screenshot {result.get('engine')} ok={result.get('ok')}.")
    if result.get("ok"):
        try:
            result["class"] = analyser.class_bundle("midterm")
        except KeyError:
            result["class"] = None
    result["image_url"] = None
    return result


@app.post("/api/demo/screenshot")
def demo_screenshot(request: Request) -> dict[str, Any]:
    _teacher(request)
    from . import ocr

    path = ocr.generate_ravi_report_png()
    result = ocr.read_and_maybe_ingest(path.read_bytes())
    store.agent_log("ingest_clerk", f"Demo screenshot via {result.get('engine')}.")
    result["image_url"] = "/samples/ravi_report.png"
    result["path"] = path.name
    try:
        result["class"] = analyser.class_bundle("midterm")
    except KeyError:
        result["class"] = None
    return result


@app.post("/api/desk/run")
async def desk_run(request: Request, body: DeskBody | None = None) -> dict[str, Any]:
    _teacher(request)
    prompt = body.prompt if body else None
    result = await asyncio.to_thread(agent_runtime.run_desk_agent, prompt)
    return result


@app.get("/api/desk/alerts")
def desk_alerts(request: Request) -> dict[str, Any]:
    _user(request)
    return {"alerts": store.load().get("alerts") or []}


@app.get("/api/workspace")
def get_workspace(request: Request) -> dict[str, Any]:
    user = _user(request)
    return workspace.snapshot(user)


@app.post("/api/workspace/broadcast")
def post_broadcast(body: BroadcastBody, request: Request) -> dict[str, Any]:
    user = _teacher(request)
    try:
        item = workspace.broadcast(
            audience=body.audience, title=body.title, body=body.body, teacher=user["name"]
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "item": item, "workspace": workspace.snapshot(user)}


@app.post("/api/workspace/task")
def post_task(body: TaskBody, request: Request) -> dict[str, Any]:
    user = _teacher(request)
    try:
        item = workspace.assign_task(
            roll=body.roll, title=body.title, body=body.body, teacher=user["name"], due=body.due
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "item": item, "workspace": workspace.snapshot(user)}


@app.post("/api/workspace/calendar")
def post_calendar(body: CalendarBody, request: Request) -> dict[str, Any]:
    user = _teacher(request)
    try:
        item = workspace.schedule_test(
            title=body.title, date=body.date, syllabus=body.syllabus, teacher=user["name"]
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "item": item, "workspace": workspace.snapshot(user)}


@app.post("/api/workspace/bonus")
def post_bonus(body: BonusBody, request: Request) -> dict[str, Any]:
    user = _teacher(request)
    try:
        applied = workspace.add_bonus(
            paper_id=body.paper_id,
            roll=body.roll,
            question_id=body.question_id,
            extra=body.extra,
            teacher=user["name"],
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc
    bundle = analyser.student_bundle(body.paper_id, body.roll)
    return {
        "ok": True,
        "applied": applied,
        "student": {**bundle, "briefs": briefs.write_briefs(bundle["analysis"], bundle["year"])},
        "class": analyser.class_bundle(body.paper_id),
    }


@app.post("/api/workspace/address")
def post_address(body: AddressBody, request: Request) -> dict[str, Any]:
    user = _teacher(request)
    try:
        result = workspace.address_issue(
            paper_id=body.paper_id,
            roll=body.roll,
            question_id=body.question_id,
            teacher=user["name"],
            note=body.note,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc
    bundle = analyser.student_bundle(body.paper_id, body.roll)
    return {
        "ok": True,
        **result,
        "student": {**bundle, "briefs": briefs.write_briefs(bundle["analysis"], bundle["year"])},
        "workspace": workspace.snapshot(user),
    }


@app.get("/api/query/faqs")
def get_faqs(request: Request) -> dict[str, Any]:
    _user(request)
    return {"faqs": query.FAQS}


@app.post("/api/query")
def post_query(body: QueryBody, request: Request) -> dict[str, Any]:
    user = _user(request)
    try:
        result = query.answer(question=body.question, user=user, faq_id=body.faq_id)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    return result


def _kpis(state: dict[str, Any]) -> dict[str, Any]:
    paper = analyser.resolve_paper(state, "midterm") or analyser.resolve_paper(state, "term-1")
    if not paper:
        return {"n": 0, "ready": 0, "incomplete": 0, "hotspot": None, "roster_lite": []}
    bundle = analyser.class_bundle(paper["id"], state)
    hot = (bundle.get("hotspots") or [None])[0]
    return {
        "paper_id": paper["id"],
        "title": paper.get("title"),
        "n": bundle["counts"]["n"],
        "ready": bundle["counts"]["ready"],
        "incomplete": bundle["counts"]["incomplete"],
        "needs_review": bundle["counts"]["needs_review"],
        "hotspot": hot,
        "roster_lite": [
            {"roll": r["roll"], "name": r["name"]} for r in bundle.get("roster") or []
        ],
    }


def _pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise HTTPException(400, "pypdf is not installed.") from exc
    reader = PdfReader(io_bytes(raw))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def io_bytes(raw: bytes):
    import io

    return io.BytesIO(raw)


def main() -> None:
    import os

    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("markmap.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
