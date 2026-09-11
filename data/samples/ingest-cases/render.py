"""Render ingest-case documents as photographed pages.

Text and numbers are drawn in code so they stay exact. Do not replace
these PNGs with image-model output.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT.parent

FONTS = [
    Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf"),
    Path("/Library/Fonts/Times New Roman.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
]
FONTS_BOLD = [
    Path("/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"),
    Path("/Library/Fonts/Times New Roman Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),
]
FONTS_MONO = [
    Path("/System/Library/Fonts/Supplemental/Courier New.ttf"),
    Path("/Library/Fonts/Courier New.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
]


def font(paths: list[Path], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in paths:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def paper_sheet(size=(1240, 1754), cream="#f7f1e3") -> Image.Image:
    img = Image.new("RGB", size, cream)
    d = ImageDraw.Draw(img)
    d.rectangle((36, 36, size[0] - 37, size[1] - 37), outline="#c9b99a", width=2)
    return img


def photograph(doc: Image.Image) -> Image.Image:
    """Sit the page on a desk with a slight tilt — still OCR-readable."""
    grain = ImageEnhance.Contrast(doc.convert("RGB")).enhance(1.05)
    grain = ImageOps.expand(grain, border=8, fill="#d9cbb3")
    rotated = grain.rotate(1.2, resample=Image.Resampling.BICUBIC, expand=True, fillcolor="#6b5344")
    desk = Image.new("RGB", (rotated.width + 120, rotated.height + 120), "#6b5344")
    desk.paste(rotated, (60, 60))
    return ImageEnhance.Sharpness(desk).enhance(1.1)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def render_paper(src: Path, out: Path, *, tag_q10: bool = False) -> None:
    body = src.read_text(encoding="utf-8")
    if tag_q10:
        body = body.replace("Q10 (20 marks)\n", "Q10 (20 marks) [Statistics]\n")
    img = paper_sheet()
    d = ImageDraw.Draw(img)
    title = font(FONTS_BOLD, 36)
    body_f = font(FONTS, 22)
    small = font(FONTS, 18)
    y = 70
    w = img.width - 140
    for i, raw in enumerate(body.splitlines()):
        line = raw.rstrip()
        if not line:
            y += 14
            continue
        fnt = title if i < 3 else (body_f if line.startswith("Q") else small if i == 2 else body_f)
        for piece in wrap(d, line, fnt, w):
            d.text((70, y), piece, fill="#1c1917", font=fnt)
            y += int(fnt.size * 1.35)
            if y > img.height - 80:
                break
    photograph(img).save(out, "PNG")


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def render_marksheet(rows: list[dict[str, str]], out: Path, *, smudge_roll: str | None = None) -> None:
    img = paper_sheet((1600, 2000), "#f4efe4")
    d = ImageDraw.Draw(img)
    title = font(FONTS_BOLD, 32)
    head = font(FONTS_BOLD, 16)
    cell = font(FONTS_MONO, 16)
    d.text((70, 56), "Greenfield Public School", fill="#1c1917", font=title)
    d.text((70, 100), "Class 10-B  Mathematics  Midterm 2  —  marksheet", fill="#44403c", font=font(FONTS, 22))
    d.text((70, 132), "Empty / NA / dash = missing. Do not write zero.", fill="#7c2d12", font=font(FONTS, 18))
    cols = ["roll", "name"] + [f"q{i}" for i in range(1, 11)]
    labels = ["Roll", "Name"] + [f"Q{i}" for i in range(1, 11)]
    x0, y0 = 56, 180
    widths = [70, 220] + [72] * 10
    # header
    x = x0
    for lab, w in zip(labels, widths):
        d.rectangle((x, y0, x + w, y0 + 36), outline="#1c1917", fill="#efe8dc")
        d.text((x + 6, y0 + 8), lab, fill="#1c1917", font=head)
        x += w
    y = y0 + 36
    for row in rows:
        x = x0
        h = 32
        for key, w in zip(cols, widths):
            d.rectangle((x, y, x + w, y + h), outline="#78716c")
            val = (row.get(key) or "").strip()
            if smudge_roll and row.get("roll") == smudge_roll and key == "q9":
                d.ellipse((x + 12, y + 6, x + w - 12, y + h - 6), fill="#1c1917")
                d.ellipse((x + 22, y + 10, x + w - 8, y + h - 4), fill="#44403c")
            elif not val:
                d.text((x + 8, y + 7), "—", fill="#a8a29e", font=cell)
            else:
                d.text((x + 8, y + 7), val, fill="#1c1917", font=cell)
            x += w
        y += h
        if y > img.height - 80:
            break
    photograph(img).save(out, "PNG")


def render_report(
    out: Path,
    *,
    name: str,
    roll: str,
    term: list[str],
    midterm: list[str],
    term_total: str,
    mid_total: str,
    blank_q9: bool = False,
) -> None:
    img = paper_sheet((1100, 1500), "#fbf7f0")
    d = ImageDraw.Draw(img)
    title = font(FONTS_BOLD, 34)
    body = font(FONTS, 22)
    d.text((70, 60), "GREENFIELD PUBLIC SCHOOL", fill="#1c1917", font=title)
    d.text((70, 108), "MARK MAP STUDENT REPORT", fill="#b45309", font=font(FONTS_BOLD, 24))
    d.text((70, 150), "Class 10-B Mathematics", fill="#44403c", font=body)
    d.text((70, 186), f"Name {name}", fill="#1c1917", font=body)
    d.text((70, 218), f"Roll {roll}", fill="#1c1917", font=body)

    def section(y: int, heading: str, lines: list[str], total: str) -> int:
        d.text((70, y), heading, fill="#1c1917", font=font(FONTS_BOLD, 24))
        y += 40
        for line in lines:
            if blank_q9 and heading.endswith("Midterm") and line.startswith("Q9"):
                line = "Q9 (12 marks) [Linear Equations]  — / 12"
            d.text((70, y), line, fill="#1c1917", font=body)
            y += 30
        d.text((70, y), f"TOTAL {total}", fill="#1c1917", font=font(FONTS_BOLD, 22))
        return y + 48

    y = 270
    y = section(y, "SECTION Term 1", term, term_total)
    section(y, "SECTION Midterm", midterm, "—/80" if blank_q9 else mid_total)
    photograph(img).save(out, "PNG")


TERM_LINES = [
    "Q1 (4 marks) [Polynomials] 3/4",
    "Q2 (4 marks) [Polynomials] 3/4",
    "Q3 (6 marks) [Linear Equations] 1/6",
    "Q4 (6 marks) [Linear Equations] 2/6",
    "Q5 (6 marks) [Triangles] 5/6",
    "Q6 (6 marks) [Triangles] 5/6",
    "Q7 (8 marks) [Trigonometry] 6/8",
    "Q8 (8 marks) [Trigonometry] 6/8",
    "Q9 (12 marks) [Linear Equations] 3/12",
    "Q10 (20 marks) [Statistics] 14/20",
]
MID_LINES = [
    "Q1 (4 marks) [Polynomials] 3/4",
    "Q2 (4 marks) [Polynomials] 4/4",
    "Q3 (6 marks) [Linear Equations] 4/6",
    "Q4 (6 marks) [Linear Equations] 4/6",
    "Q5 (6 marks) [Triangles] 5/6",
    "Q6 (6 marks) [Triangles] 6/6",
    "Q7 (8 marks) [Trigonometry] 7/8",
    "Q8 (8 marks) [Trigonometry] 6/8",
    "Q9 (12 marks) [Linear Equations] 3/12",
    "Q10 (20 marks) 16/20",
]


def write_case(folder: Path, expected: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "expected.md").write_text(expected.strip() + "\n", encoding="utf-8")


def main() -> None:
    rows = load_rows(SAMPLES / "midterm2_marks.csv")

    c1 = ROOT / "01-paper-tagged"
    write_case(
        c1,
        """
