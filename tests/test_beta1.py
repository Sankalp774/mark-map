from markmap import analyser, desk, loop, memory, seed


def test_ravi_memory_shows_linear_improvement(tmp_store):
    seed.load_demo_midterm_2()
    mem = memory.student_memory("17", "10-B")
    le = next(t for t in mem["trends"] if t["chapter"] == "Linear Equations")
    assert le["to"] > le["from"]
    assert le["delta"] >= 15
    assert mem["remaining"]["number"] == 9
    measured = [i for i in mem["interventions"] if i.get("status") == "measured"]
    assert measured
    assert measured[-1]["outcome"]["delta"] == le["delta"]
    assert "word problems" in mem["readout"].lower() or "Q9" in mem["readout"]


def test_class_strategy_q9_is_dominant(tmp_store):
    seed.load_demo_midterm_2()
    strat = memory.class_strategy("midterm", "10-B")
    rec = strat["recommendation"]
    assert rec["kind"] == "class_reteach"
    assert rec["chapter"] == "Linear Equations"
    assert rec["affected"] >= 15
    assert "higher leverage" in rec["leverage"]


def test_desk_cycle_blocks_briefs_and_opens_teacher_task(tmp_store):
    seed.load_demo_midterm_2()
    cycle = desk.run_cycle("10-B")
    phases = [s["phase"] for s in cycle["cycle"]["steps"]]
    assert "observe" in phases
    assert "plan" in phases
    assert "act" in phases
    assert "wait" in phases
    text = " ".join(s["text"] for s in cycle["cycle"]["steps"])
    assert "blocked" in text.lower()
    assert cycle["cycle"]["observe"]["briefs_blocked"] is True


def test_approve_class_reteach(tmp_store):
    seed.load_demo_midterm_2()
    # Force a complete class so the cycle proposes reteach.
    state = seed.store.load()
    for row in state["rows"]["midterm"].values():
        for qid, val in list(row["cells"].items()):
            if val is None:
                row["cells"][qid] = 0
        row["complete"] = True
        row["missing"] = []
    seed.store.save(state)
    cycle = desk.run_cycle("10-B")
    proposals = [a for a in cycle["cycle"]["acts"] if a.get("kind") == "propose"]
    assert proposals
    item = loop.approve(proposals[0]["id"], "Kavita Sharma")
    assert item["status"] in {"approved", "assigned"}
