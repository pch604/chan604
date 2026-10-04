"""v10 (paper-summary wording, review fixes): one rule for every slide —
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
tbox(s, 0.8, 2.65, 8.4, 0.45, [("측정 주기와 지연을 고려한 카메라·IMU·거리센서 융합 추정기", 17, MID, True)])
sh = tbox(s, 0.8, 3.15, 8.4, 0.5, [("Multi-Sensor Fusion for Vision-Aided Navigation in GPS-Denied Environments", 13, MID, False)])
sh.text_frame.paragraphs[0].runs[0].font.italic = True
tbox(s, 1.0, 4.35, 8.0, 1.75, [("학생자율연구 II  연구계획 발표  |  2026학년도 2학기", 14, NAVY, True),
                               ("박찬혁 (202121212)  ·  지도교수: 안창선 교수님", 14, TEXT, False),
                               ("School of Mechanical Engineering", 13, TEXT, False), ("Pusan National University", 13, TEXT, False)])
notes(s, "[10초]\n안녕하세요, 학생자율연구II 연구계획을 발표할 박찬혁입니다. 제 연구는 GPS를 쓰기 어려운 환경에서 카메라, IMU, 거리센서를 하나의 필터로 융합하되, 센서마다 다른 측정 시점까지 고려하는 위치·자세 추정기를 만드는 것입니다.")

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


# ================================================================== 2 연구 배경
s = S[2]; clear(s); title(s, "연구 배경")
subhead2(s, "GPS가 없는 환경에서의 움직임 추정")
body2(s, L, 1.68, W, 4.3, [
    ("h", "GPS가 끊기는 구간의 항법"),
    ("b", "차량 항법은 GPS 수신이 끊기면 관성 정보로 위치를 이어서 계산하지만, 적분 과정에서 **오차가 시간에 따라 누적**된다. [1]"),
    ("b", "NASA 화성 헬리콥터 Ingenuity는 **하향 카메라·IMU·레이저 고도계**를 결합하여 GPS 없이 비행하였다. [2]"),
    ("h", "카메라와 관성센서를 이용한 움직임 추정"),
    ("b", "**IMU**(관성측정장치)는 가속도·각속도를 측정하여 움직임을 예측한다."),
    ("b", "**Optical Flow**는 연속 영상에서 화면이 움직인 양을 구하는 기법이며, KLT는 특징점을 추적하여 이를 계산한다. [3]"),
    ("b", "영상 이동은 픽셀 단위이므로, **거리센서로 지면까지의 거리를 알아야 실제 속도**로 환산된다. [4]"),
], base=14)
concl(s, 5.55, ["본 연구는 하향 카메라·IMU·거리센서로 드론의 **위치·속도·자세**를 추정한다.", "(수평 위치는 속도를 적분해 구하므로 오차가 누적될 수 있다)"])
notes(s, "[55초]\n자동차 내비게이션은 터널처럼 GPS가 끊기는 구간에서도 관성 정보로 위치를 이어서 계산합니다. 하지만 가속도를 적분하는 방식이라 시간이 지날수록 오차가 쌓입니다. 하늘에서도 같은 문제를 풀어야 하는데, NASA의 화성 헬리콥터 인저뉴어티는 아래를 보는 카메라, IMU, 레이저 고도계를 결합해 GPS 없이 비행했습니다.\n"
         "이런 방식의 핵심은 두 가지입니다. IMU는 가속도와 각속도로 움직임을 예측하고, 옵티컬 플로우는 연속된 영상에서 화면이 얼마나 움직였는지를 구합니다. 다만 영상 이동은 픽셀 단위라서, 거리센서로 지면까지의 거리를 알아야 실제 속도가 됩니다.\n"
         "그래서 본 연구는 이 세 센서로 드론의 위치, 속도, 자세를 추정합니다. 다만 수평 위치는 속도를 적분해 구하기 때문에 오차가 쌓일 수 있다는 한계도 함께 봅니다.")

# ================================================================== 3 필요성 및 목적
s = S[3]; clear(s); title(s, "연구의 필요성 및 목적")
subhead2(s, "센서 융합에서 측정 시점이 어긋나는 문제")
body2(s, L, 1.68, W, 4.2, [
    ("h", "센서 융합의 필요성"),
    ("b", "IMU만 쓰면 오차가 누적되고, 카메라만으로는 실제 이동 거리를 알 수 없으므로 **세 센서를 함께 융합**해야 한다. [1, 4]"),
    ("h", "기존 융합의 한계: 측정 시점의 차이"),
    ("b", "센서마다 **측정 주기가 다르다**: IMU 200 Hz, 카메라 20 Hz, 거리센서 30 Hz [5]"),
    ("b", "영상은 처리 시간만큼 늦게 도착하므로, 도착한 값을 그대로 쓰면 **이전 시점의 움직임을 현재로 잘못 반영**한다."),
    ("b", "카메라와 IMU의 시간이 어긋나면 **추정 정확도가 저하**된다. [6]"),
], base=14)
concl(s, 5.05, ["연구 목적", "측정 주기와 지연이 다른 카메라·IMU·거리센서를 **하나의 EKF**로 융합하고, 시간 처리의 효과를 정량적으로 확인한다."], h=0.85)
notes(s, "[55초]\n세 센서를 함께 쓰는 이유는 각자 한계가 있기 때문입니다. IMU만 쓰면 오차가 쌓이고, 카메라만으로는 실제로 몇 미터 움직였는지 알 수 없습니다.\n"
         "그런데 이 센서들을 융합할 때 문제가 생깁니다. 제가 사용할 공개 드론 데이터에서 IMU는 1초에 200번, 카메라는 20번, 거리센서는 30번 측정합니다. 게다가 영상은 처리하는 데 시간이 걸려서, 지금 도착한 영상 측정은 사실 조금 전의 움직임입니다. 이것을 현재 값처럼 쓰면 과거의 움직임을 현재로 잘못 반영하게 되고, 카메라와 IMU의 시간이 어긋나면 추정 정확도가 떨어진다고 보고되어 있습니다.\n"
         "그래서 연구 목적은 이 세 센서를 하나의 EKF, 즉 IMU로 예측하고 측정값으로 고쳐 나가는 추정 필터로 융합하고, 시간 처리를 했을 때 오차가 얼마나 줄어드는지 정량적으로 확인하는 것입니다.")

# ================================================================== 4 선행연구
s = S[4]; clear(s); title(s, "선행연구와 적용 방향")
subhead2(s, "기존 지연 처리 방식과 본 연구의 위치")
body2(s, L, 1.68, W, 4.3, [
    ("h", "차량 분야: Kim & Ahn (2025) [7]"),
    ("b", "도착 시점이 다른 레이더·V2X 정보를 **지연 보상 → 시간 정렬 → 과거 상태 재추정** 순서로 처리하여 선행 차량의 상태를 추정하였다."),
    ("h", "드론 분야: 두 가지 지연 처리 방식"),
    ("b", "**PX4 EKF2**: 최대 지연만큼 늦은 시점에서 융합하고, 현재 상태는 **출력 예측기**로 따로 계산한다. [4]"),
    ("b", "**MSF-EKF**: 늦은 측정이 오면 과거 상태로 돌아가 보정한 뒤 현재까지 다시 계산한다. [8]"),
    ("h", "본 연구의 적용 범위"),
    ("b", "새 필터 구조를 제안하기보다, 차량 분야의 시간 처리 절차를 카메라·IMU·거리센서 구성에 구현하고 **지연 크기별 효과를 비교**한다."),
], base=14)
concl(s, 5.2, ["기여: 시간 처리 방식별 정확도와 처리시간을 같은 데이터에서 정량 비교"])
notes(s, "[45초]\n시간 처리 절차는 지도교수님 연구실의 Kim과 Ahn의 논문을 참고합니다. 레이더와 V2X처럼 도착 시점이 다른 정보를 지연 보상, 시간 정렬, 과거 상태 재추정 순서로 처리했습니다.\n"
         "드론 분야에는 두 가지 방식이 있습니다. PX4는 필터 자체를 조금 늦은 시점에서 돌리고 현재 값은 따로 예측하고, MSF-EKF는 늦은 측정이 오면 과거로 돌아가 다시 계산합니다.\n"
         "저는 새 필터를 제안하기보다 이 시간 처리 절차를 제 센서 구성에 구현하고, 방식별 정확도와 처리시간을 같은 데이터에서 비교하는 것을 기여로 둡니다.")

# ================================================================== 5 연구방법 (text top · figure bottom)
s = S[5]; clear(s); title(s, "연구방법")
subhead2(s, "KLT Optical Flow와 EKF 기반 다중센서 융합")
body2(s, L, 1.62, W, 2.2, [
    ("b", "**상태**: 위치·속도·자세, IMU 바이어스"),
    ("b", "**예측**: IMU 가속도·각속도  /  **보정**: 영상 이동(회전 성분 제거)과 거리(기울기 보정한 고도)"),
    ("b", "**늦은 측정**: 저장해 둔 이력에서 측정 시점의 상태를 꺼내 보정하고, 이후 IMU 입력으로 현재까지 다시 계산"),
], base=14)
fy = 3.55
fill_text(box(s, L, fy, 2.15, 0.62, fill=PALE), [("IMU", 13, NAVY, True), ("가속도·각속도", 10.5, TEXT, False)])
fill_text(box(s, L, fy + 0.82, 2.15, 0.62, fill=PALE), [("카메라 + 거리센서", 13, NAVY, True), ("영상 이동·거리", 10.5, TEXT, False)])
arrow(s, L + 2.15, fy + 0.31, 3.15, fy + 0.31); arrow(s, L + 2.15, fy + 1.13, 3.15, fy + 1.13)
fill_text(box(s, 3.15, fy - 0.05, 3.3, 1.54, fill=NAVY), [("EKF (확장 칼만필터)", 14, WHITE, True), ("IMU로 움직임 예측", 11.5, WHITE, False), ("영상·거리 측정으로 보정", 11.5, WHITE, False)])
arrow(s, 6.45, fy + 0.72, 6.95, fy + 0.72)
fill_text(box(s, 6.95, fy + 0.27, 2.55, 0.9, fill=PALE), [("위치·속도·자세", 13, NAVY, True), ("추정값", 10.5, TEXT, False)])
tbox(s, L, 5.33, W, 0.3, [("늦은 측정 처리 (과거 상태 재추정)", 12.5, NAVY, True)], align=PP_ALIGN.LEFT, m=(0, 0))
for k, (t_, f_, c_) in enumerate([("측정 시점의 상태로 복귀", PALE, NAVY), ("측정으로 보정", PALE, NAVY), ("현재까지 다시 계산", NAVY, WHITE)]):
    x = L + k * 3.1
    fill_text(box(s, x, 5.7, 2.75, 0.5, fill=f_), [(t_, 12, c_, True)])
    if k < 2: arrow(s, x + 2.75, 5.95, x + 3.1, 5.95)
tbox(s, L, 6.32, W, 0.28, [("저장: 상태·공분산·IMU 입력·측정 이력", 10.5, MUTED, False)], align=PP_ALIGN.LEFT, m=(0, 0))
notes(s, "[55초]\n방법입니다. 상태는 위치, 속도, 자세와 IMU 바이어스입니다. (위쪽 그림) IMU의 가속도와 각속도로 움직임을 예측하고, 영상 이동과 거리로 보정합니다. 영상 이동은 KLT로 구하는데, 기체가 기울기만 해도 영상이 움직이기 때문에 자이로로 회전 성분을 빼고, 추정한 고도를 이용해 실제 속도와 연결합니다. 거리센서는 기울기를 보정해 고도 측정으로 씁니다.\n"
         "(아래 흐름) 늦게 도착한 측정은 저장해 둔 이력에서 그 측정이 찍힌 시점의 상태를 꺼내 보정하고, 그 이후의 IMU 입력으로 현재까지 다시 계산합니다.")

# ================================================================== 6 구현 및 평가 (text only)
s = p.slides.add_slide(p.slide_layouts[1])
for ph in list(s.placeholders):
    if "TITLE" not in str(ph.placeholder_format.type): ph._element.getparent().remove(ph._element)
s.shapes.title.text_frame.text = "구현 및 평가 계획"
for r in s.shapes.title.text_frame.paragraphs[0].runs:
    rPr = r._r.get_or_add_rPr(); etree.SubElement(rPr, qn("a:ea")).set("typeface", EA)
subhead2(s, "공개 드론 데이터에서 지연을 재현하여 비교")
body2(s, L, 1.68, W, 4.9, [
    ("h", "데이터"),
    ("b", "**INSANE** 실내 구간: 하향 카메라 20 Hz, 거리센서 30 Hz, IMU / 정답: **모션캡처 궤적** [5]"),
    ("b", "카메라 측정에 **도착 시점 = 촬영 시점 + 실측 처리시간 + 추가 지연**을 부여하고, **도착 순서대로 재생**하여 실시간 상황을 재현"),
    ("h", "구현"),
    ("b", "**Python·OpenCV**: KLT 영상 이동과 처리시간  /  **MATLAB**: EKF·시간 처리·평가"),
    ("h", "비교 및 평가"),
    ("b", "추가 지연 0·25·50·100 ms에서 세 방식을 비교"),
    ("b2", "**A. 지연 무시**: 도착한 측정을 현재 값으로 바로 보정"),
    ("b2", "**B. 지연 시점 융합**: PX4 EKF2 방식"),
    ("b2", "**C. 과거 상태 재추정**: 본 연구에서 구현할 방식"),
    ("b", "지표: **ATE**(위치+yaw 정렬 후 위치 오차), **RE**(구간별 상대 오차), **처리시간** [9]"),
    ("b", "가설: B·C의 정확도는 비슷하고, C는 현재 상태 지연이 없는 대신 **연산이 늘어난다**"),
], base=14)
notes(s, "[50초]\n구현과 평가 계획입니다. 데이터는 공개 드론 데이터셋 INSANE의 실내 구간을 씁니다. 하향 카메라, 거리센서, IMU가 있고, 모션캡처로 측정한 정답 궤적이 있습니다. 카메라 측정마다 촬영 시점에 실제 처리시간과 추가 지연을 더해 도착 시점을 정하고, 데이터를 도착 순서대로 재생해서 실시간처럼 늦게 들어오는 상황을 재현합니다.\n"
         "영상 처리는 파이썬 OpenCV로, 필터와 시간 처리는 매트랩으로 구현합니다. 추가 지연을 0에서 100 ms까지 바꿔 가며, 지연을 무시한 경우, PX4처럼 지연 시점에서 융합한 경우, 과거 상태를 재추정한 경우를 정답 궤적 대비 위치 오차와 처리시간으로 비교하겠습니다. 예상은 B와 C의 정확도는 비슷하지만, C는 현재 상태가 늦지 않는 대신 계산량이 늘어난다는 것이고, 이 차이를 숫자로 확인하는 것이 목표입니다.")
lst = p.slides._sldIdLst
ids = lst.findall(qn("p:sldId")); new = ids[-1]; lst.remove(new); lst.insert(6, new)

# ================================================================== 7 연구계획 (table, as in user's revision)
s = S[6]; clear(s); title(s, "연구계획")
subhead2(s, "10월 ~ 12월 단계별 추진 계획")
rows = [("시기", ["수행 내용"], ["확인할 결과"]),
        ("10월 전반", ["선행논문 분석, INSANE 데이터 확보", "센서 주기·타임스탬프·지연 정리"], ["시간 처리 절차 정리", "센서 데이터 특성 파악"]),
        ("10월 후반", ["KLT 영상 이동 추적, IMU 예측 구현", "지연 없는 기본 EKF 구성"], ["센서별 처리 결과", "기본 추정기 동작(기준 결과)"]),
        ("11월", ["버퍼·시간 정렬 구현", "과거 상태 재추정 적용"], ["시간 처리를 포함한", "다중센서 융합 추정기"]),
        ("12월", ["지연 크기별 A·B·C 비교", "추정 오차·처리시간 분석"], ["효과와 한계 정리", "최종 보고서 및 발표"])]
cw = [1.35, 4.25, 3.4]; rh = [0.42, 0.9, 0.9, 0.9, 0.9]
gt = s.shapes.add_table(len(rows), 3, Inches(L), Inches(1.75), Inches(W), Inches(sum(rh)))
tbl = gt.table; tblPr = tbl._tbl.tblPr
for a in ("firstRow", "bandRow"): tblPr.set(a, "0")
sid_ = tblPr.find(qn("a:tableStyleId"))
if sid_ is not None: tblPr.remove(sid_)
for c, wv in zip(tbl.columns, cw): c.width = Inches(wv)
for i, (when, what, res) in enumerate(rows):
    tbl.rows[i].height = Inches(rh[i]); hdr = i == 0
    for j, val in enumerate([[when], what, res]):
        cell = tbl.cell(i, j); cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.1); cell.margin_top = cell.margin_bottom = Inches(0.03)
        tf = cell.text_frame
        for k, t_ in enumerate(val):
            pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph(); pg.alignment = PP_ALIGN.LEFT
            r = pg.add_run(); r.text = t_
            if hdr: font(r, 12.5, True, NAVY)
            elif j == 0: font(r, 13, True, BLACK)
            else: font(r, 13 if k == 0 and j == 1 else 12, k == 0 and j == 1, BLACK if (k == 0 and j == 1) else TEXT)
        tcPr = cell._tc.get_or_add_tcPr()
        for side, wpt, col in (("lnL", 0, None), ("lnR", 0, None),
                               ("lnT", 1.5 if hdr else 0, "000F65" if hdr else None),
                               ("lnB", 1.0 if hdr or i == len(rows) - 1 else 0.5, "000F65" if hdr or i == len(rows) - 1 else "BFBFBF")):
            ln = etree.SubElement(tcPr, qn("a:" + side)); ln.set("w", str(int(Pt(wpt))))
            if wpt == 0: etree.SubElement(ln, qn("a:noFill"))
            else:
                sf = etree.SubElement(ln, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", col)
        sf = etree.SubElement(tcPr, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", "E8ECF5" if hdr else ("F3F8F9" if i == 3 else "FFFFFF"))
concl(s, 6.0, ["최종 목표: 시간 처리를 포함한 다중센서 융합 추정기 구현과 그 효과의 정량 검증"])
notes(s, "[30초]\n일정입니다. 10월 전반에는 선행논문과 INSANE 데이터를 확보해 센서 주기와 타임스탬프를 정리하고, 10월 후반에는 영상 이동 추적과 IMU 예측으로 지연이 없는 기본 EKF를 만들어 기준 결과를 확보합니다. 핵심인 11월에는 버퍼와 시간 정렬, 과거 상태 재추정을 구현하고, 12월에 지연 크기별로 세 방식을 비교해 보고서로 정리하겠습니다.")

# ================================================================== 8 참고문헌 / 감사합니다
s = S[7]; clear(s); title(s, "참고문헌 / 감사합니다")
refs = [
    "P. D. Groves, Principles of GNSS, Inertial, and Multisensor Integrated Navigation Systems, 2nd ed., Artech House, 2013.",
    "D. S. Bayard et al., “Vision-Based Navigation for the NASA Mars Helicopter,” AIAA SciTech Forum, 2019.",
    "B. D. Lucas and T. Kanade, “An Iterative Image Registration Technique with an Application to Stereo Vision,” IJCAI, 1981.",
    "PX4 Autopilot User Guide, “Optical Flow” and “Using PX4's Navigation Filter (EKF2),” docs.px4.io, 2026. 10. 확인.",
    "C. Brommer et al., “The INSANE Dataset: Large Number of Sensors for Challenging UAV Flights in Mars Analog, Outdoor, and Out-/Indoor Transition Scenarios,” IJRR, vol. 43, no. 8, 2024.",
    "T. Qin and S. Shen, “Online Temporal Calibration for Monocular Visual-Inertial Systems,” IEEE/RSJ IROS, 2018.",
    "M. Kim and C. Ahn, “State Estimation of Preceding Target Vehicle Using Radar and V2X,” IEEE Access, vol. 13, pp. 198482–198495, 2025.",
    "S. Lynen et al., “A Robust and Modular Multi-Sensor Fusion Approach Applied to MAV Navigation,” IEEE/RSJ IROS, 2013.",
    "Z. Zhang and D. Scaramuzza, “A Tutorial on Quantitative Trajectory Evaluation for Visual(-Inertial) Odometry,” IEEE/RSJ IROS, 2018.",
]
tb = s.shapes.add_textbox(Inches(L), Inches(1.2), Inches(W), Inches(4.6))
tf = tb.text_frame; tf.word_wrap = True
for k, rt in enumerate(refs):
    pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
    bullet(pg, None, 0.42, 0.42); pg.space_before = Pt(0 if k == 0 else 6); pg.line_spacing = 1.05
    r = pg.add_run(); r.text = f"[{k + 1}]  "; font(r, 11.5, True, NAVY)
    r = pg.add_run(); r.text = rt; font(r, 11.5, False, TEXT)
tbox(s, L, 5.75, W, 0.45, [("감사합니다", 20, NAVY, True)], align=PP_ALIGN.LEFT, m=(0, 0))
tbox(s, L, 6.2, W, 0.35, [("연구계획에 대한 의견과 질문 부탁드립니다.", 13, TEXT, False)], align=PP_ALIGN.LEFT, m=(0, 0))
notes(s, "[15초]\n정리하면, 차량 분야의 시간 처리 절차를 카메라·IMU·거리센서 기반 드론 항법에 구현하고, 지연 처리 방식별 효과를 정량적으로 비교하는 것이 이 연구입니다. 이상으로 발표를 마치겠습니다. 의견과 질문 부탁드립니다. 감사합니다.")

# ------------------------------------------------------------------ delete 목차
lst = p.slides._sldIdLst
sid = lst.findall(qn("p:sldId"))[1]
p.part.drop_rel(sid.get(qn("r:id"))); lst.remove(sid)
p.save(OUT)
print("saved", OUT)
