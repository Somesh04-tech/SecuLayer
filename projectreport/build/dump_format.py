"""Dump every paragraph of the format .docx with its style, alignment, spacing and run fonts (read-only)."""
import sys
from docx import Document
from docx.oxml.ns import qn

doc = Document(sys.argv[1])
body = doc.element.body
sec = 0
for child in body.iterchildren():
    tag = child.tag.split('}')[1]
    if tag == 'p':
        from docx.text.paragraph import Paragraph
        p = Paragraph(child, doc)
        pf = p.paragraph_format
        runs = []
        for r in p.runs:
            f = r.font
            runs.append(f"[{r.text!r} sz={f.size.pt if f.size else None} b={f.bold} i={f.italic} u={f.underline} fn={f.name}]")
        has_draw = bool(child.findall('.//' + qn('w:drawing')))
        sect = child.find(qn('w:pPr') + '/' + qn('w:sectPr')) if child.find(qn('w:pPr')) is not None else None
        print(f"P style={p.style.name!r} al={pf.alignment} ls={pf.line_spacing} sb={pf.space_before.pt if pf.space_before else None} sa={pf.space_after.pt if pf.space_after else None} li={pf.left_indent.pt if pf.left_indent else None} fi={pf.first_line_indent.pt if pf.first_line_indent else None} draw={has_draw} sect={sect is not None}")
        for r in runs:
            print("    ", r)
    elif tag == 'tbl':
        print("TABLE")
    elif tag == 'sectPr':
        print("FINAL SECTPR")
