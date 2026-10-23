# 인수인계: Optical Flow → EKF (outdoor_1)

## 0. 한 줄 요약
영상 두 장으로 **카메라축 3축 속도 vC**를 구해 `.mat`으로 저장하고, 이 값을 EKF의 속도 측정값으로 쓴다.
담당 코드는 `optical_flow_new.py` 한 파일(324줄)이다.

> 이 문서를 쓴 세션에서는 `optical_flow_new.py`만 직접 확인했다.
> `optical_flow_old.py`, EKF 코드, `DATASET.json`, 실제 데이터는 보지 못했다. 그 부분은 전달받은 설명만 적었고 **[미확인]**으로 표시했다.

## 1. 파일 구성

| 파일 | 상태 | 설명 |
|---|---|---|
| `optical_flow_new.py` | 현재 사용 | FlowToTheMoon 저자 코드(추적·선형 속도 계산)를 그대로 호출한다. 지면 법선은 GT 쿼터니언으로 계산한다. |
| `optical_flow_old.py` | 이전 버전 [미확인] | 왕복(forward-backward) 추적과 RANSAC을 쓰고, 지면 법선은 IMU 비력(specific force)으로 근사한다. |
| EKF 코드 | [미확인] | `CAM_VEL_author.mat`의 `vC`를 측정값으로 읽는다. |

저자 코드: https://gitlab.com/EuropeanSpaceAgency/flowtothemoon (commit `59643a3b6f2e0e7858884c8b1808d291a4bb7cc0`)
여러 파일에 나뉘어 있던 것을 한 파일로 합친 뒤에도 결과가 같은지 확인했다. 실제 영상 20쌍과 속도 풀이 입력 50개에서 통합 전후 결과가 완전히 일치했다(이전 작업자가 확인).

## 2. 실행 방법

```
python optical_flow_new.py                 # 전체 프레임
python optical_flow_new.py --limit 20      # 앞 20쌍만 → CAM_VEL_author_test.mat
python optical_flow_new.py --data <경로>   # outdoor_1 폴더가 다른 곳에 있을 때
python optical_flow_new.py --output <파일>
```

필요한 패키지: `opencv-python numpy pandas pyyaml scipy`

### 데이터 폴더 구조 (기본값: 스크립트 옆 `outdoor_1/`)
```
outdoor_1/
  outdoor_1_sensors.zip     # outdoor_1_sensors/px4_imu.csv, lrf_range.csv, ground_truth/ground_truth_80hz.csv
  outdoor_1_nav_cam.zip     # outdoor_1_nav_cam/nav_cam_timestamps.csv, img/1.png, 2.png, ...
  <보정 YAML>               # nav_cam_radtan.intrinsics/distortion_coeffs, nav_cam_extr.T_cam_px4imu
  output/CAM_VEL_author.mat # 결과
```

### ⚠️ 먼저 채워야 할 값 (파일 23~28줄)
예전에는 `보조자료/DATASET.json`에서 읽던 값을 상수로 옮겼다. **현재는 임시값**이니 실행 전에 DATASET.json의 값으로 바꿔야 한다.
```python
CALIBRATION_FILE = 'calibration.yaml'   # DATASET.json: calibration_file
B_G = np.array([0.0, 0.0, 0.0])         # DATASET.json: initial_by_dataset.outdoor_1.b_g  (자이로 바이어스)
CAMERA_TIME_OFFSET = 0.0                # DATASET.json: camera_time_offset  (카메라-IMU 시간 오프셋, 초)
```

## 3. 처리 흐름 (`# %%` 구획 기준)

```
영상 두 장 → LK 추적 → 왜곡 보정·시간으로 나누기 → 깊이(LRF+법선) → 회전 보상(IMU) → 최소제곱 → vC
```

| 구획 | 줄 | 내용 | 출처 |
|---|---|---|---|
| 1 | 23–31 | 경로·상수, zip 안의 CSV 읽기 | 직접 작성 |
| 2 | 33–95 | `LKOpticalFlowEstimator`: `goodFeaturesToTrack` + `calcOpticalFlowPyrLK`, 가장자리 5% 제외, 마스크 적용 | 저자 |
| 3 | 97–173 | `scale_pixel_coordinates`, `__rotation123`(Rz·Ry·Rx), `__calc_A_b`(평면 운동식) | 저자 |
| 4 | 175–209 | `least_squares_estimation`: vx, vy, vz 선형 분기만 남김 → `np.linalg.lstsq` | 저자 |
| 5 | 211–245 | 실제 보정값을 저자 함수 입력으로 변환(`rotation_from_normal`, `solve_author`, `author_tracks`) | 직접 작성 |
| 6 | 247–324 | 데이터 로드, 프레임 루프, `.mat` 저장 | 직접 작성 |

### 핵심 수식 (저자 `__calc_A_b`, 평면 지면)
특징점마다 정규화 좌표 (sx, sy)와 영상 속도 (u, v)가 있고, 지면 법선은 n = (α, β, γ) = R[2, :]이다.
- 깊이 역수: `h = -(α·sx + β·sy + γ) / z`, `z = -rho·cosφ·cosθ` (= -rho·n_z)
- 병진 성분: `h · [[-f, 0, sx], [0, -f, sy]] · v`
- 회전 성분: `L_w · ω`를 관측 flow에서 뺀다 (`b = U - L_w ω`)
- `A v = b`를 최소제곱으로 풀면 v가 나온다. 저자 함수는 `R @ v`(관성축)로 돌려준다.

