"""Render the checked Markdown report to the single PDF for Brightspace."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (HRFlowable, Image, Paragraph,
                                Preformatted, SimpleDocTemplate, Spacer, Table,
                                TableStyle)


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "results" / "report.md"
OUTPUT = ROOT / "results" / "report.pdf"


def register_fonts() -> None:
    import matplotlib

    font_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    for name, file in [("DejaVu", "DejaVuSans.ttf"),
                       ("DejaVu-Bold", "DejaVuSans-Bold.ttf"),
                       ("DejaVu-Mono", "DejaVuSansMono.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")


def inline(text: str) -> str:
    """Convert the limited Markdown used in this report to ReportLab markup."""
    parts = re.split(r"(\[[^]]+\]\(https?://[^)]+\)|`[^`]+`)", text)
    out = []
    for part in parts:
        link = re.fullmatch(r"\[([^]]+)\]\((https?://[^)]+)\)", part)
        if link:
            out.append(f'<link href="{html.escape(link.group(2), quote=True)}" color="#155fa0">'
                       f'{html.escape(link.group(1))}</link>')
        elif part.startswith("`") and part.endswith("`"):
            out.append(f'<font name="DejaVu-Mono">{html.escape(part[1:-1])}</font>')
        else:
            out.append(html.escape(part).replace("**", ""))
    return "".join(out)


def styles():
    base = getSampleStyleSheet()
    normal = ParagraphStyle("ReportNormal", parent=base["Normal"], fontName="DejaVu",
                            fontSize=8.7, leading=12.8, spaceAfter=7)
    return {
        "title": ParagraphStyle("ReportTitle", parent=normal, fontName="DejaVu-Bold",
                                fontSize=17, leading=22, spaceAfter=12, textColor=colors.HexColor("#17324f")),
        "h2": ParagraphStyle("ReportH2", parent=normal, fontName="DejaVu-Bold",
                             fontSize=11.4, leading=16, spaceBefore=12, spaceAfter=5,
                             keepWithNext=True, textColor=colors.HexColor("#17324f")),
        "h3": ParagraphStyle("ReportH3", parent=normal, fontName="DejaVu-Bold",
                             fontSize=9.7, leading=14, spaceBefore=9, spaceAfter=4,
                             keepWithNext=True, textColor=colors.HexColor("#17324f")),
        "normal": normal,
        "bullet": ParagraphStyle("ReportBullet", parent=normal, leftIndent=15,
                                 firstLineIndent=-9, spaceAfter=4),
        "code": ParagraphStyle("ReportCode", parent=normal, fontName="DejaVu-Mono",
                               fontSize=6.5, leading=9, leftIndent=9, rightIndent=5,
                               spaceBefore=3, spaceAfter=9, backColor=colors.HexColor("#f2f5f7")),
        "cell": ParagraphStyle("ReportCell", parent=normal, fontSize=7.2, leading=10,
                               spaceAfter=0),
        "cell_header": ParagraphStyle("ReportCellHeader", parent=normal,
                                      fontName="DejaVu-Bold", fontSize=7.1,
                                      leading=10, spaceAfter=0),
    }


def build_story(text: str):
    st = styles()
    story = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == "```":
            code = []
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                code.append(lines[i])
                i += 1
            story.append(Preformatted("\n".join(code), st["code"], maxLineLength=120,
                                      splitChars=" "))
            i += 1
            continue
        if line.startswith("| "):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+", cell) for cell in cells):
                    rows.append(cells)
                i += 1
            widths = [2.6 * inch, .42 * inch, .42 * inch, 1.18 * inch, 1.7 * inch]
            content = [[Paragraph(inline(cell), st["cell_header"] if row_index == 0 else st["cell"])
                        for cell in row] for row_index, row in enumerate(rows)]
            table = Table(content, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5edf4")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fa")]),
                ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#c7d3dd")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.extend([table, Spacer(1, 10)])
            continue
        if line.startswith("!["):
            match = re.fullmatch(r"!\[([^]]+)\]\(([^)]+)\)", line)
            if not match:
                raise ValueError(f"Invalid image Markdown: {line}")
            story.append(Image(str(SOURCE.parent / match.group(2)), width=6.95 * inch,
                               height=3.18 * inch, hAlign="CENTER"))
            story.append(Spacer(1, 8))
            i += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), st["title"]))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b9c8d5")))
            story.append(Spacer(1, 9))
            i += 1
            continue
        if line.startswith("## ") or line.startswith("### "):
            level = "h3" if line.startswith("###") else "h2"
            story.append(Paragraph(inline(line.lstrip("# ")), st[level]))
            i += 1
            continue
        if line.startswith("- "):
            story.append(Paragraph("&#8226; " + inline(line[2:]), st["bullet"]))
            i += 1
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "- ", "|", "```")):
            paragraph.append(lines[i].strip())
            i += 1
        story.append(Paragraph(inline(" ".join(paragraph)), st["normal"]))
    return story


def page_decoration(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(colors.HexColor("#d8e1e8"))
    canvas.line(.63 * inch, .52 * inch, width - .63 * inch, .52 * inch)
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(colors.HexColor("#566575"))
    canvas.drawString(.65 * inch, .35 * inch, "CS 422  |  Assignment 4  |  Bhavin Gupta")
    canvas.drawRightString(width - .65 * inch, .35 * inch, str(doc.page))
    canvas.restoreState()


def main() -> None:
    register_fonts()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    draw_topologies()
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=letter, leftMargin=.65 * inch,
                            rightMargin=.65 * inch, topMargin=.62 * inch,
                            bottomMargin=.68 * inch, title="Assignment 4 - Maximum Concurrent Flow",
                            author="Bhavin Gupta")
    doc.build(build_story(SOURCE.read_text()), onFirstPage=page_decoration,
              onLaterPages=page_decoration)
    print(OUTPUT)


def draw_topologies() -> None:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap

    graphs = [
        (7, 3, lambda i, j: (j - i) % 7 in {1, 2, 4}, "n = 7, d = 3 | shifts 1, 2, 4"),
        (8, 4, lambda i, j: (i - j) % 2 == 1, "n = 8, d = 4 | even/odd bipartite"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.4), constrained_layout=True)
    color_map = ListedColormap(["#f0f3f6", "#23618a"])
    for ax, (n, d, edge, title) in zip(axes, graphs):
        data = np.array([[int(edge(i, j)) for j in range(n)] for i in range(n)])
        assert np.all(data.sum(axis=0) == d) and np.all(data.sum(axis=1) == d)
        ax.imshow(data, cmap=color_map, vmin=0, vmax=1)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xlabel("Destination j")
        ax.set_ylabel("Source i")
        ax.set_xticks(np.arange(-.5, n, 1), minor=True)
        ax.set_yticks(np.arange(-.5, n, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.5)
        ax.tick_params(which="minor", bottom=False, left=False)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=13)
    path = SOURCE.parent / "plots" / "topology_adjacency.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
