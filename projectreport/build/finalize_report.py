"""Condense the author's changed.docx to a 40-page A4 report in its own format.

changed.docx is read only. The script keeps its styles, cover, certificate,
header and footer, applies the condensed wording in final_content.py, fits
tables and figures to the A4 text width, puts the cover in its own section
with a dark page border (light borders on every other page), and rebuilds the
contents and the lists of figures and tables with page numbers read back from
a LibreOffice render.

  uv run --no-project --with python-docx --with pillow \
      python projectreport/build/finalize_report.py
"""
from __future__ import annotations

import copy
import re
import shutil
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from final_content import DELETE, REWRITE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'build' / 'out' / 'changed.docx'
WORK = ROOT / 'build' / 'out' / 'final'
TARGET = ROOT / 'SecuLayer_Project_Report.docx'
PDF = ROOT / 'SecuLayer_Project_Report.pdf'

A4_W, A4_H, MARGIN = 11906, 16838, 1440
TEXT_W = A4_W - 2 * MARGIN
EMU = 914400
MAX_W = TEXT_W / 1440
WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

FRONT_ENTRIES = ['Acknowledgement', 'Abstract', 'Abbreviations', 'List of Figures', 'List of Tables']
TOC, LOF, LOT, LISTS_BREAK = 59, 71, 74, 72
COVER_END, CERT_END, FRONT_END = 20, 38, 75
REFERENCES = range(559, 601)
APPENDIX_A = 601

# Column shares per table (element index in changed.docx).
TABLES = {
    68: [0.2, 0.8],
    113: [0.11, 0.42, 0.37, 0.10],
    127: [0.15, 0.19, 0.21, 0.27, 0.18],
    151: [0.08, 0.70, 0.22],
    155: [0.09, 0.16, 0.75],
    178: [0.17, 0.83],
    192: [0.17, 0.38, 0.17, 0.28],
    200: [0.2, 0.5, 0.15, 0.15],
    247: [0.37, 0.30, 0.20, 0.13],
    257: [0.14, 0.11, 0.57, 0.18],
    270: [0.32, 0.07, 0.61],
    276: [0.16, 0.24, 0.37, 0.23],
    281: [0.32, 0.36, 0.32],
    435: [0.16, 0.25, 0.07, 0.52],
    440: [0.22, 0.70, 0.08],
    456: [0.07, 0.29, 0.24, 0.32, 0.08],
    460: [0.24, 0.14, 0.40, 0.22],
    465: [0.42, 0.24, 0.34],
    472: [0.12, 0.15, 0.2, 0.15, 0.38],
    478: [0.1, 0.34, 0.09, 0.38, 0.09],
    483: [0.2, 0.32, 0.25, 0.23],
    490: [0.2, 0.22, 0.1, 0.48],
    513: [0.25, 0.22, 0.22, 0.31],
    517: [0.4, 0.2, 0.2, 0.2],
    524: [0.18, 0.14, 0.14, 0.16, 0.17, 0.21],
    604: [0.3, 0.7],
}
TABLE_PT = 9
# Representative test cases kept in Table 6.3 (old IDs); they are renumbered in order.
TEST_CASES = 456
# Rows dropped by the text of their first cell, and single cells rewritten: (table, row, column).
DROP_ROWS = {151: ['FR-14'], 472: ['C', 'D'], 604: ['docs/PLAN.md, PROGRESS.md', 'projectreport/build/']}
CELLS = {(472, 1, 3): '2 × 3', (472, 2, 3): '2 × 3',
         (472, 1, 4): 'Measured: 2 featured attacks, 6 runs', (472, 2, 4): 'Measured: 2 featured attacks, 6 runs'}
KEEP_TCS = ['TC-01', 'TC-03', 'TC-04', 'TC-08', 'TC-09', 'TC-10', 'TC-11', 'TC-12', 'TC-13',
            'TC-14', 'TC-15', 'TC-17', 'TC-18', 'TC-19']

# Single figures: image paragraph -> height in inches (width capped at the text width).
FIGURES = {183: 3.2, 189: 2.6, 203: 2.3, 224: 2.8, 253: 2.6, 400: 2.05, 403: 2.05, 495: 2.4}
# Side-by-side figures: (image, caption, image, caption, max height in inches).
PAIRS = [(234, 235, 237, 238, 2.9), (240, 241, 244, 245, 2.6), (260, 261, 262, 263, 2.4), (394, 395, 397, 398, 2.1),
         (406, 407, 408, 409, 2.0), (505, 506, 510, 511, 2.4)]


