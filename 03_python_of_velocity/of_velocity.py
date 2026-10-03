"""
하향 카메라 Optical Flow → (회전 제거) → 미터 단위 속도 측정치 + 시간 동기화

[처리 흐름]  영상쌍 (k-1, k) 마다
  1) 특징점 추적       : Shi-Tomasi + KLT 피라미드, 정방향-역방향(FB) 검사
                         (VINS-Mono / OpenVINS feature tracker 방식)
  2) 왜곡 보정         : 픽셀 → 정규화 좌표 (x, y, 1)
  3) 회전 성분 제거    : [t_{k-1}, t_k] 자이로 적분 → R_c1c0 로 예측한 위치를 빼줌
                         (PX4 EKF2: flow_compensated = flow_rate - gyro 와 같은 개념)
  4) 속도 추정         : 남은 병진 flow = 운동장(motion field) 모델
                            u = (-v_x + x v_z) / Z,  w = (-v_y + y v_z) / Z
                         Z = LRF 거리, robust LS(Huber) 로 카메라 속도 v_C 를 품
  5) 바디 속도         : v_B = R_BC v_C - ω_B × r_BC   (레버암 보정)
  6) 품질 Q            : 특징점 수 · FB 통과율 · 잔차 → [0,1]  (MATLAB 적응 R 에 사용)
  7) 바이어스 민감도 M : 자이로 바이어스가 속도로 새는 양 (v_B 오차 = M b_g) → MATLAB 이 b_g 추정

[시간 동기화]  김민수·안창선(2025, IEEE Access) 의 delay 처리 방식을 따름
  - 기준 시계 = IMU 시계 (논문의 ego 차량 시계 역할)
  - 지연 보정 (논문 식 10) : z_true(t - τ) = z_meas(t)
        카메라 : t = t_cam + timeshift_cam_imu   (Kalibr 보정값)
        LRF    : t_valid = t_stamp - lrf_delay
  - 동기화 (논문 Fig.3)    : 느린/다른 주기 신호(자이로 200 Hz, LRF 30 Hz)를
                             카메라 시각에 맞춰 보간/적분
  - 각 측정치는 두 개의 시각을 가짐
        t_valid : 이 측정이 나타내는 상태의 시각 (영상쌍 중간 시각)
        t_avail : 필터가 이 값을 받는 시각 (t_k + 처리지연)
    → MATLAB 에서 t_avail 에 도착하면 t_valid 로 되돌아가 보정 후 재추정 (논문 Fig.4)

사용법
  python of_velocity.py --config config_demo.yaml
  python of_velocity.py --config config_insane.yaml --backend dis
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import yaml
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot


# =====================================================================
# 0. 데이터 로드 & 기준 시계로 변환
# =====================================================================
def load_csv(path, cols, time_scale):
    """cols: {표준이름: 원본 헤더이름}.  시간은 초 단위로 변환."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lstrip("#").strip() for c in df.columns]
    out = pd.DataFrame({k: df[v] for k, v in cols.items()})
    out["t"] = out["t"] * time_scale
    return out.sort_values("t").reset_index(drop=True)


def load_dataset(cfg):
    d, c = cfg["dataset"], cfg["calib"]
    root = Path(cfg["_dir"]) / d["root"]
    ts = d["time_scale"]

    imu = load_csv(root / d["imu_csv"], d["columns"]["imu"], ts)
    lrf = load_csv(root / d["lrf_csv"], d["columns"]["lrf"], ts)
    cam = load_csv(root / d["cam_csv"], d["columns"]["cam"], ts)
    gt = load_csv(root / d["gt_csv"], d["columns"]["gt"], ts) if d.get("gt_csv") else None

    # --- 지연 보정 (논문 식 10): 모두 IMU 시계의 '실제 발생 시각'으로 ---
    cam["t"] = cam["t"] + c["timeshift_cam_imu"]
    lrf = lrf[(lrf["range"] > c["lrf_min"]) & (lrf["range"] < c["lrf_max"])]   # 0 값 등 제거
    lrf = lrf.assign(t_avail=lrf["t"], t=lrf["t"] - c["lrf_delay"])

    # 시작 시각을 0 으로 (MATLAB 그림 보기 편하게)
    t0 = imu["t"].iloc[0]
    for df in (imu, lrf, cam, gt):
        if df is not None:
            df["t"] -= t0
    lrf["t_avail"] -= t0
    cam["path"] = [str(root / d["cam_dir"] / f) for f in cam["file"]]
    return imu, lrf, cam, gt


