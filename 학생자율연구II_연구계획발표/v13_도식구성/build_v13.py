"""v13: 13 slides, diagram-led (lab reference deck visual language), HWP content one rule for every slide —
   text-only slides  → subheading + ▣ section + ◆ bullets (bold key phrases, inline citations)
   slides with visual → text on one side, figure/table on the other (left/right or top/bottom)
   visuals are real (PX4 User Guide photos, CC BY 4.0) or grounded (dataset values, PX4 EKF2-style chain, Gantt).
Base = user's v2 deck → 4:3, VDEC banner, title + underline. Fonts: Latin Arial / East Asian MS PGothic."""
import os, re, sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

SRC, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
NAVY = RGBColor(0x00, 0x0F, 0x65); MID = RGBColor(0x33, 0x33, 0x99); PALE = RGBColor(0xDA, 0xED, 0xEF)
BAR = RGBColor(0x8C, 0x96, 0xC9); TEXT = RGBColor(0x33, 0x33, 0x33); BLACK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x66, 0x66, 0x66); WHITE = RGBColor(0xFF, 0xFF, 0xFF); LINEC = RGBColor(0xBF, 0xBF, 0xBF)
SOFT = RGBColor(0xC8, 0xCE, 0xEA)
EA = "MS PGothic"
L, R, W = 0.5, 9.5, 9.0

p = Presentation(SRC)
S = list(p.slides)


# ------------------------------------------------------------------ primitives
def font(run, size, bold=False, color=TEXT, italic=False):
    f = run.font
    f.name = "Arial"; f.size = Pt(size); f.bold = bold; f.italic = italic; f.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for e in rPr.findall(qn("a:ea")): rPr.remove(e)
    etree.SubElement(rPr, qn("a:ea")).set("typeface", EA)


def parts(t):
    return [(x, i % 2 == 1) for i, x in enumerate(re.split(r"\*\*", t)) if x]


def bullet(pg, char, marL=0.0, indent=0.0, pct=80):
    pPr = pg._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(marL)))); pPr.set("indent", str(int(Inches(-indent))))
    for tag in ("a:buNone", "a:buChar", "a:buFont", "a:buSzPct"):
        for e in pPr.findall(qn(tag)): pPr.remove(e)
    if char is None:
        etree.SubElement(pPr, qn("a:buNone")); return
    etree.SubElement(pPr, qn("a:buSzPct")).set("val", str(pct * 1000))
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", EA)
    etree.SubElement(pPr, qn("a:buChar")).set("char", char)


def nostyle(sh):
    st = sh._element.find(qn("p:style"))
    if st is not None: sh._element.remove(st)


def box(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, lw=1.0):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None: sh.fill.background()
    else: sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb = line; sh.line.width = Pt(lw)
    nostyle(sh)
    return sh


def fill_text(sh, paras, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, m=(0.08, 0.04)):
    """paras: [(text, size, color, bold)]"""
    tf = sh.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(m[0]); tf.margin_top = tf.margin_bottom = Inches(m[1])
    for k, (t, sz, c, b) in enumerate(paras):
        pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        pg.alignment = align; pg.line_spacing = 1.1; bullet(pg, None)
        r = pg.add_run(); r.text = t; font(r, sz, b, c)
    return sh


def tbox(slide, x, y, w, h, paras, **kw):
    return fill_text(slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)), paras, **kw)


def arrow(slide, x1, y1, x2, y2, color=MID, width=1.75):
    c = slide.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color; c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    t = etree.SubElement(ln, qn("a:tailEnd")); t.set("type", "triangle"); t.set("w", "med"); t.set("len", "med")
    return c


