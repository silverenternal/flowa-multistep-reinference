"""Export the Chinese research manuscript while preserving tables and figures."""

import argparse
import math
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image


def inline(paragraph, text):
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    for token in re.split(r"(\*\*.*?\*\*|`[^`]+`)", text):
        if not token:
            continue
        bold = token.startswith("**") and token.endswith("**")
        code = token.startswith("`") and token.endswith("`")
        run = paragraph.add_run(token[2:-2] if bold else token[1:-1] if code else token)
        if bold:
            run.bold = True


def export(repo, source, output):
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2)
    section.header_distance = section.footer_distance = Cm(0.8)
    for name, size in [
        ("Normal", 10.5),
        ("Title", 19),
        ("Subtitle", 10),
        ("Heading 1", 13.5),
        ("Heading 2", 11.5),
        ("Caption", 9),
        ("Header", 8),
        ("Footer", 8),
    ]:
        style = document.styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Songti SC")
        style.paragraph_format.space_after = Pt(5)
        ppr = style._element.find(qn("w:pPr"))
        if ppr is not None:
            for border in list(ppr.findall(qn("w:pBdr"))):
                ppr.remove(border)
    document.styles["Normal"].paragraph_format.line_spacing = 1.15
    document.styles["Normal"].paragraph_format.widow_control = True
    for name in ["Heading 1", "Heading 2"]:
        document.styles[name].paragraph_format.space_before = Pt(11)
        document.styles[name].paragraph_format.keep_with_next = True
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    document.core_properties.author = ""
    document.core_properties.title = "流匹配端点再推理的目标保持条件与经验边界"
    document.core_properties.subject = "中文修订稿 第七版"
    lines = source.read_text().split("## 内部复现索引", 1)[0].splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if line.startswith("中文修订稿"):
            document.add_paragraph("中文修订稿 第七版   2026年11月3日", "Subtitle")
            continue
        if line.startswith("本文研究冻结检查点下的端点再推理。中文稿采用"):
            continue
        if line.startswith("|"):
            raw = [line]
            while i < len(lines) and lines[i].strip().startswith("|"):
                raw.append(lines[i].strip())
                i += 1
            rows = [
                [x.strip() for x in row.strip("|").split("|")]
                for row in raw
                if not re.fullmatch(r"[|\s:\-]+", row)
            ]
            table = document.add_table(rows=0, cols=len(rows[0]))
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            weights = []
            for col in range(len(rows[0])):
                lengths = [
                    sum(1.8 if "\u4e00" <= x <= "\u9fff" else 1 for x in row[col]) for row in rows
                ]
                weights.append(max(6, min(28, math.sqrt(max(lengths)) * 3)))
            widths = [17 * weight / sum(weights) for weight in weights]
            for col, width in zip(table.columns, widths, strict=True):
                col.width = Cm(width)
            properties = table._tbl.tblPr
            borders = OxmlElement("w:tblBorders")
            for edge in ["top", "left", "bottom", "right", "insideH", "insideV"]:
                item = OxmlElement("w:" + edge)
                for key, value in [("val", "single"), ("sz", "4"), ("color", "D9D9D9")]:
                    item.set(qn("w:" + key), value)
                borders.append(item)
            properties.append(borders)
            margins = OxmlElement("w:tblCellMar")
            for edge, value in [("top", 65), ("bottom", 65), ("left", 75), ("right", 75)]:
                item = OxmlElement("w:" + edge)
                item.set(qn("w:w"), str(value))
                item.set(qn("w:type"), "dxa")
                margins.append(item)
            properties.append(margins)
            for row_index, values in enumerate(rows):
                row = table.add_row()
                row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
                if row_index == 0:
                    row._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
                for col_index, (cell, value) in enumerate(zip(row.cells, values, strict=True)):
                    cell.width = Cm(widths[col_index])
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    paragraph = cell.paragraphs[0]
                    paragraph.paragraph_format.space_after = Pt(1)
                    paragraph.paragraph_format.space_before = Pt(1)
                    paragraph.paragraph_format.line_spacing = 1.05
                    paragraph.paragraph_format.keep_with_next = row_index == 0
                    numeric = bool(re.fullmatch(r"[\d\s+−–.,%\[\]/=A-Za-z_()<>:]+", value))
                    paragraph.alignment = (
                        WD_ALIGN_PARAGRAPH.CENTER
                        if row_index == 0 or numeric
                        else WD_ALIGN_PARAGRAPH.LEFT
                    )
                    inline(paragraph, value)
                    for run in paragraph.runs:
                        run.font.size = Pt(9)
                        if row_index == 0:
                            run.bold = True
                    if row_index == 0:
                        shade = OxmlElement("w:shd")
                        shade.set(qn("w:fill"), "E7E7E7")
                        cell._tc.get_or_add_tcPr().append(shade)
            # Caption following a table is kept with its final row.
            if len(rows) > 1:
                for cell in table.rows[-1].cells:
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.keep_with_next = True
            continue
        if line.startswith("!["):
            match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            picture = (repo / "docs/drafts" / match[2]).resolve()
            with Image.open(picture) as image:
                ratio = image.height / image.width
            width = min(6.65, 7.0 / ratio)
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.add_run().add_picture(str(picture), width=Inches(width))
            paragraph.paragraph_format.keep_with_next = True
            paragraph.paragraph_format.space_after = Pt(3)
            picture_properties = paragraph._p.xpath(".//wp:docPr")
            if picture_properties:
                picture_properties[0].set("descr", match[1])
            continue
        if line.startswith("# "):
            document.add_heading(line[2:], 0)
            continue
        if line.startswith("## "):
            heading = line[3:]
            heading = re.sub(r"^([IVX]+)\. ", r"\1 ", heading)
            heading = heading.replace("附录 A.", "附录 A").replace("附录 B.", "附录 B")
            document.add_heading(heading, 1)
            continue
        if line.startswith("### "):
            document.add_heading(re.sub(r"^([A-Z])\. ", r"\1 ", line[4:]), 2)
            continue
        caption = bool(re.match(r"^(图\s*\d|表\s*[IVX]+\.)", line))
        paragraph = document.add_paragraph(style="Caption" if caption else "Normal")
        if caption:
            paragraph.paragraph_format.keep_with_next = False
            paragraph.paragraph_format.space_after = Pt(8)
        if re.search(r"\([1-8]\)\s*$", line):
            line = re.sub(r"\s{2,}", "  ", line)
            paragraph.paragraph_format.keep_with_next = True
            paragraph.paragraph_format.space_before = Pt(4)
        if line.startswith(("**引理", "**命题")):
            paragraph.paragraph_format.keep_with_next = True
        following = next((value.strip() for value in lines[i:] if value.strip()), "")
        if re.search(r"\([1-8]\)\s*$", following):
            paragraph.paragraph_format.keep_with_next = True
        inline(paragraph, line)
        if re.match(r"^\[\d+\]", line):
            paragraph.paragraph_format.line_spacing = 1.05
            for run in paragraph.runs:
                run.font.size = Pt(9)
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    print(f"{output}: {len(document.tables)} tables; {len(document.inline_shapes)} figures")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export(args.repo, args.source, args.output)