# =====================================================================
# 1. 동기화 유틸: 자이로 적분 / 보간
# =====================================================================
def gyro_rotation(t_imu, w_imu, t0, t1):
    """R_b0b1 : t1 시점 바디 → t0 시점 바디.  구간 끝은 선형보간, 내부는 중점적분."""
    inside = (t_imu > t0) & (t_imu < t1)
    ts = np.concatenate([[t0], t_imu[inside], [t1]])
    ws = np.column_stack([np.interp(ts, t_imu, w_imu[:, i]) for i in range(3)])
    R = np.eye(3)
    for i in range(len(ts) - 1):
        w_mid = 0.5 * (ws[i] + ws[i + 1])
        R = R @ Rot.from_rotvec(w_mid * (ts[i + 1] - ts[i])).as_matrix()
    return R


def interp_valid(t_query, t, y, max_gap):
    """t_query 양옆 샘플 간격이 max_gap 보다 크면 NaN (신호 끊김)."""
    i = np.searchsorted(t, t_query)
    if i == 0 or i >= len(t) or t[i] - t[i - 1] > max_gap:
        return np.nan
    return float(np.interp(t_query, t, y))


# =====================================================================
# 2. 특징점 추적 (backend: klt / dis / raft)
# =====================================================================
class Tracker:
    def __init__(self, cfg):
        self.c = cfg
        self.backend = cfg["backend"]
        self.clahe = cv2.createCLAHE(2.0, (8, 8)) if cfg["clahe"] else None
        if self.backend == "dis":
            self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        if self.backend == "raft":
            self._init_raft()

    def prep(self, img):
        return self.clahe.apply(img) if self.clahe is not None else img

    def detect(self, img):
        p = cv2.goodFeaturesToTrack(img, self.c["max_corners"], self.c["quality_level"],
                                    self.c["min_distance"], blockSize=7)
        return np.empty((0, 2), np.float32) if p is None else p.reshape(-1, 2)

    def track(self, img0, img1):
        """반환: p0, p1 (N,2 픽셀), 검출 개수 n_det"""
        img0, img1 = self.prep(img0), self.prep(img1)
        p0 = self.detect(img0)
        if len(p0) < 8:
            return p0, p0, len(p0)
        if self.backend == "klt":
            p1, fb = self._klt(img0, img1, p0)
        else:
            f01, f10 = self._dense(img0, img1)
            p1 = p0 + sample(f01, p0)
            fb = np.linalg.norm(p1 + sample(f10, p1) - p0, axis=1)  # 왕복 오차
        h, w = img0.shape
        ok = (fb < self.c["fb_thresh"]) & inside(p1, w, h)
        return p0[ok], p1[ok], len(p0)

    def _klt(self, img0, img1, p0):
        lk = dict(winSize=(self.c["win"], self.c["win"]), maxLevel=self.c["levels"],
                  criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
        p1, st1, _ = cv2.calcOpticalFlowPyrLK(img0, img1, p0, None, **lk)
        p0b, st2, _ = cv2.calcOpticalFlowPyrLK(img1, img0, p1, None, **lk)
        fb = np.linalg.norm(p0 - p0b, axis=1)
        fb[(st1.ravel() == 0) | (st2.ravel() == 0)] = np.inf
        return p1, fb

    def _dense(self, img0, img1):
        if self.backend == "dis":
            return self.dis.calc(img0, img1, None), self.dis.calc(img1, img0, None)
        return self._raft(img0, img1), self._raft(img1, img0)

    # --- (선택) 딥러닝 Optical Flow: torchvision RAFT ---------------------
    def _init_raft(self):
        import torch
        from torchvision.models.optical_flow import Raft_Small_Weights, raft_small
        self.torch = torch
        self.raft = raft_small(weights=Raft_Small_Weights.DEFAULT).eval()

    def _raft(self, a, b):
        torch = self.torch
        h, w = a.shape
        H8, W8 = (h + 7) // 8 * 8, (w + 7) // 8 * 8          # RAFT 입력은 8의 배수
        def to_t(g):
            g = cv2.resize(g, (W8, H8))
            t = torch.from_numpy(np.repeat(g[None], 3, 0)).float()[None]
            return t / 127.5 - 1.0                           # [-1, 1] 정규화
        with torch.no_grad():
            flow = self.raft(to_t(a), to_t(b))[-1][0].permute(1, 2, 0).numpy()
        flow = cv2.resize(flow, (w, h))
        flow[..., 0] *= w / W8; flow[..., 1] *= h / H8
        return flow


def sample(flow, p):
    """dense flow (H,W,2) 를 점 p 위치에서 bilinear 샘플."""
    m = p.reshape(-1, 1, 2).astype(np.float32)
    fx = cv2.remap(flow[..., 0], m[..., 0], m[..., 1], cv2.INTER_LINEAR)
    fy = cv2.remap(flow[..., 1], m[..., 0], m[..., 1], cv2.INTER_LINEAR)
    return np.column_stack([fx.ravel(), fy.ravel()])


def inside(p, w, h):
    return (p[:, 0] >= 0) & (p[:, 0] < w - 1) & (p[:, 1] >= 0) & (p[:, 1] < h - 1)


# =====================================================================
# 3. 회전 제거 + 속도 추정 (핵심)
# =====================================================================
class Camera:
    def __init__(self, c):
        fx, fy, cx, cy = c["K"]
        self.K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], float)
        self.D = np.array(c["D"], float)
        self.model = c["dist_model"]
        self.f = 0.5 * (fx + fy)

    def normalize(self, p):
        p = p.reshape(-1, 1, 2).astype(np.float64)
        if self.model == "equidistant":
            return cv2.fisheye.undistortPoints(p, self.K, self.D).reshape(-1, 2)
        return cv2.undistortPoints(p, self.K, self.D).reshape(-1, 2)


