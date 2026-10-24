"""Print the page setup, styles, headers/footers and numbering of the format .docx (read-only)."""
import sys
from docx import Document
from docx.shared import Emu

path = sys.argv[1]
doc = Document(path)
for i, s in enumerate(doc.sections):
    print(f"section {i}: start={s.start_type} page={Emu(s.page_width).inches:.2f}x{Emu(s.page_height).inches:.2f}in "
          f"margins T{Emu(s.top_margin).inches:.2f} B{Emu(s.bottom_margin).inches:.2f} "
          f"L{Emu(s.left_margin).inches:.2f} R{Emu(s.right_margin).inches:.2f} "
          f"header_dist={Emu(s.header_distance).inches:.2f} footer_dist={Emu(s.footer_distance).inches:.2f}")
    for kind in ("header", "footer"):
        part = getattr(s, kind)
        print(f"   {kind}: linked={part.is_linked_to_previous} text={[p.text for p in part.paragraphs]!r}")
print()
styles = doc.styles
for st in styles:
    try:
        font = st.font
    except AttributeError:
        continue
    if st.type != 1:  # paragraph styles only
        continue
    pf = st.paragraph_format
    print(f"{st.name!r:28} base={st.base_style.name if st.base_style else None!r:14} font={font.name!r} size={font.size.pt if font.size else None} "
          f"bold={font.bold} align={pf.alignment} line={pf.line_spacing} before={pf.space_before} after={pf.space_after}")
# docDefaults
from docx.oxml.ns import qn
rpr = doc.styles.element.find(qn('w:docDefaults'))
print()
print(rpr.xml if rpr is not None else 'no docDefaults')
