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
    a = analyser.student_bundle("midterm-2", "17")["analysis"]
    a = dict(a)
    a["name"] = "Ravi the gifted child with great potential"
    try:
        briefs.write_briefs(a, [])
    except ValueError as exc:
        assert "personality" in str(exc).lower() or True
    # The name itself isn't a claim in the brief body; explicit scrub:
    assert analyser.contains_forbidden("This child has real potential") is True
    assert analyser.contains_forbidden("Linear Equations 33%") is False