def skew(w):
    return np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])


def derotate(f0, R_c1c0):
    """f0(정규화좌표)를 순수 회전만 했을 때 프레임1에 보일 위치."""
    g = np.column_stack([f0, np.ones(len(f0))]) @ R_c1c0.T
    return g[:, :2] / g[:, 2:3]


def solve_velocity(f_mid, disp, Z, dt, f_px, huber_px):
    """
    병진 flow 로 카메라 속도 v_C 추정 (평면 지면, 깊이 Z ≈ LRF 거리).
        disp = (A v) dt / Z ,  A = [[-1, 0, x], [0, -1, y]]
    잔차는 픽셀 단위로 정의 → Huber 임계값을 px 로 직관적으로 설정.
    """
    x, y = f_mid[:, 0], f_mid[:, 1]
    n = len(x)
    A = np.zeros((2 * n, 3))
    A[0::2, 0], A[0::2, 2] = -1, x
    A[1::2, 1], A[1::2, 2] = -1, y
    J = A * (dt / Z) * f_px                     # [px / (m/s)]
    b = disp.reshape(-1) * f_px                 # [px]

    v0 = np.linalg.lstsq(J, b, rcond=None)[0]
    sol = least_squares(lambda v: J @ v - b, v0, loss="huber", f_scale=huber_px)
    r = (J @ sol.x - b).reshape(-1, 2)
    r_norm = np.linalg.norm(r, axis=1)

    sigma = 1.4826 * np.median(r_norm) + 1e-3   # MAD 기반 robust 잔차 크기 [px]
    inl = r_norm < 3 * max(sigma, huber_px)
    Ji = J[np.repeat(inl, 2)]
    JtJ_inv = np.linalg.inv(Ji.T @ Ji + 1e-9 * np.eye(3))
    cov = sigma**2 * JtJ_inv

    # 자이로 바이어스 민감도 M_c :  v_C 오차 = M_c · b_C
    #   바이어스 낀 자이로로 회전을 빼면 '-회전 flow(b)' 가 남고, 그것이 LS 를 거쳐 속도로 새어 들어감
    #   회전 flow (단위 ω):  [[xy, -(1+x²), y], [1+y², -xy, -x]]
    Bw = np.zeros((2 * n, 3))
    Bw[0::2] = np.column_stack([x * y, -(1 + x**2), y])
    Bw[1::2] = np.column_stack([1 + y**2, -x * y, -x])
    M_c = -JtJ_inv @ Ji.T @ (Bw[np.repeat(inl, 2)] * dt * f_px)
    return sol.x, cov, inl, sigma, M_c


