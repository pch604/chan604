# chan604 — 학생자율연구II: GPS 없는 환경에서 비전 보조 항법

하향 카메라 **Optical Flow + IMU + LRF** 를 칼만필터로 융합해 드론의 위치·속도·자세를 추정한다.
영상 품질이 떨어질 때(흐림, 저조도, 프레임 누락) 측정잡음 R을 조절하는 방법이 효과가 있는지 비교한다.

## 폴더 구성

```
01_연구계획발표/        연구계획 발표 PPT·PDF·대본 (이전 작업 브랜치에서 가져옴)
02_논문정리/            참고 논문 3편 + 참고 코드(PX4, VINS/OpenVINS) 정리 → 무엇을 어디에 썼는지
03_python_of_velocity/  ① OF → 회전 제거 → 속도 측정치 + 시간 동기화 (Python)
04_matlab_kf/           ② 상태 정의 → EKF → 위치 추정 → RMSE, 그림 (MATLAB)
data/demo/              Python 출력(합성 데이터) → MATLAB 입력.  바로 실행 가능
99_기타/                예전 명령어 메모 (ROS / 경로 생성)
```

## 전체 흐름

```
[영상 20Hz] ─┐
[IMU 200Hz] ─┼─▶ of_velocity.py ──▶ of_meas.csv ─┐
[LRF 30Hz] ──┘   (KLT → 회전 제거 → LS 속도)      ├─▶ main_vio_kf.m ──▶ RMSE + figures/
                 시간 동기화 (t_valid, t_avail)   │   (ESEKF + 지연보정 재추정)
                 imu.csv, lrf.csv, gt.csv ────────┘
```

## 정한 것 1 — Python: OF 속도 + 타임스탬프 동기화 (`03_python_of_velocity/of_velocity.py`)

영상쌍 (k−1, k) 마다:

1. **특징점 추적**: Shi-Tomasi + 피라미드 KLT, 정방향·역방향 왕복 오차 < 1 px만 사용 (VINS-Mono/OpenVINS 방식).
   `--backend dis`(OpenCV dense flow), `--backend raft`(딥러닝 RAFT, torchvision 필요)로 바꿀 수 있다.
2. **회전 성분 제거**: [t_{k−1}, t_k] 구간의 자이로를 적분해 `R_c1c0`를 구한다. 순수 회전만 했을 때의 위치를 빼면 병진 flow만 남는다.
3. **속도**: 남은 flow를 운동장 모델 `u = (−v_x + x·v_z)/Z`에 맞춰 robust LS(Huber)로 푼다. 깊이 Z는 LRF 값이다.
4. **바디 속도**: `v_B = R_BC·v_C − ω×r_BC` (레버암 보정).
5. **품질 Q** ∈ [0, 1] = 특징점 수 × 추적 성공률 × 잔차 패널티. 성공률만 보면 저조도 영상에서 속기 때문에 세 가지를 같이 본다.
6. **바이어스 민감도 M**: 자이로 바이어스가 속도로 새어 들어가는 양 (`v_B 오차 = M·b_g`). MATLAB에서 b_g를 추정할 때 쓴다.

**시간 동기화** (김민수·안창선 2025 방식, 자세한 대응표는 `02_논문정리/논문정리.md`):
- 기준 시계는 IMU다. 카메라는 `t + timeshift_cam_imu`, LRF는 `t − lrf_delay`로 지연을 보정한다 (논문 식 10).
- 자이로는 영상 구간에서 적분하고, LRF는 영상 시각에 보간한다 (논문 Fig. 3).
- 측정마다 `t_valid`(측정이 나타내는 상태의 시각 = 영상쌍 중간)와 `t_avail`(필터가 받는 시각 = t_k + 처리지연)을 같이 저장한다.

## 정한 것 2 — MATLAB: 칼만필터 (`04_matlab_kf/main_vio_kf.m`)

기본 선형 KF(예측 2줄 + 보정 3줄)를 그대로 두고 **F, H, Q, R만 바꿔 끼우는 구조**다. 대응표는 파일 맨 위 주석에 있다.

