"""
INSANE 형식을 흉내 낸 합성(시뮬레이션) 데이터 생성기.

실제 데이터 없이도 of_velocity.py → MATLAB KF 전체 파이프라인을 검증하기 위한 용도.
정답(GT)을 알고 있으므로 코드가 맞게 동작하는지 수치로 확인할 수 있다.

  - 하향 카메라 20 Hz (텍스처 지면을 homography로 렌더링)
  - IMU 200 Hz (바이어스 + 잡음), LRF 30 Hz (지연 + 잡음 + 가끔 0 값)
  - 시간 오프셋: 카메라 timestamp는 실제 노출 시각보다 tau_cam 만큼 이르게 기록됨 (Kalibr timeshift)
  - 영상 열화 구간: 흐림(blur), 저조도(dark), 프레임 누락(dropout)

좌표계 (전체 코드 공통)
  W : 월드, z-up, 중력 g_W = [0, 0, -9.81]
  B : 바디(IMU), x 전방 / y 좌측 / z 상방
  C : 카메라, x 영상 오른쪽 / y 영상 아래 / z 광축(지면 방향)

사용법:  python make_demo_data.py --out ../data/demo_raw
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
import yaml
from scipy.spatial.transform import Rotation as Rot

# ---------------- 시뮬레이션 파라미터 ----------------
T_END = 60.0
IMU_HZ, CAM_HZ, LRF_HZ, GT_HZ = 200, 20, 30, 100
W_IMG, H_IMG = 480, 360
K = np.array([[240.0, 0, 240.0], [0, 240.0, 180.0], [0, 0, 1]])   # FOV ≈ 90°

R_BC = np.array([[0, -1, 0], [-1, 0, 0], [0, 0, -1]], float)       # 카메라 → 바디 (하향)
r_BC = np.array([0.05, 0.0, -0.03])                                  # 카메라 레버암 [m]

TAU_CAM = 0.015      # t_imu = t_cam + TAU_CAM
TAU_LRF = 0.020      # LRF는 실제보다 늦게 찍힘
BIAS_G = np.array([0.010, -0.008, 0.005])
BIAS_A = np.array([0.05, -0.04, 0.08])
SIG_G, SIG_A, SIG_LRF = 0.003, 0.03, 0.025

DEGRADE = [  # (시작, 끝, 종류)
    (20.0, 27.0, "blur"),
    (38.0, 45.0, "dark"),
    (52.0, 54.5, "dropout"),
]

TEX_SIZE, TEX_RES = 4000, 0.01   # 40 m x 40 m 지면, 1 cm/px
G_W = np.array([0, 0, -9.81])


# ---------------- 궤적 (해석식) ----------------
def pos(t):
    return np.array([6 * np.sin(0.2 * t), 4 * np.sin(0.4 * t), 3.0 + 0.8 * np.sin(0.15 * t)])


def euler(t):  # roll, pitch, yaw (ZYX)
    return np.array([0.12 * np.sin(0.7 * t), 0.10 * np.sin(0.5 * t + 1.0), 0.6 * np.sin(0.1 * t)])


def rot_wb(t):
    r, p, y = euler(t)
    return Rot.from_euler("ZYX", [y, p, r]).as_matrix()


def kinematics(t, h=1e-4):
    """수치미분으로 v_W, a_W, omega_B 계산 (궤적이 매끄러우므로 충분히 정확)."""
    v = (pos(t + h) - pos(t - h)) / (2 * h)
    a = (pos(t + h) - 2 * pos(t) + pos(t - h)) / h**2
    w = Rot.from_matrix(rot_wb(t - h).T @ rot_wb(t + h)).as_rotvec() / (2 * h)
    return v, a, w


# ---------------- 지면 텍스처 & 렌더링 ----------------
def make_texture(rng):
    tex = np.zeros((TEX_SIZE, TEX_SIZE), np.float32)
    for scale, amp in [(4, 1.0), (16, 0.8), (64, 0.6), (256, 0.4)]:
        n = rng.standard_normal((TEX_SIZE // scale, TEX_SIZE // scale)).astype(np.float32)
        tex += amp * cv2.resize(n, (TEX_SIZE, TEX_SIZE), interpolation=cv2.INTER_CUBIC)
    tex = cv2.GaussianBlur(tex, (0, 0), 1.0)
    tex = (tex - tex.min()) / (tex.max() - tex.min())
    return (40 + 180 * tex).astype(np.uint8)


def render(tex, t_true):
    """지면(z=0) 평면 → 영상 homography:  x ~ K [r1 r2 t] S [u v 1]^T"""
    R_wc = rot_wb(t_true) @ R_BC
    p_wc = pos(t_true) + rot_wb(t_true) @ r_BC
    R_cw = R_wc.T
    c = TEX_SIZE / 2
    S = np.array([[TEX_RES, 0, -c * TEX_RES], [0, TEX_RES, -c * TEX_RES], [0, 0, 1]])
    H = K @ np.column_stack([R_cw[:, 0], R_cw[:, 1], -R_cw @ p_wc]) @ S
    return cv2.warpPerspective(tex, H, (W_IMG, H_IMG), flags=cv2.INTER_LINEAR)


def degrade(img, t, rng):
    for t0, t1, kind in DEGRADE:
        if t0 <= t < t1:
            if kind == "blur":
                k = np.zeros((31, 31), np.float32); k[15, :] = 1 / 31      # 모션블러
                img = cv2.GaussianBlur(cv2.filter2D(img, -1, k), (0, 0), 3.0)
            elif kind == "dark":
                f = img.astype(np.float32) * 0.05 + rng.normal(0, 4.0, img.shape)
                img = np.clip(f, 0, 255).astype(np.uint8)
            elif kind == "dropout":
                return None
    return img


def lrf_range(t_true):
    """LRF는 카메라 광축 방향으로 지면까지 거리를 잰다 (co-mounted)."""
    R = rot_wb(t_true)
    p_l = pos(t_true) + R @ r_BC
    d_w = R @ R_BC @ np.array([0, 0, 1.0])
    return -p_l[2] / d_w[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../data/demo_raw")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    out = Path(args.out); (out / "cam").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    # IMU
    t_imu = np.arange(0, T_END, 1 / IMU_HZ)
    rows = []
    for t in t_imu:
        _, a_w, w_b = kinematics(t)
        f_b = rot_wb(t).T @ (a_w - G_W)                     # 비력(specific force)
        rows.append([t, *(w_b + BIAS_G + rng.normal(0, SIG_G, 3)),
                     *(f_b + BIAS_A + rng.normal(0, SIG_A, 3))])
    np.savetxt(out / "imu.csv", rows, delimiter=",", fmt="%.6f",
               header="t,wx,wy,wz,ax,ay,az", comments="")

    # LRF (stamp = 실제시각 + TAU_LRF, 1% 확률로 0 값)
    rows = []
    for t in np.arange(0.01, T_END, 1 / LRF_HZ):
        r = lrf_range(t) + rng.normal(0, SIG_LRF)
        rows.append([t + TAU_LRF, 0.0 if rng.random() < 0.01 else r])
    np.savetxt(out / "lrf.csv", rows, delimiter=",", fmt="%.6f", header="t,range", comments="")

    # GT
    rows = []
    for t in np.arange(0, T_END, 1 / GT_HZ):
        v, _, _ = kinematics(t)
        qx, qy, qz, qw = Rot.from_matrix(rot_wb(t)).as_quat()
        rows.append([t, *pos(t), *v, qw, qx, qy, qz])
    np.savetxt(out / "gt.csv", rows, delimiter=",", fmt="%.6f",
               header="t,px,py,pz,vx,vy,vz,qw,qx,qy,qz", comments="")

    # 카메라 (stamp = 실제 노출시각 - TAU_CAM, 약간의 지터)
    tex = make_texture(rng)
    rows = []
    for k, t_nom in enumerate(np.arange(0.05, T_END - 0.05, 1 / CAM_HZ)):
        t_true = t_nom + rng.normal(0, 0.001)
        img = degrade(render(tex, t_true), t_true, rng)
        if img is None:
            continue
        name = f"{k:06d}.jpg"
        cv2.imwrite(str(out / "cam" / name), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        rows.append(f"{t_true - TAU_CAM:.6f},{name}")
    (out / "cam" / "timestamps.csv").write_text("t,file\n" + "\n".join(rows) + "\n")

    calib = {
        "K": [float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2])],
        "dist_model": "radtan", "D": [0.0, 0.0, 0.0, 0.0],
        "R_BC": R_BC.tolist(), "r_BC": r_BC.tolist(),
        "timeshift_cam_imu": TAU_CAM, "lrf_delay": TAU_LRF,
        "truth": {"bias_gyro": BIAS_G.tolist(), "bias_acc": BIAS_A.tolist(),
                  "degrade": [list(d) for d in DEGRADE]},
    }
    (out / "calib.yaml").write_text(yaml.safe_dump(calib, sort_keys=False))
    print(f"[done] {len(rows)} images → {out}")


if __name__ == "__main__":
    main()
