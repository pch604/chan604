// 학생자율연구II 연구계획 발표 — 16:9 재제작 (pptxgenjs)
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");
const path = require("path");

const A = (f) => path.join(__dirname, "assets", f);
const NOTES = require("./notes.json");
const OUT = process.argv[2] || path.join(__dirname, "deck_raw.pptx");

// ---------- palette ----------
const NAVY = "26357A", NAVY_D = "1B2559", BLUE = "3B5BA9", SKY = "7DB3E0",
  SKY_L = "DCEBF8", SKY_XL = "EEF5FC", GRAY_BG = "F3F6FB", LINE = "C9D3E3",
  TEXT = "2B2F36", MUTED = "5F6878", ORANGE = "E07B39", ORANGE_L = "FCEBDD", WHITE = "FFFFFF";

const SW = 13.333, ML = 0.6, MR = SW - 0.6;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "박찬혁";
pres.company = "부산대학교 기계공학부";
pres.title = "GPS 사용 불가 환경에서 비전 보조 항법을 위한 다중센서 융합";
pres.subject = "학생자율연구II 연구계획 발표";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };

// ---------- icons ----------
async function icon(name, color, px = 256) {
  const Comp = lu[name];
  if (!Comp) throw new Error("missing icon " + name);
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Comp, { color: "#" + color, size: px, strokeWidth: 2 })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ---------- layouts ----------
pres.defineSlideMaster({
  title: "COVER",
  background: { color: WHITE },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    { image: { x: 0, y: 0, w: SW, h: 0.95, path: A("titlebar.png") } },
    {
      placeholder: {
        options: { name: "title", type: "title", x: 1.42, y: 0.13, w: 8.4, h: 0.7, fontSize: 28, bold: true,
          color: WHITE, valign: "middle", align: "left", margin: 0 },
        text: "",
      },
    },
    {
      placeholder: {
        options: { name: "eng", type: "body", x: 9.0, y: 0.25, w: 3.73, h: 0.45, fontSize: 13, italic: true,
          color: "C3D8F2", valign: "middle", align: "right", margin: 0 },
        text: "",
      },
    },
  ],
  slideNumber: { x: 6.17, y: 7.08, w: 1.0, h: 0.28, fontSize: 10, color: NAVY, align: "center" },
});

// ---------- helpers ----------
function T(s, text, o) {
  return s.addText(text, Object.assign({ isTextBox: true, margin: 0, valign: "top", fontSize: 17, color: TEXT,
    lang: "ko-KR", paraSpaceAfter: 0 }, o));
}
function box(s, o) {
  const opt = Object.assign({ rectRadius: 0.08 }, o);
  return s.addShape(pres.shapes.ROUNDED_RECTANGLE, opt);
}
function rect(s, o) { return s.addShape(pres.shapes.RECTANGLE, o); }
function shadow() { return { type: "outer", blur: 8, offset: 2, angle: 90, color: "1B2559", opacity: 0.12 }; }
function arrow(s, x1, y1, x2, y2, color = NAVY, width = 2, dash) {
  const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(x2 - x1), 0.001),
    h: Math.max(Math.abs(y2 - y1), 0.001), line: { color, width, endArrowType: "triangle" } };
  if (dash) o.line.dashType = dash;
  if (x2 < x1) o.flipH = true;
  if (y2 < y1) o.flipV = true;
  return s.addShape(pres.shapes.LINE, o);
}
function line(s, x1, y1, x2, y2, color = LINE, width = 1, dash) {
  const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(x2 - x1), 0.001),
    h: Math.max(Math.abs(y2 - y1), 0.001), line: { color, width } };
  if (dash) o.line.dashType = dash;
  if (y2 < y1) o.flipV = true;
  return s.addShape(pres.shapes.LINE, o);
}
function header(s, num, title, eng) {
  s.addText(title, { placeholder: "title" });
  s.addText(eng, { placeholder: "eng" });
  s.addText(num, { shape: pres.shapes.ROUNDED_RECTANGLE, x: 0.6, y: 0.2, w: 0.66, h: 0.55, rectRadius: 0.08,
    fill: { color: SKY }, fontSize: 18, bold: true, color: NAVY_D, align: "center", valign: "middle", margin: 0 });
}
function lead(s, runs, o) {
  T(s, runs, Object.assign({ x: ML, y: 1.1, w: MR - ML, h: 0.5, fontSize: 20, bold: true, color: NAVY_D, valign: "middle" }, o));
}
function circleNum(s, x, y, d, txt, fill, color = WHITE, fs = 15, line) {
  const o = { shape: pres.shapes.OVAL, x, y, w: d, h: d, fill: { color: fill }, fontSize: fs, bold: true, color,
    align: "center", valign: "middle", margin: 0 };
  if (line) o.line = line;
  s.addText(txt, o);
}
function iconCircle(s, data, x, y, d, fill) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill } });
  const p = d * 0.56;
  s.addImage({ data, x: x + (d - p) / 2, y: y + (d - p) / 2, w: p, h: p });
}
const src = (s, text, o) => T(s, text, Object.assign({ fontSize: 10.5, color: MUTED }, o));