| Step | 내용 | 파일 |
|---|---|---|
| 0 | CSV 불러오기 | `main_vio_kf.m` |
| 1 | 상태 정의 `x = {p, v, R, b_a, b_g}`, 오차상태 15차 | `main_vio_kf.m` |
| 2 | 시스템 모델: IMU 적분 + 오차상태 F, Q | `lib/ekf_predict.m` |
| 3 | 측정 모델: OF `h = Rᵀv + M·b_g`, LRF `d = p_z/cosθ` | `lib/meas_of_velocity.m`, `lib/meas_lrf_range.m` |
| 4 | 측정이 늦게 오면 과거로 돌아가 재추정 + 측정모델 스위칭 (논문 Fig. 4) | `lib/run_filter.m` |
| 5 | 보정 + 주입 (`R ← R·Exp(δθ)`) | `lib/ekf_update.m` |
| 6 | RMSE 표, 그림 6장 | `main_vio_kf.m` → `figures/` |

비교 방법: **A** IMU 단독 / **B** 고정 R / **C** 품질 기반 적응 R (제안) / **C0** C에서 지연 보정만 끔

## 실행 방법

```bash
# (선택) 합성 데이터부터 다시 만들기 — data/demo 는 이미 들어 있으므로 건너뛰어도 됨
cd 03_python_of_velocity
pip install -r requirements.txt
python make_demo_data.py --out ../data/demo_raw        # 영상 1148장 + IMU/LRF/GT (약 40 MB)
python of_velocity.py --config config_demo.yaml        # → ../data/demo/*.csv
```

```matlab
% MATLAB (R2020a 이상 권장: 한글 주석 UTF-8)
cd 04_matlab_kf
main_vio_kf
```

실제 INSANE 데이터를 쓸 때는 `config_insane.yaml`의 `TODO`(파일 경로, CSV 헤더, 보정값)를 채운 뒤 실행하고, `main_vio_kf.m`의 `data_dir`을 `data/insane`으로 바꾼다.

## 합성 데이터 검증 결과 (60 s, 8자 비행, 고도 2.2~3.8 m)

정답을 아는 합성 데이터로 코드가 맞는지 확인했다. 열화 구간은 흐림 20~27 s, 저조도 38~45 s, 프레임 누락 52~54.5 s다.

| 방법 | 위치 RMSE [m] | 최종 오차 [m] | 속도 RMSE [m/s] |
|---|---|---|---|
| A: IMU 단독 | 1655 | 4343 | 96.8 |
| B: 고정 R | 0.73 | 1.22 | 0.214 |
| **C: 적응 R** | **0.22** | **0.05** | **0.060** |
| C0: 지연 보정 없음 | 0.49 | 0.42 | 0.119 |

- 다른 시드 2개(1, 2)에서도 순서가 같았다: C(0.25 / 0.15 m) < C0(0.41 / 0.35 m) < B(0.88 / 0.65 m).
- OF 속도 오차(정상 구간, 바이어스 보정 후): x 0.021 / y 0.017 / z 0.054 m/s. 저조도 구간은 0.13~0.20 m/s이고 Q ≈ 0.05로 떨어진다.
- 바이어스 추정: b_g = [0.0099, −0.0081, 0.0050] (참값 [0.010, −0.008, 0.005]), b_a = [0.048, −0.039, 0.080] (참값 [0.05, −0.04, 0.08]).
- 흐림(모션블러)은 텍스처가 풍부한 지면에서는 KLT 정확도를 거의 떨어뜨리지 않았다 (Q ≈ 0.8). 품질 저하는 사실상 저조도와 프레임 누락에서만 나타났다.

## 알려진 한계 / 다음 할 일

- **자이로 바이어스 → OF 속도**: 처음에는 이 항이 없어서 위치가 한쪽으로 꾸준히 드리프트했다. 화각이 90°로 넓으면 `Z·(광축×b_g)` 근사로는 부족하다(가장자리에서 `1+x²`배). 그래서 Python이 정확한 M을 계산해 넘긴다.
- **평면 가정**: 지면이 광축에 수직이라고 가정한다(깊이 = LRF 값 하나). 기울어진 상태에서 v_z에 ±0.05 m/s 정도의 파형 오차가 생기고, 속도 스케일이 약 1% 작게 나온다. 개선하려면 EKF 자세로 지면 법선을 구해 깊이를 픽셀마다 계산하면 된다.
- **위치와 yaw는 관측되지 않는다** (속도만 측정하므로). 오래 날면 천천히 드리프트한다. VIO(MSCKF)에서도 마찬가지다.
- `config_insane.yaml`의 CSV 헤더 이름은 데이터를 내려받은 뒤 확인해야 한다 (논문에 정확한 열 이름이 없음).
- RAFT 백엔드는 이 작업 환경에서 PyTorch 서버 접근이 막혀 **실행 검증을 못 했다**. KLT와 DIS는 검증했다 (두 결과의 속도 차이는 평균 0.004 m/s).
