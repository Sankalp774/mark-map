from markmap import agents, seed


def test_run_desk_goes_through_agent_tools(tmp_store):
    seed.load_demo_midterm_2()
    result = agents.run_desk_agent(class_id="10-B")
    assert result["strands"] is True
    assert result["mode"] == "scripted"
    assert result["model"] == "scripted-desk"
    assert "list_incomplete_rows" in result["tools_called"]
    assert "class_hotspots" in result["tools_called"]
    assert "write_student_briefs" in result["tools_called"]
    assert "run_desk_nags" in result["tools_called"]
    assert result["cycle"]["observe"]["briefs_blocked"] is True
    assert "blocked" in (result["summary"] or "").lower() or result["cycle"]["observe"]["briefs_blocked"]


def test_health_reports_scripted_backend(client):
    health = client.get("/api/health").json()
    assert health["strands_sdk"] is True
    assert health["strands_enabled"] is True
    assert health["backend"] == "scripted"
    assert health["model"] == "scripted-desk"