# Case 01 — tagged question paper

**Drop:** paper photo
**File:** `photo.png`

The agent may read Q1–Q10, max marks, and `[Chapter]` tags.
Q1–Q10 are tagged on the page, including Q10 `[Statistics]`.
Must not invent an 11th question.
""",
    )
    render_paper(SAMPLES / "midterm2_paper.txt", c1 / "photo.png", tag_q10=True)
    tagged = (SAMPLES / "midterm2_paper.txt").read_text(encoding="utf-8").replace(
        "Q10 (20 marks)\n", "Q10 (20 marks) [Statistics]\n"
    )
    (c1 / "source.txt").write_text(tagged, encoding="utf-8")

    c2 = ROOT / "02-paper-needs-review"
    write_case(
        c2,
        """
# Case 02 — paper with an untagged question

**Drop:** paper photo
**File:** `photo.png`

Same Midterm 2 paper. Q10 has no `[Chapter]` tag on the page.
Agent must flag Q10 `needs_review`. Must not silently assign Statistics.
""",
    )
    render_paper(SAMPLES / "midterm2_paper.txt", c2 / "photo.png", tag_q10=False)
    text = (SAMPLES / "midterm2_paper.txt").read_text(encoding="utf-8").replace(
        "Q10 (20 marks)\nThe following table", "Q10 (20 marks)\nThe following table"
    )
    (c2 / "source.txt").write_text(text, encoding="utf-8")

    c3 = ROOT / "03-marksheet-empty-cells"
    write_case(
        c3,
        """
