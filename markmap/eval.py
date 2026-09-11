"""One measured gate on the product claim. pytest / python -m markmap.eval"""

from __future__ import annotations

from typing import Any

from . import analyser, briefs, seed, store, tools, workspace


def snapshot(state: dict[str, Any] | None = None) -> dict[str, int]:
    state = state or store.load()
    invented = 0
    leaked = 0
    for rows in (state.get("rows") or {}).values():
        for row in rows.values():
            missing = set(row.get("missing") or [])
            for qid, val in (row.get("cells") or {}).items():
                if qid in missing and val is not None:
                    invented += 1
    for query in state.get("queries") or []:
        if query.get("role") in {"student", "parent"}:
            blob = str(query.get("answer") or "").lower()
            if "ptm talking" in blob or "teacher brief" in blob:
                leaked += 1
    return {"invented_marks": invented, "leaked_teacher_briefs": leaked}


def run() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    seed.reset_store()
    seed.load_demo_midterm_2()
    seed.load_ravi_q9_blank()
    row = store.load()["rows"]["midterm"]["17"]
    checks.append(("blank_q9_is_none", row["cells"]["q9"] is None))
    checks.append(("blank_q9_not_zero", row["cells"]["q9"] != 0))
    bundle = analyser.student_bundle("midterm", "17")
    payload = briefs.write_briefs(bundle["analysis"], bundle["year"])
    checks.append(("incomplete_briefs_none", payload["teacher"] is None and payload["family"] is None))
    checks.append(("incomplete_blocked", payload["blocked"] is True))
    family = {"teacher": None, "family": payload["family"], "blocked": payload["blocked"]}
    checks.append(("family_has_no_teacher_brief", family["teacher"] is None))
    checks.append(("family_has_no_ptm", "ptm" not in str(family.get("family") or "").lower()))
    checks.append(("forbidden_potential", analyser.contains_forbidden("This child has real potential")))
    checks.append(("forbidden_gifted", analyser.contains_forbidden("gifted")))
    checks.append(("forbidden_lazy", analyser.contains_forbidden("lazy")))
    checks.append(("clean_marks_ok", not analyser.contains_forbidden("Linear Equations 33%")))
    before = store.load()["rows"]["midterm"]["17"]["cells"]["q9"]
    tools.write_mark("17", "q9", 8)
    after = store.load()["rows"]["midterm"]["17"]["cells"]["q9"]
    checks.append(("write_mark_unchanged", before is None and after is None))
    tools.unlock_brief("17")
    still = briefs.write_briefs(analyser.student_bundle("midterm", "17")["analysis"])
    checks.append(("unlock_still_blocked", still["blocked"] is True))
    try:
        workspace.add_bonus(paper_id="midterm", roll="17", question_id="q9", extra=1, teacher="Kavita")
        bonus_ok = False
    except ValueError:
        bonus_ok = True
    checks.append(("bonus_cannot_fill_empty", bonus_ok))
    leaked = briefs._family_or_block("PTM talking points for the parent meeting.")
    checks.append(("family_ptm_blocks", leaked[0] is None and leaked[1]))
    failed = [name for name, ok in checks if not ok]
    out = {
        "ok": not failed,
        "passed": sum(1 for _, ok in checks if ok),
        "failed": failed,
        **snapshot(),
    }
    return out


def main() -> None:
    import tempfile
    from pathlib import Path

    from . import config

    config.STORE_PATH = Path(tempfile.gettempdir()) / "markmap-eval.json"
    result = run()
    status = "PASS" if result["ok"] else "FAIL"
    print(
        f"{status} invented_marks={result['invented_marks']} "
        f"leaked_teacher_briefs={result['leaked_teacher_briefs']} "
        f"{result['passed']} checks"
    )
    if result["failed"]:
        print("failed:", ", ".join(result["failed"]))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
