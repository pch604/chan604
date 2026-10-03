"""
데이터셋 폴더 점검 → of_velocity.py 설정 초안 자동 생성

INSANE 처럼 CSV 열 이름/시간 단위를 미리 모를 때 사용.
  1) 모든 CSV 의 헤더, 행 수, 시간 단위(s/ms/us/ns), 주기[Hz] 출력
  2) 열 이름 + 주기 + 내용으로 역할 추정 (IMU / LRF / 카메라 timestamp / GT)
  3) Kalibr 보정 YAML(T_cam_imu 포함) 탐색
  4) config 초안 저장 → 반드시 눈으로 확인 후 사용 ('# 확인' 표시)

사용법:  python inspect_dataset.py ../data/insane_raw/<시퀀스> --out config_<시퀀스>.yaml
"""
import argparse
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

# 표준이름 → 열 이름 정규식 (위에서부터 먼저 맞는 것)
PATTERNS = {
    "t":  [r"^(t|time|timestamp|stamp|ts)$", r"time|stamp"],
    "wx": [r"^(w|omega|gyro|g|ang\w*)_?x$", r"(gyro|ang|omega).*x"],
    "wy": [r"^(w|omega|gyro|g|ang\w*)_?y$", r"(gyro|ang|omega).*y"],
    "wz": [r"^(w|omega|gyro|g|ang\w*)_?z$", r"(gyro|ang|omega).*z"],
    "ax": [r"^(a|acc\w*|lin\w*)_?x$", r"acc.*x"],
    "ay": [r"^(a|acc\w*|lin\w*)_?y$", r"acc.*y"],
    "az": [r"^(a|acc\w*|lin\w*)_?z$", r"acc.*z"],
    "range": [r"range|dist|lrf|lidar|height"],
    "px": [r"^(p|pos\w*)_?x$"], "py": [r"^(p|pos\w*)_?y$"], "pz": [r"^(p|pos\w*)_?z$"],
    "vx": [r"^(v|vel\w*)_?x$"], "vy": [r"^(v|vel\w*)_?y$"], "vz": [r"^(v|vel\w*)_?z$"],
    "qw": [r"^(q|quat\w*|ori\w*)_?w$"], "qx": [r"^(q|quat\w*|ori\w*)_?x$"],
    "qy": [r"^(q|quat\w*|ori\w*)_?y$"], "qz": [r"^(q|quat\w*|ori\w*)_?z$"],
}
ROLE_KEYS = {
    "imu": ["t", "wx", "wy", "wz", "ax", "ay", "az"],
    "lrf": ["t", "range"],
    "gt":  ["t", "px", "py", "pz", "qw", "qx", "qy", "qz"],
}


def match(cols, key, used=()):
    for pat in PATTERNS[key]:
        for c in cols:
            if c not in used and re.search(pat, c.lower()):
                return c
    return None


def time_scale(t):
    """값의 크기로 시간 단위 추정 (epoch 기준 / 상대 시간 모두 고려)."""
    m = np.nanmedian(np.abs(t))
    dt = np.nanmedian(np.diff(t))
    if m > 1e17 or dt > 1e5:
        return 1e-9, "ns"
    if m > 1e14 or dt > 1e2:
        return 1e-6, "us"
    if m > 1e11:
        return 1e-3, "ms"
    return 1.0, "s"


def inspect_csv(path):
    df = pd.read_csv(path)
    df.columns = [c.strip().lstrip("#").strip() for c in df.columns]
    cols = list(df.columns)
    info = {"path": path, "cols": cols, "n": len(df)}
    tcol = match(cols, "t") or cols[0]
    t = pd.to_numeric(df[tcol], errors="coerce").to_numpy(float)
    sc, unit = time_scale(t)
    info.update(tcol=tcol, scale=sc, unit=unit,
                hz=1.0 / (np.nanmedian(np.diff(t)) * sc) if len(t) > 1 else np.nan,
                span=(np.nanmax(t) - np.nanmin(t)) * sc)
    img_col = next((c for c in cols if not pd.api.types.is_numeric_dtype(df[c])
                    and str(df[c].iloc[0]).lower().endswith(IMG_EXT)), None)
    info["img_col"] = img_col

    # 역할별 열 매핑 + 점수 (매칭된 비율)
    info["maps"] = {}
    for role, keys in ROLE_KEYS.items():
        m, used = {}, set()
        for k in keys:
            c = tcol if k == "t" else match(cols, k, used)
            if c:
                m[k] = c
                used.add(c)
        info["maps"][role] = (len(m) / len(keys), m)
    if img_col:
        info["maps"]["cam"] = (1.0, {"t": tcol, "file": img_col})
    return info