def body(slide, x, y, w, h, items, base=15):
    """items: (kind, text) — sub | sec | b | b2 | cite ; **bold** markup."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    for side in ("left", "right", "top", "bottom"): setattr(tf, "margin_" + side, Inches(0.02))
    for k, (kind, t) in enumerate(items):
        pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        pg.line_spacing = 1.15
        if kind == "sub":
            bullet(pg, None); pg.space_after = Pt(4)
            for x_, b in parts(t): r = pg.add_run(); r.text = x_; font(r, base + 4, True, BLACK)
        elif kind == "sec":
            bullet(pg, "▣", 0.3, 0.3, 90); pg.space_before = Pt(0 if k == 0 else 10); pg.space_after = Pt(2)
            for x_, b in parts(t): r = pg.add_run(); r.text = x_; font(r, base + 1, True, NAVY)
        elif kind == "b":
            bullet(pg, "◆", 0.62, 0.24, 75); pg.space_before = Pt(4)
            for x_, b in parts(t): r = pg.add_run(); r.text = x_; font(r, base, b, BLACK if b else TEXT)
        elif kind == "b2":
            bullet(pg, "–", 0.9, 0.18, 100); pg.space_before = Pt(1)
            for x_, b in parts(t): r = pg.add_run(); r.text = x_; font(r, base - 0.5, b, BLACK if b else TEXT)
        elif kind == "cite":   # citation on its own line under a bullet
            bullet(pg, None, 0.62, 0); pg.space_before = Pt(0)
            r = pg.add_run(); r.text = t; font(r, base - 4, False, MUTED)
    return tb


def subhead(slide, t):
    body(slide, L, 1.1, W, 0.5, [("sub", t)])


def table(slide, x, y, w, colw, rows, size=12.5, rowh=0.38):
    gt = slide.shapes.add_table(len(rows), len(colw), Inches(x), Inches(y), Inches(w), Inches(rowh * len(rows)))
    tbl = gt.table; tblPr = tbl._tbl.tblPr
    for a in ("firstRow", "bandRow"): tblPr.set(a, "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is not None: tblPr.remove(sid)
    for c, wv in zip(tbl.columns, colw): c.width = Inches(wv)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(rowh)
        for j, val in enumerate(row):
            cell = tbl.cell(i, j); hdr = i == 0
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.08); cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.03); cell.margin_bottom = Inches(0.03)
            pg = cell.text_frame.paragraphs[0]; pg.alignment = PP_ALIGN.CENTER
            r = pg.add_run(); r.text = val
            font(r, size, hdr or j == 0, NAVY if hdr else (BLACK if j == 0 else TEXT))
            tcPr = cell._tc.get_or_add_tcPr()
            for side, wpt, col in (("lnL", 0, None), ("lnR", 0, None),
                                   ("lnT", 1.5 if hdr else 0, "000F65" if hdr else None),
                                   ("lnB", 1.0 if hdr or i == len(rows) - 1 else 0.5, "000F65" if hdr or i == len(rows) - 1 else "BFBFBF")):
                ln = etree.SubElement(tcPr, qn("a:" + side)); ln.set("w", str(int(Pt(wpt))))
                if wpt == 0: etree.SubElement(ln, qn("a:noFill"))
                else:
                    sf = etree.SubElement(ln, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", col)
            if hdr:
                sf = etree.SubElement(tcPr, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", "E8ECF5")
            else:
                etree.SubElement(tcPr, qn("a:noFill"))
    return gt


def clear(slide):
    for sh in list(slide.shapes):
        if sh.is_placeholder and "TITLE" in str(sh.placeholder_format.type): continue
        sh._element.getparent().remove(sh._element)


def title(slide, t):
    tf = slide.shapes.title.text_frame
    tf.paragraphs[0].runs[0].text = t
    for r in tf.paragraphs[0].runs[1:]: r.text = ""
    for r in tf.paragraphs[0].runs:
        rPr = r._r.get_or_add_rPr()
        for e in rPr.findall(qn("a:ea")): rPr.remove(e)
        etree.SubElement(rPr, qn("a:ea")).set("typeface", EA)


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


def photo(slide, f, x, y, w):
    from PIL import Image
    im = Image.open(f); h = w * im.size[1] / im.size[0]
    slide.shapes.add_picture(f, Inches(x), Inches(y), Inches(w), Inches(h))
    return h


# ================================================================== 1 표지
s = S[0]; clear(s)
t = s.shapes.title; t.text_frame.text = ""
fill_text(t, [("GPS 사용 불가 환경에서 비전 보조 항법을 위한", 26, NAVY, True), ("다중센서 융합", 26, NAVY, True)])
t.left, t.top, t.width, t.height = Inches(0.6), Inches(1.15), Inches(8.8), Inches(1.45)
tbox(s, 0.8, 2.65, 8.4, 0.45, [("카메라·IMU 융합 기반 위치·속도·자세 추정과 영상 측정 품질 반영", 17, MID, True)])
sh = tbox(s, 0.8, 3.15, 8.4, 0.5, [("Multi-Sensor Fusion for Vision-Aided Navigation in GPS-Denied Environments", 13, MID, False)])
sh.text_frame.paragraphs[0].runs[0].font.italic = True
tbox(s, 1.0, 4.35, 8.0, 1.75, [("학생자율연구 II  연구계획 발표  |  2026학년도 2학기", 14, NAVY, True),
                               ("박찬혁 (202121212)  ·  지도교수: 안창선 교수님", 14, TEXT, False),
                               ("School of Mechanical Engineering", 13, TEXT, False), ("Pusan National University", 13, TEXT, False)])
notes(s, "[10초]\n안녕하세요, 학생자율연구II 연구계획을 발표할 박찬혁입니다. 제 연구는 GPS를 쓸 수 없는 환경에서 카메라와 IMU를 융합해 위치, 속도, 자세를 추정하고, 영상 품질이 나빠질 때에도 안정적으로 추정하는 방법을 다룹니다.")

# ------------------------------------------------------------------ user-edited style (from user's revised v8 PDF)
def body2(slide, x, y, w, h, items, base=14):
    """items: (kind, text) — h (bold section) | b (• bullet) | b2 (– sub) | gap ; **bold** markup."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    for side in ("left", "right", "top", "bottom"): setattr(tf, "margin_" + side, Inches(0.02))
    for k, (kind, t) in enumerate(items):
        pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        pg.line_spacing = 1.15
        if kind == "h":
            bullet(pg, None); pg.space_before = Pt(0 if k == 0 else 12); pg.space_after = Pt(2)
            for x_, b in parts(t): r = pg.add_run(); r.text = x_; font(r, base + 1.5, True, BLACK)
        elif kind == "b":
            bullet(pg, "•", 0.3, 0.18, 100); pg.space_before = Pt(4)
            for x_, b in parts(t): r = pg.add_run(); r.text = x_; font(r, base, b, BLACK if b else TEXT)
        elif kind == "b2":
            bullet(pg, "–", 0.55, 0.18, 100); pg.space_before = Pt(2)
            for x_, b in parts(t): r = pg.add_run(); r.text = x_; font(r, base - 0.5, b, BLACK if b else TEXT)
    return tb


def subhead2(slide, t):
    tb = slide.shapes.add_textbox(Inches(L), Inches(1.08), Inches(W), Inches(0.45))
    tf = tb.text_frame; tf.margin_left = Inches(0.02); tf.word_wrap = True
    tf.paragraphs[0].alignment = PP_ALIGN.LEFT
    r = tf.paragraphs[0].add_run(); r.text = t; font(r, 17, True, NAVY)


