#!/usr/bin/env python3
"""Generate the HX-CCD22 integration PDF from the Markdown report source."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "HX_CCD22_Integration_Report.md"
OUTPUT = ROOT / "HX_CCD22_Integration_Report.pdf"
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 0.62 * inch
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)


def clean_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def image_size(path: Path, max_width: float, max_height: float) -> tuple[float, float]:
    img = Image(str(path))
    width, height = img.imageWidth, img.imageHeight
    scale = min(max_width / width, max_height / height, 1)
    return width * scale, height * scale


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            spaceAfter=18,
            textColor=colors.HexColor("#1F2937"),
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=23,
            spaceBefore=16,
            spaceAfter=9,
            textColor=colors.HexColor("#111827"),
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            spaceBefore=12,
            spaceAfter=7,
            textColor=colors.HexColor("#1F2937"),
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.8,
            leading=13.5,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12.8,
            leftIndent=12,
            firstLineIndent=0,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8.2,
            leading=10.5,
            leftIndent=7,
            rightIndent=7,
            borderColor=colors.HexColor("#E5E7EB"),
            borderWidth=0.5,
            borderPadding=7,
            backColor=colors.HexColor("#F9FAFB"),
            spaceBefore=4,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4B5563"),
            spaceBefore=4,
            spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["BodyText"],
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
        ),
    }


def parse_table(rows: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    parsed: list[list[Paragraph]] = []
    for row in rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        parsed.append([Paragraph(clean_inline(cell), styles["body"]) for cell in cells])

    table = Table(parsed, colWidths=None, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def flush_paragraph(buffer: list[str], story: list, styles: dict[str, ParagraphStyle]) -> None:
    if not buffer:
        return
    text = " ".join(line.strip() for line in buffer).strip()
    if text:
        story.append(Paragraph(clean_inline(text), styles["body"]))
    buffer.clear()


def flush_bullets(buffer: list[str], story: list, styles: dict[str, ParagraphStyle]) -> None:
    if not buffer:
        return
    items = [
        ListItem(Paragraph(clean_inline(item), styles["bullet"]), leftIndent=8)
        for item in buffer
    ]
    story.append(
        ListFlowable(
            items,
            bulletType="bullet",
            start="circle",
            leftIndent=14,
            bulletFontSize=5,
        )
    )
    story.append(Spacer(1, 4))
    buffer.clear()


def flush_table(buffer: list[str], story: list, styles: dict[str, ParagraphStyle]) -> None:
    if not buffer:
        return
    story.append(parse_table(buffer, styles))
    story.append(Spacer(1, 8))
    buffer.clear()


def build_story(markdown: str, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    paragraph: list[str] = []
    bullets: list[str] = []
    table: list[str] = []
    code: list[str] = []
    in_code = False
    first_title = True

    for raw in markdown.splitlines():
        line = raw.rstrip()

        if line.startswith("```"):
            flush_paragraph(paragraph, story, styles)
            flush_bullets(bullets, story, styles)
            flush_table(table, story, styles)
            if in_code:
                story.append(Preformatted("\n".join(code), styles["code"]))
                code.clear()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code.append(line)
            continue

        image_match = re.match(r"!\[(.+?)\]\((.+?)\)", line)
        if image_match:
            flush_paragraph(paragraph, story, styles)
            flush_bullets(bullets, story, styles)
            flush_table(table, story, styles)
            caption, path_text = image_match.groups()
            path = Path(path_text)
            if path.exists():
                width, height = image_size(path, CONTENT_WIDTH, 4.8 * inch)
                story.append(KeepTogether([Image(str(path), width=width, height=height), Paragraph(caption, styles["caption"])]))
            else:
                story.append(Paragraph(f"Missing screenshot: {clean_inline(path_text)}", styles["body"]))
            continue

        if line.startswith("|"):
            flush_paragraph(paragraph, story, styles)
            flush_bullets(bullets, story, styles)
            table.append(line)
            continue
        flush_table(table, story, styles)

        if not line.strip():
            flush_paragraph(paragraph, story, styles)
            flush_bullets(bullets, story, styles)
            continue

        if line.startswith("# "):
            flush_paragraph(paragraph, story, styles)
            flush_bullets(bullets, story, styles)
            if first_title:
                story.append(Paragraph(clean_inline(line[2:]), styles["title"]))
                story.append(Spacer(1, 8))
                first_title = False
            else:
                story.append(PageBreak())
                story.append(Paragraph(clean_inline(line[2:]), styles["h1"]))
            continue

        if line.startswith("## "):
            flush_paragraph(paragraph, story, styles)
            flush_bullets(bullets, story, styles)
            story.append(Paragraph(clean_inline(line[3:]), styles["h1"]))
            continue

        if line.startswith("### "):
            flush_paragraph(paragraph, story, styles)
            flush_bullets(bullets, story, styles)
            story.append(Paragraph(clean_inline(line[4:]), styles["h2"]))
            continue

        if line.startswith("- "):
            flush_paragraph(paragraph, story, styles)
            bullets.append(line[2:].strip())
            continue

        flush_bullets(bullets, story, styles)
        paragraph.append(line)

    flush_paragraph(paragraph, story, styles)
    flush_bullets(bullets, story, styles)
    flush_table(table, story, styles)
    return story


def draw_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(MARGIN, 0.38 * inch, "HX-CCD22 Integration Report")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def main() -> None:
    styles = make_styles()
    story = build_story(SOURCE.read_text(encoding="utf-8"), styles)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=0.58 * inch,
        bottomMargin=0.58 * inch,
        title="HX-CCD22 Integration Report",
        author="Bus AI Dashboard",
    )
    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(OUTPUT)


if __name__ == "__main__":
    main()