def pick(infos, role, hz_range, prefer=()):
    """역할 점수가 가장 높은 CSV. 동점이면 주기 범위·경로 키워드로 결정."""
    cands = []
    for i in infos:
        sc, m = i["maps"].get(role, (0, {}))
        if sc < 1.0:
            continue
        bonus = int(hz_range[0] <= i["hz"] <= hz_range[1]) + int(any(p in i["path"].lower() for p in prefer))
        cands.append((bonus, i))
    cands.sort(key=lambda x: -x[0])
    return cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(a.root)

    csvs = sorted(str(p) for p in root.rglob("*.csv"))
    infos = []
    print(f"\n[CSV] {len(csvs)}개")
    for p in csvs:
        try:
            i = inspect_csv(p)
        except Exception as e:                              # 형식이 다른 파일은 건너뜀
            print(f"  ! {p}: {e}")
            continue
        infos.append(i)
        print(f"  {os.path.relpath(p, root):40s} n={i['n']:7d}  {i['hz']:7.1f} Hz  "
              f"{i['span']:7.1f} s  t='{i['tcol']}'[{i['unit']}]  cols={i['cols'][:10]}")

    kal = []
    for p in sorted(root.rglob("*.yaml")) + sorted(root.rglob("*.yml")):
        try:
            y = yaml.safe_load(p.read_text())
        except Exception:
            continue
        if isinstance(y, dict) and any(isinstance(v, dict) and "T_cam_imu" in v for v in y.values()):
            kal.append((str(p), [k for k, v in y.items() if isinstance(v, dict) and "T_cam_imu" in v]))
    print(f"\n[Kalibr YAML] {kal if kal else '없음 → calib 를 직접 입력'}")

    sel = {
        "imu": pick(infos, "imu", (100, 1000), prefer=("px4",)),
        "lrf": pick(infos, "lrf", (10, 100), prefer=("lrf", "lidar", "range")),
        "cam": pick(infos, "cam", (5, 60), prefer=("nav",)),
        "gt":  pick(infos, "gt", (1, 1000), prefer=("ground", "gt", "truth")),
    }
    print("\n[역할 추정]  (* = 선택, 나머지는 후보)")
    for role, cands in sel.items():
        for n, (_, i) in enumerate(cands):
            print(f"  {role:4s} {'*' if n == 0 else ' '} {os.path.relpath(i['path'], root)}  "
                  f"{i['maps'][role][1]}")
        if not cands:
            print(f"  {role:4s}   (못 찾음 → 직접 지정)")

    if a.out:
        write_config(a.out, root, sel, kal)


def write_config(out, root, sel, kal):
    out = Path(out)
    rel = lambda p: os.path.relpath(p, root)                # noqa: E731
    first = {r: (c[0][1] if c else None) for r, c in sel.items()}
    for need in ("imu", "lrf", "cam"):
        if first[need] is None:
            raise SystemExit(f"{need} CSV 를 찾지 못함 → config_insane.yaml 을 직접 수정하세요")
    scales = {first[r]["scale"] for r in first if first[r]}
    if len(scales) > 1:
        print("  ! 파일마다 시간 단위가 다름 → time_scale 확인 필요")
    cam = first["cam"]
    cfg = {
        "dataset": {
            "root": os.path.relpath(root, out.resolve().parent),
            "imu_csv": rel(first["imu"]["path"]),
            "lrf_csv": rel(first["lrf"]["path"]),
            "cam_csv": rel(cam["path"]),
            "cam_dir": rel(Path(cam["path"]).parent),
            "gt_csv": rel(first["gt"]["path"]) if first["gt"] else None,
            "time_scale": first["imu"]["scale"],
            "columns": {r: first[r]["maps"][r][1] for r in ("imu", "lrf", "cam", "gt") if first[r]},
        },
    }
    if not first["gt"]:
        del cfg["dataset"]["gt_csv"]
    if kal:
        cfg["kalibr_yaml"] = os.path.relpath(kal[0][0], out.resolve().parent)
        cfg["kalibr_cam"] = kal[0][1][0]
    tmpl = yaml.safe_load((Path(__file__).parent / "config_insane.yaml").read_text())
    cfg["calib"] = dict(tmpl["calib"])
    if not kal:                                             # Kalibr 없음 → 직접 입력할 자리
        cfg["calib"] = {"K": "TODO [fx, fy, cx, cy]", "dist_model": "radtan", "D": [0.0, 0.0, 0.0, 0.0],
                        "T_cam_imu": "TODO 4x4", "timeshift_cam_imu": 0.0, **cfg["calib"]}
    cfg["tracker"], cfg["quality"] = tmpl["tracker"], tmpl["quality"]
    cfg["output_dir"] = tmpl["output_dir"]
    head = ("# inspect_dataset.py 가 만든 초안 — 실행 전 반드시 확인\n"
            "#  - columns 매핑 (특히 IMU 가 PX4 main IMU 인지), time_scale\n"
            "#  - Kalibr 의 cam 이 하향 nav camera 인지 (kalibr_cam)\n"
            "#  - lrf_delay (모르면 0)\n")
    out.write_text(head + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    print(f"\n[저장] {out}")


if __name__ == "__main__":
    main()
