"""v5: merge v4 wording with the reference deck's slide structure (key message line, box flows, phase cards,
gantt, numbered references). Base = user's v2 deck → keeps 4:3, VDEC banner, title + underline.
Fonts: Latin Arial / East Asian MS PGothic."""
import re, sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

SRC, OUT = sys.argv[1], sys.argv[2]
NAVY = RGBColor(0x00, 0x0F, 0x65)
MID = RGBColor(0x33, 0x33, 0x99)
PALE = RGBColor(0xDA, 0xED, 0xEF)
BAR = RGBColor(0x8C, 0x96, 0xC9)
TEXT = RGBColor(0x33, 0x33, 0x33)
MUTED = RGBColor(0x66, 0x66, 0x66)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
EA = "MS PGothic"
L, R, W = 0.5, 9.5, 9.0

p = Presentation(SRC)
S = list(p.slides)


# ---------------------------------------------------------------- primitives
def font(run, size, bold=False, color=TEXT, italic=False):
    f = run.font
    f.name = "Arial"; f.size = Pt(size); f.bold = bold; f.italic = italic; f.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for e in rPr.findall(qn("a:ea")): rPr.remove(e)
    etree.SubElement(rPr, qn("a:ea")).set("typeface", EA)


def parts(text):
    return [(t, i % 2 == 1) for i, t in enumerate(re.split(r"\*\*", text)) if t]


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


def box(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.08):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.shadow.inherit = False
    if fill is None: sh.fill.background()
    else: sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb = line; sh.line.width = Pt(1)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE: sh.adjustments[0] = adj
    nostyle(sh)
    return sh


def nostyle(sh):
    st = sh._element.find(qn("p:style"))
    if st is not None: sh._element.remove(st)


def write(sh, paras, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, margin=(0.12, 0.08)):
    """paras: list of (text_with_**bold**, size, color, kind) ; kind: None | '◆' | 'base-bold'"""
    tf = sh.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margin[0]); tf.margin_top = tf.margin_bottom = Inches(margin[1])
    for k, item in enumerate(paras):
        text, size, color = item[0], item[1], item[2]
        kind = item[3] if len(item) > 3 else None
        pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        pg.alignment = align; pg.line_spacing = 1.12
        if kind == "◆":
            bullet(pg, "◆", 0.28, 0.24, 70); pg.space_before = Pt(3)
        else:
            bullet(pg, None)
            if k: pg.space_before = Pt(2)
        allbold = kind == "B"
        for t, b in parts(text):
            r = pg.add_run(); r.text = t
            font(r, size, b or allbold, NAVY if (b and kind == "◆") else color)
    return sh


def text(slide, x, y, w, h, paras, **kw):
    sh = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    return write(sh, paras, **kw)


def arrow(slide, x, y, w=0.32, h=0.3, down=False):
    sh = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW if down else MSO_SHAPE.RIGHT_ARROW,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    sh.shadow.inherit = False; sh.fill.solid(); sh.fill.fore_color.rgb = MID; sh.line.fill.background(); nostyle(sh)


def key(slide, msg, y=1.12):
    """centered key message under the title (reference style)"""
    text(slide, L, y, W, 0.55, [(msg, 19, NAVY, "B")])


def clear(slide):
    for sh in list(slide.shapes):
        if sh.is_placeholder and "TITLE" in str(sh.placeholder_format.type):
            continue
        sh._element.getparent().remove(sh._element)


def title(slide, t):
    tf = slide.shapes.title.text_frame
    runs = tf.paragraphs[0].runs
    runs[0].text = t
    for r in runs[1:]: r.text = ""
    for r in tf.paragraphs[0].runs:
        rPr = r._r.get_or_add_rPr()
        for e in rPr.findall(qn("a:ea")): rPr.remove(e)
        etree.SubElement(rPr, qn("a:ea")).set("typeface", EA)


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


