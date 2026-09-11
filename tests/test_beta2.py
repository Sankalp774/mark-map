from markmap import analyser, desk, policy, seed, tools


def test_mapper_confidence_tag_vs_guess():
    paper = (analyser.config.SAMPLES_DIR / "midterm2_paper.txt").read_text()
    questions = analyser.map_paper(paper)
    by_id = {q["id"]: q for q in questions}
    assert by_id["q9"]["source"] == "paper_tag"
    assert by_id["q9"]["confidence"] == 1.0
    assert by_id["q9"]["needs_review"] is False
    assert by_id["q10"]["source"] == "keyword"
    assert by_id["q10"]["needs_review"] is True
    assert 0.35 <= by_id["q10"]["confidence"] < 1.0


def test_teacher_tag_sets_full_confidence(tmp_store):
    seed.load_demo_midterm_2()
    paper = analyser.set_question_chapter("midterm", "q10", "Statistics")
    q10 = next(q for q in paper["questions"] if q["id"] == "q10")
    assert q10["source"] == "teacher"
    assert q10["confidence"] == 1.0
    assert q10["needs_review"] is False


def test_policy_refuses_mark_writes():
    dumped = tools.write_mark("17", "q9", 4)
    assert "alter_marks" in dumped
    assert "false" in dumped.lower() or '"allowed": false' in dumped.replace(" ", "").lower()
    chapter = tools.set_question_chapter("midterm", "q10", "Statistics")
    assert "change_chapter_without_approval" in chapter
    unlock = tools.unlock_brief("17")
    assert "unlock_incomplete_briefs" in unlock
    assert policy.allowed("inspect_marks") is True
    assert policy.allowed("alter_marks") is False


def test_desk_trace_when_incomplete(tmp_store):
    seed.load_demo_midterm_2()
    cycle = desk.run_cycle("10-B")["cycle"]
    kinds = [t["kind"] for t in cycle["trace"]]
    text = " ".join(t["text"] for t in cycle["trace"])
    assert "ok" in kinds
    assert "warn" in kinds
    assert "briefs blocked" in text.lower()
    assert "Score Clerk" in text


def test_hotspot_includes_affected_students(tmp_store):
    seed.load_demo_midterm_2()
    hot = analyser.class_bundle("midterm")["hotspots"][0]
    assert hot["number"] == 9
    assert hot["affected"] >= 15
    assert hot["lost"] > 0
    bundle = analyser.student_bundle("midterm", "17")
    q9 = next(n for n in bundle["brain"]["nodes"] if n.get("question_id") == "q9")
    assert q9["leaked"] is True
    assert q9["affected"] == hot["affected"]
    assert q9["confidence"] == 1.0
