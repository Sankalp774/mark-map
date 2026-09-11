# Ingest photo cases

Each folder is one drop the desk should handle. `photo.png` is the page. `source.txt` / `source.csv` is the ground truth. `expected.md` is what the agent may and must not do.

| Folder | Drop | Rule |
|---|---|---|
| `01-paper-tagged` | Question paper | Read Q1–Qn, max marks, `[Chapter]` tags |
| `02-paper-needs-review` | Question paper | Q10 has no tag → `needs_review` |
| `03-marksheet-empty-cells` | Class marksheet | Rolls 04, 11, 28 Q9 empty — not zero |
| `04-student-report-complete` | One report card | Attach every cell for Ravi 17 |
| `05-student-report-blank-q9` | One report card | Midterm Q9 is `—` — block the brief |
| `06-marksheet-smudged-cell` | Class marksheet | Ink blot on 17/Q9 — do not read as 8 |

Rebuild the photos (do not use an image model):

```bash
python data/samples/ingest-cases/render.py
```