### 저자 함수에 실제 보정값을 넣는 방법 (`solve_author`, 222줄) — 가장 헷갈리는 부분
저자 함수는 픽셀 좌표·초점거리·이미지 폭·framerate를 받는다. 여기서는 먼저 `cv.undistortPoints`로 **정규화 좌표 q**를 만든 뒤, 저자 함수가 "폭 1, 초점거리 1인 가상 카메라"를 보도록 값을 넘긴다.
- `scale_pixel_coordinates(p, 1) = p - 0.5` → 그래서 `points = q + 0.5`로 넘긴다
- 저자 함수는 `변위 × framerate`로 속도를 만든다 → `flow = flow_rate·dt`, `framerate = 1/dt`로 넘긴다 (프레임마다 dt가 다르다)
- 저자 함수가 관성축으로 돌려준 값에 `rot.T`를 곱해 **카메라축 vC**로 되돌린다
- `rotation_from_normal`은 `Rz·Ry·Rx`의 세 번째 행이 법선 n이 되도록 φ, θ를 고른다(ψ = 0). `assert`로 확인한다.

### 프레임 루프의 입력 (main)
- `dt = cam_t[k+1] - cam_t[k]`, 측정 시각 `tm`은 두 프레임의 중간 시각
- `omega = R_CI @ mean(IMU 자이로 − B_G)`: [ti, tk] 구간 평균을 카메라축으로 변환
- `rho = interp(LRF range)`: 시각 tm의 값
- `normal = R_CI @ R_GT(tm).T @ [0, 0, -1]`: GT 쿼터니언을 Slerp로 보간해 카메라축 지면 법선을 구한다
- 영상은 0.5배로 줄여 쓰고(`SCALE`), K도 같은 비율로 줄인다. 마스크는 좌상단과 좌하단 영역을 가린다(축소된 좌표 기준).
- 저장 조건: `rank == 3`이고 결과가 유한값일 때

## 4. 출력 `CAM_VEL_author.mat`

| 키 | 크기 | 의미 |
|---|---|---|
| `t_meas` | N×1 | 측정 시각 [s], IMU 첫 시각 t0 기준 |
| `vC` | N×3 | **카메라축 속도 (EKF 측정값)** |
| `rho` | N×1 | LRF 거리 |
| `n_pts` | N×1 | 사용한 특징점 수 |
| `n_C` | N×3 | 카메라축 지면 법선 |
| `frame_index`, `dt` | N×1 | 프레임 번호, 프레임 간격 |
| `ok` | N×1 | 항상 1 (의미 없음) |
| `b_g` | 3×1 | 사용한 자이로 바이어스 |
| `R_CI`, `r_IC` | 3×3, 3×1 | IMU→카메라 회전, IMU 기준 카메라 위치(레버암) |
| `dataset`, `t0`, `pose_source` | – | 메타 정보 (`pose_source='GT quaternion'`) |

## 5. EKF 연결 [미확인 — EKF 코드를 직접 보고 확인할 것]
- EKF는 `vC`를 속도 측정값으로 쓴다고 전달받았다.
- `.mat`에 `R_CI`와 `r_IC`가 들어 있으므로, 측정 모델은 `vC = R_CI·(R_IW·v_W + ω×r_IC)` 형태로 IMU 속도를 카메라축으로 변환하는 것으로 **추정**된다. 실제 식은 EKF 코드에서 확인해야 한다.
- 시간축을 맞추려면 EKF도 같은 `t0`(IMU 첫 시각)를 기준으로 써야 한다.

## 6. 알려진 문제·할 일
1. **GT를 쓰는 문제 (가장 중요)**: 지면 법선을 GT 쿼터니언으로 구한다. 그래서 이 vC를 EKF에 넣으면 정답 자세가 측정값에 섞인다. 검증용으로만 괜찮고, 최종 결과에서는 EKF 추정 자세(또는 old 버전처럼 비력 근사)로 바꿔야 한다.
2. `B_G`, `CAMERA_TIME_OFFSET`, `CALIBRATION_FILE`이 임시값이다(2절).
3. 이상치 제거가 없다. old 버전의 왕복 추적과 RANSAC을 new 버전에서 뺐다. 결과가 튀면 여기부터 확인한다.
4. LRF가 카메라 광축 방향을 잰다고 가정하고 깊이를 계산한다(`z = -rho·n_z`).
5. 결과에는 영향이 없는 정리 거리:
   - `import cv2`와 `import cv2 as cv`가 둘 다 있다
   - `ok` 열은 필요 없다
   - `author_tracks`의 `finite` 검사는 하는 일이 없다
   - `rho > 0` 검사를 추적 앞으로 옮기면 잘못된 프레임의 추적을 건너뛸 수 있다
   - `ns` dict는 이름이 모호하다
6. 저자 원본에 있던 것이라 손대지 않은 것:
   - `forward`에서 x, y 여백 계산에 쓰는 이미지 크기(`shape[0]`, `shape[1]`)가 뒤바뀌어 있다
   - `target_radius`와 `stable_depth`는 받기만 하고 쓰지 않는다
