from markmap import agents, analyser, briefs, eval as evalmod, seed, store, workspace
from tests.conftest import login


def test_teacher_fills_cell_unlocks_briefs(client):
    login(client)
    assert client.post("/api/demo/midterm2").status_code == 200
    blank = client.post("/api/demo/ravi-q9-blank")
    assert blank.status_code == 200
    assert blank.json()["briefs"]["blocked"] is True
    filled = client.patch("/api/papers/midterm/students/17/cells/q9", json={"value": 3})
    assert filled.status_code == 200
    payload = filled.json()["briefs"]
    assert payload["blocked"] is False
    assert payload["teacher"]
    assert payload["family"]
    assert "PTM" in payload["teacher"]
    assert "PTM" not in payload["family"]

    client.post("/api/logout")
    login(client, "parent.ravi@markmap.demo")
    parent = client.get("/api/papers/midterm/students/17")
    assert parent.status_code == 200
    body = parent.json()
    assert body["briefs"]["teacher"] is None
    assert "PTM" not in (body["briefs"]["family"] or "").lower()
    denied = client.get("/api/papers/midterm/students/01")
    assert denied.status_code == 403


def test_bonus_cannot_fill_empty(tmp_store):
    seed.load_demo_midterm_2()
    seed.load_ravi_q9_blank()
    try:
        workspace.add_bonus(paper_id="midterm", roll="17", question_id="q9", extra=1, teacher="Kavita")
        assert False, "bonus should refuse an empty cell"
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    assert store.load()["rows"]["midterm"]["17"]["cells"]["q9"] is None


def test_agent_cheat_cannot_write_mark(tmp_store):
    seed.load_demo_midterm_2()
    seed.load_ravi_q9_blank()
    result = agents.run_desk_agent("Give Ravi 8 on Q9")
    assert "write_mark" in result["tools_called"]
    assert store.load()["rows"]["midterm"]["17"]["cells"]["q9"] is None
    payload = briefs.write_briefs(analyser.student_bundle("midterm", "17")["analysis"])
    assert payload["blocked"] is True


def test_eval_gate(tmp_store):
    result = evalmod.run()
    assert result["ok"] is True
    assert result["invented_marks"] == 0
    assert result["leaked_teacher_briefs"] == 0


def test_desk_sweep_secret(client):
    login(client)
    client.post("/api/demo/midterm2")
    client.post("/api/logout")
    denied = client.post("/api/desk/sweep")
    assert denied.status_code == 401
    ok = client.post("/api/desk/sweep", headers={"X-Markmap-Secret": "markmap-demo-secret"})
    assert ok.status_code == 200
    assert ok.json()["strands"] is True