# ================================================================ 1 표지 (reference cover structure)
s = S[0]; clear(s)
t = s.shapes.title
t.text_frame.text = ""
write(t, [("GPS 사용 불가 환경에서 비전 보조 항법을 위한", 26, NAVY, "B"), ("다중센서 융합", 26, NAVY, "B")])
t.left, t.top, t.width, t.height = Inches(0.6), Inches(1.15), Inches(8.8), Inches(1.45)
text(s, 0.8, 2.65, 8.4, 0.45, [("측정 주기와 지연을 고려한 카메라·IMU·거리센서 융합 추정기", 17, MID, "B")])
sh = text(s, 0.8, 3.15, 8.4, 0.6, [("Multi-Sensor Fusion for Vision-Aided Navigation in GPS-Denied Environments", 13, MID)])
for r in sh.text_frame.paragraphs[0].runs: r.font.italic = True
text(s, 1.0, 4.35, 8.0, 1.75, [
    ("학생자율연구 II  연구계획 발표  |  2026학년도 2학기", 14, NAVY, "B"),
    ("박찬혁 (202121212)  ·  지도교수: 안창선 교수님", 14, TEXT),
    ("School of Mechanical Engineering", 13, TEXT),
    ("Pusan National University", 13, TEXT),
])
notes(s, "[10초]\n안녕하세요, 학생자율연구II 연구계획을 발표할 박찬혁입니다. 제 연구는 GPS를 쓰기 어려운 환경에서 카메라, IMU, 거리센서를 하나의 필터로 융합하되, 센서마다 다른 측정 시점까지 고려하는 위치·자세 추정기를 만드는 것입니다.")

# ================================================================ 2 연구 배경
s = S[2]; clear(s); title(s, "연구 배경")
key(s, "항법은 IMU로 예측하고, 외부 센서로 보정한다")
cols = [("차량", "터널에서 GPS가 끊겨도\n속도·회전 정보로\n위치를 이어서 계산", MID),
        ("드론", "실내에서 하향 카메라·\nIMU·거리센서로\n위치 유지", NAVY),
        ("항공기", "화성 헬리콥터 Ingenuity\n하향 카메라·IMU·레이저\n고도계를 EKF로 융합", MID)]
cw, gx = 2.5, 0.75
for i, (h, d, c) in enumerate(cols):
    x = L + i * (cw + gx)
    write(box(s, x, 1.85, cw, 0.62, fill=c), [(h, 18, WHITE, "B")])
    text(s, x, 2.52, cw, 1.0, [(ln, 13.5, TEXT) for ln in d.split("\n")])
    if i < 2: arrow(s, x + cw + 0.2, 2.01)
text(s, L, 3.55, W, 0.3, [("(Bayard et al., 2019)", 10.5, MUTED)], align=PP_ALIGN.RIGHT)
# Optical Flow → VIO
bw = 4.1
write(box(s, L, 3.95, bw, 1.25, fill=PALE), [
    ("Optical Flow  =  측정", 17, NAVY, "B"),
    ("연속 영상에서 점의 이동을 추적해", 14, TEXT), ("영상 속 움직임을 측정", 14, TEXT),
    ("(Lucas and Kanade, 1981)", 10.5, MUTED)])
arrow(s, L + bw + 0.24, 4.42, w=0.32)
write(box(s, R - bw, 3.95, bw, 1.25, fill=PALE), [
    ("VIO  =  추정", 17, NAVY, "B"),
    ("영상 측정을 IMU와 결합해", 14, TEXT), ("위치·자세를 추정", 14, TEXT),
    ("(Mourikis and Roumeliotis, 2007; Geneva et al., 2020)", 10.5, MUTED)])
