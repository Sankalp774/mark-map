from markmap import analyser, ocr, seed


def test_year_line_is_term1_then_midterm(tmp_store):
    seed.load_demo_midterm_2()
    year = analyser.year_line("17")
    assert [p["title"] for p in year] == ["Term 1", "Midterm"]
    assert year[0]["section"] == "term-1"
    assert year[1]["section"] == "midterm"
    assert year[0]["percent"] < year[1]["percent"]


def test_brain_graph_has_wikilink_and_q9(tmp_store):
    seed.load_demo_midterm_2()
    bundle = analyser.student_bundle("midterm", "17")
    brain = bundle["brain"]
    kinds = {n["kind"] for n in brain["nodes"]}
    assert {"student", "chapter", "question", "paper"} <= kinds
    labels = [n["label"] for n in brain["nodes"]]
    assert any("Linear Equations" in label for label in labels)
    assert "Q9" in labels
    assert "Linear Equations" in brain["backlinks"]
    assert "Q9" in brain["backlinks"]["Linear Equations"]


def test_screenshot_report_splits_sections(tmp_store):
    path = ocr.generate_ravi_report_png()
    text, engine = ocr.extract_text(path.read_bytes())
    assert engine in {"tesseract", "png-meta"}
    parsed = ocr.parse_report(text)
    assert parsed["roll"] == "17"
    assert parsed["name"] == "Ravi Mehta"
    ids = [s["section"] for s in parsed["sections"]]
    assert ids == ["term-1", "midterm"]
    mid = parsed["sections"][1]
    assert mid["cells"]["q9"] == 3
    assert mid["cells"]["q10"] == 16

    seed.load_demo_midterm_2()
    ocr.ingest_parsed_report(parsed, source="screenshot")
    blocks = analyser.student_sections("17")
    assert [b["title"] for b in blocks] == ["Term 1", "Midterm"]
    assert blocks[1]["analysis"]["percent"] == 68.8
    assert blocks[1]["briefs"]["blocked"] is False