def w(tag):
    return qn('w:' + tag)


RPR_ORDER = ['rStyle', 'rFonts', 'b', 'bCs', 'i', 'iCs', 'caps', 'smallCaps', 'strike', 'dstrike',
             'outline', 'shadow', 'emboss', 'imprint', 'noProof', 'snapToGrid', 'vanish', 'webHidden',
             'color', 'spacing', 'w', 'kern', 'position', 'sz', 'szCs', 'highlight', 'u', 'effect',
             'bdr', 'shd', 'fitText', 'vertAlign', 'rtl', 'cs', 'em', 'lang', 'eastAsianLayout']
PPR_ORDER = ['pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr', 'widowControl', 'numPr',
             'suppressLineNumbers', 'pBdr', 'shd', 'tabs', 'suppressAutoHyphens', 'kinsoku', 'wordWrap',
             'overflowPunct', 'topLinePunct', 'autoSpaceDE', 'autoSpaceDN', 'bidi', 'adjustRightInd',
             'snapToGrid', 'spacing', 'ind', 'contextualSpacing', 'mirrorIndents', 'suppressOverlap', 'jc',
             'textDirection', 'textAlignment', 'textboxTightWrap', 'outlineLvl', 'divId', 'cnfStyle',
             'rPr', 'sectPr', 'pPrChange']


def put(parent, tag, order, **attrs):
    """Set child w:<tag> with attrs, inserted in schema order."""
    el = parent.find(w(tag))
    if el is None:
        el = OxmlElement('w:' + tag)
        rank = order.index(tag)
        for i, child in enumerate(parent):
            name = child.tag.split('}')[1]
            if name in order and order.index(name) > rank:
                parent.insert(i, el)
                break
        else:
            parent.append(el)
    for k, v in attrs.items():
        el.set(w(k), str(v))
    return el


def rprop(rpr, tag, **attrs):
    return put(rpr, tag, RPR_ORDER, **attrs)


def pprop(ppr, tag, **attrs):
    return put(ppr, tag, PPR_ORDER, **attrs)


def ppr_of(p):
    ppr = p.find(w('pPr'))
    if ppr is None:
        ppr = OxmlElement('w:pPr')
        p.insert(0, ppr)
    return ppr


def text_of(el):
    return ''.join(t.text or '' for t in el.iter(w('t')))


def is_code(rpr):
    f = rpr.find(w('rFonts')) if rpr is not None else None
    return f is not None and 'Courier' in (f.get(w('ascii')) or '')


def is_bold(rpr):
    b = rpr.find(w('b')) if rpr is not None else None
    return b is not None and b.get(w('val')) not in ('0', 'false')


def tokens(markup):
    for part in re.split(r'(\*\*.+?\*\*|`.+?`)', markup):
        if not part:
            continue
        if part.startswith('**'):
            yield 'b', part[2:-2]
        elif part.startswith('`'):
            yield 'c', part[1:-1]
        else:
            yield 't', part


def run(rpr, text):
    r = OxmlElement('w:r')
    r.append(rpr)
    t = OxmlElement('w:t')
    t.set(XML_SPACE, 'preserve')
    t.text = text
    r.append(t)
    return r


def rewrite(p, markup):
    rprs = [r.find(w('rPr')) for r in p.findall(w('r'))]
    plain = [x for x in rprs if x is not None and not is_code(x) and not is_bold(x)]
    base = copy.deepcopy(plain[0] if plain else next((x for x in rprs if x is not None), OxmlElement('w:rPr')))
    rprop(base, 'b', val=0)
    rprop(base, 'bCs', val=0)
    sz = base.find(w('sz'))
    size = int(sz.get(w('val'))) if sz is not None else 24
    for child in list(p):
        if child.tag != w('pPr'):
            p.remove(child)
    for kind, text in tokens(markup):
        rpr = copy.deepcopy(base)
        if kind == 'b':
            rprop(rpr, 'b', val=1)
            rprop(rpr, 'bCs', val=1)
        elif kind == 'c':
            rprop(rpr, 'rFonts', ascii='Courier New', hAnsi='Courier New', cs='Courier New', eastAsia='Courier New')
            rprop(rpr, 'sz', val=size - 3)
            rprop(rpr, 'szCs', val=size - 3)
        p.append(run(rpr, text))