write(box(s, L, 5.5, W, 0.85, fill=NAVY), [("플랫폼은 달라도  IMU 예측 + 카메라·거리센서 보정  구조는 같다", 17, WHITE, "B")])
notes(s, "[65초]\n자동차 내비게이션은 터널에 들어가 GPS가 끊겨도 화면 속 차량이 계속 움직입니다. 마지막 위치에서 속도와 회전 정보로 위치를 이어서 계산하기 때문입니다. 이처럼 항법은 관성 정보로 움직임을 예측하고, 다른 센서로 그 예측을 보정하는 구조입니다.\n"
         "(위 세 칸) 이 원리는 드론과 항공기에도 그대로 쓰입니다. 실내 드론은 하향 카메라와 IMU, 거리센서로 위치를 유지하고, NASA의 화성 헬리콥터 인저뉴어티도 같은 조합을 EKF로 융합해 비행했습니다.\n"
         "(아래 두 칸) 보정에 많이 쓰이는 센서가 카메라입니다. 옵티컬 플로우는 연속된 영상에서 점이 얼마나 움직였는지 추적하는 기법으로, 광마우스가 움직임을 읽는 것과 같은 원리입니다. VIO는 이 영상 정보를 IMU와 결합해 위치와 자세를 추정합니다. 옵티컬 플로우가 측정이라면, VIO는 그 측정을 쓰는 추정입니다.\n"
         "플랫폼은 달라도 IMU로 예측하고, 카메라와 거리센서로 보정한다는 구조는 같습니다.")

# ================================================================ 3 연구의 필요성 및 목적
s = S[3]; clear(s); title(s, "연구의 필요성 및 목적")
key(s, "실제 센서 융합에서는 두 가지 문제가 생긴다")
write(box(s, L, 1.8, W, 1.55, fill=PALE), [
    ("1.  개별 센서의 한계", 16, NAVY, "B"),
    ("IMU만 사용하면 적분 과정에서 **작은 오차가 시간에 따라 누적**됨", 14, TEXT, "◆"),
    ("카메라는 영상 속 이동만 측정 → **실제 이동 거리로 환산하려면 거리 정보가 필요**함", 14, TEXT, "◆"),
    ("→ IMU로 예측하고 카메라·거리센서로 보정하는 **센서 융합이 필요**", 14, TEXT, "◆"),
], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, margin=(0.2, 0.08))
write(box(s, L, 3.5, 6.15, 1.75, fill=PALE), [
    ("2.  센서별 측정 시점의 차이", 16, NAVY, "B"),
    ("IMU는 빠른 주기, 카메라는 느린 주기로 측정되고 **영상 처리에도 시간이 소요**됨", 14, TEXT, "◆"),
    ("필터에 도착한 영상 측정은 **도착 시점보다 이전의 움직임**을 나타냄", 14, TEXT, "◆"),
], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, margin=(0.2, 0.08))
write(box(s, L + 6.3, 3.5, W - 6.3, 1.75, fill=None, line=MID), [
    ("e.g. 5 m/s × 50 ms 지연", 12.5, TEXT),
    ("≈ 25 cm", 26, NAVY, "B"),
    ("위치 차이", 13, TEXT),
    ("(단순 계산 예시)", 10.5, MUTED)])
write(box(s, L, 5.45, W, 1.2, fill=NAVY), [
    ("연구 목적", 15, RGBColor(0xC8, 0xCE, 0xEA), "B"),
    ("측정 주기와 지연 차이를 고려하여 카메라·IMU·거리센서를", 16, WHITE, "B"),
    ("하나의 필터로 융합하는 위치·자세 추정기 구현", 16, WHITE, "B")])
notes(s, "[55초]\n그런데 이 구조를 실제 센서에 적용하면 두 가지 문제가 생깁니다.\n"
         "첫째는 개별 센서의 한계입니다. IMU만 쓰면 작은 오차가 적분되면서 계속 쌓입니다. 카메라는 영상 속 이동만 알려 주기 때문에, 실제 이동 거리로 바꾸려면 거리센서 정보가 필요합니다. 그래서 세 센서를 함께 써야 합니다.\n"
         "둘째는 측정 시점의 차이입니다. IMU는 매우 빠른 주기로 들어오지만 카메라는 그보다 느리고, 영상 처리에도 시간이 걸립니다. 그래서 지금 필터에 들어온 영상 측정은 사실 조금 전의 움직임입니다. (오른쪽 숫자) 예를 들어 초속 5 m로 움직일 때 50 ms 늦은 측정을 현재 값처럼 쓰면 25 cm의 차이가 생깁니다.\n"
         "그래서 제 연구의 목적은 측정 주기와 지연 차이를 고려해 카메라, IMU, 거리센서를 하나의 필터로 융합하는 위치·자세 추정기를 구현하는 것입니다.")