(async () => {
  const I = {};
  const need = {
    sat: ["LuSatelliteDish", WHITE], act: ["LuActivity", WHITE], cam: ["LuCamera", WHITE],
    bulb: ["LuLightbulb", WHITE], alert: ["LuCircleAlert", NAVY], quote: ["LuQuote", WHITE],
    cpu: ["LuCpu", WHITE], camW: ["LuCamera", WHITE], ruler: ["LuMoveVertical", WHITE],
    target: ["LuTarget", WHITE], sun: ["LuSun", NAVY], moon: ["LuMoon", NAVY], wind: ["LuWaves", NAVY],
    film: ["LuFilm", NAVY], route: ["LuRoute", NAVY], gauge: ["LuCrosshair", NAVY], flag: ["LuFlag", NAVY],
    trend: ["LuTrendingUp", NAVY], timer: ["LuTimer", NAVY], db: ["LuDatabase", WHITE], shield: ["LuShieldCheck", WHITE],
    info: ["LuInfo", WHITE], check: ["LuCheck", WHITE],
  };
  for (const [k, [n, c]] of Object.entries(need)) I[k] = await icon(n, c);

  // =====================================================================
  // 1. 표지
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "COVER" });
    s.addShape(pres.shapes.OVAL, { x: 8.55, y: 0.75, w: 4.6, h: 4.6, fill: { color: SKY_XL }, line: { color: SKY_XL } });
    // cover illustration (cropped svg) 738 x 659.5 svg units
    const iw = 4.3, ih = iw * 659.5 / 738, ix = 8.7, iy = 1.15;
    s.addImage({ path: A("cover_c.png"), x: ix, y: iy, w: iw, h: ih, altText: "드론 센서 구성 선형 일러스트" });
    const sc = iw / 738, cx = (v) => ix + (v - 131.0) * sc, cy = (v) => iy + (v - 180.7) * sc;
    T(s, "IMU", { x: cx(450), y: cy(196), w: 100 * sc, h: 0.26, fontSize: 12, bold: true, color: NAVY, align: "center" });
    T(s, "하향 카메라", { x: cx(205), y: cy(420), w: 1.2, h: 0.28, fontSize: 12, bold: true, color: BLUE, align: "right" });
    T(s, "거리 센서", { x: cx(566), y: cy(520), w: 1.1, h: 0.28, fontSize: 12, bold: true, color: ORANGE });
    T(s, "Optical Flow", { x: cx(380), y: iy + ih + 0.05, w: 1.6, h: 0.28, fontSize: 12, bold: true, color: NAVY, align: "center" });

    s.addText("학생자율연구II  연구계획 발표", { shape: pres.shapes.ROUNDED_RECTANGLE, x: ML, y: 1.4, w: 3.55, h: 0.46,
      rectRadius: 0.23, fill: { color: SKY_L }, fontSize: 15, bold: true, color: NAVY, align: "center", valign: "middle", margin: 0, lang: "ko-KR" });
    T(s, [
      { text: "GPS 사용 불가 환경에서", options: { breakLine: true } },
      { text: "비전 보조 항법을 위한 다중센서 융합" },
    ], { x: ML, y: 2.05, w: 7.7, h: 1.4, fontSize: 34, bold: true, color: NAVY_D, lineSpacingMultiple: 1.05, valign: "middle" });
    T(s, "Multi-Sensor Fusion for Vision-Aided Navigation in GPS-Denied Environments",
      { x: ML, y: 3.55, w: 7.8, h: 0.4, fontSize: 15, italic: true, color: BLUE });
    // presenter block
    rect(s, { x: ML, y: 4.45, w: 0.06, h: 1.55, fill: { color: SKY }, line: { color: SKY } });
    T(s, [
      { text: "박찬혁 (202121212)", options: { bold: true, fontSize: 20, color: NAVY_D, breakLine: true } },
      { text: "부산대학교 기계공학부 제어자동화시스템", options: { breakLine: true } },
      { text: "지도교수: 안창선 교수님", options: { breakLine: true } },
      { text: "2026. 10.", options: { color: MUTED } },
    ], { x: ML + 0.28, y: 4.42, w: 6.5, h: 1.62, fontSize: 16, color: TEXT, lineSpacingMultiple: 1.2, valign: "middle" });
    s.addNotes(NOTES[0]);
  }

  // =====================================================================
  // 2. 연구 배경
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "01", "연구 배경", "Background");
    lead(s, "GPS 없이 드론의 위치를 어떻게 추정할 것인가?");
    // left: photo + stat
    s.addImage({ path: A("drone.jpg"), x: ML, y: 1.78, w: 5.3, h: 2.75,
      sizing: { type: "cover", w: 5.3, h: 2.75 }, altText: "실내에서 비행 중인 상용 드론 (예시 사진)" });
    src(s, "예시 사진(본 연구 장비 아님) · -stk, Wikimedia Commons, CC BY-SA 4.0",
      { x: ML, y: 4.57, w: 5.3, h: 0.25, fontSize: 10 });
    box(s, { x: ML, y: 4.92, w: 5.3, h: 0.86, fill: { color: GRAY_BG }, line: { color: LINE, width: 0.75 } });
    T(s, [{ text: "≈ 90", options: { fontSize: 30, bold: true, color: NAVY } }, { text: " m", options: { fontSize: 18, bold: true, color: NAVY } }],
      { x: ML + 0.15, y: 4.98, w: 1.55, h: 0.74, valign: "middle" });
    T(s, [
      { text: "바이어스 0.05 m/s² → 60 s 후 위치 오차", options: { fontSize: 14, bold: true, color: TEXT, breakLine: true } },
      { text: "δp = ½ b t² · 이상적 가정의 이론값 (실험 결과 아님)", options: { fontSize: 11, color: MUTED } },
    ], { x: ML + 1.75, y: 5.0, w: 3.45, h: 0.72, valign: "middle" });

    // right: three blocks
    const bx = 6.3, bw = MR - bx, bh = 1.22, ys = [1.78, 3.17, 4.56];
    const items = [
      [I.sat, "GPS 사용이 어려운 환경", "실내 · 지하 · 교량 하부에서는 위성 신호가 약하거나 끊긴다"],
      [I.act, "IMU 단독 항법의 오차 누적", "가속도를 두 번 적분하므로 바이어스와 잡음에 의한 오차가 시간에 따라 커진다"],
      [I.cam, "카메라로 외부 운동 정보 확보", "영상에서 드론의 움직임을 관측하면 IMU의 누적 오차를 보정할 수 있다"],
    ];
    items.forEach(([ic, h, b], i) => {
      const y = ys[i];
      box(s, { x: bx, y, w: bw, h: bh, fill: { color: i === 2 ? SKY_XL : GRAY_BG }, line: { color: i === 2 ? SKY : LINE, width: 0.75 } });
      iconCircle(s, ic, bx + 0.25, y + 0.3, 0.62, i === 2 ? BLUE : NAVY);
      T(s, [{ text: `0${i + 1}  `, options: { color: SKY, bold: true } }, { text: h, options: { bold: true } }],
        { x: bx + 1.1, y: y + 0.14, w: bw - 1.25, h: 0.4, fontSize: 20, color: NAVY_D, valign: "middle" });
      T(s, b, { x: bx + 1.1, y: y + 0.56, w: bw - 1.25, h: 0.6, fontSize: 17, color: TEXT });
    });
    // key message
    box(s, { x: ML, y: 5.95, w: MR - ML, h: 0.8, fill: { color: SKY_L }, line: { color: SKY_L } });
    iconCircle(s, I.bulb, ML + 0.2, 6.06, 0.58, NAVY);
    T(s, "GPS를 사용할 수 없는 환경에서는 IMU의 누적 오차를 보정할 추가적인 운동 관측이 필요하다.",
      { x: ML + 0.95, y: 5.95, w: MR - ML - 1.1, h: 0.8, fontSize: 19, bold: true, color: NAVY_D, valign: "middle" });
    s.addNotes(NOTES[1]);
  }

  // =====================================================================
  // 3. 연구 필요성
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "01", "연구 필요성: 카메라 측정은 항상 신뢰할 수 있는가?", "Motivation");
    lead(s, "같은 장면이라도 영상 상태에 따라 카메라 측정의 질이 달라진다");
    const iw = 3.9, ih = 2.925, gap = 0.2, x0 = ML + (MR - ML - (3 * iw + 2 * gap)) / 2, y0 = 1.68;
    const imgs = [
      ["ft_normal.png", "① 정상 영상", [{ text: "특징점 " }, { text: "200", options: { bold: true } }, { text: "개 · 추적 성공 " }, { text: "100%", options: { bold: true } }]],
      ["ft_blur.png", "② 흐림 (Motion Blur)", [{ text: "특징점 " }, { text: "170", options: { bold: true } }, { text: "개 · 추적 성공 " }, { text: "95%", options: { bold: true } }]],
      ["ft_dark.png", "③ 저조도 (Low-light)", [{ text: "특징점 " }, { text: "13", options: { bold: true, color: ORANGE } }, { text: "개 · 추적 성공 " }, { text: "100%", options: { bold: true } }]],
    ];
    imgs.forEach(([f, tag, stat], i) => {
      const x = x0 + i * (iw + gap);
      s.addImage({ path: A(f), x, y: y0, w: iw, h: ih, altText: tag + " 특징점 추적 결과" });
      s.addText(tag, { shape: pres.shapes.ROUNDED_RECTANGLE, x: x + 0.12, y: y0 + 0.12, w: 2.35, h: 0.4, rectRadius: 0.06,
        fill: { color: NAVY, transparency: 8 }, fontSize: 14, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, lang: "ko-KR" });
      T(s, stat, { x, y: y0 + ih + 0.07, w: iw, h: 0.4, fontSize: 17, align: "center", valign: "middle" });
    });
    if (true) {
      const lx = x0 + 2 * (iw + gap);
      box(s, { x: lx - 0.04, y: y0 - 0.04, w: iw + 0.08, h: ih + 0.08, fill: { type: "none" }, line: { color: ORANGE, width: 2.25 } });
    }
    // insight row
    const ry = 5.15, rh = 1.17;
    box(s, { x: ML, y: ry, w: 6.15, h: rh, fill: { color: GRAY_BG }, line: { color: LINE, width: 0.75 } });
    s.addImage({ data: I.alert, x: ML + 0.2, y: ry + 0.17, w: 0.38, h: 0.38 });
    T(s, "추적 성공률 하나로는 부족하다", { x: ML + 0.7, y: ry + 0.13, w: 5.3, h: 0.45, fontSize: 18, bold: true, color: NAVY_D, valign: "middle" });
    T(s, [
      { text: "저조도는 성공률 100%지만 특징점이 13개뿐 → " },
      { text: "특징점 수 · 성공률 · 잔차", options: { bold: true, color: NAVY } },
      { text: "를 함께 고려해야 한다" },
    ], { x: ML + 0.2, y: ry + 0.58, w: 5.8, h: 0.55, fontSize: 15.5, color: TEXT });
    const kx = ML + 6.35;
    box(s, { x: kx, y: ry, w: MR - kx, h: rh, fill: { color: NAVY }, line: { color: NAVY }, shadow: shadow() });
    T(s, [
      { text: "영상 품질에 따라 카메라 측정의", options: { breakLine: true } },
      { text: "신뢰도를 판단하는 방법이 필요하다" },
    ], { x: kx + 0.25, y: ry, w: MR - kx - 0.5, h: rh, fontSize: 20, bold: true, color: WHITE, align: "center", valign: "middle" });
    src(s, "설명용 예시(실험 데이터 아님) · Wikimedia Commons CC0 'Gravel Stones'(Saral Shots)에 흐림 · 저조도를 인위적으로 부여, Shi–Tomasi + KLT 실제 실행 · 초록 ○ 성공, 빨강 × 실패",
      { x: ML, y: 6.43, w: MR - ML, h: 0.3, fontSize: 10 });
    s.addNotes(NOTES[2]);
  }

  // =====================================================================
  // 4. 기존 연구와 연구의 위치
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "02", "기존 연구와 본 연구의 위치", "Related Work");
    lead(s, "검증된 기존 기법을 활용하고, 본 연구는 영상 품질 조건별 비교에 초점을 둔다");
    // L1
    const dx = ML, dw = 6.95;
    const l1 = { x: dx + 1.35, y: 1.78, w: 4.25, h: 0.95 };
    box(s, Object.assign({ fill: { color: NAVY }, line: { color: NAVY }, shadow: shadow() }, l1));
    T(s, [
      { text: "Kalman Filter / EKF", options: { fontSize: 19, bold: true, color: WHITE, breakLine: true } },
      { text: "상태 예측 + 측정 보정 · Kalman (1960)", options: { fontSize: 13, color: "C3D8F2" } },
    ], Object.assign({}, l1, { align: "center", valign: "middle" }));
    // L2
    const l2y = 3.05, l2h = 1.75, l2w = 3.37;
    const l2 = [
      { x: dx, t: "VIO", d: "카메라 특징점 + IMU로 자세 · 위치 추정",
        c: ["필터: MSCKF (2007)", "최적화: OKVIS (2015), VINS-Mono (2018)"] },
      { x: dx + dw - l2w, t: "Optical Flow 보조 항법", d: "프레임 간 특징점 이동 측정",
        c: ["Lucas–Kanade (1981) · PX4Flow (2013)", "Grabe et al. (2015)"] },
    ];
    l2.forEach((b) => {
      box(s, { x: b.x, y: l2y, w: l2w, h: l2h, fill: { color: SKY_XL }, line: { color: SKY, width: 1 } });
      T(s, [
        { text: b.t, options: { fontSize: 17, bold: true, color: NAVY_D, breakLine: true } },
        { text: b.d, options: { fontSize: 15, color: TEXT, breakLine: true } },
        { text: b.c[0], options: { fontSize: 12, color: MUTED, breakLine: true } },
        { text: b.c[1], options: { fontSize: 12, color: MUTED } },
      ], { x: b.x + 0.2, y: l2y + 0.08, w: l2w - 0.4, h: l2h - 0.16, valign: "middle", paraSpaceAfter: 4 });
    });
    arrow(s, l1.x + 1.0, l1.y + l1.h, dx + l2w / 2, l2y, BLUE, 1.75);
    arrow(s, l1.x + l1.w - 1.0, l1.y + l1.h, dx + dw - l2w / 2, l2y, BLUE, 1.75);
    // L3
    const l3 = { x: dx + 0.55, y: 5.15, w: dw - 1.1, h: 1.3 };
    arrow(s, dx + l2w / 2, l2y + l2h, l3.x + 1.2, l3.y, BLUE, 1.75);
    arrow(s, dx + dw - l2w / 2, l2y + l2h, l3.x + l3.w - 1.2, l3.y, BLUE, 1.75);
    box(s, Object.assign({ fill: { color: GRAY_BG }, line: { color: NAVY, width: 1.25 } }, l3));
    T(s, [
      { text: "Adaptive Measurement Noise", options: { fontSize: 17, bold: true, color: NAVY_D, breakLine: true } },
      { text: "측정 신뢰도에 따라 잡음 공분산 R 조절", options: { fontSize: 15, color: TEXT, breakLine: true } },
      { text: "Mehra (1970) · PX4 EKF2 (flow 품질 → R) · Asil & Nasibov (2025)", options: { fontSize: 12, color: MUTED } },
    ], { x: l3.x + 0.2, y: l3.y + 0.06, w: l3.w - 0.4, h: l3.h - 0.12, align: "center", valign: "middle", paraSpaceAfter: 3 });

    // connector arrows to focus
    const fx = 8.2;
    s.addShape(pres.shapes.RIGHT_ARROW, { x: 7.63, y: 3.4, w: 0.45, h: 0.5, fill: { color: SKY }, line: { color: SKY } });
    s.addShape(pres.shapes.RIGHT_ARROW, { x: 7.63, y: 4.3, w: 0.45, h: 0.5, fill: { color: ORANGE }, line: { color: ORANGE } });
    // focus box
    box(s, { x: fx, y: 1.98, w: MR - fx, h: 4.62, fill: { color: SKY_XL }, line: { color: SKY, width: 1.5 }, shadow: shadow() });
    s.addText("본 연구의 초점", { shape: pres.shapes.ROUNDED_RECTANGLE, x: fx + (MR - fx - 2.4) / 2, y: 1.74, w: 2.4, h: 0.5,
      rectRadius: 0.25, fill: { color: ORANGE }, fontSize: 18, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, lang: "ko-KR" });
    const rows = [
      ["활용", "기존 EKF · Optical Flow ·\n적응형 R 기법"],
      ["구성", "하향 카메라 + IMU\n+ 거리 센서"],
      ["비교", "영상 품질 조건별\n융합 성능과 한계"],
    ];
    rows.forEach(([k, v], i) => {
      const y = 2.5 + i * 1.02;
      s.addText(k, { shape: pres.shapes.ROUNDED_RECTANGLE, x: fx + 0.3, y: y + 0.17, w: 0.85, h: 0.46, rectRadius: 0.08,
        fill: { color: i === 2 ? ORANGE : NAVY }, fontSize: 15, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, lang: "ko-KR" });
      T(s, v, { x: fx + 1.35, y, w: MR - fx - 1.55, h: 0.8, fontSize: 17, bold: i === 2, color: i === 2 ? NAVY_D : TEXT, valign: "middle" });
      if (i < 2) line(s, fx + 0.3, y + 0.92, MR - 0.3, y + 0.92, SKY_L, 1);
    });
    box(s, { x: fx + 0.3, y: 5.6, w: MR - fx - 0.6, h: 0.78, fill: { color: WHITE }, line: { color: ORANGE, width: 1.25 } });
    T(s, [{ text: "새 기법 제안이 아닌,", options: { breakLine: true, color: TEXT, bold: false, fontSize: 14 } }, { text: "같은 조건에서의 비교 검증" }],
      { x: fx + 0.3, y: 5.6, w: MR - fx - 0.6, h: 0.78, fontSize: 17, bold: true, color: ORANGE, align: "center", valign: "middle" });
    s.addNotes(NOTES[3]);
  }

  // =====================================================================
  // 5. 연구 목적 및 연구 질문
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "03", "연구 목적 및 연구 질문", "Objectives & Questions");
    lead(s, "영상 품질에 따른 카메라 신뢰도 조절이 언제, 얼마나 도움이 되는지 검증한다");
    // left: objectives
    const lx = ML, lw = 5.75;
    line(s, lx, 2.03, lx + lw, 2.03, ORANGE_L, 6);
    s.addText("연구 목적", { shape: pres.shapes.ROUNDED_RECTANGLE, x: lx + (lw - 2.3) / 2, y: 1.78, w: 2.3, h: 0.5, rectRadius: 0.25,
      fill: { color: ORANGE }, fontSize: 18, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, lang: "ko-KR" });
    const objs = [
      [{ text: "하향 카메라 · IMU · 거리 센서 기반 " }, { text: "EKF 상태추정 시스템", options: { bold: true, color: NAVY_D } }, { text: " 구성" }],
      [{ text: "특징점 수 · 추적 성공률 · 잔차로 " }, { text: "영상 품질을 평가", options: { bold: true, color: NAVY_D } }, { text: "하고, 측정 잡음 R 조절 또는 측정 제외 적용" }],
      [{ text: "IMU 단독 · 고정 R 융합 · 품질 반영 융합을 " }, { text: "동일 조건에서 비교", options: { bold: true, color: NAVY_D } }, { text: "해 효과와 한계 검증" }],
    ];
    const oy = [2.55, 3.75, 4.95];
    objs.forEach((r, i) => {
      circleNum(s, lx + 0.05, oy[i] + 0.12, 0.52, String(i + 1), WHITE, ORANGE, 18, { color: ORANGE, width: 2 });
      T(s, r, { x: lx + 0.8, y: oy[i], w: lw - 0.85, h: 0.95, fontSize: 17, valign: "middle" });
      if (i < 2) line(s, lx, oy[i] + 1.08, lx + lw, oy[i] + 1.08, LINE, 0.75);
    });
    // right: questions
    const rx = 6.85, rw = MR - rx;
    line(s, rx, 2.03, rx + rw, 2.03, SKY_L, 6);
    s.addText("연구 질문", { shape: pres.shapes.ROUNDED_RECTANGLE, x: rx + (rw - 2.3) / 2, y: 1.78, w: 2.3, h: 0.5, rectRadius: 0.25,
      fill: { color: SKY }, fontSize: 18, bold: true, color: NAVY_D, align: "center", valign: "middle", margin: 0, lang: "ko-KR" });
    const qs = [
      ["Q1", "정상 영상", "품질 반영 방법이 고정 신뢰도 융합과 비교해 정확도를 유지하는가?"],
      ["Q2", "영상 품질 저하", "흐림 · 저조도에서 신뢰도 조절이 위치 오차 증가를 줄이는가?"],
      ["Q3", "측정 중단", "카메라 측정이 일시적으로 끊기면 추정 오차는 어떻게 변하는가?"],
    ];
    const qy = [2.5, 3.72, 4.94], qh = 1.1;
    qs.forEach(([q, l, t], i) => {
      box(s, { x: rx, y: qy[i], w: rw, h: qh, fill: { color: SKY_XL }, line: { color: SKY_L, width: 0.75 }, shadow: shadow() });
      T(s, q, { x: rx + 0.18, y: qy[i], w: 0.85, h: qh, fontSize: 26, bold: true, color: NAVY, valign: "middle" });
      line(s, rx + 1.1, qy[i] + 0.2, rx + 1.1, qy[i] + qh - 0.2, SKY, 1);
      T(s, l, { x: rx + 1.28, y: qy[i] + 0.1, w: rw - 1.4, h: 0.36, fontSize: 18, bold: true, color: NAVY_D, valign: "middle" });
      T(s, t, { x: rx + 1.28, y: qy[i] + 0.46, w: rw - 1.4, h: 0.6, fontSize: 16, color: TEXT });
    });
    // principle strip
    box(s, { x: ML, y: 6.22, w: MR - ML, h: 0.52, fill: { color: GRAY_BG }, line: { color: GRAY_BG } });
    T(s, [
      { text: "평가 원칙  ", options: { bold: true, color: NAVY } },
      { text: "GPS · RTK · 모션캡처 정답은 추정에 쓰지 않고 평가에만 사용  ·  규칙 설정 구간과 평가 구간을 분리" },
    ], { x: ML + 0.25, y: 6.22, w: MR - ML - 0.5, h: 0.52, fontSize: 15, color: TEXT, valign: "middle" });
    s.addNotes(NOTES[4]);
  }

  // =====================================================================
  // 6. 연구 방법 — 다중센서 융합 구조
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "04", "연구 방법: 다중센서 융합 구조", "System Architecture");
    lead(s, [
      { text: "IMU로 예측하고, 품질을 반영한 Optical Flow 측정으로 보정한다 " },
      { text: "(거리 센서 보조 융합)", options: { color: BLUE, bold: false, fontSize: 17 } },
    ]);
    const IN = { x: ML, w: 1.5 }, C1 = { x: 2.45, w: 2.4 }, C2 = { x: 5.2, w: 2.45 }, EK = { x: 8.0, w: 1.9 }, OU = { x: 10.3, w: MR - 10.3 };
    const R1 = { y: 1.75, h: 0.74 }, R2 = { y: 2.82, h: 0.74 }, R3 = { y: 3.89, h: 0.74 }, R4 = { y: 4.93, h: 0.6 };
    const cy = (r) => r.y + r.h / 2;
    const inBox = (r, ic, label) => {
      box(s, { x: IN.x, y: r.y, w: IN.w, h: r.h, fill: { color: NAVY }, line: { color: NAVY } });
      s.addImage({ data: ic, x: IN.x + 0.14, y: cy(r) - 0.17, w: 0.34, h: 0.34 });
      T(s, label, { x: IN.x + 0.52, y: r.y, w: IN.w - 0.58, h: r.h, fontSize: 14.5, bold: true, color: WHITE, valign: "middle" });
    };
    const pBox = (c, r, runs, hl) => {
      box(s, { x: c.x, y: r.y, w: c.w, h: r.h, fill: { color: hl ? ORANGE_L : SKY_XL }, line: { color: hl ? ORANGE : SKY, width: hl ? 1.75 : 1 } });
      T(s, runs, { x: c.x + 0.08, y: r.y, w: c.w - 0.16, h: r.h, fontSize: 13.5, color: TEXT, align: "center", valign: "middle" });
    };
    const B = (t) => ({ text: t, options: { bold: true, color: NAVY_D, fontSize: 14.5, breakLine: true } });
    inBox(R1, I.cpu, "IMU");
    inBox(R2, I.camW, "하향 카메라");
    inBox(R4, I.ruler, "거리 센서");
    pBox(C1, R1, [B("가속도 f · 각속도 ω"), { text: "IMU 원시 측정" }]);
    pBox(C2, R1, [B("관성 항법 적분"), { text: "자세 회전 · 중력 보상" }]);
    pBox(C1, R2, [B("특징점 검출 · 추적"), { text: "Shi–Tomasi + KLT" }]);
    pBox(C2, R2, [B("Optical Flow"), { text: "픽셀 이동 → 각속도 [rad/s]" }]);
    pBox(C1, R3, [B("영상 품질 평가"), { text: "특징점 수 · 성공률 · 잔차" }], true);
    pBox(C2, R3, [B("측정 잡음 R 조절"), { text: "품질이 너무 낮으면 측정 제외" }], true);
    box(s, { x: C1.x, y: R4.y, w: C2.x + C2.w - C1.x, h: R4.h, fill: { color: SKY_XL }, line: { color: SKY, width: 1 } });
    T(s, [{ text: "지면까지 거리 d", options: { bold: true, color: NAVY_D, fontSize: 14.5 } }, { text: "  →  Flow 스케일 결정 (평탄 지면 가정)" }],
      { x: C1.x + 0.1, y: R4.y, w: C2.x + C2.w - C1.x - 0.2, h: R4.h, fontSize: 13.5, align: "center", valign: "middle" });
    // horizontal arrows
    [R1, R2, R4].forEach((r) => arrow(s, IN.x + IN.w, cy(r), C1.x, cy(r), NAVY, 1.75));
    [R1, R2].forEach((r) => arrow(s, C1.x + C1.w, cy(r), C2.x, cy(r), NAVY, 1.75));
    arrow(s, C1.x + C1.w, cy(R3), C2.x, cy(R3), ORANGE, 1.75);
    arrow(s, C1.x + C1.w / 2, R2.y + R2.h, C1.x + C1.w / 2, R3.y, ORANGE, 1.75);
    // gyro compensation (dashed)
    arrow(s, C1.x + C1.w - 0.35, R1.y + R1.h, C2.x + 0.25, R2.y, BLUE, 1.25, "dash");
    T(s, "ω → 회전 성분 보상", { x: C2.x + 0.4, y: R1.y + R1.h + 0.04, w: 1.8, h: 0.24, fontSize: 10.5, color: BLUE, bold: true });
    // EKF block
    const ey = R1.y, eh = R4.y + R4.h - R1.y;
    box(s, { x: EK.x, y: ey, w: EK.w, h: eh, fill: { color: SKY_L }, line: { color: NAVY, width: 2 }, shadow: shadow() });
    const pin = { x: EK.x + 0.15, y: R1.y + 0.08, w: EK.w - 0.3, h: R1.h - 0.16 };
    box(s, Object.assign({ fill: { color: WHITE }, line: { color: NAVY, width: 1 } }, pin));
    T(s, [{ text: "예측", options: { bold: true, fontSize: 15, breakLine: true } }, { text: "Predict", options: { fontSize: 11, color: MUTED } }],
      Object.assign({}, pin, { align: "center", valign: "middle", color: NAVY_D }));
    T(s, "EKF", { x: EK.x, y: R1.y + R1.h + 0.04, w: EK.w, h: 0.42, fontSize: 22, bold: true, color: NAVY, align: "center", valign: "middle" });
    const uin = { x: EK.x + 0.15, y: R2.y + 0.12, w: EK.w - 0.3, h: R4.y + R4.h - R2.y - 0.2 };
    box(s, Object.assign({ fill: { color: WHITE }, line: { color: NAVY, width: 1 } }, uin));
    T(s, [{ text: "보정", options: { bold: true, fontSize: 15, breakLine: true } }, { text: "Update", options: { fontSize: 11, color: MUTED, breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "z = flow (회전 보상)", options: { fontSize: 11.5, color: TEXT, breakLine: true } },
      { text: "h(x): 속도 · 자세 · d", options: { fontSize: 11.5, color: TEXT } }],
      Object.assign({}, uin, { align: "center", valign: "middle", color: NAVY_D }));
    arrow(s, C2.x + C2.w, cy(R1), EK.x + 0.15, cy(R1), NAVY, 1.75);
    arrow(s, C2.x + C2.w, cy(R2), EK.x + 0.15, cy(R2), NAVY, 1.75);
    arrow(s, C2.x + C2.w, cy(R3), EK.x + 0.15, cy(R3), ORANGE, 1.75);
    arrow(s, C2.x + C2.w, cy(R4), EK.x + 0.15, cy(R4), NAVY, 1.75);
    // output
    const oy = 2.0, oh = 3.3;
    arrow(s, EK.x + EK.w, oy + oh / 2, OU.x, oy + oh / 2, NAVY, 2.25);
    box(s, { x: OU.x, y: oy, w: OU.w, h: oh, fill: { color: GRAY_BG }, line: { color: LINE, width: 0.75 } });
    T(s, "추정 상태  x", { x: OU.x, y: oy + 0.1, w: OU.w, h: 0.4, fontSize: 16, bold: true, color: NAVY_D, align: "center", valign: "middle" });
    [["위치  p", "Position"], ["속도  v", "Velocity"], ["자세  q", "Attitude"]].forEach(([a, b], i) => {
      const y = oy + 0.62 + i * 0.86;
      box(s, { x: OU.x + 0.2, y, w: OU.w - 0.4, h: 0.68, fill: { color: WHITE }, line: { color: SKY, width: 1 } });
      T(s, [{ text: a, options: { bold: true, color: NAVY_D, fontSize: 16 } }, { text: "   " + b, options: { fontSize: 11, color: MUTED } }],
        { x: OU.x + 0.2, y, w: OU.w - 0.4, h: 0.68, align: "center", valign: "middle" });
    });
    // bottom equation strip
    const sy = 5.72, sh = 1.02;
    box(s, { x: ML, y: sy, w: 5.15, h: sh, fill: { color: SKY_XL }, line: { color: SKY_L } });
    T(s, "Optical Flow 측정 (영상 중심 근처, 평탄 지면)", { x: ML + 0.18, y: sy + 0.07, w: 4.9, h: 0.24, fontSize: 11.5, bold: true, color: BLUE });
    T(s, [
      { text: "z", options: { italic: true, fontFace: "Times New Roman" } },
      { text: " = " },
      { text: "Ω", options: { fontFace: "Times New Roman" } }, { text: "flow", options: { subscript: true, fontSize: 13 } },
      { text: " − " },
      { text: "ω", options: { italic: true, fontFace: "Times New Roman" } }, { text: "gyro", options: { subscript: true, fontSize: 13 } },
      { text: "  ≈  " },
      { text: "v", options: { italic: true, fontFace: "Times New Roman" } }, { text: "⊥", options: { subscript: true, fontSize: 13 } },
      { text: " / " }, { text: "d", options: { italic: true, fontFace: "Times New Roman" } },
    ], { x: ML + 0.18, y: sy + 0.31, w: 4.9, h: 0.42, fontSize: 20, color: NAVY_D, valign: "middle" });
    T(s, "회전 성분은 자이로로 제거, 병진 성분의 스케일은 거리 d로 결정", { x: ML + 0.18, y: sy + 0.73, w: 4.9, h: 0.25, fontSize: 11.5, color: MUTED });
    const px = ML + 5.35;
    box(s, { x: px, y: sy, w: 4.1, h: sh, fill: { color: SKY_XL }, line: { color: SKY_L } });
    T(s, "EKF 보정 이득과 측정 잡음 R", { x: px + 0.18, y: sy + 0.07, w: 3.8, h: 0.24, fontSize: 11.5, bold: true, color: BLUE });
    T(s, [
      { text: "K", options: { italic: true, fontFace: "Times New Roman" } }, { text: " = " },
      { text: "PH", options: { italic: true, fontFace: "Times New Roman" } }, { text: "T", options: { superscript: true, fontSize: 13 } },
      { text: "(" }, { text: "HPH", options: { italic: true, fontFace: "Times New Roman" } }, { text: "T", options: { superscript: true, fontSize: 13 } },
      { text: " + " }, { text: "R", options: { italic: true, fontFace: "Times New Roman", bold: true, color: ORANGE } }, { text: ")" },
      { text: "−1", options: { superscript: true, fontSize: 13 } },
    ], { x: px + 0.18, y: sy + 0.31, w: 3.8, h: 0.42, fontSize: 20, color: NAVY_D, valign: "middle" });
    T(s, [{ text: "R ↑  →  K ↓  →  카메라 보정 반영 ↓", options: { bold: true } }], { x: px + 0.18, y: sy + 0.73, w: 3.8, h: 0.25, fontSize: 11.5, color: ORANGE });
    // legend
    const gx = px + 4.3;
    box(s, { x: gx, y: sy + 0.1, w: 0.32, h: 0.22, fill: { color: SKY_XL }, line: { color: SKY, width: 1 } });
    T(s, "기존 기법 활용", { x: gx + 0.42, y: sy + 0.06, w: 2.2, h: 0.3, fontSize: 12, valign: "middle" });
    box(s, { x: gx, y: sy + 0.45, w: 0.32, h: 0.22, fill: { color: ORANGE_L }, line: { color: ORANGE, width: 1.5 } });
    T(s, "본 연구에서 구성 · 평가", { x: gx + 0.42, y: sy + 0.41, w: 2.3, h: 0.3, fontSize: 12, valign: "middle" });
    T(s, "※ 순수 Camera–IMU VIO가 아닌 거리 센서 보조 융합 · 상세 모델은 부록 A2–A3",
      { x: gx, y: sy + 0.74, w: MR - gx, h: 0.3, fontSize: 9.5, color: MUTED });
    s.addNotes(NOTES[5]);
  }

  // =====================================================================
  // 7. 실험 설계 및 성능 평가
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "04", "실험 설계 및 성능 평가", "Experimental Design");
    lead(s, "같은 데이터 · 같은 초기 조건 · 같은 평가 구간에서 세 방법을 비교한다");
    const top = 1.75, hh = 0.5, bot = 5.9;
    const cols = [{ x: ML, w: 4.15, t: "비교 대상" }, { x: 4.95, w: 3.7, t: "실험 조건" }, { x: 8.85, w: MR - 8.85, t: "평가 지표" }];
    cols.forEach((c) => {
      box(s, { x: c.x, y: top, w: c.w, h: bot - top, fill: { color: GRAY_BG }, line: { color: GRAY_BG } });
      s.addText(c.t, { shape: pres.shapes.ROUNDED_RECTANGLE, x: c.x, y: top, w: c.w, h: hh, rectRadius: 0.08, fill: { color: NAVY },
        fontSize: 18, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, lang: "ko-KR" });
    });
    // col1: A/B/C
    const abc = [
      ["A", "IMU 단독 항법", "카메라 보정 없음 (기준선)", "8A94A6"],
      ["B", "고정 R 기반 EKF", "R 고정 · 품질과 무관하게 반영", BLUE],
      ["C", "영상 품질 반영 EKF", "품질에 따라 R 조절 · 저품질 제외", ORANGE],
    ];
    abc.forEach(([L, t, d, col], i) => {
      const y = 2.42 + i * 1.15, x = cols[0].x + 0.15, w = cols[0].w - 0.3;
      box(s, { x, y, w, h: 1.0, fill: { color: i === 2 ? ORANGE_L : WHITE }, line: { color: i === 2 ? ORANGE : LINE, width: i === 2 ? 1.75 : 0.75 } });
      circleNum(s, x + 0.15, y + 0.22, 0.56, L, col, WHITE, 20);
      T(s, t, { x: x + 0.85, y: y + 0.1, w: w - 0.95, h: 0.4, fontSize: 18, bold: true, color: NAVY_D, valign: "middle" });
      T(s, d, { x: x + 0.85, y: y + 0.5, w: w - 0.95, h: 0.42, fontSize: 14, color: TEXT, valign: "middle" });
    });
    // col2: conditions
    const conds = [
      [I.sun, "정상 영상", "기준 조건"],
      [I.wind, "흐림 (Motion Blur)", "인위적 부여"],
      [I.moon, "저조도 (Low-light)", "인위적 부여"],
      [I.film, "프레임 누락", "측정 중단 모사"],
      [I.route, "운동 조건", "직선 · 선회 · 정지 구간"],
    ];
    conds.forEach(([ic, t, d], i) => {
      const y = 2.42 + i * 0.68, x = cols[1].x + 0.18;
      s.addShape(pres.shapes.OVAL, { x, y: y + 0.04, w: 0.5, h: 0.5, fill: { color: SKY_L }, line: { color: SKY_L } });
      s.addImage({ data: ic, x: x + 0.12, y: y + 0.16, w: 0.26, h: 0.26 });
      T(s, [{ text: t, options: { bold: true, color: NAVY_D, fontSize: 16.5, breakLine: true } }, { text: d, options: { fontSize: 12, color: MUTED } }],
        { x: x + 0.65, y, w: cols[1].w - 0.95, h: 0.6, valign: "middle" });
    });
    // col3: metrics tiles + schematic
    const mx = cols[2].x + 0.15, mw = cols[2].w - 0.3, tw = (mw - 0.15) / 2;
    const mets = [[I.gauge, "위치 RMSE"], [I.flag, "최종 위치 오차"], [I.trend, "저하 구간 오차 증가량"], [I.timer, "처리시간"]];
    mets.forEach(([ic, t], i) => {
      const x = mx + (i % 2) * (tw + 0.15), y = 2.42 + Math.floor(i / 2) * 0.82;
      box(s, { x, y, w: tw, h: 0.7, fill: { color: WHITE }, line: { color: LINE, width: 0.75 } });
      s.addImage({ data: ic, x: x + 0.12, y: y + 0.21, w: 0.28, h: 0.28 });
      T(s, t, { x: x + 0.46, y, w: tw - 0.52, h: 0.7, fontSize: 13.5, bold: true, color: NAVY_D, valign: "middle" });
    });
    // schematic graph (format example, no data)
    const gx = mx, gy = 4.15, gw = mw, gh = 1.65;
    box(s, { x: gx, y: gy, w: gw, h: gh, fill: { color: WHITE }, line: { color: LINE, width: 0.75 } });
    T(s, "결과 그래프 형식 예시 · 데이터 아님", { x: gx + 0.12, y: gy + 0.06, w: gw - 0.24, h: 0.22, fontSize: 9.5, color: MUTED, italic: true });
    const ax = gx + 0.45, ay = gy + 1.38, aw = gw - 0.7, ah = 1.0;
    rect(s, { x: ax + aw * 0.45, y: ay - ah, w: aw * 0.24, h: ah, fill: { color: "E6EAF0" }, line: { color: "E6EAF0" } });
    T(s, "품질 저하 구간", { x: ax + aw * 0.45 - 0.2, y: ay - ah + 0.04, w: aw * 0.24 + 0.4, h: 0.22, fontSize: 9.5, color: MUTED, align: "center" });
    arrow(s, ax, ay, ax + aw, ay, TEXT, 1);
    arrow(s, ax, ay, ax, ay - ah, TEXT, 1);
    arrow(s, ax + aw * 0.78, ay - ah * 0.35, ax + aw * 0.78, ay - ah * 0.8, ORANGE, 1.5);
    arrow(s, ax + aw * 0.78, ay - ah * 0.8, ax + aw * 0.78, ay - ah * 0.35, ORANGE, 1.5);
    T(s, "오차 증가량", { x: ax + aw * 0.8, y: ay - ah * 0.72, w: 0.85, h: 0.22, fontSize: 9.5, color: ORANGE, bold: true });
    T(s, "시간", { x: ax + aw - 0.5, y: ay + 0.02, w: 0.5, h: 0.2, fontSize: 9.5, color: MUTED, align: "right" });
    T(s, "위치 오차", { x: gx + 0.05, y: ay - ah + 0.05, w: 0.38, h: 0.9, fontSize: 9.5, color: MUTED, vert: "eaVert", align: "center" });
    // data strip
    box(s, { x: ML, y: 6.05, w: MR - ML, h: 0.7, fill: { color: SKY_XL }, line: { color: SKY_L } });
    iconCircle(s, I.db, ML + 0.15, 6.13, 0.52, NAVY);
    T(s, [
      { text: "데이터 후보  INSANE (Brommer et al., IJRR 2024)", options: { bold: true, color: NAVY_D, breakLine: true } },
      { text: "하향 카메라 · 하향 레이저 거리계 · 다중 IMU 포함 / 정답: 실내 OptiTrack, 실외 dual RTK-GNSS → 평가에만 사용 (실제 파일로 구간 확인 예정)", options: { fontSize: 12, color: TEXT } },
    ], { x: ML + 0.82, y: 6.07, w: MR - ML - 1.0, h: 0.66, fontSize: 14, valign: "middle" });
    s.addNotes(NOTES[6]);
  }

  // =====================================================================
  // 8. 기대 결과 · 연구 일정 · 결론
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "05", "기대 결과 및 연구 일정", "Expected Outcomes & Timeline");
    lead(s, [
      { text: "예상 결과는 실험 전 가설이며, " },
      { text: "효과가 없거나 작은 조건도 그대로 보고한다", options: { color: ORANGE } },
    ], { fontSize: 18 });
    const cards = [
      ["1", "가설 H1 · 정상 영상", "B와 C의 정확도가\n비슷할 것", SKY_XL, SKY],
      ["2", "가설 H2 · 저하 · 중단", "C의 오차 증가가\nB보다 작을 것", SKY_XL, SKY],
      ["3", "검증 산출물", "상태추정 코드 · 조건별\n비교 결과 · 보고서", GRAY_BG, NAVY],
      ["4", "기대 기여", "품질 지표별 효과와\n한계를 정량적으로 제시", GRAY_BG, NAVY],
    ];
    const cw = (MR - ML - 3 * 0.2) / 4, cy0 = 1.85, ch = 1.32;
    cards.forEach(([n, t, d, fill, nc], i) => {
      const x = ML + i * (cw + 0.2);
      box(s, { x, y: cy0, w: cw, h: ch, fill: { color: fill }, line: { color: fill } });
      circleNum(s, x + 0.12, cy0 - 0.2, 0.44, n, nc, WHITE, 15);
      T(s, t, { x: x + 0.2, y: cy0 + 0.22, w: cw - 0.35, h: 0.36, fontSize: 16.5, bold: true, color: NAVY_D, valign: "middle" });
      T(s, d, { x: x + 0.2, y: cy0 + 0.6, w: cw - 0.35, h: 0.66, fontSize: 15, color: TEXT });
    });
    // timeline
    const steps = [
      ["10월 초", "데이터 구성 ·\n센서 전처리"],
      ["10월 말", "기준 EKF\n구현"],
      ["11월 초", "품질 지표 ·\n신뢰도 규칙 설계"],
      ["11월 말", "조건별\n비교 실험"],
      ["12월 초", "성능 분석 ·\n최종 보고서"],
    ];
    const ty = 3.5, tchH = 0.78, step = 2.4, tcw = 2.5;
    steps.forEach(([m, t], i) => {
      const x = ML + i * step;
      const hl = i === 2;
      s.addText(m, { shape: pres.shapes.CHEVRON, x, y: ty, w: tcw, h: tchH, fill: { color: hl ? ORANGE_L : SKY_L },
        line: { color: hl ? ORANGE_L : SKY_L }, fontSize: 18, bold: true, color: hl ? ORANGE : NAVY_D, align: "center", valign: "middle", margin: 0, lang: "ko-KR" });
      const cx = x + tcw / 2;
      [0, 1, 2].forEach((k) => s.addShape(pres.shapes.OVAL, { x: cx - 0.04, y: ty + tchH + 0.1 + k * 0.13, w: 0.08, h: 0.08, fill: { color: LINE }, line: { color: LINE } }));
      T(s, t, { x: cx - 1.1, y: ty + tchH + 0.5, w: 2.2, h: 0.7, fontSize: 15.5, bold: hl, color: hl ? NAVY_D : TEXT, align: "center", valign: "top" });
    });
    src(s, "계획(안): 세부 일정은 지도교수님과 협의하여 조정", { x: MR - 4.5, y: 5.5, w: 4.5, h: 0.24, align: "right" });
    // conclusion
    box(s, { x: ML, y: 5.85, w: MR - ML, h: 0.88, fill: { color: NAVY }, line: { color: NAVY }, shadow: shadow() });
    iconCircle(s, I.target, ML + 0.22, 6.0, 0.58, BLUE);
    T(s, [
      { text: "최종 목표 · GPS 불가 · 영상 품질 저하 환경에서", options: { color: "C3D8F2", fontSize: 13, bold: false, breakLine: true } },
      { text: "카메라 측정을 언제, 얼마나 믿어야 하는지 정량적 근거를 제시한다" },
    ], { x: ML + 0.98, y: 5.85, w: MR - ML - 1.15, h: 0.88, fontSize: 18.5, bold: true, color: WHITE, valign: "middle" });
    s.addNotes(NOTES[7]);
  }

  // =====================================================================
  // 9. 감사합니다 / Q&A
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "COVER" });
    s.addShape(pres.shapes.OVAL, { x: 4.67, y: 0.75, w: 4.0, h: 4.0, fill: { color: SKY_XL }, line: { color: SKY_XL } });
    T(s, "감사합니다", { x: 0, y: 1.75, w: SW, h: 0.9, fontSize: 40, bold: true, color: NAVY_D, align: "center", valign: "middle" });
    T(s, "Q&A", { x: 0, y: 2.6, w: SW, h: 1.1, fontSize: 60, bold: true, color: SKY, align: "center", valign: "middle" });
    T(s, [
      { text: "GPS 사용 불가 환경에서 비전 보조 항법을 위한 다중센서 융합", options: { bold: true, color: NAVY, breakLine: true } },
      { text: "박찬혁 · 부산대학교 기계공학부 제어자동화시스템 · 지도교수 안창선 교수님", options: { fontSize: 14, color: MUTED } },
    ], { x: 1, y: 5.0, w: SW - 2, h: 0.9, fontSize: 17, align: "center", valign: "middle" });
    s.addNotes(NOTES[8]);
  }

  // =====================================================================
  // A1. 참고문헌
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "A1", "부록 1. 참고문헌", "Appendix · References");
    const refs = [
      ["R. E. Kalman, “A New Approach to Linear Filtering and Prediction Problems,” J. Basic Eng., 82(1), 1960.", "Kalman Filter 기본 구조"],
      ["R. K. Mehra, “On the Identification of Variances and Adaptive Kalman Filtering,” IEEE TAC, 15(2), 1970.", "적응형 Kalman Filter"],
      ["B. D. Lucas, T. Kanade, “An Iterative Image Registration Technique with an Application to Stereo Vision,” IJCAI, 1981.", "특징점 추적 (KLT의 기반)"],
      ["J. Shi, C. Tomasi, “Good Features to Track,” IEEE CVPR, 1994.", "특징점 검출 (Shi–Tomasi)"],
      ["A. I. Mourikis, S. I. Roumeliotis, “A Multi-State Constraint Kalman Filter for Vision-aided Inertial Navigation,” IEEE ICRA, 2007.", "필터 기반 VIO (MSCKF)"],
      ["S. Leutenegger et al., “Keyframe-based Visual–Inertial Odometry using Nonlinear Optimization,” IJRR, 34(3), 2015.", "최적화 기반 VIO (OKVIS)"],
      ["T. Qin, P. Li, S. Shen, “VINS-Mono: A Robust and Versatile Monocular Visual-Inertial State Estimator,” IEEE T-RO, 34(4), 2018.", "최적화 기반 단안 VIO"],
      ["D. Honegger et al., “An Open Source and Open Hardware Embedded Metric Optical Flow CMOS Camera for Indoor and Outdoor Applications,” IEEE ICRA, 2013.", "하향 flow 센서 (PX4Flow)"],
      ["V. Grabe et al., “Nonlinear Ego-Motion Estimation from Optical Flow for Online Control of a Quadrotor UAV,” IJRR, 34(8), 2015.", "flow 기반 자기운동 추정"],
      ["PX4 Autopilot, EKF2 optical flow fusion — optical_flow_control.cpp, optical_flow_fusion.cpp (main 브랜치, 2026. 10. 확인)", "flow 품질 → R 보간 · 저품질 제외"],
      ["U. Asil, E. Nasibov, “Adaptive Covariance and Quaternion-Focused Hybrid Error-State EKF/UKF for Visual-Inertial Odometry,” Int. J. Comput. Intell. Syst., 18, 2025 (arXiv:2512.17505).", "영상 신뢰도 기반 R 조절"],
      ["C. Brommer et al., “The INSANE Dataset: Large Number of Sensors for Challenging UAV Flights in Mars Analog, Outdoor, and Out-/Indoor Transition Scenarios,” IJRR, 43(8), 2024.", "공개 데이터셋 후보"],
    ];
    const rows = [[
      { text: "#", options: { bold: true, color: NAVY_D, fill: { color: SKY_L }, align: "center" } },
      { text: "문헌", options: { bold: true, color: NAVY_D, fill: { color: SKY_L } } },
      { text: "본 연구에서의 역할", options: { bold: true, color: NAVY_D, fill: { color: SKY_L } } },
    ]];
    refs.forEach(([r, role], i) => rows.push([
      { text: String(i + 1), options: { align: "center", color: MUTED } },
      { text: r },
      { text: role, options: { color: NAVY_D, bold: true } },
    ]));
    s.addTable(rows, { x: ML, y: 1.18, w: MR - ML, colW: [0.45, 9.0, MR - ML - 9.45], fontSize: 10.5, color: TEXT,
      border: { type: "solid", pt: 0.5, color: LINE }, valign: "middle", margin: [0.03, 0.08, 0.03, 0.08], rowH: 0.4, lang: "ko-KR" });
    s.addNotes("[부록 · 질의응답용] 참고문헌. PX4 EKF2 동작은 공개 소스 코드(optical_flow_fusion.cpp의 calcOptFlowMeasVar, predictFlow)로 확인함.");
  }

  // =====================================================================
  // A2. 측정모델 · 좌표계
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "A2", "부록 2. Optical Flow 측정모델과 좌표계", "Appendix · Measurement Model");
    // diagram 880.5 x 623.1 svg units
    const iw = 5.4, ih = iw * 623.1 / 880.5, ix = ML, iy = 1.3;
    box(s, { x: ix - 0.05, y: iy - 0.1, w: iw + 0.1, h: ih + 0.55, fill: { color: GRAY_BG }, line: { color: GRAY_BG } });
    s.addImage({ path: A("frames_c.png"), x: ix, y: iy, w: iw, h: ih, altText: "기체 · 카메라 좌표계와 거리 관계 도식" });
    const sc = iw / 880.5, X = (v) => ix + (v - 59.76) * sc, Y = (v) => iy + (v - 136.8) * sc;
    const lab = (t, sx, sy, o) => T(s, t, Object.assign({ x: X(sx), y: Y(sy), w: 1.3, h: 0.26, fontSize: 12, bold: true, color: NAVY_D }, o));
    lab([{ text: "x" }, { text: "B", options: { subscript: true } }, { text: " (기체 전방)" }], 600, 195, { color: BLUE, w: 1.5 });
    lab("v", 790, 132, { color: ORANGE, w: 0.3 });
    lab("h", 385, 470, { color: MUTED, w: 0.3 });
    lab("d (광축 거리)", 560, 600, { color: ORANGE, w: 1.4 });
    lab("θ", 440, 445, { w: 0.3 });
    lab([{ text: "x" }, { text: "W", options: { subscript: true } }], 228, 545, { w: 0.6 });
    lab([{ text: "z" }, { text: "W", options: { subscript: true } }], 122, 655, { w: 0.6 });
    lab("평탄 지면 가정", 700, 710, { color: MUTED, w: 1.5, fontSize: 11 });
    T(s, "카메라는 하향(광축 ≈ 기체 z축), 거리 센서는 광축 방향 거리 d를 측정한다고 가정 (장착 오프셋은 보정 필요)",
      { x: ix + 0.05, y: iy + ih + 0.05, w: iw - 0.1, h: 0.38, fontSize: 10.5, color: MUTED });
    // equations
    const ex = 6.35, ew = MR - ex;
    const C = { text: "C", options: { superscript: true } };
    const sb = (t) => ({ text: t, options: { subscript: true } });
    const sp = (t) => ({ text: t, options: { superscript: true } });
    const tx = (t) => ({ text: t });
    const eqs = [
      ["① 영상 운동 (핀홀, 영상 중심 근처의 정적 지면점)",
        [tx("ẋ ≈ −v"), sb("x"), tx(" / Z − ω"), sb("y"), tx(" ,     ẏ ≈ −v"), sb("y"), tx(" / Z + ω"), sb("x")],
        "v, ω: 카메라 좌표계(C) 성분 · 병진(÷ 깊이 Z)과 회전이 합쳐짐 · 부호는 축 정의에 따름"],
      ["② 픽셀 → 각도 (카메라 내부 파라미터)",
        [tx("ẋ ≈ (Δu / f"), sb("px"), tx(") / Δt")],
        "f_px: 픽셀 단위 초점거리 · Δt: 프레임 간격 (왜곡 보정 후)"],
      ["③ 회전 보상 · 좌표변환 (외부 파라미터)",
        [tx("ω"), sb("C"), tx(" = R"), sb("CB"), tx(" ω"), sb("B"), tx(" ,   v"), sb("C"), tx(" = R"), sb("CB"), tx(" ( R(q)"), sp("T"), tx(" v"), sb("W"), tx(" + ω"), sb("B"), tx(" × r"), sb("BC"), tx(" )")],
        "R_CB: IMU→카메라 회전 · r_BC: IMU→카메라 위치 차이(레버암) · q: 드론 자세"],
      ["④ 거리 센서로 깊이 결정",
        [tx("Z ≈ d = h / (cos φ cos θ)")],
        "평탄 지면 · 정적 장면 가정, 기울기가 크면 측정 제외 (PX4 EKF2도 기울기 조건 사용)"],
    ];
    let y = 1.2;
    eqs.forEach(([t, eq, note]) => {
      T(s, t, { x: ex, y, w: ew, h: 0.3, fontSize: 13.5, bold: true, color: BLUE });
      T(s, eq, { x: ex + 0.15, y: y + 0.32, w: ew - 0.15, h: 0.4, fontSize: 17, color: NAVY_D, fontFace: "Times New Roman", valign: "middle" });
      T(s, note, { x: ex + 0.15, y: y + 0.73, w: ew - 0.15, h: 0.26, fontSize: 11, color: MUTED });
      y += 1.08;
    });
    box(s, { x: ex, y: 5.6, w: ew, h: 1.1, fill: { color: SKY_XL }, line: { color: SKY, width: 1 } });
    T(s, [
      { text: "EKF 측정모델:  ", options: { bold: true, color: BLUE, fontSize: 13.5 } },
      tx("z = [ ẋ + ω"), sb("y"), tx(" ,  ẏ − ω"), sb("x"), tx(" ]  ≈  −[ v"), sb("x"), tx(" ,  v"), sb("y"),
      { text: " ] / d  =  h(x)", options: { breakLine: true } },
      { text: "Optical Flow는 속도 자체가 아니라 ‘속도/거리 + 회전’을 관측한다 → 자이로 · 자세 · 거리 · 외부 파라미터가 모두 필요", options: { fontSize: 11.5, color: TEXT } },
    ], { x: ex + 0.15, y: 5.6, w: ew - 0.3, h: 1.1, fontSize: 16, color: NAVY_D, valign: "middle", paraSpaceAfter: 4 });
    s.addNotes("[부록 · 질의응답용]\n" +
      "옵티컬 플로우는 영상 속 점의 이동, 즉 시선 방향의 각속도를 측정합니다. 영상 중심 근처의 정적인 지면점에 대해 표준 핀홀 운동 모델을 쓰면, 플로우는 카메라 병진속도를 깊이로 나눈 항과 카메라 각속도 항의 합입니다. " +
      "따라서 자이로 각속도를 카메라 좌표로 변환해 회전 성분을 빼고, 거리 센서의 광축 방향 거리로 깊이를 정해야 병진속도 정보가 됩니다. 카메라 속도는 IMU 위치의 속도에 회전에 의한 레버암 속도를 더한 뒤 카메라 좌표로 회전한 값입니다. " +
      "이 형태는 PX4 EKF2의 predictFlow 구현(기체 속도 + 레버암, 거리로 나눔, 자이로 보상된 flow를 관측값으로 사용)과 같은 구조입니다. 부호는 센서 축 정의에 따라 달라집니다.");
  }

  // =====================================================================
  // A3. EKF 구조와 품질 → R 규칙
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "A3", "부록 3. EKF 예측 · 보정과 품질 → R 규칙", "Appendix · EKF & Adaptive R");
    const cx = ML, cw = 6.05;
    const panel = (x, y, w, h, title) => {
      box(s, { x, y, w, h, fill: { color: GRAY_BG }, line: { color: GRAY_BG } });
      T(s, title, { x: x + 0.2, y: y + 0.1, w: w - 0.4, h: 0.34, fontSize: 15, bold: true, color: NAVY_D, valign: "middle" });
    };
    const TNR = (t, o) => ({ text: t, options: Object.assign({ fontFace: "Times New Roman" }, o || {}) });
    panel(cx, 1.2, cw, 1.15, "상태 · 측정 벡터");
    T(s, [TNR("x = [ p, v, q ]", { bold: true }), { text: "   위치 · 속도 · 자세(쿼터니언)", options: { fontSize: 13, color: MUTED, breakLine: true } },
      TNR("z = flow (회전 보상, 2차원)", { bold: true }), { text: "   d: 거리 센서 값을 h(x)에 사용", options: { fontSize: 13, color: MUTED } }],
      { x: cx + 0.3, y: 1.55, w: cw - 0.5, h: 0.75, fontSize: 16, color: NAVY_D, valign: "middle", paraSpaceAfter: 2 });
    panel(cx, 2.5, cw, 1.7, "예측 (IMU, 매 샘플)");
    T(s, [
      TNR("v"), TNR("k", { subscript: true }), TNR(" = v"), TNR("k−1", { subscript: true }), TNR(" + ( R(q) f"), TNR("m", { subscript: true }), TNR(" + g ) Δt", { breakLine: true }),
      TNR("p"), TNR("k", { subscript: true }), TNR(" = p"), TNR("k−1", { subscript: true }), TNR(" + v"), TNR("k−1", { subscript: true }), TNR(" Δt ,   q"), TNR("k", { subscript: true }), TNR(" = q"), TNR("k−1", { subscript: true }), TNR(" ⊗ Δq( ω"), TNR("m", { subscript: true }), TNR(" Δt )", { breakLine: true }),
      TNR("P"), TNR("−", { superscript: true }), TNR(" = F P F"), TNR("T", { superscript: true }), TNR(" + Q"),
    ], { x: cx + 0.3, y: 2.9, w: cw - 0.5, h: 1.2, fontSize: 16, color: NAVY_D, valign: "middle", paraSpaceAfter: 3 });
    panel(cx, 4.35, cw, 1.6, "보정 (Optical Flow, 측정 시)");
    T(s, [
      TNR("y = z − h(x̂"), TNR("−", { superscript: true }), TNR(") ,   S = H P"), TNR("−", { superscript: true }), TNR("H"), TNR("T", { superscript: true }), TNR(" + "), TNR("R", { bold: true, color: ORANGE }), TNR(" ,   K = P"), TNR("−", { superscript: true }), TNR("H"), TNR("T", { superscript: true }), TNR("S"), TNR("−1", { superscript: true, breakLine: true }),
      TNR("x̂ = x̂"), TNR("−", { superscript: true }), TNR(" + K y ,   P = ( I − K H ) P"), TNR("−", { superscript: true, breakLine: true }),
      { text: "f_m, ω_m: IMU 측정값 · χ² 게이트 초과 시 측정 거부", options: { fontSize: 12, color: MUTED } },
    ], { x: cx + 0.3, y: 4.75, w: cw - 0.5, h: 1.15, fontSize: 16, color: NAVY_D, valign: "middle", paraSpaceAfter: 3 });
    T(s, "※ IMU 바이어스(b_a, b_g)를 상태에 넣을지는 기준 EKF 구현 단계(10월 말)에서 결정할 검토 항목 — PX4 EKF2 등 일반적인 INS-EKF는 바이어스를 추정",
      { x: cx, y: 6.05, w: cw, h: 0.55, fontSize: 11, color: MUTED });

    // right: quality -> R
    const rx = 6.95, rw = MR - rx;
    panel(rx, 1.2, rw, 5.4, "영상 품질 Q → 측정 잡음 R (규칙 형태)");
    T(s, [
      TNR("w = clip( (Q − Q"), TNR("min", { subscript: true }), TNR(") / (Q"), TNR("max", { subscript: true }), TNR(" − Q"), TNR("min", { subscript: true }), TNR("), 0, 1 )", { breakLine: true }),
      TNR("σ = w σ"), TNR("best", { subscript: true }), TNR(" + (1 − w) σ"), TNR("worst", { subscript: true }), TNR(" ,   "), TNR("R = σ", { bold: true, color: ORANGE }), TNR("2", { superscript: true, bold: true, color: ORANGE }), TNR(" I", { bold: true, color: ORANGE, breakLine: true }),
      TNR("Q < Q"), TNR("min", { subscript: true }), TNR("  →  측정 제외"),
    ], { x: rx + 0.3, y: 1.6, w: rw - 0.5, h: 1.25, fontSize: 16, color: NAVY_D, valign: "middle", paraSpaceAfter: 3 });
    // native chart: sigma vs Q (normalised illustration)
    const qs = [], sig = [];
    for (let i = 0; i <= 10; i++) { const q = i / 10; qs.push(q.toFixed(1)); const w = Math.min(Math.max((q - 0.2) / 0.8, 0), 1); sig.push(+(w * 0.2 + (1 - w) * 1.0).toFixed(3)); }
    s.addChart(pres.charts.LINE, [{ name: "σ (정규화)", labels: qs, values: sig }], {
      x: rx + 0.2, y: 2.95, w: rw - 0.4, h: 2.35, chartColors: [ORANGE], lineSize: 2.5, lineDataSymbol: "none",
      showLegend: false, showTitle: true, title: "측정 잡음 표준편차 σ vs 품질 Q (형태 예시)", titleFontSize: 11, titleColor: NAVY_D, titleFontFace: "+mn-lt",
      catAxisTitle: "품질 Q (정규화)", showCatAxisTitle: true, catAxisTitleFontSize: 10, catAxisTitleColor: MUTED,
      valAxisTitle: "σ", showValAxisTitle: true, valAxisTitleFontSize: 10, valAxisTitleColor: MUTED,
      catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, catAxisLabelFontSize: 9, valAxisLabelFontSize: 9,
      catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valAxisMinVal: 0, valAxisMaxVal: 1.2,
      valGridLine: { color: "E3E8F0", size: 0.5 }, catGridLine: { style: "none" },
    });
    T(s, [
      { text: "PX4 EKF2와 같은 형태(소스 코드 확인): σ를 품질에 따라 선형 보간, 최소 품질 미만은 사용하지 않음. ", options: { breakLine: true } },
      { text: "본 연구의 Q는 특징점 수 · 추적 성공률 · 잔차로 구성하며, 형태와 파라미터는 설정 구간에서만 결정한다. 그래프 수치는 형태를 보이기 위한 정규화 예시." },
    ], { x: rx + 0.25, y: 5.38, w: rw - 0.45, h: 1.15, fontSize: 11, color: TEXT, paraSpaceAfter: 3 });
    s.addNotes("[부록 · 질의응답용]\n" +
      "기준 EKF의 상태는 위치, 속도, 자세이고, 측정은 자이로로 회전을 보상한 2차원 flow입니다. 예측 단계에서 IMU 비력을 자세로 회전하고 중력을 더해 적분합니다. " +
      "보정 단계에서 칼만 이득은 R이 클수록 작아집니다. 품질 Q에서 R로 가는 규칙은 PX4 EKF2처럼 표준편차를 선형 보간해 제곱하는 형태를 출발점으로 하고, Q가 최소값보다 낮으면 측정을 제외합니다. " +
      "Q의 구성과 파라미터는 설정 구간에서만 정하고 평가 구간에서는 바꾸지 않습니다. IMU 바이어스 상태 포함 여부는 기준 EKF 구현 단계에서 결정합니다.");
  }

  // =====================================================================
  // A4. 데이터셋 및 평가 조건
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, "A4", "부록 4. 데이터셋 및 평가 조건", "Appendix · Dataset & Evaluation");
    const lx = ML, lw = 6.0, rx = 6.85, rw = MR - rx;
    box(s, { x: lx, y: 1.2, w: lw, h: 3.3, fill: { color: SKY_XL }, line: { color: SKY, width: 1 } });
    T(s, "INSANE 데이터셋 — 공개 자료로 확인한 내용", { x: lx + 0.25, y: 1.3, w: lw - 0.5, h: 0.4, fontSize: 16, bold: true, color: NAVY_D, valign: "middle" });
    T(s, [
      { text: "Brommer et al., IJRR 43(8), 2024 · Univ. of Klagenfurt / NASA JPL", options: { fontSize: 12, color: MUTED, breakLine: true } },
      { text: "센서 18종: 다중 IMU, 고해상도 하향 내비게이션 카메라, 다중 GNSS, UWB 등", options: { bullet: true, breakLine: true } },
      { text: "레이저 거리계(LRF)가 내비게이션 카메라와 같은 방향(하향)으로 장착", options: { bullet: true, breakLine: true } },
      { text: "시나리오: 실내 모션캡처 · 실외→실내 전이 · Mars analog 실외", options: { bullet: true, breakLine: true } },
      { text: "정답: 실내 OptiTrack, 실외 dual RTK-GNSS (cm급)", options: { bullet: true, bold: true, color: NAVY_D } },
    ], { x: lx + 0.25, y: 1.75, w: lw - 0.5, h: 3.1, fontSize: 15, color: TEXT, paraSpaceAfter: 6, valign: "top" });
    box(s, { x: rx, y: 1.2, w: rw, h: 3.3, fill: { color: GRAY_BG }, line: { color: LINE, width: 0.75 } });
    T(s, "10월 초 실제 파일로 확인할 항목", { x: rx + 0.25, y: 1.3, w: rw - 0.5, h: 0.4, fontSize: 16, bold: true, color: NAVY_D, valign: "middle" });
    T(s, [
      { text: "하향 카메라 해상도 · 프레임률 · 노출 조건", options: { bullet: true, breakLine: true } },
      { text: "LRF 측정 주기 · 유효 거리 · 카메라 광축과의 정렬", options: { bullet: true, breakLine: true } },
      { text: "카메라–IMU–LRF 외부 파라미터와 시간 동기화", options: { bullet: true, breakLine: true } },
      { text: "시퀀스별 정답 종류(OptiTrack / RTK)와 사용 가능 구간", options: { bullet: true, breakLine: true } },
      { text: "평탄 지면 가정이 성립하는 구간 선정", options: { bullet: true } },
    ], { x: rx + 0.25, y: 1.8, w: rw - 0.5, h: 3.05, fontSize: 15, color: TEXT, paraSpaceAfter: 6 });
    // evaluation protocol strip
    const steps = [["설정 구간", "품질 지표 · R 규칙 파라미터 결정"], ["평가 구간", "규칙 고정 후 A · B · C 동일 조건 실행"], ["정답 비교", "시간 정렬 후 RMSE · 최종 오차 · 증가량"]];
    const sw = (MR - ML - 2 * 0.45) / 3;
    steps.forEach(([t, d], i) => {
      const x = ML + i * (sw + 0.45), y = 4.8;
      box(s, { x, y, w: sw, h: 1.0, fill: { color: i === 1 ? NAVY : WHITE }, line: { color: NAVY, width: 1.25 } });
      T(s, [{ text: t, options: { bold: true, fontSize: 16, breakLine: true } }, { text: d, options: { fontSize: 13 } }],
        { x: x + 0.15, y, w: sw - 0.3, h: 1.0, color: i === 1 ? WHITE : NAVY_D, align: "center", valign: "middle" });
      if (i < 2) arrow(s, x + sw + 0.05, y + 0.5, x + sw + 0.4, y + 0.5, NAVY, 2);
    });
    src(s, "해석 시 주의: flow는 수평 속도 정보를 주므로 융합 후에도 수평 위치 오차는 서서히 누적될 수 있음 → 구간 길이를 함께 보고 · 흐림 · 저조도 · 프레임 누락은 원본 영상에 인위적으로 부여",
      { x: ML, y: 6.0, w: MR - ML, h: 0.42, fontSize: 11.5 });
    s.addNotes("[부록 · 질의응답용]\n" +
      "INSANE 데이터셋은 하향 카메라와 같은 방향으로 장착된 레이저 거리계, 다중 IMU를 포함합니다. 실내 시퀀스의 정답은 OptiTrack 모션캡처, 실외는 dual RTK-GNSS입니다. " +
      "따라서 실내 구간에 RTK 정답이 있다고 가정하지 않고, 실제 파일로 시퀀스별 정답 종류와 구간, 센서 사양, 외부 파라미터와 시간 동기화를 10월 초에 확인합니다. " +
      "평가는 설정 구간에서 규칙을 정하고, 평가 구간에서는 규칙을 고정해 세 방법을 같은 조건으로 실행한 뒤 정답과 비교합니다.");
  }

  await pres.writeFile({ fileName: OUT });
  const { applyTheme } = require("/root/.claude/skills/synced/c1f289dd-5267-4395-801d-374d068c8226_9a20d148-3bc3-41b3-9cdd-9a064927fe7b/pptx/scripts/apply_theme.js");
  await applyTheme(OUT, { name: "VDEC Navy", headFontFace: "Arial", bodyFontFace: "Arial", colors: { dk1: TEXT, lt1: WHITE, dk2: NAVY, lt2: "EEF2F8",
    accent1: NAVY, accent2: SKY, accent3: ORANGE, accent4: BLUE, accent5: LINE, accent6: MUTED, hlink: BLUE, folHlink: "6B5BA9" } });
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