def flow_quality(n_det, n_trk, n_inl, resid_px, qc):
    """0~1 품질.  특징점 수 × 추적 성공률 × 잔차 패널티 (성공률만 보면 저조도에서 속는다)."""
    if n_det == 0:
        return 0.0
    q_num = min(1.0, n_inl / qc["n_ref"])
    q_trk = n_trk / n_det
    q_res = 1.0 / (1.0 + (resid_px / qc["resid_ref_px"]) ** 2)
    return float(q_num * q_trk * q_res)


# =====================================================================
# 4. 메인 루프
# =====================================================================
def run(cfg):
    imu, lrf, cam, gt = load_dataset(cfg)
    c, tc, qc = cfg["calib"], cfg["tracker"], cfg["quality"]
    R_BC, r_BC = np.array(c["R_BC"], float), np.array(c["r_BC"], float)
    R_CB = R_BC.T
    s = tc.get("scale", 1.0)                      # 고해상도 영상 축소 (INSANE 2056x1542)
    camera, tracker = Camera({**c, "K": [k * s for k in c["K"]]}), Tracker(tc)

    t_imu = imu["t"].to_numpy()
    w_imu = imu[["wx", "wy", "wz"]].to_numpy()
    t_lrf, d_lrf = lrf["t"].to_numpy(), lrf["range"].to_numpy()

    n = len(cam) if cfg["max_frames"] is None else min(len(cam), cfg["max_frames"])
    rows, img0 = [], None
    for k in range(n):
        img1 = cv2.imread(cam["path"][k], cv2.IMREAD_GRAYSCALE)
        if s != 1.0:
            img1 = cv2.resize(img1, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        if k == 0 or img0 is None:
            img0 = img1
            continue
        t0, t1 = cam["t"][k - 1], cam["t"][k]
        dt = t1 - t0
        t_valid = 0.5 * (t0 + t1)                 # 영상쌍 = 구간 평균속도 → 중간 시각
        t_avail = t1 + c["proc_latency"]          # 필터에 도착하는 시각
        row = dict(t_valid=t_valid, t_avail=t_avail, dt=dt)

        # (동기화) 자이로 적분 → 카메라 회전,  LRF 보간 → 깊이
        R_b0b1 = gyro_rotation(t_imu, w_imu, t0, t1)
        R_c1c0 = (R_CB @ R_b0b1 @ R_BC).T
        Z = interp_valid(t_valid, t_lrf, d_lrf, c["lrf_max_gap"])
        w_b = np.array([np.interp(t_valid, t_imu, w_imu[:, i]) for i in range(3)])

        p0, p1, n_det = tracker.track(img0, img1)
        ok = len(p0) >= tc["min_tracks"] and np.isfinite(Z) and dt < tc["max_dt"]
        if ok:
            f0, f1 = camera.normalize(p0), camera.normalize(p1)
            f0r = derotate(f0, R_c1c0)            # ← 회전 성분 제거
            disp = f1 - f0r                        # 남은 것 = 병진에 의한 이동
            v_c, cov_c, inl, sig, M_c = solve_velocity(0.5 * (f0r + f1), disp, Z, dt,
                                                       camera.f, tc["huber_px"])
            v_b = R_BC @ v_c - np.cross(w_b, r_BC)
            cov_b = R_BC @ cov_c @ R_BC.T
            M_b = R_BC @ M_c @ R_CB + skew(r_BC)            # 바디 기준 (+ 레버암 항)
            flow_rate = np.median(disp, axis=0) / dt                  # [rad/s] (PX4 스타일)
            raw_rate = np.median(f1 - f0, axis=0) / dt                  # 회전 제거 전
            q = flow_quality(n_det, len(p0), int(inl.sum()), sig, qc)
            row.update(vx=v_b[0], vy=v_b[1], vz=v_b[2],
                       sx=np.sqrt(cov_b[0, 0]), sy=np.sqrt(cov_b[1, 1]), sz=np.sqrt(cov_b[2, 2]),
                       flow_x=flow_rate[0], flow_y=flow_rate[1],
                       raw_flow_x=raw_rate[0], raw_flow_y=raw_rate[1],
                       **{f"m{i}{j}": M_b[i, j] for i in range(3) for j in range(3)},
                       range=Z, n_det=n_det, n_trk=len(p0), n_inl=int(inl.sum()),
                       resid_px=sig, quality=q, valid=1)
        else:
            row.update(range=Z, n_det=n_det, n_trk=len(p0), quality=0.0, valid=0)
        rows.append(row)
        img0 = img1
        if k % 100 == 0:
            print(f"  frame {k:5d}/{n}  n_trk={len(p0):3d}  Q={row['quality']:.2f}")

    # ---------------- 저장 (MATLAB 입력) ----------------
    out = Path(cfg["_dir"]) / cfg["output_dir"]
    out.mkdir(parents=True, exist_ok=True)
    cols = ["t_valid", "t_avail", "dt", "vx", "vy", "vz", "sx", "sy", "sz",
            "flow_x", "flow_y", "raw_flow_x", "raw_flow_y", "range",
            "m00", "m01", "m02", "m10", "m11", "m12", "m20", "m21", "m22",
            "n_det", "n_trk", "n_inl", "resid_px", "quality", "valid"]
    pd.DataFrame(rows).reindex(columns=cols).fillna(0).to_csv(out / "of_meas.csv", index=False, float_format="%.6f")
    imu.to_csv(out / "imu.csv", index=False, float_format="%.6f")
    lrf[["t", "t_avail", "range"]].rename(columns={"t": "t_valid"}).to_csv(
        out / "lrf.csv", index=False, float_format="%.6f")
    if gt is not None:
        save_gt(gt, out / "gt.csv")
    if "truth" in c:                              # 합성 데이터: 참 바이어스 (검증용)
        tb = c["truth"]
        pd.DataFrame([tb["bias_gyro"] + tb["bias_acc"]],
                     columns=["bgx", "bgy", "bgz", "bax", "bay", "baz"]).to_csv(out / "truth_bias.csv", index=False)
    pd.DataFrame([np.array(c["R_BC"]).ravel(order="F").tolist() + list(c["r_BC"])],
                 columns=[f"R{i}" for i in range(9)] + ["rx", "ry", "rz"]
                 ).to_csv(out / "extrinsic.csv", index=False)   # MATLAB 용 (column-major)
    print(f"[done] {len(rows)} OF 측정 → {out}")


def save_gt(gt, path):
    if not {"vx", "vy", "vz"} <= set(gt.columns):                 # 속도 없으면 미분
        for a in "xyz":
            gt["v" + a] = np.gradient(gt["p" + a].to_numpy(), gt["t"].to_numpy())
    gt[["t", "px", "py", "pz", "vx", "vy", "vz", "qw", "qx", "qy", "qz"]].to_csv(
        path, index=False, float_format="%.6f")


def load_kalibr(path, cam="cam0"):
    """Kalibr camchain-imucam.yaml → calib 항목 (INSANE 보정 파일 형식)."""
    k = yaml.safe_load(Path(path).read_text())[cam]
    if k.get("camera_model", "pinhole") != "pinhole":
        raise ValueError(f"지원하지 않는 camera_model: {k['camera_model']}")
    return {"K": k["intrinsics"], "D": k["distortion_coeffs"],
            "dist_model": k["distortion_model"], "T_cam_imu": k["T_cam_imu"],
            "timeshift_cam_imu": k.get("timeshift_cam_imu", 0.0)}


def load_config(path):
    """
    calib 우선순위 (뒤가 앞을 덮어씀):
        kalibr_yaml  <  calib_file  <  config 의 calib 항목
    """
    cfg = yaml.safe_load(Path(path).read_text())
    cfg["_dir"] = str(Path(path).resolve().parent)
    base = Path(cfg["_dir"])
    c = {}
    if cfg.get("kalibr_yaml"):
        c.update(load_kalibr(base / cfg["kalibr_yaml"], cfg.get("kalibr_cam", "cam0")))
    if cfg.get("calib_file"):
        c.update(yaml.safe_load((base / cfg["calib_file"]).read_text()))
    c.update(cfg.get("calib") or {})
    if "T_cam_imu" in c:                          # IMU 좌표 → 카메라 좌표  ⇒  R_BC, r_BC
        T = np.array(c["T_cam_imu"], float)
        c["R_BC"] = T[:3, :3].T.tolist()
        c["r_BC"] = (-T[:3, :3].T @ T[:3, 3]).tolist()
    cfg["calib"] = c
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config_demo.yaml")
    ap.add_argument("--backend", choices=["klt", "dis", "raft"])
    ap.add_argument("--max-frames", type=int)
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.backend:
        cfg["tracker"]["backend"] = a.backend
    cfg["max_frames"] = a.max_frames
    run(cfg)


if __name__ == "__main__":
    main()