# ================================================================ 4 선행연구와 적용 방향
s = S[4]; clear(s); title(s, "선행연구와 적용 방향")
key(s, "차량 분야의 시간 처리 방법을 비전 항법에 적용한다")
fw = 3.9
write(box(s, L, 1.8, fw, 0.95, fill=PALE), [("차량 분야 (Kim and Ahn, 2025)", 15, NAVY, "B"),
                                          ("레이더·V2X 융합 · 선행 차량 상태 추정", 13, TEXT)])
arrow(s, L + fw + 0.39, 2.12, w=0.42, h=0.32)
write(box(s, R - fw, 1.8, fw, 0.95, fill=NAVY), [("본 연구", 15, WHITE, "B"),
                                              ("카메라·IMU·거리센서 융합 · 위치·자세 추정", 13, WHITE)])
text(s, L, 2.92, W, 0.35, [("참고할 시간 처리 방법", 15, MID, "B")])
cards = [("지연 보상", "수신 시점과 실제\n측정 시점을 구분"),
         ("시간 정렬", "함께 쓰는 신호의 시점을\n맞추고 필요 시 보간"),
         ("과거 상태 재추정", "지연된 측정으로 과거를\n보정한 후 현재까지 재추정")]
cw, gap = 2.9, 0.15
for i, (h, d) in enumerate(cards):
    x = L + i * (cw + gap)
    write(box(s, x, 3.32, cw, 1.3, fill=PALE),
          [(h, 16, NAVY, "B")] + [(ln, 13.5, TEXT) for ln in d.split("\n")])
write(box(s, L, 4.8, W, 0.85, fill=None, line=MID), [
    ("비전 항법 참고 구조:  MSCKF·OpenVINS는 **과거 카메라 자세를 상태에 유지**하며 추정", 14, TEXT),
    ("(Mourikis and Roumeliotis, 2007; Geneva et al., 2020)", 10.5, MUTED)])
write(box(s, L, 5.82, W, 0.83, fill=NAVY), [
    ("차량 모델이 아닌 시간 처리 방법을 센서 구성에 맞게 적용하고, 적용 전·후 차이를 확인", 15, WHITE, "B")])
notes(s, "[55초]\n이 시간 문제는 차량 분야에서도 중요하게 다뤄졌습니다. 지도교수님 연구실의 Kim과 Ahn의 논문은 레이더와 V2X 통신처럼 도착 시점이 서로 다른 정보를 융합해 앞 차량의 상태를 추정했습니다. 저는 이 논문에서 가운데 세 가지 처리 방법을 참고하겠습니다.\n"
         "첫째, 지연 보상입니다. 데이터를 받은 시점과 실제로 측정한 시점을 구분합니다. 둘째, 시간 정렬입니다. 함께 쓰는 신호의 시점을 맞추고, 필요하면 앞뒤 데이터로 그 사이 값을 보간합니다. 셋째, 과거 상태 재추정입니다. 늦게 들어온 측정으로 그 시점의 추정값을 고치고, 거기서부터 현재까지 다시 계산합니다.\n"
         "비전 항법 쪽에서는 과거 카메라 자세를 함께 유지하며 추정하는 MSCKF와 OpenVINS의 구조를 참고하겠습니다. 차량 모델을 그대로 가져오는 것이 아니라, 시간 처리 방법을 제 센서 구성에 맞게 옮기는 것이 핵심입니다.")

# ================================================================ 5 연구방법
s = S[5]; clear(s); title(s, "연구방법")
key(s, "EKF로 융합하고, 늦게 도착한 측정은 측정 시점에 반영한다")
ins = [("IMU", "가속도·각속도 → 예측"), ("카메라", "KLT로 영상 이동 추적"), ("거리센서", "지면까지 거리 → 실제 크기")]
iy, ih, ig = 1.82, 0.6, 0.1
for i, (h, d) in enumerate(ins):
    y = iy + i * (ih + ig)
    write(box(s, L, y, 3.25, ih, fill=PALE), [(f"**{h}**   {d}", 13.5, TEXT)], align=PP_ALIGN.LEFT)
    arrow(s, L + 3.33, y + 0.16, w=0.28, h=0.28)
