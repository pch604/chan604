"""v12: realigned to the official research plan (HWP) one rule for every slide —
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


# ================================================================== 2 연구 배경 (text)
s = S[2]; clear(s); title(s, "연구 배경")
subhead2(s, "GPS 사용 불가 환경의 항법")
body2(s, L, 1.6, W, 4.2, [
    ("h", "GPS를 쓸 수 없는 환경"),
    ("b", "실내·지하 공간·구조물 내부에서는 GPS를 쓸 수 없어, 이동체의 **위치·속도·자세를 다른 센서로 추정**해야 한다."),
    ("b", "**IMU**(관성측정장치)만 쓰면 잡음과 바이어스가 적분되어 **오차가 시간에 따라 누적**된다. [1]"),
    ("h", "비전 보조 항법 (Vision-Aided Navigation)"),
    ("b", "카메라 영상에서 얻은 움직임 정보로 **IMU의 누적 오차를 보정**하는 방식이다. [2]"),
    ("b", "예: NASA 화성 헬리콥터 Ingenuity는 **하향 카메라와 IMU**를 결합하여 위성항법 없이 비행하였다. [3]"),
], base=14)
concl(s, 5.55, ["본 연구는 카메라와 IMU를 융합하는 **비전 보조 항법 시스템**을 구성하고,", "GPS 사용 불가 환경에서 그 추정 성능을 평가한다."])
notes(s, "[45초]\n자동차 내비게이션은 터널에서 GPS가 끊기면 위치가 틀어지기 시작합니다. 실내나 지하 공간, 구조물 내부처럼 GPS를 아예 쓸 수 없는 곳에서는 다른 센서로 위치, 속도, 자세를 추정해야 합니다.\n"
         "가장 기본은 IMU, 즉 관성측정장치인데, 가속도와 각속도를 적분하는 방식이라 잡음과 바이어스가 쌓여 시간이 갈수록 오차가 커집니다. 그래서 카메라 영상의 움직임으로 이 오차를 보정하는 비전 보조 항법을 씁니다. NASA의 화성 헬리콥터 인저뉴어티도 아래를 보는 카메라와 IMU를 결합해 위성항법 없이 비행했습니다.\n"
         "본 연구는 이렇게 카메라와 IMU를 융합하는 비전 보조 항법 시스템을 구성하고, 그 성능을 평가합니다.")

# ================================================================== 3 필요성 및 목적 (IMU vs camera side by side · purpose)
s = S[3]; clear(s); title(s, "연구의 필요성 및 목적")
subhead2(s, "카메라와 IMU의 상호 보완적 특성")
cw2, gx = 4.35, 0.3
cols = [("IMU", "가속도·각속도 측정",
         [("장점", "높은 주기로 측정 → 연속적인 움직임 예측", NAVY)],
         [("한계", "적분 과정에서 잡음·바이어스 누적 → 오차 증가", RED)]),
        ("카메라", "주변 환경의 시각 정보",
         [("장점", "영상의 움직임으로 누적 오차 보정", NAVY)],
         [("한계", "조명 변화·영상 흐림·특징점 부족, 깊이(거리 스케일) 불확실", RED)])]
for k, (nm, sub_, pros, cons) in enumerate(cols):
    x0 = L + k * (cw2 + gx)
    card(s, x0, 1.62, cw2, nm, sub_)
    box(s, x0, 2.24, cw2, 1.55, fill=None, line=LINEC, lw=0.75)
    yy = 2.34
    for tag, txt, col in pros + cons:
        label(s, x0 + 0.15, yy, 0.6, tag, 12, col, True)
        tbox(s, x0 + 0.8, yy - 0.04, cw2 - 0.95, 0.62, [(txt, 12, TEXT, False)], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, m=(0, 0))
        yy += 0.7
arrow(s, L + cw2 / 2, 3.82, L + W / 2 - 0.6, 4.15); arrow(s, L + cw2 + gx + cw2 / 2, 3.82, L + W / 2 + 0.6, 4.15)
fill_text(box(s, L + W / 2 - 2.1, 4.15, 4.2, 0.5, fill=NAVY), [("상호 보완 → 다중센서 융합", 13, WHITE, True)])
g = redbox(s, L, 4.82, W, 0.55)
fill_text(g, [("문제: 영상 품질이 떨어지는 구간에서도 영상 측정을 같은 비중으로 반영하면 추정이 불안정해질 수 있다", 12, RED, True)], align=PP_ALIGN.LEFT)
purpose(s, 5.55, [("연구 목적   ", True, NAVY), ("IMU 예측과 영상 보정을 결합한 ", False, TEXT), ("filter 기반 상태추정", True, BLACK),
                  ("을 구현하고, ", False, TEXT), ("영상 측정 품질에 따른 성능 변화", True, BLACK), ("를 분석하여 위치·속도·자세 추정의 정확성과 안정성을 평가", False, TEXT)], h=0.85)
notes(s, "[55초]\n(위 두 칸) IMU와 카메라는 서로 보완적입니다. IMU는 높은 주기로 측정해서 움직임을 끊김 없이 예측할 수 있지만, 적분하면서 오차가 쌓입니다. 카메라는 주변 환경을 보기 때문에 이 누적 오차를 잡아 줄 수 있지만, 조명이 바뀌거나 영상이 흐려지거나 특징점이 부족하면 측정이 나빠지고, 영상만으로는 실제 거리 스케일도 알기 어렵습니다. 그래서 두 센서를 함께 융합합니다.\n"
         "(빨간 상자) 문제는 영상 품질이 떨어지는 구간에서도 영상 측정을 똑같은 비중으로 반영하면 추정이 오히려 불안정해질 수 있다는 점입니다.\n"
         "그래서 본 연구의 목적은 IMU 예측과 영상 보정을 결합한 필터 기반 상태추정을 구현하고, 영상 측정 품질에 따라 성능이 어떻게 변하는지 분석해서, 위치·속도·자세 추정의 정확성과 안정성을 평가하는 것입니다.")

# ================================================================== 4 이론적 배경 (text left · optical-flow figure right)
s = S[4]; clear(s); title(s, "이론적 배경")
subhead2(s, "상태추정 filter와 옵티컬 플로우")
body2(s, L, 1.6, 5.15, 4.9, [
    ("h", "상태추정 filter"),
    ("b", "운동 모델로 **예측**하고 센서 관측으로 **보정**하여 상태를 추정한다."),
    ("b", "IMU로 예측하고 영상 움직임으로 보정하는 구조가 비전 보조 항법의 기본이다. [2]"),
    ("h", "옵티컬 플로우"),
    ("b", "연속 영상에서 **특징점의 이동**을 추적한다 (KLT). [4]"),
    ("b", "영상 이동은 **병진운동·회전운동·깊이**의 영향을 받으므로, 카메라 보정, 장착 위치·방향, 좌표계, **거리 스케일**을 고려해야 한다."),
    ("h", "연구실 선행연구"),
    ("b", "저가 센서·레이더·V2X 융합 상태추정에서 **센서별 시간 정합과 지연 보상** 절차를 참고한다. [5, 6]"),
], base=13.5)
fx, fw = 5.95, R - 5.95
card(s, fx, 1.7, fw, "병진운동 ÷ 깊이", "이동 속도 / 카메라 높이")
card(s, fx, 2.5, fw, "회전운동", "기체의 각속도")
label(s, fx + fw / 2 - 0.2, 2.21, 0.4, "+", 14, NAVY, True, align=PP_ALIGN.CENTER, h=0.28)
arrow(s, fx + fw / 2, 3.14, fx + fw / 2, 3.5)
fill_text(box(s, fx, 3.5, fw, 0.62, fill=NAVY), [("영상 이동 (옵티컬 플로우)", 12, WHITE, True), ("KLT로 측정", 10.5, SOFT, False)])
box(s, fx, 4.3, fw, 1.25, fill=None, line=LINEC, lw=0.75)
tbox(s, fx + 0.12, 4.36, fw - 0.24, 1.15, [("움직임 정보로 쓰려면", 12, NAVY, True),
                                           ("• 회전 성분: 자이로로 제거", 10.5, TEXT, False),
                                           ("• 거리 스케일: 카메라 높이와", 10.5, TEXT, False),
                                           ("   평면 가정 활용 검토", 10.5, TEXT, False)], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, m=(0, 0))
notes(s, "[50초]\n상태추정 필터는 운동 모델로 다음 상태를 예측하고, 센서 관측으로 그 예측을 고쳐 나가는 방법입니다. 이 연구에서는 IMU로 예측하고 영상 움직임으로 보정합니다.\n"
         "영상 움직임은 옵티컬 플로우, 즉 연속된 영상에서 특징점이 얼마나 움직였는지로 구합니다. (오른쪽 그림) 그런데 영상 속 이동에는 실제 이동뿐 아니라 기체가 회전한 효과와 바닥까지의 거리 효과가 섞여 있습니다. 그래서 회전 성분은 자이로로 빼고, 실제 크기는 카메라 높이와 바닥이 평평하다는 가정으로 맞추는 방법을 검토합니다.\n"
         "또 지도교수님 연구실의 저가 센서, 레이더·V2X 융합 상태추정 연구에서 센서별 시간을 맞추고 지연을 보상하는 절차를 참고합니다.")

# ================================================================== 5 연구방법 (figure top · steps bottom)
s = S[5]; clear(s); title(s, "연구방법")
subhead2(s, "IMU 예측 + 영상 보정 + 영상 품질 반영")
ty0 = 1.65
card(s, L, ty0, 1.6, "IMU", "가속도·각속도")
card(s, L, ty0 + 1.0, 1.6, "카메라", "연속 영상")
arrow(s, L + 1.6, ty0 + 0.31, 6.0, ty0 + 0.31)
label(s, L + 1.7, ty0 + 0.02, 2.0, "예측", 10.5, NAVY, True)
card(s, 2.4, ty0 + 1.0, 1.55, "KLT", "옵티컬 플로우")
arrow(s, L + 1.6, ty0 + 1.31, 2.4, ty0 + 1.31)
fill_text(box(s, 4.2, ty0 + 0.88, 1.55, 0.86, fill=WHITE, line=RED, lw=1.25),
          [("품질 지표", 12, RED, True), ("특징점 수", 10.5, TEXT, False), ("추적 성공률 · 잔차", 10.5, TEXT, False)])
arrow(s, 3.95, ty0 + 1.31, 4.2, ty0 + 1.31)
arrow(s, 5.75, ty0 + 1.31, 6.0, ty0 + 1.31)
fill_text(box(s, 6.0, ty0, 1.75, 1.62, fill=NAVY), [("상태추정 filter", 12.5, WHITE, True), ("IMU로 예측", 10.5, WHITE, False), ("영상으로 보정", 10.5, WHITE, False), ("(보정 비중 조절)", 10.5, SOFT, False)])
arrow(s, 7.75, ty0 + 0.81, 8.0, ty0 + 0.81)
card(s, 8.0, ty0 + 0.5, 1.5, "위치·속도·자세", "추정값")
label(s, 3.7, ty0 + 1.86, 2.6, "본 연구의 핵심", 10.5, RED, True, align=PP_ALIGN.CENTER)
body2(s, L, 3.85, W, 2.9, [
    ("b", "**① 데이터 전처리**: 센서별 측정 주기·시간 동기화·좌표계·카메라 보정 확인. GPS는 입력에서 제외하고, 기준 궤적은 **검증용으로만** 사용"),
    ("b", "**② 기준 추정기**: MATLAB으로 IMU 예측 + 옵티컬 플로우 보정을 구성. 잡음·바이어스, 카메라 회전, 거리 스케일 고려"),
    ("b", "**③ 영상 품질 반영**: 신뢰도가 낮으면 **보정 비중을 줄이고**, 유효 관측이 없으면 **보정을 생략하고 IMU 예측 유지**. 기준은 조정용 구간에서 정하고 별도 평가 구간에 적용"),
], base=13.5)
notes(s, "[55초]\n(위 그림) 전체 구조입니다. IMU로 움직임을 예측하고, 카메라 영상에서 KLT로 옵티컬 플로우를 구해 보정합니다. 이 연구의 핵심은 빨간 상자입니다. 유효 특징점 수, 추적 성공률, 운동 모델 잔차로 영상 품질을 판단하고, 그에 따라 필터의 보정 비중을 조절합니다.\n"
         "(아래) 진행은 세 단계입니다. 먼저 센서별 주기, 시간 동기화, 좌표계, 카메라 보정을 확인합니다. GPS는 입력에서 빼고, 기준 궤적은 검증에만 씁니다. 다음으로 매트랩으로 IMU 예측과 옵티컬 플로우 보정을 결합한 기준 추정기를 만듭니다. 마지막으로 영상 신뢰도가 낮으면 보정 비중을 줄이고, 유효한 관측이 없으면 보정을 건너뛰고 IMU 예측을 유지합니다. 이 기준은 조정용 구간에서 정하고 별도 평가 구간에 적용합니다.")

# ================================================================== 6 실험 및 평가 (three cards · text)
s = p.slides.add_slide(p.slide_layouts[1])
for ph in list(s.placeholders):
    if "TITLE" not in str(ph.placeholder_format.type): ph._element.getparent().remove(ph._element)
s.shapes.title.text_frame.text = "실험 및 평가 계획"
for r in s.shapes.title.text_frame.paragraphs[0].runs:
    rPr = r._r.get_or_add_rPr(); etree.SubElement(rPr, qn("a:ea")).set("typeface", EA)
subhead2(s, "동일한 초기 조건과 데이터 구간에서 세 방법 비교")
cw_, gap = 2.85, 0.225
for k, (hd, sb, dk) in enumerate([("① IMU 단독", "비교 기준", False), ("② 고정 신뢰도 융합", "영상 보정 비중 고정", False), ("③ 영상 신뢰도 반영 융합", "품질에 따라 비중 조절", True)]):
    card(s, L + k * (cw_ + gap), 1.62, cw_, hd, sb, dark=dk)
redbox(s, L + 2 * (cw_ + gap) - 0.05, 1.57, cw_ + 0.1, 0.72)
label(s, L + 2 * (cw_ + gap), 2.3, cw_, "본 연구", 10.5, RED, True, align=PP_ALIGN.CENTER, h=0.22)
body2(s, L, 2.6, W, 4.1, [
    ("h", "실험 조건"),
    ("b", "**직선 주행·선회·정지/출발** 조건과 **영상 품질 저하 구간**을 구분하여 평가"),
    ("b", "추가로 **영상 흐림·프레임 누락**을 부여한 실험을 수행하고, 원본 데이터 실험과 구분하여 기록"),
    ("h", "평가 지표"),
    ("b", "기준 궤적 구간: **위치 RMSE, 최종 위치 오차, 영상 관측 중단 시 오차 증가량**"),
    ("b", "기준 속도가 있으면 **속도 RMSE**, 그리고 구현 가능성을 위한 **처리시간**"),
    ("b", "모든 방법에 **동일한 시간 정합·좌표 정렬 기준**을 적용"),
], base=13.5)
notes(s, "[45초]\n(위 세 칸) 실험은 세 방법을 같은 초기 조건과 같은 데이터 구간에서 비교합니다. IMU만 쓴 경우, 영상 보정 비중을 고정한 융합, 그리고 영상 신뢰도를 반영한 본 연구의 융합입니다.\n"
         "직선 주행, 선회, 정지와 출발 조건을 나누고, 영상 품질이 떨어지는 구간도 따로 봅니다. 또 영상을 일부러 흐리게 하거나 프레임을 빼는 실험을 추가하되, 원본 실험과 구분해서 기록합니다.\n"
         "평가는 기준 궤적과 비교한 위치 RMSE, 최종 위치 오차, 그리고 영상이 끊겼을 때 오차가 얼마나 늘어나는지로 하고, 기준 속도가 있으면 속도 RMSE와 처리시간도 봅니다.")
lst = p.slides._sldIdLst
ids = lst.findall(qn("p:sldId")); new = ids[-1]; lst.remove(new); lst.insert(6, new)

# ================================================================== 7 연구계획 (table)
s = S[6]; clear(s); title(s, "연구계획")
subhead2(s, "10월 ~ 12월 단계별 추진 계획")
rows = [("시기", ["수행 내용"], ["확인할 결과"]),
        ("10월 전반", ["① 데이터 구성 및 전처리", "측정 주기·시간 동기화·좌표계·카메라 보정"], ["센서 데이터 특성 파악", "기준 궤적 확보"]),
        ("10월 후반", ["② 기준 추정기 구성", "IMU 예측 + 옵티컬 플로우 보정"], ["IMU 단독·고정 신뢰도 결과", "(비교 기준)"]),
        ("11월", ["③ 영상 품질 반영 융합", "품질 지표·신뢰도 기준·보정 규칙"], ["영상 신뢰도 반영", "융합 추정기"]),
        ("12월", ["④ 조건별 비교 실험·평가", "⑤ 결과 분석 및 보고서"], ["성능 평가표·비교 그래프", "최종 보고서 및 발표"])]
cwt = [1.35, 4.25, 3.4]; rht = [0.42, 0.9, 0.9, 0.9, 0.9]
gt = s.shapes.add_table(len(rows), 3, Inches(L), Inches(1.75), Inches(W), Inches(sum(rht)))
tbl = gt.table; tblPr = tbl._tbl.tblPr
for a_ in ("firstRow", "bandRow"): tblPr.set(a_, "0")
sid_ = tblPr.find(qn("a:tableStyleId"))
if sid_ is not None: tblPr.remove(sid_)
for c, wv in zip(tbl.columns, cwt): c.width = Inches(wv)
for i, (when, what, res) in enumerate(rows):
    tbl.rows[i].height = Inches(rht[i]); hdr = i == 0
    for j, val in enumerate([[when], what, res]):
        cell = tbl.cell(i, j); cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.1); cell.margin_top = cell.margin_bottom = Inches(0.03)
        tf = cell.text_frame
        for k, t_ in enumerate(val):
            pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph(); pg.alignment = PP_ALIGN.LEFT
            r = pg.add_run(); r.text = t_
            if hdr: font(r, 12, True, NAVY)
            elif j == 0: font(r, 12, True, BLACK)
            else: font(r, 12, k == 0 and j == 1, BLACK if (k == 0 and j == 1) else TEXT)
        tcPr = cell._tc.get_or_add_tcPr()
        for side, wpt, col in (("lnL", 0, None), ("lnR", 0, None),
                               ("lnT", 1.5 if hdr else 0, "000F65" if hdr else None),
                               ("lnB", 1.0 if hdr or i == len(rows) - 1 else 0.5, "000F65" if hdr or i == len(rows) - 1 else "BFBFBF")):
            ln = etree.SubElement(tcPr, qn("a:" + side)); ln.set("w", str(int(Pt(wpt))))
            if wpt == 0: etree.SubElement(ln, qn("a:noFill"))
            else:
                sf = etree.SubElement(ln, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", col)
        sf = etree.SubElement(tcPr, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", "E8ECF5" if hdr else "FFFFFF")
redbox(s, L - 0.05, 1.75 + 0.42 + 1.8, W + 0.1, 0.9)
label(s, R - 1.3, 1.75 + 0.42 + 1.8 + 0.6, 1.25, "핵심 단계", 10.5, RED, True, align=PP_ALIGN.RIGHT)
concl(s, 6.0, ["최종 목표: 영상 신뢰도를 반영한 카메라·IMU 융합 추정기 구현과 성능 검증"])
notes(s, "[30초]\n일정입니다. 10월 전반에 데이터를 구성하고 전처리하며, 10월 후반에 IMU 단독과 고정 신뢰도 융합으로 비교 기준을 만듭니다. 핵심인 11월에는 영상 품질 지표와 신뢰도 기준, 보정 규칙을 만들고, 12월에 조건별 비교 실험과 결과 정리를 하겠습니다.")

# ================================================================== 8 참고문헌 / 감사합니다
s = S[7]; clear(s); title(s, "참고문헌 / 감사합니다")
refs = [
    "P. D. Groves, Principles of GNSS, Inertial, and Multisensor Integrated Navigation Systems, 2nd ed., Artech House, 2013.",
    "A. I. Mourikis and S. I. Roumeliotis, “A Multi-State Constraint Kalman Filter for Vision-aided Inertial Navigation,” IEEE ICRA, pp. 3565–3572, 2007.",
    "D. S. Bayard et al., “Vision-Based Navigation for the NASA Mars Helicopter,” AIAA SciTech Forum, 2019.",
    "B. D. Lucas and T. Kanade, “An Iterative Image Registration Technique with an Application to Stereo Vision,” IJCAI, pp. 674–679, 1981.",
    "M. Kim, W. Kang, and C. Ahn, “Delay-Compensated Lane-Coordinate Vehicle State Estimation Using Low-Cost Sensors,” Sensors, vol. 25, no. 19, 6251, 2025.",
    "M. Kim and C. Ahn, “State Estimation of Preceding Target Vehicle Using Radar and V2X,” IEEE Access, vol. 13, 2025.",
]
tb = s.shapes.add_textbox(Inches(L), Inches(1.25), Inches(W), Inches(4.3))
tf = tb.text_frame; tf.word_wrap = True
for k, rt in enumerate(refs):
    pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
    bullet(pg, None, 0.42, 0.42); pg.space_before = Pt(0 if k == 0 else 8); pg.line_spacing = 1.05
    r = pg.add_run(); r.text = f"[{k + 1}]  "; font(r, 12, True, NAVY)
    r = pg.add_run(); r.text = rt; font(r, 12, False, TEXT)
tbox(s, L, 5.6, W, 0.45, [("감사합니다", 20, NAVY, True)], align=PP_ALIGN.LEFT, m=(0, 0))
tbox(s, L, 6.08, W, 0.35, [("연구계획에 대한 의견과 질문 부탁드립니다.", 14, TEXT, False)], align=PP_ALIGN.LEFT, m=(0, 0))
notes(s, "[15초]\n정리하면, GPS를 쓸 수 없는 환경에서 카메라와 IMU를 융합하고, 영상 품질에 따라 영상 측정의 반영 비중을 조절해 위치·속도·자세 추정을 더 안정적으로 만드는 것이 이 연구입니다. 이상으로 발표를 마치겠습니다. 감사합니다.")

# ------------------------------------------------------------------ delete 목차
lst = p.slides._sldIdLst
sid = lst.findall(qn("p:sldId"))[1]
p.part.drop_rel(sid.get(qn("r:id"))); lst.remove(sid)
SCALE = {14.5: 14, 13.5: 14, 15: 15.5, 13: 12, 12.5: 12, 11.5: 12, 11: 10.5}
for sl in list(p.slides)[1:7]:
    for sh in sl.shapes:
        tfs = []
        if sh.has_text_frame and not sh.is_placeholder: tfs.append(sh.text_frame)
        if getattr(sh, "has_table", False) and sh.has_table:
            tfs += [c.text_frame for row in sh.table.rows for c in row.cells]
        for tf in tfs:
            for pg in tf.paragraphs:
                for r in pg.runs:
                    if r.font.size and r.font.size.pt in SCALE: r.font.size = Pt(SCALE[r.font.size.pt])
p.save(OUT)
print("saved", OUT)
