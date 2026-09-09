from markmap import analyser, briefs, config, seed
from tests.conftest import login


def test_map_paper_tag_wins_keyword_needs_review():
    paper = (config.SAMPLES_DIR / "midterm2_paper.txt").read_text()
    questions = analyser.map_paper(paper)
    by_id = {q["id"]: q for q in questions}
    assert by_id["q9"]["chapter"] == "Linear Equations"
    assert by_id["q9"]["source"] == "paper_tag"
    assert by_id["q9"]["needs_review"] is False
    assert by_id["q10"]["chapter"] == "Statistics"
    assert by_id["q10"]["source"] == "keyword"
    assert by_id["q10"]["needs_review"] is True


def test_demo_script_ravi_and_hotspot(tmp_store):
    seed.load_demo_midterm_2()
    bundle = analyser.student_bundle("midterm", "17")
    a = bundle["analysis"]
    assert a["name"] == "Ravi Mehta"
    assert a["complete"] is True
    assert "Linear Equations" in a["weak"]
    top = a["losses"][0]
    assert top["number"] == 9
    assert top["chapter"] == "Linear Equations"

    hot = analyser.class_bundle("midterm")["hotspots"]
    assert hot[0]["number"] == 9
    assert hot[0]["leaked"] is True

    payload = briefs.write_briefs(a, bundle["year"])
    assert payload["blocked"] is False
    assert "PTM talking points" in payload["teacher"]
    assert "PTM" not in payload["family"]
    assert "potential" not in payload["family"].lower()
    assert "Linear Equations" in payload["family"]

    year = analyser.year_line("17")
    titles = [p["title"] for p in year]
    assert titles == ["Term 1", "Midterm"]
    assert year[0]["percent"] < year[1]["percent"]


def test_blank_q9_blocks_brief(tmp_store):
    seed.load_demo_midterm_2()
    seed.load_ravi_q9_blank()
    bundle = analyser.student_bundle("midterm", "17")
    payload = briefs.write_briefs(bundle["analysis"], bundle["year"])
    assert payload["blocked"] is True
    assert payload["teacher"] is None
    assert payload["family"] is None
    assert "do not invent" in payload["reason"].lower()


def test_incomplete_class_alerts(tmp_store):
    seed.load_demo_midterm_2()
    from markmap import desk

    alerts = desk.compute_alerts()
    texts = " ".join(a["text"] for a in alerts)
    assert "3 scripts incomplete — briefs blocked" in texts
    assert "27/30 ready" in texts


def test_teacher_family_three_doors(client):
    login(client)
    assert client.post("/api/demo/midterm2").status_code == 200

    teacher = client.get("/api/papers/midterm/students/17").json()
    assert teacher["briefs"]["teacher"]
    assert "PTM" in teacher["briefs"]["teacher"]

    client.post("/api/logout")
    login(client, "ravi@markmap.demo")
    ravi = client.get("/api/papers/midterm/students/17").json()
    assert ravi["briefs"]["teacher"] is None
    assert ravi["briefs"]["family"]
    assert "PTM" not in ravi["briefs"]["family"]

    denied = client.get("/api/papers/midterm/students/01")
    assert denied.status_code == 403

    client.post("/api/logout")
    login(client, "parent.ravi@markmap.demo")
    parent = client.get("/api/students/17/year").json()
    assert len(parent["year"]) == 2
    sections = client.get("/api/students/17/sections").json()
    assert [b["title"] for b in sections["sections"]] == ["Term 1", "Midterm"]
    assert sections["sections"][0]["briefs"]["teacher"] is None
    assert "brain" in sections["sections"][1]