eh = 3 * ih + 2 * ig
write(box(s, 4.15, iy, 2.2, eh, fill=MID), [("EKF", 22, WHITE, "B"), ("확장 칼만필터", 11, RGBColor(0xC8, 0xCE, 0xEA)), ("예측: IMU", 13.5, WHITE),
                                           ("보정: 영상 이동·거리", 13.5, WHITE), ("(자이로로 회전 성분 제거)", 10.5, RGBColor(0xC8, 0xCE, 0xEA))])
arrow(s, 6.43, iy + eh / 2 - 0.15, w=0.3, h=0.3)
write(box(s, 6.83, iy, R - 6.83, eh, fill=None, line=MID), [("위치·자세", 18, NAVY, "B"), ("추정값", 15, TEXT)])
text(s, L, 4.02, W, 0.35, [("시간 처리", 15, MID, "B")])
steps = [("①  확인", "센서별 주기·\n타임스탬프·지연"), ("②  저장", "과거 상태·IMU 입력·\n측정값 보관"),
         ("③  재추정", "늦은 측정은 측정 시점에서\n보정 후 현재까지 재추정")]
sw, sg = 2.65, 0.52
for i, (h, d) in enumerate(steps):
    x = L + i * (sw + sg)
    write(box(s, x, 4.4, sw, 1.05, fill=PALE if i < 2 else NAVY),
          [(h, 15, NAVY if i < 2 else WHITE, "B")] + [(ln, 12.5, TEXT if i < 2 else WHITE) for ln in d.split("\n")])
    if i < 2: arrow(s, x + sw + 0.1, 4.78, w=0.32, h=0.3)
write(box(s, L, 5.65, W, 1.0, fill=PALE), [
    ("검증 계획", 14, MID, "B"),
    ("같은 데이터·초기 조건에서 **시간 처리 적용 전·후** 비교  →  **위치·자세 오차**와 **처리시간** 분석", 14, TEXT)])
notes(s, "[65초]\n구체적인 방법입니다. (위쪽 그림) 영상의 이동은 KLT 옵티컬 플로우로 추적하고, 융합은 확장 칼만필터, 즉 EKF를 기본 구조로 사용합니다.\n"
         "예측 단계에서는 IMU의 가속도와 각속도로 다음 순간의 위치와 자세를 계산합니다. 보정 단계에서는 영상 이동과 거리 정보를 측정 모델로 넣어 예측을 바로잡습니다. 이때 영상 이동에는 회전 성분이 섞여 있어서, 자이로로 회전을 빼고 거리로 실제 크기를 정합니다.\n"
         "(아래 세 칸) 시간 처리는 이렇게 합니다. 먼저 센서별 주기와 타임스탬프, 지연을 확인합니다. 필터는 과거 일정 구간의 상태와 입력을 저장해 두고, 새 측정이 없을 때는 예측만 합니다. 늦게 도착한 측정이 오면 그 측정 시점으로 돌아가 보정하고, 저장해 둔 IMU 입력으로 현재까지 다시 계산합니다.\n"
         "검증은 같은 데이터와 초기 조건에서 시간 처리를 넣기 전과 후를 비교합니다. 기준값 대비 위치 오차와 재추정에 드는 처리시간을 함께 보고, 효과와 한계를 정리하겠습니다.")

# ================================================================ 6 연구계획 (gantt, reference style)
s = S[6]
old = next(sh for sh in s.shapes if sh.has_table)
plan = [[old.table.cell(i, j).text_frame.text.replace("\x0b", "\n") for j in range(3)] for i in range(1, 5)]
clear(s); title(s, "연구계획")
key(s, "10월 ~ 12월, 기본 융합 → 시간 처리 → 비교 검증")
gx0, gcw = 5.3, 1.05
for j, m in enumerate(["10월 전반", "10월 후반", "11월", "12월"]):
    text(s, gx0 + j * gcw, 1.72, gcw, 0.32, [(m, 12, NAVY, "B")])