# ---------------------------------------------------------------- tables

def format_table(tbl, shares, pt):
    tblpr = tbl.find(w('tblPr'))
    tblpr.find(w('tblW')).set(w('w'), str(TEXT_W))
    widths = [round(TEXT_W * s) for s in shares]
    widths[-1] = TEXT_W - sum(widths[:-1])
    grid = tbl.find(w('tblGrid'))
    for child in list(grid):
        grid.remove(child)
    for wd in widths:
        col = OxmlElement('w:gridCol')
        col.set(w('w'), str(wd))
        grid.append(col)
    mar = tblpr.find(w('tblCellMar'))
    if mar is None:
        mar = OxmlElement('w:tblCellMar')
        look = tblpr.find(w('tblLook'))
        (look.addprevious(mar) if look is not None else tblpr.append(mar))
    for side in ('left', 'right'):
        el = mar.find(w(side))
        if el is None:
            el = OxmlElement('w:' + side)
            mar.append(el)
        el.set(w('w'), '72')
        el.set(w('type'), 'dxa')
    half = str(int(pt * 2))
    for tr in tbl.findall(w('tr')):
        for tc, wd in zip(tr.findall(w('tc')), widths):
            tcpr = tc.find(w('tcPr'))
            if tcpr is None:
                tcpr = OxmlElement('w:tcPr')
                tc.insert(0, tcpr)
            tcw = tcpr.find(w('tcW'))
            if tcw is None:
                tcw = OxmlElement('w:tcW')
                tcpr.insert(0, tcw)
            tcw.set(w('w'), str(wd))
            tcw.set(w('type'), 'dxa')
            for p in tc.findall(w('p')):
                pprop(ppr_of(p), 'spacing', before=10, after=10, line=240, lineRule='auto')
            for rpr in tc.iter(w('rPr')):
                rprop(rpr, 'sz', val=half)
                rprop(rpr, 'szCs', val=half)


# ---------------------------------------------------------------- figures

def extents(p):
    return p.find('.//{%s}extent' % WP), p.find('.//{%s}xfrm/{%s}ext' % (A, A))


def aspect(p):
    ext, _ = extents(p)
    return int(ext.get('cx')) / int(ext.get('cy'))


def size_image(p, height, max_w=MAX_W):
    ar = aspect(p)
    width = min(height * ar, max_w)
    height = width / ar
    for el in extents(p):
        el.set('cx', str(int(width * EMU)))
        el.set('cy', str(int(height * EMU)))