# Case 03 — class marksheet with blanks

**Drop:** marksheet photo
**File:** `photo.png`

Printed Midterm 2 sheet. Rolls **04, 11, 28** have Q9 as em dash (empty).
Agent may attach other cells. Must not fill those three with 0 or a guess.
Expected missing: `04/q9`, `11/q9`, `28/q9`.
""",
    )
    render_marksheet(rows, c3 / "photo.png")
    (c3 / "source.csv").write_text((SAMPLES / "midterm2_marks.csv").read_text(encoding="utf-8"), encoding="utf-8")

    c4 = ROOT / "04-student-report-complete"
    write_case(
        c4,
        """
# Case 04 — complete student report

**Drop:** one student’s report card photo
**File:** `photo.png`

Ravi Mehta, roll 17, Term 1 and Midterm both complete.
Agent may attach every cell. Midterm Q9 is 3/12 (not empty).
Must not invent a third section.
""",
    )
    render_report(
        c4 / "photo.png",
        name="Ravi Mehta",
        roll="17",
        term=TERM_LINES,
        midterm=MID_LINES,
        term_total="48/80",
        mid_total="58/80",
    )
    (c4 / "source.txt").write_text((SAMPLES / "ravi_report.txt").read_text(encoding="utf-8"), encoding="utf-8")

    c5 = ROOT / "05-student-report-blank-q9"
    write_case(
        c5,
        """
# Case 05 — report with a missing mark

**Drop:** student report photo
**File:** `photo.png`

Same report, Midterm Q9 printed as `— / 12`.
Agent must leave Q9 empty. Briefs stay blocked. Must not treat dash as zero.
""",
    )
    render_report(
        c5 / "photo.png",
        name="Ravi Mehta",
        roll="17",
        term=TERM_LINES,
        midterm=MID_LINES,
        term_total="48/80",
        mid_total="58/80",
        blank_q9=True,
    )
    src = (SAMPLES / "ravi_report.txt").read_text(encoding="utf-8")
    src = src.replace("Q9 (12 marks) [Linear Equations] 3/12", "Q9 (12 marks) [Linear Equations] —/12")
    src = src.replace("TOTAL 58/80", "TOTAL —/80")
    (c5 / "source.txt").write_text(src, encoding="utf-8")

    c6 = ROOT / "06-marksheet-smudged-cell"
    write_case(
        c6,
        """
# Case 06 — ink smudge, not a number

**Drop:** marksheet photo
**File:** `photo.png`

Ravi Mehta (17) Q9 is an ink blot, not a digit.
Agent must not read it as 8, 3, or 0. Cell stays missing.
Other cells on the row stay as printed.
""",
    )
    render_marksheet(rows, c6 / "photo.png", smudge_roll="17")
    (c6 / "source.csv").write_text(
        "roll,name,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10\n"
        "17,Ravi Mehta,3,4,4,4,5,6,7,6,,16\n",
        encoding="utf-8",
    )

    print("wrote", ROOT)


if __name__ == "__main__":
    main()