rh = 0.88
for i, (when, what, res) in enumerate(plan):
    y = 2.08 + i * (rh + 0.06)
    if i % 2 == 0: box(s, L, y, W, rh, fill=PALE, shape=MSO_SHAPE.RECTANGLE)
    wl = [l for l in what.split("\n") if l.strip()]
    rl = " · ".join(l for l in res.split("\n") if l.strip())
    text(s, L + 0.05, y, 4.7, rh, [(wl[0], 14.5, NAVY, "B"), (" · ".join(wl[1:]), 12, TEXT), ("→ " + rl, 11, MUTED)],
         align=PP_ALIGN.LEFT)
    core = i == 2
    box(s, gx0 + i * gcw + 0.06, y + rh / 2 - 0.19, gcw - 0.12, 0.38, fill=NAVY if core else BAR, adj=0.3)
write(box(s, L, 5.95, W, 0.72, fill=NAVY), [("최종 목표:  시간 처리를 포함한 다중센서 융합 추정기 구현과 효과 검증", 16, WHITE, "B")])
notes(s, "[25초]\n일정입니다. 10월 전반에는 선행논문을 분석하고 센서의 주기와 타임스탬프, 지연을 정리합니다. 10월 후반에는 옵티컬 플로우와 IMU 예측으로 기본 융합 구조를 만듭니다. 이 연구의 핵심인 11월에는 지연 보상과 시간 정렬, 과거 상태 재추정을 넣고, 12월에 적용 전후를 비교해 보고서로 정리하겠습니다.")

# ================================================================ 7 참고문헌 / 감사합니다 (numbered cards)
s = S[7]; clear(s); title(s, "참고문헌")
refs = [
    "M. Kim and C. Ahn, “State Estimation of Preceding Target Vehicle Using Radar and V2X,” IEEE Access, vol. 13, pp. 198482–198495, 2025.",
    "A. I. Mourikis and S. I. Roumeliotis, “A Multi-State Constraint Kalman Filter for Vision-aided Inertial Navigation,” IEEE ICRA, pp. 3565–3572, 2007.",
    "P. Geneva et al., “OpenVINS: A Research Platform for Visual-Inertial Estimation,” IEEE ICRA, pp. 4666–4672, 2020.",
    "D. S. Bayard et al., “Vision-Based Navigation for the NASA Mars Helicopter,” AIAA SciTech Forum, 2019.",
    "B. D. Lucas and T. Kanade, “An Iterative Image Registration Technique with an Application to Stereo Vision,” IJCAI, 1981.",
]
ch, cg = 0.72, 0.09
for i, rtext in enumerate(refs):
    y = 1.15 + i * (ch + cg)
    write(box(s, L, y, 0.55, ch, fill=NAVY, shape=MSO_SHAPE.RECTANGLE), [(str(i + 1), 15, WHITE, "B")], margin=(0.02, 0.02))
    write(box(s, L + 0.62, y, W - 0.62, ch, fill=PALE, shape=MSO_SHAPE.RECTANGLE), [(rtext, 11, TEXT)],
          align=PP_ALIGN.LEFT, margin=(0.12, 0.05))
text(s, L, 5.45, W, 0.6, [("감사합니다", 24, NAVY, "B")])
text(s, L, 6.0, W, 0.4, [("연구계획에 대한 의견과 질문 부탁드립니다.", 14, TEXT)])
notes(s, "[15초]\n정리하면, 차량 분야에서 다뤄 온 시간 처리 방법을 카메라·IMU·거리센서 기반 비전 항법에 적용하고 그 효과를 확인하는 것이 이 연구입니다. 이상으로 발표를 마치겠습니다. 의견과 질문 부탁드립니다. 감사합니다.")

# ---------------------------------------------------------------- delete 목차
lst = p.slides._sldIdLst
sid = lst.findall(qn("p:sldId"))[1]
p.part.drop_rel(sid.get(qn("r:id"))); lst.remove(sid)
p.save(OUT)
print("saved", OUT)