def no_borders():
    b = OxmlElement('w:tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement('w:' + side)
        e.set(w('val'), 'nil')
        b.append(e)
    return b


def pair(img1, cap1, img2, cap2, max_h):
    half = TEXT_W // 2
    cell_in = (half - 160) / 1440
    height = min(max_h, cell_in / aspect(img1), cell_in / aspect(img2))
    tbl = OxmlElement('w:tbl')
    pr = OxmlElement('w:tblPr')
    tw = OxmlElement('w:tblW')
    tw.set(w('w'), str(TEXT_W))
    tw.set(w('type'), 'dxa')
    jc = OxmlElement('w:jc')
    jc.set(w('val'), 'center')
    layout = OxmlElement('w:tblLayout')
    layout.set(w('type'), 'fixed')
    for child in (tw, jc, no_borders(), layout):
        pr.append(child)
    tbl.append(pr)
    grid = OxmlElement('w:tblGrid')
    for _ in range(2):
        col = OxmlElement('w:gridCol')
        col.set(w('w'), str(half))
        grid.append(col)
    tbl.append(grid)
    tr = OxmlElement('w:tr')
    trpr = OxmlElement('w:trPr')
    trpr.append(OxmlElement('w:cantSplit'))
    tr.append(trpr)
    img1.addprevious(tbl)
    for img, cap in ((img1, cap1), (img2, cap2)):
        size_image(img, height, cell_in)
        tc = OxmlElement('w:tc')
        tcpr = OxmlElement('w:tcPr')
        tcw = OxmlElement('w:tcW')
        tcw.set(w('w'), str(half))
        tcw.set(w('type'), 'dxa')
        tcpr.append(tcw)
        va = OxmlElement('w:vAlign')
        va.set(w('val'), 'bottom')
        tcpr.append(va)
        tc.append(tcpr)
        tc.append(img)
        pprop(ppr_of(cap), 'spacing', before=60, after=120, line=240, lineRule='auto')
        tc.append(cap)
        tr.append(tc)
    tbl.append(tr)


# ---------------------------------------------------------------- sections

def border(color, sz, style='single'):
    b = OxmlElement('w:pgBorders')
    b.set(w('offsetFrom'), 'page')
    for side in ('top', 'left', 'bottom', 'right'):
        e = OxmlElement('w:' + side)
        e.set(w('val'), style)
        e.set(w('sz'), str(sz))
        e.set(w('space'), '24')
        e.set(w('color'), color)
        b.append(e)
    return b


def sect(refs, fmt, start=None, dark=False):
    s = OxmlElement('w:sectPr')
    for kind, rid in refs:
        ref = OxmlElement('w:%sReference' % kind)
        ref.set(w('type'), 'default')
        ref.set(qn('r:id'), rid)
        s.append(ref)
    t = OxmlElement('w:type')
    t.set(w('val'), 'nextPage')
    s.append(t)
    sz = OxmlElement('w:pgSz')
    sz.set(w('w'), str(A4_W))
    sz.set(w('h'), str(A4_H))
    s.append(sz)
    mar = OxmlElement('w:pgMar')
    for k, v in (('top', MARGIN), ('right', MARGIN), ('bottom', MARGIN), ('left', MARGIN),
                 ('header', 720), ('footer', 720), ('gutter', 0)):
        mar.set(w(k), str(v))
    s.append(mar)
    s.append(border('000000', 24, 'thinThickSmallGap') if dark else border('8C8C8C', 8))
    num = OxmlElement('w:pgNumType')
    num.set(w('fmt'), fmt)
    if start is not None:
        num.set(w('start'), str(start))
    s.append(num)
    return s


def set_sect(p, sectpr):
    ppr = ppr_of(p)
    old = ppr.find(w('sectPr'))
    if old is not None:
        ppr.remove(old)
    pprop(ppr, 'sectPr')
    ppr.replace(ppr.find(w('sectPr')), sectpr)


# ---------------------------------------------------------------- contents and lists

def entry(template, text, page, level):
    p = copy.deepcopy(template)
    ppr = ppr_of(p)
    for child in list(p):
        if child.tag != w('pPr'):
            p.remove(child)
    tabs = pprop(ppr, 'tabs')
    for t in list(tabs):
        tabs.remove(t)
    tab = OxmlElement('w:tab')
    tab.set(w('val'), 'right')
    tab.set(w('leader'), 'dot')
    tab.set(w('pos'), str(TEXT_W))
    tabs.append(tab)
    if level == 0:
        pprop(ppr, 'spacing', before=70, after=10, line=240, lineRule='auto')
        pprop(ppr, 'ind', left=0, right=0, firstLine=0)
    elif level == 1:
        pprop(ppr, 'spacing', before=0, after=10, line=240, lineRule='auto')
        pprop(ppr, 'ind', left=400, right=0, firstLine=0)
    else:
        pprop(ppr, 'spacing', before=0, after=6, line=240, lineRule='auto')
        pprop(ppr, 'ind', left=1050, right=500, hanging=1050)
    rpr = copy.deepcopy(ppr.find(w('rPr'))) if ppr.find(w('rPr')) is not None else OxmlElement('w:rPr')
    bold = level == 0
    rprop(rpr, 'b', val=int(bold))
    rprop(rpr, 'bCs', val=int(bold))
    rprop(rpr, 'sz', val=21 if level < 2 else 20)
    rprop(rpr, 'szCs', val=21 if level < 2 else 20)
    r = run(rpr, text)
    r.append(OxmlElement('w:tab'))
    t = OxmlElement('w:t')
    t.text = page
    r.append(t)
    p.append(r)
    return p


def short_caption(text):
    label, _, rest = text.partition(': ')
    first = re.split(r'(?<=[a-z0-9\)])\. ', rest)[0].rstrip('.')
    first = re.sub(r' \(.*\)$', '', first) if len(first) > 80 else first
    return f'{label}: {first}'


def replace_list(sdt, paragraphs):
    for p in paragraphs:
        sdt.addprevious(p)
    sdt.getparent().remove(sdt)


# ---------------------------------------------------------------- build

def build(pages):
    doc = Document(SOURCE)
    body = doc.element.body
    els = list(body.iterchildren())
    keep = {i: el for i, el in enumerate(els)}

    for i, markup in REWRITE.items():
        assert els[i].tag == w('p'), i
        rewrite(els[i], markup)

    toc_tpl = copy.deepcopy(els[TOC].find('.//' + w('p')))
    list_tpl = copy.deepcopy(els[LOF].find('.//' + w('p')))

    for i, shares in TABLES.items():
        assert els[i].tag == w('tbl'), i
        format_table(els[i], shares, 10.5 if i == 68 else TABLE_PT)
    for i, height in FIGURES.items():
        size_image(els[i], height)
    for a, b, c, d, h in PAIRS:
        pair(els[a], els[b], els[c], els[d], h)

    for i in REFERENCES:
        p = els[i]
        pprop(ppr_of(p), 'spacing', before=0, after=20, line=240, lineRule='auto')
        for rpr in p.iter(w('rPr')):
            rprop(rpr, 'sz', val=19)
            rprop(rpr, 'szCs', val=19)

    tc_rows = els[TEST_CASES].findall(w('tr'))
    kept = 0
    for tr in tc_rows[1:]:
        first = tr.find(w('tc'))
        if text_of(first) in KEEP_TCS:
            kept += 1
            ts = list(first.iter(w('t')))
            ts[0].text = 'TC-%02d' % kept
            for t in ts[1:]:
                t.text = ''
        else:
            els[TEST_CASES].remove(tr)
    assert kept == len(KEEP_TCS)

    for (ti, ri, ci), value in CELLS.items():
        tc = els[ti].findall(w('tr'))[ri].findall(w('tc'))[ci]
        ts = list(tc.iter(w('t')))
        ts[0].text = value
        for extra in ts[1:]:
            extra.text = ''
    for ti, firsts in DROP_ROWS.items():
        for tr in els[ti].findall(w('tr')):
            if text_of(tr.find(w('tc'))) in firsts:
                els[ti].remove(tr)

    # Appendix A follows the references on the same page.
    pprop(ppr_of(els[APPENDIX_A]), 'pageBreakBefore', val=0)
    pprop(ppr_of(els[APPENDIX_A]), 'spacing', before=200)

    # LoF and LoT share one page.
    for br in els[LISTS_BREAK].iter(w('br')):
        br.getparent().remove(br)
    pprop(ppr_of(els[LISTS_BREAK]), 'spacing', before=0, after=0, line=240, lineRule='auto')

    set_sect(els[COVER_END], sect([], 'lowerRoman', start=1, dark=True))
    set_sect(els[CERT_END], sect([('header', 'rId7'), ('footer', 'rId8')], 'lowerRoman'))
    set_sect(els[FRONT_END], sect([('header', 'rId7'), ('footer', 'rId8')], 'lowerRoman'))
    final = body.find(w('sectPr'))
    final.addprevious(sect([('header', 'rId31'), ('footer', 'rId32')], 'decimal', start=1))
    body.remove(final)

    for i in sorted(DELETE, reverse=True):
        el = keep[i]
        if el.getparent() is not None:
            el.getparent().remove(el)

    # Right tab stops set for the Letter text width move to the A4 text width.
    for tab in body.iter(w('tab')):
        if tab.get(w('pos')) and int(tab.get(w('pos'))) > TEXT_W:
            tab.set(w('pos'), str(TEXT_W))

    # An empty paragraph just before a chapter heading can spill onto a page of its own.
    kids = list(body.iterchildren())
    for prev, nxt in zip(kids, kids[1:]):
        nppr = nxt.find(w('pPr')) if nxt.tag == w('p') else None
        heading = nppr is not None and nppr.find(w('pStyle')) is not None and \
            nppr.find(w('pStyle')).get(w('val')) == 'Heading1'
        if heading and prev.tag == w('p') and not text_of(prev).strip() and \
                not list(prev.iter(w('drawing'))) and prev.find('.//' + w('sectPr')) is None:
            body.remove(prev)

    # Contents, list of figures and list of tables from the final document.
    toc, figs, tabs = [], [], []
    for p in body.iter(w('p')):
        if any(a.tag == w('sdt') for a in p.iterancestors()):
            continue
        ppr = p.find(w('pPr'))
        style = ppr.find(w('pStyle')).get(w('val')) if ppr is not None and ppr.find(w('pStyle')) is not None else ''
        text = text_of(p).strip()
        if style in ('Heading1', 'Heading2'):
            toc.append((text, int(style[-1]) - 1))
        elif re.match(r'Figure \d+\.\d+: ', text):
            figs.append(short_caption(text))
        elif re.match(r'Table [0-9A]+\.\d+: ', text):
            tabs.append(short_caption(text))
    toc = [(t, 0) for t in FRONT_ENTRIES] + toc
    replace_list(els[TOC], [entry(toc_tpl, t, pages.get(('h', t), '00'), lvl) for t, lvl in toc])
    replace_list(els[LOF], [entry(list_tpl, t, pages.get(('c', t.split(':')[0]), '00'), 2) for t in figs])
    replace_list(els[LOT], [entry(list_tpl, t, pages.get(('c', t.split(':')[0]), '00'), 2) for t in tabs])

    WORK.mkdir(parents=True, exist_ok=True)
    out = WORK / 'SecuLayer_Project_Report.docx'
    doc.save(out)
    return out, toc, figs, tabs


def render(docx):
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(docx.parent), str(docx)],
                   check=True, capture_output=True, timeout=600)
    return docx.with_suffix('.pdf')


