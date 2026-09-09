from markmap import analyser, query, seed, workspace
from tests.conftest import login


def test_bonus_and_address_q9(tmp_store):
    seed.load_demo_midterm_2()
    before = analyser.student_bundle("midterm", "17")["analysis"]
    q9 = next(l for l in before["losses"] if l["number"] == 9)
    applied = workspace.add_bonus(
        paper_id="midterm", roll="17", question_id="q9", extra=2, teacher="Kavita Sharma"
    )
    assert applied["awarded"] == 2
    after = analyser.student_bundle("midterm", "17")
    assert after["row"]["cells"]["q9"] == q9["got"] + 2
    assert after["brain"]["nodes"]
    qnode = next(n for n in after["brain"]["nodes"] if n.get("question_id") == "q9")
    assert qnode["bonus"] == 2

    addressed = workspace.address_issue(
        paper_id="midterm", roll="17", question_id="q9", teacher="Kavita Sharma"
    )
    assert addressed["task"]["roll"] == "17"
    bundle = analyser.student_bundle("midterm", "17")
    assert "q9" in (bundle["row"].get("addressed") or [])
    qnode = next(n for n in bundle["brain"]["nodes"] if n.get("question_id") == "q9")
    assert qnode["addressed"] is True


def test_bonus_refuses_empty_cell(tmp_store):
    seed.load_demo_midterm_2()
    seed.load_ravi_q9_blank()
    try:
        workspace.add_bonus(paper_id="midterm", roll="17", question_id="q9", extra=1, teacher="K")
        assert False, "should have refused"
    except ValueError as exc:
        assert "invent" in str(exc).lower()


def test_broadcast_and_query(tmp_store):
    seed.load_demo_midterm_2()
    workspace.broadcast(audience="parents", title="PTM Friday", body="Bring the family brief.", teacher="Kavita")
    workspace.schedule_test(
        title="Term examination",
        date="2026-09-28",
        syllabus="Linear Equations word problems",
        teacher="Kavita",
    )
    user = {"email": "parent.ravi@markmap.demo", "role": "parent", "roll": "17", "name": "Parent"}
    snap = workspace.snapshot(user)
    assert any(b["title"] == "PTM Friday" for b in snap["broadcasts"])
    ans = query.answer(question="When is the next test?", user=user)
    assert "2026-09-28" in ans["answer"]
    q9 = query.answer(question="", user=user, faq_id="q9")
    assert "Q9" in q9["answer"] or "3/" in q9["answer"]


def test_screenshot_api_returns_preview(client):
    login(client)
    res = client.post("/api/demo/screenshot")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ok"] is True
    assert data["engine"] in {"tesseract", "png-meta"}
    assert data["image_url"]
    titles = [s["title"] for s in data["sections"]]
    assert titles == ["Term 1", "Midterm"]
