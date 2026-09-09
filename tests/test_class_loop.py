from markmap import analyser, seed, workspace
from tests.conftest import login


def test_teacher_can_switch_class(client):
    login(client)
    client.post("/api/demo/midterm2")
    me = client.get("/api/me").json()
    ids = [c["id"] for c in me["classes"]]
    assert ids == ["10-B", "10-A", "9-C"]
    assert me["current_class"]["id"] == "10-B"
    assert me["kpis"]["n"] == 30

    res = client.post("/api/class/select", json={"class_id": "10-A"})
    assert res.status_code == 200
    me = client.get("/api/me").json()
    assert me["current_class"]["id"] == "10-A"
    assert me["kpis"]["n"] == 12
    papers = [p["id"] for p in me["papers"]]
    assert "10-A:midterm" in papers
    assert "midterm" not in papers


def test_two_way_loop(tmp_store):
    seed.load_demo_midterm_2()
    teacher = {"name": "Kavita Sharma", "role": "teacher", "class_id": "10-B", "class_ids": ["10-B"]}
    parent = {"name": "Parent of Ravi Mehta", "role": "parent", "roll": "17", "class_id": "10-B"}
    item = workspace.broadcast(
        audience="parents", title="PTM Friday", body="Please acknowledge.", teacher="Kavita", class_id="10-B"
    )
    workspace.ack_broadcast(broadcast_id=item["id"], user=parent)
    workspace.reply_broadcast(broadcast_id=item["id"], user=parent, body="We will come.")
    workspace.thread_message(class_id="10-B", roll="17", user=teacher, body="Ravi should drill Q9.")
    workspace.thread_message(class_id="10-B", roll="17", user=parent, body="We started tonight.")
    snap_t = workspace.snapshot(teacher, "10-B")
    snap_p = workspace.snapshot(parent, "10-B")
    assert snap_p["broadcasts"][0]["acks"]
    assert snap_p["broadcasts"][0]["replies"][0]["body"] == "We will come."
    assert snap_t["threads"][0]["messages"][-1]["role"] == "parent"
    assert snap_t["unread"] >= 1


def test_ira_stays_in_10a(tmp_store):
    seed.load_demo_midterm_2()
    blocks = analyser.student_sections("01", class_id="10-A")
    assert blocks
    assert all(b["paper"]["class_id"] == "10-A" for b in blocks)
    ravi = analyser.student_sections("17", class_id="10-B")
    assert ravi[0]["analysis"]["name"] == "Ravi Mehta"