def page_texts(pdf):
    n = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', str(pdf)], capture_output=True,
                                                         text=True).stdout).group(1))
    texts = []
    for i in range(1, n + 1):
        t = subprocess.run(['pdftotext', '-layout', '-f', str(i), '-l', str(i), str(pdf), '-'],
                           capture_output=True, text=True).stdout
        texts.append(t)
    return texts


def label(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[-1] if lines and re.fullmatch(r'[ivxlc]+|\d+', lines[-1]) else ''


def locate(pdf, toc, figs, tabs):
    texts = page_texts(pdf)
    labels = [label(t) for t in texts]
    pages = {}
    front_titles = {'Acknowledgement': 'Acknowledgement', 'Abstract': 'Abstract', 'Abbreviations': 'Abbreviations',
                    'List of Figures': 'List of Figures', 'List of Tables': 'List of Tables'}
    body_start = next(i for i, t in enumerate(texts) if re.search(r'^\s*Chapter 1: Introduction\s*$', t, re.M)
                      and labels[i] == '1')
    for title in front_titles:
        for i, t in enumerate(texts[:body_start]):
            if re.search(r'^\s*%s\s*$' % re.escape(title), t, re.M) and i >= 2:
                if title in ('Acknowledgement',) or not re.search(r'^\s*Contents\s*$', t, re.M):
                    pages[('h', title)] = labels[i]
                    break
    cursor = body_start
    for text, _ in toc[len(FRONT_ENTRIES):]:
        pat = re.compile(r'^\s*%s\s*$' % re.escape(text), re.M)
        for i in range(cursor, len(texts)):
            if pat.search(texts[i]):
                pages[('h', text)] = labels[i]
                cursor = i
                break
        else:
            print('heading not found:', text)
    for cap in figs + tabs:
        key = cap.split(':')[0]
        for i in range(body_start, len(texts)):
            if key + ':' in texts[i]:
                pages[('c', key)] = labels[i]
                break
        else:
            print('caption not found:', key)
    return pages, len(texts)


def main():
    out, toc, figs, tabs = build({})
    pdf = render(out)
    pages, n = locate(pdf, toc, figs, tabs)
    out, *_ = build(pages)
    pdf = render(out)
    pages2, n2 = locate(pdf, toc, figs, tabs)
    if pages2 != pages:
        print('page numbers moved after filling the lists:',
              {k: (pages.get(k), v) for k, v in pages2.items() if pages.get(k) != v})
    shutil.copyfile(out, TARGET)
    shutil.copyfile(pdf, PDF)
    print(f'{n2} pages -> {TARGET.name}, {PDF.name}')


if __name__ == '__main__':
    main()
