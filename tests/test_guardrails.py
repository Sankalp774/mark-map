from markmap import analyser, briefs, seed


def test_empty_cell_is_not_zero(tmp_store):
    seed.load_demo_midterm_2()
    seed.load_ravi_q9_blank()
    row = seed.store.load()["rows"]["midterm"]["17"]
    assert row["cells"]["q9"] is None
    assert row["complete"] is False


def test_teacher_can_fix_tag(tmp_store):
    seed.load_demo_midterm_2()
    paper = analyser.set_question_chapter("midterm", "q10", "Statistics")
    q10 = next(q for q in paper["questions"] if q["id"] == "q10")
    assert q10["source"] == "teacher"
    assert q10["needs_review"] is False
    assert q10["chapter"] == "Statistics"


def test_forbidden_claims_rejected(tmp_store):
    seed.load_demo_midterm_2()
    assert analyser.contains_forbidden("This child has real potential") is True
    assert analyser.contains_forbidden("gifted") is True
    assert analyser.contains_forbidden("lazy") is True
    assert analyser.contains_forbidden("Linear Equations 33%") is False
    blocked, hits = briefs._family_or_block("PTM talking points for Friday.")
    assert blocked is None
    assert hits