def concl(slide, y, lines, h=0.75):
    tb = slide.shapes.add_textbox(Inches(L), Inches(y), Inches(W), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.margin_left = Inches(0.02)
    for k, t in enumerate(lines):
        pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph(); pg.line_spacing = 1.15
        for x_, b in parts(t):
            r = pg.add_run(); r.text = x_; font(r, 14.5 if k == 0 and len(lines) > 1 and b else 14, True, NAVY if not b else BLACK)
    return tb


# ------------------------------------------------------------------ figure helpers (lecture style)
RED = RGBColor(0xC0, 0x00, 0x00)


def line(slide, x1, y1, x2, y2, color=TEXT, width=1.0, dash=None, head=False):
    c = slide.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color; c.line.width = Pt(width)
    if dash: c.line.dash_style = dash
    if head:
        ln = c.line._get_or_add_ln()
        t = etree.SubElement(ln, qn("a:tailEnd")); t.set("type", "triangle"); t.set("w", "sm"); t.set("len", "sm")
    return c


def label(slide, x, y, w, t, size=10.5, color=TEXT, bold=False, align=PP_ALIGN.LEFT, h=0.26):
    return tbox(slide, x, y, w, h, [(t, size, color, bold)], align=align, anchor=MSO_ANCHOR.MIDDLE, m=(0, 0))


def redbox(slide, x, y, w, h):
    return box(slide, x, y, w, h, fill=None, line=RED, lw=1.5)


def purpose(slide, y, runs, h=0.72):
    g = box(slide, L, y, W, h, fill=None, line=NAVY, lw=1.5)
    tf = g.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE; tf.margin_left = Inches(0.15); tf.margin_right = Inches(0.1)
    pg = tf.paragraphs[0]
    for t_, b_, c_ in runs:
        r = pg.add_run(); r.text = t_; font(r, 14, b_, c_)


def card(slide, x, y, w, head, sub, dark=False, h=0.62):
    f_, c_ = (NAVY, WHITE) if dark else (PALE, NAVY)
    fill_text(box(slide, x, y, w, h, fill=f_), [(head, 12, c_, True), (sub, 10.5, c_ if dark else TEXT, False)])


# ------------------------------------------------------------------ v13 helpers (lab deck visual language: key line, pale/navy blocks, block arrows)
def keyline(slide, t, y=1.08):
    tb = slide.shapes.add_textbox(Inches(L), Inches(y), Inches(W), Inches(0.45))
    tf = tb.text_frame; tf.word_wrap = True; tf.margin_left = tf.margin_right = Inches(0)
    pg = tf.paragraphs[0]; pg.alignment = PP_ALIGN.CENTER
    for x_, b in parts(t):
        r = pg.add_run(); r.text = x_; font(r, 17, True, NAVY if not b else RED)


def rb(slide, x, y, w, h, paras, fill=PALE, line_=None, lw=1.0, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, m=(0.1, 0.05)):
    sh = box(slide, x, y, w, h, fill=fill, line=line_, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=lw)
    sh.adjustments[0] = 0.08
    if paras: fill_text(sh, paras, align=align, anchor=anchor, m=m)
    return sh


def barrow(slide, x, y, w=0.38, h=0.32, color=MID, rot=0):
    sh = box(slide, x, y, w, h, fill=color, shape=MSO_SHAPE.RIGHT_ARROW if rot == 0 else MSO_SHAPE.DOWN_ARROW)
    return sh


def new_slide(t):
    s_ = p.slides.add_slide(p.slide_layouts[1])
    for ph in list(s_.placeholders):
        if "TITLE" not in str(ph.placeholder_format.type): ph._element.getparent().remove(ph._element)
    s_.shapes.title.text_frame.text = t
    for r in s_.shapes.title.text_frame.paragraphs[0].runs:
        rPr = r._r.get_or_add_rPr(); etree.SubElement(rPr, qn("a:ea")).set("typeface", EA)
    return s_


def T(t, sz=12, c=TEXT, b=False): return (t, sz, c, b)


# ================================================================== 2 목차
s = S[1]; clear(s); title(s, "목차")
toc = ["연구 배경 및 필요성", "연구 목적", "이론적 배경", "핵심 방법: 영상 측정 품질 반영", "시스템 구조 및 연구 방법", "검증 계획", "수행 일정 (15주)"]
for k, t_ in enumerate(toc):
    y = 1.45 + k * 0.7
    rb(s, 1.6, y, 0.55, 0.5, [T(str(k + 1), 17, WHITE, True)], fill=NAVY)
    label(s, 2.4, y + 0.02, 6.0, t_, 17, BLACK, True, h=0.46)
notes(s, "[10초]\n발표는 연구 배경과 필요성, 목적, 이론적 배경, 핵심 방법, 시스템 구조와 연구 방법, 검증 계획, 수행 일정 순서로 진행하겠습니다.")

# ================================================================== 3 연구 배경
s = S[2]; clear(s); title(s, "연구 배경")
keyline(s, "GPS를 쓸 수 없는 환경에서는 다른 센서로 위치·속도·자세를 추정해야 한다")
for k, (a_, b_) in enumerate([("실내", "건물 내부"), ("지하 공간", "터널·지하 시설"), ("구조물 내부", "대형 구조물 안")]):
    rb(s, L + k * 3.1, 1.75, 2.8, 0.72, [T(a_, 14, NAVY, True), T(b_, 12)])
barrow(s, L + W / 2 - 0.2, 2.55, 0.4, 0.32, rot=1)
rb(s, L, 2.95, W, 0.5, [T("위성 신호 차단 → GPS 사용 불가", 14, WHITE, True)], fill=NAVY)
rb(s, L, 3.7, 4.1, 1.9, [T("IMU 단독 관성항법", 14, NAVY, True), T("가속도·각속도를 적분하여 추정", 12),
                         T("잡음·바이어스가 적분되어", 12, RED, True), T("오차가 시간에 따라 누적 [1]", 12, RED, True)], fill=PALE)
barrow(s, L + 4.2, 4.45, 0.5, 0.4)
rb(s, L + 4.8, 3.7, 4.2, 1.9, [T("비전 보조 항법", 14, WHITE, True), T("카메라 영상의 움직임으로", 12, WHITE), T("IMU의 누적 오차를 보정 [2]", 12, WHITE),
                               T("예: NASA 화성 헬리콥터 Ingenuity", 12, SOFT), T("(하향 카메라 + IMU) [3]", 12, SOFT)], fill=MID)
rb(s, L, 5.85, W, 0.6, [T("본 연구: GPS 사용 불가 환경을 위한 카메라·IMU 다중센서 융합 기반 비전 보조 항법", 14, NAVY, True)], fill=PALE)
notes(s, "[35초]\n실내, 지하 공간, 구조물 내부처럼 위성 신호가 막히는 곳에서는 GPS를 쓸 수 없어서, 다른 센서로 위치와 속도, 자세를 추정해야 합니다.\n"
         "(왼쪽) 가장 기본은 IMU만 쓰는 관성항법인데, 가속도와 각속도를 적분하기 때문에 잡음과 바이어스가 쌓여 시간이 갈수록 오차가 커집니다. (오른쪽) 그래서 카메라 영상의 움직임으로 이 오차를 보정하는 비전 보조 항법을 씁니다. NASA의 화성 헬리콥터 인저뉴어티도 아래를 보는 카메라와 IMU로 비행했습니다.")

# ================================================================== 4 연구의 필요성
s = S[3]; clear(s); title(s, "연구의 필요성")
keyline(s, "카메라와 IMU는 서로의 약점을 보완한다")
for k, (nm, fillc, pro, con) in enumerate([
        ("IMU", NAVY, "높은 주기로 측정 → 끊김 없는 움직임 예측", "적분 오차 누적 → 장시간 사용 시 오차 증가"),
        ("카메라", MID, "주변 환경 관측 → 누적 오차 보정", "조명 변화·영상 흐림·특징점 부족, 깊이(거리 스케일) 불확실")]):
    x0 = L + k * 4.65
    rb(s, x0, 1.7, 4.35, 0.48, [T(nm, 14, WHITE, True)], fill=fillc)
    rb(s, x0, 2.25, 4.35, 0.62, [T("장점", 12, NAVY, True), T(pro, 12)], fill=PALE)
    rb(s, x0, 2.94, 4.35, 0.72, [T("한계", 12, RED, True), T(con, 12)], fill=WHITE, line_=LINEC, lw=0.75)
barrow(s, L + W / 2 - 0.2, 3.75, 0.4, 0.3, rot=1)
rb(s, L + 1.5, 4.1, W - 3.0, 0.5, [T("상호 보완 → 다중센서 융합", 14, WHITE, True)], fill=NAVY)
rb(s, L, 4.8, W, 0.78, [T("현실적 문제", 12, RED, True),
                        T("영상 품질이 떨어지는 구간에서도 영상 관측을 고정된 비중으로 반영하면, 추정의 정확성과 안정성이 떨어질 수 있다", 12)],
   fill=WHITE, line_=RED, lw=1.25)
rb(s, L, 5.75, W, 0.7, [T("해결 방향", 12, NAVY, True), T("영상 측정 품질을 평가하여 관측 반영 비중을 조절하는 다중센서 융합", 14, NAVY, True)], fill=PALE)
notes(s, "[40초]\n(위 두 칸) IMU는 높은 주기로 측정해 움직임을 끊김 없이 예측하지만 오차가 쌓이고, 카메라는 주변 환경을 보며 그 오차를 잡아 주지만 조명 변화, 흐림, 특징점 부족에 약하고 영상만으로는 실제 거리 스케일을 알기 어렵습니다. 그래서 둘을 융합합니다.\n"
         "(빨간 상자) 그런데 영상 품질이 나쁜 구간에서도 영상 관측을 항상 같은 비중으로 반영하면 오히려 추정이 흔들릴 수 있습니다. 그래서 영상 측정 품질을 평가해 반영 비중을 조절하는 융합이 필요합니다.")

# ================================================================== 5 연구 목적
s = S[4]; clear(s); title(s, "연구 목적")
keyline(s, "IMU 예측 + 영상 보정 + 영상 품질 반영")
blocks = [("IMU 예측", "운동 상태 예측", MID, "가속도·각속도로 이동체의 운동 상태를 연속적으로 예측"),
          ("영상 기반 보정", "옵티컬 플로우", NAVY, "KLT 옵티컬 플로우로 얻은 영상 움직임으로 누적 오차 보정"),
          ("영상 품질 반영", "신뢰도 기반 비중 조절", MID, "특징점 수·추적 성공률·잔차로 영상 신뢰도를 판단하여 보정 비중 조절")]
for k, (h_, s_, c_, d_) in enumerate(blocks):
    x0 = L + k * 3.2
    rb(s, x0, 1.85, 2.6, 1.15, [T(h_, 14, WHITE, True), T(s_, 12, SOFT)], fill=c_)
    tbox(s, x0, 3.12, 2.6, 1.0, [T(d_, 12, BLACK, True)], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, m=(0.02, 0))
    if k < 2: barrow(s, x0 + 2.68, 2.27, 0.44, 0.34)
rb(s, L, 4.45, W, 0.95, [T("연구 목적", 12, NAVY, True),
                         T("IMU 예측과 영상 보정을 결합한 filter 기반 상태추정을 구현하고,", 14, BLACK, True),
                         T("영상 측정 품질에 따른 추정 성능 변화를 분석한다", 14, BLACK, True)], fill=PALE)
rb(s, L, 5.6, W, 0.75, [T("최종 목표: GPS 사용 불가 환경에서 위치·속도·자세 추정의 정확성과 안정성 평가", 14, WHITE, True)], fill=NAVY)
notes(s, "[30초]\n연구 목적은 세 단계로 정리됩니다. IMU로 운동 상태를 예측하고, 옵티컬 플로우로 얻은 영상 움직임으로 누적 오차를 보정하며, 특징점 수와 추적 성공률, 잔차로 영상 신뢰도를 판단해 보정 비중을 조절합니다.\n"
         "즉, 필터 기반 상태추정을 구현하고 영상 품질에 따라 성능이 어떻게 달라지는지 분석해서, GPS 없이도 위치·속도·자세를 정확하고 안정적으로 추정할 수 있는지 평가하는 것이 목표입니다.")

# ================================================================== 6 이론적 배경 ① 상태추정 filter
s = S[5]; clear(s); title(s, "이론적 배경 ① 상태추정 filter")
keyline(s, "운동 모델로 예측하고, 센서 관측으로 보정한다")
rb(s, L, 1.95, 1.7, 0.75, [T("IMU", 14, NAVY, True), T("가속도·각속도 u", 10.5)], fill=PALE)
barrow(s, L + 1.78, 2.17, 0.4, 0.32)
rb(s, 2.75, 1.75, 2.75, 1.15, [T("예측 (Prediction)", 14, WHITE, True), T("x⁻ₖ = f(xₖ₋₁, uₖ)", 14, WHITE), T("공분산 P 증가", 10.5, SOFT)], fill=MID)
barrow(s, 5.58, 2.17, 0.4, 0.32)
rb(s, 6.05, 1.75, 3.45, 1.15, [T("보정 (Update)", 14, WHITE, True), T("xₖ = x⁻ₖ + Kₖ (zₖ − h(x⁻ₖ))", 14, WHITE), T("공분산 P 감소", 10.5, SOFT)], fill=NAVY)
rb(s, 6.6, 3.25, 2.35, 0.7, [T("카메라", 14, NAVY, True), T("영상 관측 z (움직임)", 10.5)], fill=PALE)
barrow(s, 7.62, 2.93, 0.32, 0.3, rot=1)
s.shapes[-1].rotation = 180
line(s, 6.3, 2.9, 6.3, 3.75, color=MID, width=1.5)
line(s, 6.3, 3.75, 4.1, 3.75, color=MID, width=1.5)
line(s, 4.1, 3.75, 4.1, 2.92, color=MID, width=1.5, head=True)
label(s, 4.1, 3.78, 2.2, "다음 시점 (k → k+1) 반복", 10.5, MID, True, align=PP_ALIGN.CENTER)
rb(s, L, 4.35, 4.35, 1.3, [T("상태 x", 14, NAVY, True), T("위치 · 속도 · 자세 (+ IMU 바이어스)", 12),
                           T("filter 구조는 데이터 특성에 맞춰 선정 (예: EKF)", 10.5, MUTED)], fill=PALE)
rb(s, L + 4.65, 4.35, 4.35, 1.3, [T("칼만 이득 K", 14, NAVY, True), T("관측 잡음 R이 클수록 K가 작아져", 12),
                                  T("관측 반영 비중이 줄어든다", 12, RED, True)], fill=WHITE, line_=RED, lw=1.25)
rb(s, L, 5.85, W, 0.6, [T("IMU로 예측 → 영상으로 보정: 비전 보조 항법의 기본 구조 [2]", 14, NAVY, True)], fill=PALE)
notes(s, "[35초]\n상태추정 필터는 두 단계를 반복합니다. (위 그림) IMU 입력으로 다음 상태를 예측하고, 카메라 관측으로 그 예측을 고칩니다. 예측하면 불확실성이 커지고, 보정하면 줄어듭니다.\n"
         "상태는 위치, 속도, 자세와 IMU 바이어스입니다. (오른쪽 빨간 상자) 중요한 점은 칼만 이득입니다. 관측 잡음 R을 크게 잡으면 이득이 작아져 그 관측을 덜 반영하게 됩니다. 이것이 뒤에서 설명할 영상 품질 반영의 원리입니다.")

# ================================================================== 7 이론적 배경 ② 옵티컬 플로우
s = S[6]; clear(s); title(s, "이론적 배경 ② 옵티컬 플로우")
keyline(s, "영상 이동에는 병진운동·회전운동·깊이가 함께 섞여 있다")
rb(s, L + 1.2, 1.75, W - 2.4, 0.8, [T("영상 이동  ≈  (f / h) · v   +   f · ω", 17, NAVY, True)], fill=WHITE, line_=NAVY, lw=1.25)
for k, (a_, b_) in enumerate([("병진운동 v ÷ 깊이 h", "실제 이동 속도 / 카메라 높이"), ("회전운동 ω", "기체 회전도 영상을 움직임")]):
    rb(s, L + 1.2 + k * 3.45, 2.7, 3.15, 0.65, [T(a_, 12, NAVY, True), T(b_, 10.5)], fill=PALE)
label(s, L, 3.38, W, "f: 초점거리, 하향 카메라·평면 지면 가정", 10.5, MUTED, align=PP_ALIGN.CENTER)
steps = [("연속 영상", "카메라", PALE, NAVY), ("특징점 추적", "KLT [4]", PALE, NAVY), ("회전 보상", "자이로 ω로 제거", PALE, NAVY),
         ("스케일 환산", "높이 h·평면 가정", PALE, NAVY), ("속도 관측 z", "filter 보정에 사용", NAVY, WHITE)]
for k, (a_, b_, f_, c_) in enumerate(steps):
    x0 = L + k * 1.86
    rb(s, x0, 3.95, 1.5, 0.95, [T(a_, 12, c_, True), T(b_, 10.5, c_ if f_ == NAVY else TEXT)], fill=f_)
    if k < 4: barrow(s, x0 + 1.53, 4.28, 0.3, 0.28)
rb(s, L, 5.2, W, 0.62, [T("함께 고려: 카메라 보정(내부 파라미터) · 센서 장착 위치와 방향 · 좌표계", 12, NAVY, True)], fill=PALE)
rb(s, L, 5.95, W, 0.5, [T("옵티컬 플로우를 이동체 운동과 연결하려면 회전 보상과 거리 스케일이 필수", 14, WHITE, True)], fill=NAVY)
notes(s, "[40초]\n(위 식) 아래를 보는 카메라에서 영상 속 이동은 대략 실제 이동 속도를 높이로 나눈 성분과 회전 성분의 합입니다. 즉, 기체가 제자리에서 기울기만 해도 영상은 움직이고, 같은 속도라도 높이에 따라 영상 이동이 달라집니다.\n"
         "(아래 흐름) 그래서 연속 영상에서 KLT로 특징점을 추적한 뒤, 자이로로 회전 성분을 빼고, 카메라 높이와 평면 가정으로 실제 크기로 바꿔서 속도 관측으로 필터에 넣습니다. 이때 카메라 보정값, 장착 위치와 방향, 좌표계도 함께 맞춰야 합니다.")

# ================================================================== 8 핵심: 영상 측정 품질 반영
s = S[7]; clear(s); title(s, "핵심 방법: 영상 측정 품질 반영")
keyline(s, "영상 신뢰도에 따라 관측 반영 비중을 조절한다")
label(s, L, 1.62, 2.6, "품질 지표", 12, NAVY, True, align=PP_ALIGN.CENTER)
for k, (a_, b_) in enumerate([("유효 특징점 수", "추적 가능한 점의 개수"), ("추적 성공률", "이전 프레임 대비 유지 비율"), ("운동 모델 잔차", "추정 운동과 맞지 않는 정도")]):
    rb(s, L, 1.95 + k * 0.92, 2.6, 0.78, [T(a_, 12, NAVY, True), T(b_, 10.5)], fill=PALE)
barrow(s, 3.2, 3.15, 0.45, 0.36)
rb(s, 3.75, 2.45, 2.0, 1.75, [T("영상 신뢰도", 14, WHITE, True), T("판단", 14, WHITE, True)], fill=NAVY)
outs = [("신뢰도 높음", "정상 보정", PALE, NAVY, None),
        ("신뢰도 낮음", "관측 잡음 R↑ → 보정 비중↓", MID, WHITE, None),
        ("유효 관측 없음", "보정 생략, IMU 예측 유지", WHITE, RED, RED)]
for k, (a_, b_, f_, c_, ln_) in enumerate(outs):
    y = 1.95 + k * 0.92
    line(s, 5.75, 3.32, 6.15, y + 0.39, color=MID, width=1.5, head=True)
    rb(s, 6.15, y, 3.35, 0.78, [T(a_, 12, c_, True), T(b_, 12, c_ if f_ != PALE else TEXT, f_ == MID)], fill=f_, line_=ln_, lw=1.25)
rb(s, L, 4.95, W, 0.68, [T("신뢰도 기준과 보정 규칙은 조정용 구간에서 결정하고, 별도의 평가 구간에 적용", 12, NAVY, True)], fill=PALE)
rb(s, L, 5.8, W, 0.62, [T("영상 품질이 나빠도 추정이 무너지지 않는 다중센서 융합", 14, WHITE, True)], fill=NAVY)
notes(s, "[40초]\n이 연구의 핵심입니다. (왼쪽) 영상 품질은 유효 특징점 수, 추적 성공률, 운동 모델 잔차 세 가지로 판단합니다.\n"
         "(오른쪽) 신뢰도가 높으면 평소처럼 보정하고, 낮으면 관측 잡음을 크게 잡아 보정 비중을 줄이며, 유효한 관측이 아예 없으면 보정을 건너뛰고 IMU 예측을 유지합니다. 이 기준은 조정용 구간에서 정하고, 결과는 별도의 평가 구간에서 확인합니다. 이렇게 해서 영상이 나빠지는 구간에서도 추정이 무너지지 않게 하는 것이 목표입니다.")

# ================================================================== 9 시스템 구조
s = new_slide("시스템 구조")
keyline(s, "GPS는 입력에서 제외하고, 기준 궤적은 검증에만 사용한다")
rb(s, L, 1.8, 1.55, 0.7, [T("IMU", 14, NAVY, True), T("가속도·각속도", 10.5)])
rb(s, L, 3.0, 1.55, 0.7, [T("카메라", 14, NAVY, True), T("연속 영상", 10.5)])
rb(s, 2.35, 3.0, 1.35, 0.7, [T("KLT", 12, NAVY, True), T("옵티컬 플로우", 10.5)])
rb(s, 4.0, 3.0, 1.55, 0.7, [T("품질 평가", 12, RED, True), T("신뢰도 판단", 10.5)], fill=WHITE, line_=RED, lw=1.25)
line(s, L + 1.55, 2.15, 5.85, 2.15, color=MID, width=1.75, head=True)
label(s, 2.2, 1.88, 2.0, "예측", 10.5, MID, True)
line(s, L + 1.55, 3.35, 2.35, 3.35, color=MID, width=1.75, head=True)
line(s, 3.7, 3.35, 4.0, 3.35, color=MID, width=1.75, head=True)
line(s, 5.55, 3.35, 5.85, 3.35, color=MID, width=1.75, head=True)
label(s, 4.0, 3.72, 2.0, "보정 비중 조절", 10.5, RED, True)
rb(s, 5.85, 1.8, 1.8, 1.9, [T("상태추정", 14, WHITE, True), T("filter", 14, WHITE, True), T("예측 + 보정", 10.5, SOFT)], fill=NAVY)
line(s, 7.65, 2.75, 7.95, 2.75, color=MID, width=1.75, head=True)
rb(s, 7.95, 2.3, 1.55, 0.9, [T("위치·속도·자세", 12, NAVY, True)])
rb(s, 7.95, 4.25, 1.55, 0.7, [T("성능 평가", 12, WHITE, True)], fill=MID)
line(s, 8.72, 3.2, 8.72, 4.25, color=MID, width=1.5, head=True)
rb(s, 5.85, 4.25, 1.8, 0.7, [T("기준 궤적", 12, MUTED, True), T("검증용", 10.5, MUTED)], fill=WHITE, line_=LINEC)
line(s, 7.65, 4.6, 7.95, 4.6, color=MUTED, width=1.25, dash=4, head=True)
rb(s, L, 4.25, 1.55, 0.7, [T("GPS", 12, MUTED, True), T("사용 안 함", 10.5, RED, True)], fill=WHITE, line_=RED, lw=1.0)
rb(s, L, 5.3, W, 1.1, [T("구현: MATLAB 기반 영상·IMU 처리", 14, NAVY, True),
                       T("센서별 측정 주기·시간 동기화·좌표계·카메라 보정을 확인한 뒤 융합 (연구실 시간 정합·지연 보상 절차 참고 [5, 6])", 12)], fill=PALE)
notes(s, "[30초]\n전체 구조입니다. IMU는 예측에, 카메라 영상은 KLT와 품질 평가를 거쳐 보정에 쓰이고, 품질에 따라 보정 비중이 조절됩니다. 필터는 위치, 속도, 자세를 출력합니다.\n"
         "GPS는 입력에서 완전히 빼고, 기준 궤적은 성능 평가에만 씁니다. 구현은 매트랩으로 하며, 센서 주기와 시간 동기화, 좌표계는 연구실의 시간 정합 절차를 참고해 맞춥니다.")

# ================================================================== 10 연구 방법 (Phase)
s = new_slide("연구 방법")
keyline(s, "연구계획서의 5단계 진행")
phases = [("데이터 구성 및 전처리", "센서별 측정 주기·시간 동기화·좌표계·카메라 보정 확인, 기준 궤적은 검증용으로 분리"),
          ("기준 추정기 구성", "MATLAB 기반 IMU 예측 + 옵티컬 플로우 보정, 잡음·바이어스·회전·거리 스케일 고려"),
          ("영상 품질 반영 융합", "품질 지표 구성 → 신뢰도 기준·보정 규칙 설정 (비중 축소 / 보정 생략)"),
          ("비교 실험 및 성능 평가", "이동 조건·영상 조건별로 세 방법 비교, 영상 흐림·프레임 누락 실험"),
          ("결과 분석 및 정리", "알고리즘 코드 · 비교 그래프 · 성능 평가표 · 최종 연구보고서")]
for k, (h_, d_) in enumerate(phases):
    y = 1.65 + k * 0.92
    core = k == 2
    rb(s, L, y, 1.45, 0.78, [T(f"Phase {k + 1}", 14, WHITE, True)], fill=RED if core else NAVY)
    rb(s, L + 1.6, y, W - 1.6, 0.78, [T(h_, 14, NAVY, True), T(d_, 12)], fill=PALE, line_=RED if core else None, lw=1.25, align=PP_ALIGN.LEFT, m=(0.18, 0.04))
notes(s, "[35초]\n연구는 다섯 단계로 진행합니다. 먼저 데이터를 구성하고 시간 동기화와 좌표계를 맞춥니다. 다음으로 IMU 예측과 옵티컬 플로우 보정을 결합한 기준 추정기를 만듭니다. 세 번째, 빨간색으로 표시한 핵심 단계에서 영상 품질 지표와 보정 규칙을 만듭니다. 네 번째로 조건별 비교 실험을 하고, 마지막으로 코드와 그래프, 평가표, 보고서로 정리합니다.")

# ================================================================== 11 검증 계획
s = new_slide("검증 계획")
keyline(s, "동일한 초기 조건과 데이터 구간에서 세 방법 비교")
for k, (a_, b_, dk) in enumerate([("IMU 단독", "비교 기준", False), ("고정 신뢰도 융합", "영상 보정 비중 고정", False), ("영상 신뢰도 반영 융합", "본 연구", True)]):
    rb(s, L + k * 3.1, 1.7, 2.8, 0.85, [T(a_, 14, WHITE if dk else NAVY, True), T(b_, 12, SOFT if dk else TEXT)], fill=NAVY if dk else PALE)
label(s, L, 2.75, W, "실험 조건", 14, NAVY, True, align=PP_ALIGN.CENTER, h=0.32)
for k, a_ in enumerate(["직선 주행", "선회", "정지·출발", "영상 품질 저하 구간"]):
    rb(s, L + k * 2.3, 3.12, 2.1, 0.55, [T(a_, 12, NAVY, True)])
rb(s, L, 3.75, W, 0.45, [T("추가: 영상 흐림 · 프레임 누락 부여 (원본 데이터 실험과 구분하여 기록)", 12, RED, True)], fill=WHITE, line_=RED, lw=1.0)
label(s, L, 4.38, W, "평가 지표", 14, NAVY, True, align=PP_ALIGN.CENTER, h=0.32)
for k, a_ in enumerate(["위치 RMSE", "최종 위치 오차", "영상 중단 시 오차 증가량"]):
    rb(s, L + k * 3.1, 4.75, 2.8, 0.55, [T(a_, 12, NAVY, True)])
for k, a_ in enumerate(["속도 RMSE (기준 속도 제공 시)", "처리시간 (구현 가능성)"]):
    rb(s, L + 1.55 + k * 3.1, 5.4, 2.8, 0.55, [T(a_, 12, NAVY, True)])
label(s, L, 6.08, W, "모든 방법에 동일한 시간 정합·좌표 정렬 기준 적용", 12, MUTED, True, align=PP_ALIGN.CENTER)
notes(s, "[35초]\n(위 세 칸) 세 방법을 같은 초기 조건과 같은 데이터 구간에서 비교합니다. IMU 단독, 보정 비중을 고정한 융합, 그리고 영상 신뢰도를 반영한 본 연구의 융합입니다.\n"
         "실험 조건은 직선 주행, 선회, 정지와 출발, 영상 품질이 떨어지는 구간으로 나누고, 영상을 흐리게 하거나 프레임을 빼는 실험도 따로 기록합니다. 평가는 위치 RMSE, 최종 위치 오차, 영상이 끊겼을 때 오차가 얼마나 늘어나는지를 중심으로, 속도 RMSE와 처리시간도 봅니다.")

# ================================================================== 12 수행 일정 (15주)
s = new_slide("수행 일정 (15주)")
gx0, nw = 4.05, 15
gw = (R - gx0) / nw
for j in range(nw):
    label(s, gx0 + j * gw, 1.2, gw, str(j + 1), 10.5, NAVY, True, align=PP_ALIGN.CENTER, h=0.25)
label(s, gx0 - 0.6, 1.2, 0.55, "주", 10.5, MUTED, align=PP_ALIGN.RIGHT, h=0.25)
plan = [("선행연구 분석·데이터 확보", "1~3주", 1, 3),
        ("데이터 전처리", "3~5주 · 동기화·좌표계·보정", 3, 5),
        ("기준 추정기 구성", "5~8주 · IMU 예측 + 플로우 보정", 5, 8),
        ("영상 품질 반영 융합", "9~11주 · 품질 지표·보정 규칙", 9, 11),
        ("비교 실험·성능 평가", "12~13주 · 조건별 비교", 12, 13),
        ("결과 분석·최종 보고", "14~15주 · 보고서·발표", 14, 15)]
rh_, y0_ = 0.72, 1.5
for i, (a_, b_, w0, w1) in enumerate(plan):
    y = y0_ + i * rh_
    if i % 2 == 0: box(s, L, y, W, rh_, fill=PALE)
    tbox(s, L + 0.1, y, gx0 - L - 0.15, rh_, [T(a_, 14, NAVY, True), T(b_, 10.5)], align=PP_ALIGN.LEFT, m=(0, 0))
    bar = box(s, gx0 + (w0 - 1) * gw + 0.03, y + rh_ / 2 - 0.13, (w1 - w0 + 1) * gw - 0.06, 0.26, fill=NAVY if i == 3 else BAR, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
for j in range(nw + 1):
    ln_ = line(s, gx0 + j * gw, 1.45, gx0 + j * gw, y0_ + len(plan) * rh_, color=LINEC, width=0.5)
mx = gx0 + 7.5 * gw
line(s, mx + gw / 2, 1.45, mx + gw / 2, y0_ + len(plan) * rh_, color=RED, width=1.25, dash=4)
label(s, mx + gw / 2 - 1.0, y0_ + len(plan) * rh_ + 0.03, 2.0, "8주 말: 중간 점검 (기준 결과)", 10.5, RED, True, align=PP_ALIGN.CENTER)
redbox(s, L - 0.04, y0_ + 3 * rh_ - 0.03, W + 0.08, rh_ + 0.06)
rb(s, L, 6.15, W, 0.42, [T("결과물: 알고리즘 코드 · 비교 그래프 · 성능 평가표 · 최종 연구보고서", 12, WHITE, True)], fill=NAVY)
notes(s, "[30초]\n일정은 15주입니다. 3주까지 선행연구와 데이터를 확보하고, 5주까지 전처리, 8주까지 기준 추정기를 만들어 중간 점검을 합니다. 핵심인 영상 품질 반영은 9주부터 11주, 비교 실험은 12, 13주, 마지막 두 주는 결과 정리와 보고서입니다.")

# ================================================================== 13 참고문헌 (numbered cards)
s = new_slide("참고문헌")
refs = [
    "P. D. Groves, Principles of GNSS, Inertial, and Multisensor Integrated Navigation Systems, 2nd ed., Artech House, 2013.",
    "A. I. Mourikis and S. I. Roumeliotis, “A Multi-State Constraint Kalman Filter for Vision-aided Inertial Navigation,” IEEE ICRA, pp. 3565–3572, 2007.",
    "D. S. Bayard et al., “Vision-Based Navigation for the NASA Mars Helicopter,” AIAA SciTech Forum, 2019.",
    "B. D. Lucas and T. Kanade, “An Iterative Image Registration Technique with an Application to Stereo Vision,” IJCAI, pp. 674–679, 1981.",
    "M. Kim, W. Kang, and C. Ahn, “Delay-Compensated Lane-Coordinate Vehicle State Estimation Using Low-Cost Sensors,” Sensors, vol. 25, no. 19, 6251, 2025.",
    "M. Kim and C. Ahn, “State Estimation of Preceding Target Vehicle Using Radar and V2X,” IEEE Access, vol. 13, 2025.",
]
for k, rt in enumerate(refs):
    y = 1.3 + k * 0.76
    rb(s, L, y, 0.55, 0.66, [T(str(k + 1), 14, WHITE, True)], fill=NAVY)
    rb(s, L + 0.65, y, W - 0.65, 0.66, [T(rt, 10.5)], fill=PALE, align=PP_ALIGN.LEFT, m=(0.12, 0.03))
tbox(s, L, 5.95, W, 0.5, [T("감사합니다", 17, NAVY, True)], align=PP_ALIGN.CENTER, m=(0, 0))
notes(s, "[10초]\n정리하면, GPS를 쓸 수 없는 환경에서 카메라와 IMU를 융합하고, 영상 품질에 따라 보정 비중을 조절해 위치·속도·자세를 안정적으로 추정하는 것이 이 연구입니다. 감사합니다.")

p.save(OUT)
print("saved", OUT)
