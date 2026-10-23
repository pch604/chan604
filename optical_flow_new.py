"""outdoor_1 Optical Flow -> 카메라축 속도 vC.

실행: python optical_flow_new.py [--data outdoor_1 폴더] [--limit N]
흐름: LK 추적 -> 왜곡 보정·시간 정규화 -> GT 자세·LRF로 깊이 -> 회전 보상 -> 최소제곱 vC

추적 클래스와 평면 속도 계산(2~4절)은 FlowToTheMoon 저자 코드
(https://gitlab.com/EuropeanSpaceAgency/flowtothemoon, commit 59643a3)에서 가져왔다.
"""
import argparse
import io
from pathlib import Path
from typing import Optional
import zipfile
import cv2
import cv2 as cv
import numpy as np
import pandas as pd
import yaml
from scipy.io import savemat
from scipy.optimize import OptimizeResult
from scipy.spatial.transform import Rotation, Slerp

# %% 1. 데이터 경로와 설정
DATASET = 'outdoor_1'
DATA_DIR = Path(__file__).resolve().parent / DATASET   # outdoor_1_sensors.zip, outdoor_1_nav_cam.zip, 보정 YAML
CALIBRATION_FILE = 'calibration.yaml'                  # DATASET.json의 calibration_file 값
B_G = np.array([0.0, 0.0, 0.0])                        # DATASET.json의 initial_by_dataset.outdoor_1.b_g 값
CAMERA_TIME_OFFSET = 0.0                               # DATASET.json의 camera_time_offset 값

def read_csv(z, name):
    return pd.read_csv(io.BytesIO(z.read(name)), skipinitialspace=True, encoding='utf-8')

# %% 2. 특징점 검출과 LK 추적 [저자 코드]
class LKOpticalFlowEstimator:

    def __init__(self, feature_params: dict=None, lk_params: dict=None, do_histogram_equalization: bool=False, mask: np.ndarray=None):
        if feature_params is None:
            self.feature_params = dict(maxCorners=1000, qualityLevel=0.1, minDistance=50, blockSize=10)
        else:
            self.feature_params = feature_params
        if lk_params is None:
            self.lk_params = dict(winSize=(50, 50), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        else:
            self.lk_params = lk_params
        self.do_histogram_equalization = do_histogram_equalization
        self.mask = mask

    def forward(self, img0: np.ndarray, img1: np.ndarray, features: np.ndarray=None, verbose: bool=False) -> tuple[np.ndarray, np.ndarray]:
        """Compute the optical flow between two frames

        Args:
            img0 (np.ndarray): [3]xHxW cv2 image representing the first frame
            img1 (np.ndarray): [3]xHxW cv2 image representing the second frame
            features (np.ndarray): Nx2 array representing already tracked feature coordinates (Optional)
            verbose (bool): Debugging mode flag

        Returns:
            tuple[np.ndarray, np.ndarray]: Nx2 array representing features coordinates and Nx2 array representing their flow
        """
        if img0.ndim == 3:
            img0 = cv2.cvtColor(img0, cv2.COLOR_BGR2GRAY)
        if img1.ndim == 3:
            img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        if self.do_histogram_equalization:
            img0 = cv2.equalizeHist(img0)
            img1 = cv2.equalizeHist(img1)
        if features is None:
            features0 = cv2.goodFeaturesToTrack(img0, mask=self.mask, **self.feature_params)
        else:
            features0 = features
        try:
            features1, status, err = cv2.calcOpticalFlowPyrLK(img0, img1, features0, None, **self.lk_params)
        except Exception as e:
            print('Error in calculating OF. Probably no tracked points')
            print(e)
            return (None, None)
        features1 = np.reshape(features1, (-1, 1, 2))
        features0 = np.reshape(features0, (-1, 1, 2))
        img1_points = features1[status == 1]
        img0_points = features0[status == 1]
        buffer = 0.05
        x_buffer = buffer * img1.shape[0]
        y_buffer = buffer * img1.shape[1]
        valid_mask = (img1_points[:, 0] >= x_buffer) & (img1_points[:, 0] < img1.shape[1] - x_buffer) & (img1_points[:, 1] >= y_buffer) & (img1_points[:, 1] < img1.shape[0] - y_buffer)
        img1_points = img1_points[valid_mask]
        img0_points = img0_points[valid_mask]
        if self.mask is not None:
            mask_values = self.mask[img1_points[:, 1].astype(int), img1_points[:, 0].astype(int)]
            mask_valid_mask = mask_values != 0
            img1_points = img1_points[mask_valid_mask]
            img0_points = img0_points[mask_valid_mask]
        flow = img1_points - img0_points
        if verbose:
            print('Number of tracked points', len(flow))
        return (img0_points, flow)

# %% 3. 좌표·회전 및 평면 운동식 [저자 코드]
def scale_pixel_coordinates(coord: np.ndarray, image_width: int) -> np.ndarray:
    """Scale pixels coordinates in [-0.5, 0.5]

    Args:
        x (np.ndarray): pixel coordinates
        image_width (int): image resolution

    Returns:
        np.ndarray: rescaled coordinates
    """
    return (coord - image_width / 2) / image_width

def __rotation123(phi, theta, psi):
    """
    Compute rotation matrix from 3-2-1 Euler angles (phi, theta, psi).

    Args:
        phi (float): Rotation about x-axis.
        theta (float): Rotation about y-axis.
        psi (float): Rotation about z-axis.

    Returns:
        np.ndarray: 3x3 rotation matrix.
    """
    cph = np.cos(phi)
    sph = np.sin(phi)
    cth = np.cos(theta)
    sth = np.sin(theta)
    cps = np.cos(psi)
    sps = np.sin(psi)
    R_x = np.array([[1, 0, 0], [0, cph, -sph], [0, sph, cph]])
    R_y = np.array([[cth, 0, sth], [0, 1, 0], [-sth, 0, cth]])
    R_z = np.array([[cps, -sps, 0], [sps, cps, 0], [0, 0, 1]])
    R = np.dot(R_z, np.dot(R_y, R_x))
    return R

def __calc_A_b(state, points, flow, fx, fy, target_radius=None, stable_depth=False):
    """
    Calculate the A matrix and b vector for the linear least squares estimation.

    Args:
        state: The state of the system ([z], phi, theta, psi, p, q, r, [rho]).
            Values inside square brakets can be None
        points: The pixel coordinates of the points.
        flow: The optical flow vectors at the points.
        focal_length: The focal length of the camera.
        framerate: The framerate of the camera.
        image_width: The width of the image in pixels.
        target_radius: The radius of the target sphere (if applicable).
        stable_depth: Whether to use a stable depth calculation.

    Returns:
        A: The A matrix for the linear least squares estimation.
        b: The b vector for the linear least squares estimation.
    """
    n_equations = len(points) * 2
    A = np.zeros((n_equations, 3))
    b = np.zeros(n_equations)
    z, phi, theta, psi, p, q, r, rho = state
    omega = np.array([p, q, r])
    R = __rotation123(phi, theta, psi)
    for i, (sx, sy, u, v) in enumerate(zip(points[:, 0], points[:, 1], flow[:, 0], flow[:, 1])):
        if target_radius is None:
            alpha, beta, gamma = R[2, :]
            if rho is not None:
                z = -rho * np.cos(phi) * np.cos(theta)
            h = -(alpha * sx / fx + beta * sy / fy + gamma) / z
        else:
            raise ValueError('이 단일 파일은 평면 모델만 사용합니다.')
        L_t = np.array([[-fx, 0, sx], [0, -fy, sy]])
        A[i * 2:i * 2 + 2, :] = h * L_t
        L_w = np.array([[sx * sy / fy, -(fx + sx ** 2 / fx), sy], [fy + sy ** 2 / fy, -sx * sy / fx, -sx]])
        C = L_w @ omega
        U = np.array([u, v])
        b[i * 2:i * 2 + 2] = U - C
    return (A, b)

# %% 4. 3축 속도 선형 최소제곱 [저자 코드, 선형 분기만]
def least_squares_estimation(vars: dict[str, float], pars: dict[str, float], points: np.ndarray, flow: np.ndarray, focal_length: float, framerate: int, image_width: int, target_radius: Optional[int]=None, stable_depth: bool=False, least_squares_kwargs: dict={}) -> OptimizeResult:
    """Estimate the spacecraft state using least squares optimization over motion field equations.
    If the system is linear, linear least squares will be used, otheriwse a non-linear version will be used.

    Args:
        vars (dict[str, float]): variables to optimize. The keys are the variable names and the values are the initial guesses.
        pars (dict[str, float]): parameters with known values
        points (np.ndarray): points in the image plane, shape (n, 2)
        flow (np.ndarray): optical flow vectors corresponding to `points`, shape (n, 2)
        focal_length (float): camera focal length related to the image width
        framerate (int): camera framerate
        image_width (int): image width, in pixels
        target_radius (int, optional): radius of the target in meters. Defaults to None (planar case)
        stable_depth (bool, optional): If True, replaces NaN depth values with the maximum depth
        least_squares_kwargs (dict, optional): additional arguments to pass to `scipy.optimize.least_squares`. Defaults to {}.

    Returns:
        OptimizeResult: optimization result. The `x` attribute contains the optimized variables
    """
    n_equations = len(points) * 2
    assert len(vars) <= n_equations, f'The system is under-determined. You have {len(vars)} variables and {n_equations} equations'
    var_values = list(vars.values())
    var_keys = list(vars.keys())
    if set(var_keys) == {'vx', 'vy', 'vz'}:
        phi, theta, psi = (pars['phi'], pars['theta'], pars['psi'])
        state = [pars.get('z', None), phi, theta, psi, pars['p'], pars['q'], pars['r'], pars.get('rho', None)]
        A, b = __calc_A_b(state, scale_pixel_coordinates(points, image_width), flow * framerate / image_width, fx=focal_length, fy=focal_length, target_radius=target_radius, stable_depth=stable_depth)
        v_est, residuals, rank, singular_values = np.linalg.lstsq(A, b, rcond=None)
        R = __rotation123(phi, theta, psi)
        v_est_inertial = R @ v_est
        result = OptimizeResult(x=v_est_inertial, residuals=residuals, rank=rank, singular_values=singular_values)
    else:
        raise ValueError('이 단일 파일은 vx, vy, vz 선형 추정만 사용합니다.')
    return result

# %% 5. 실제 카메라 보정값을 저자 함수 입력으로 변환
def rotation_from_normal(normal):
    """원본 Rz*Ry*Rx의 세 번째 행을 normal에 맞추는 자세 표현."""
    n = np.asarray(normal) / np.linalg.norm(normal)
    phi = np.arctan2(n[1], n[2])
    theta = -np.arcsin(np.clip(n[0], -1, 1))
    psi = 0.0
    rot = Rotation.from_euler('xyz', [phi, theta, psi]).as_matrix()
    assert np.allclose(rot[2], n, atol=1e-10)
    return (rot, np.array([phi, theta, psi]))

def solve_author(points, flow_rate, omega, rho, normal, dt):
    """실제 K 보정 후 가상 픽셀계(width=1, focal=1)로 원본 공개 함수를 호출.

    원본 scale_pixel_coordinates(p,1)=p-.5 이므로 p=q+.5로 전달.
    원본은 변위*framerate를 사용하므로 flow_rate*dt, 1/dt 전달.
    원본의 관성축 반환을 rot.T로 역변환해 v_C를 반환한다.
    """
    rot, angles = rotation_from_normal(normal)
    phi, theta, psi = angles
    result = least_squares_estimation(vars={'vx': 0.0, 'vy': 0.0, 'vz': 0.0}, pars=dict(phi=phi, theta=theta, psi=psi, p=omega[0], q=omega[1], r=omega[2], rho=rho), points=points + 0.5, flow=flow_rate * dt, focal_length=1.0, framerate=1 / dt, image_width=1)
    return (rot.T @ result.x, int(result.rank))

def author_tracks(tracker, im0, im1, ns, dt):
    p0, delta = tracker.forward(im0, im1)
    if p0 is None or delta is None or len(p0) < 2:
        return None
    p1 = p0 + delta
    finite = np.isfinite(p0).all(1) & np.isfinite(p1).all(1)
    p0, p1 = (p0[finite], p1[finite])
    if len(p0) < 2:
        return None
    q0 = cv.undistortPoints(p0, ns['K'], ns['dist'], None, None, None, ns['UNDIST']).reshape(-1, 2)
    q1 = cv.undistortPoints(p1, ns['K'], ns['dist'], None, None, None, ns['UNDIST']).reshape(-1, 2)
    return (q0, (q1 - q0) / dt, len(q0))

# %% 6. outdoor_1 전체 처리 및 저장
def main(limit=0, output=None, data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    cv.setNumThreads(4)
    SCALE = 0.5
    with zipfile.ZipFile(data_dir / f'{DATASET}_sensors.zip') as z:
        imu = read_csv(z, f'{DATASET}_sensors/px4_imu.csv')
        lrf = read_csv(z, f'{DATASET}_sensors/lrf_range.csv')
        gt = read_csv(z, f'{DATASET}_sensors/ground_truth/ground_truth_80hz.csv')
    ZIP = data_dir / f'{DATASET}_nav_cam.zip'
    with zipfile.ZipFile(ZIP) as z:
        cam = read_csv(z, f'{DATASET}_nav_cam/nav_cam_timestamps.csv')
    t0 = float(imu.t.iloc[0])
    imu_t = imu.t.to_numpy() - t0
    imu_w = imu[['w_x', 'w_y', 'w_z']].to_numpy() - B_G
    lrf_t = lrf.t.to_numpy() - t0
    lrf_r = lrf['range'].to_numpy()
    cam_t = cam.iloc[:, 1].to_numpy(float) - t0 + CAMERA_TIME_OFFSET
    gt_t = gt.t.to_numpy() - t0
    attitude = Slerp(gt_t, Rotation.from_quat(gt[['q_x', 'q_y', 'q_z', 'q_w']].to_numpy()))
    calib = yaml.safe_load((data_dir / CALIBRATION_FILE).read_text(encoding='utf-8'))
    fx, fy, cx, cy = calib['nav_cam_radtan']['intrinsics']
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]]) * [[SCALE], [SCALE], [1]]
    dist = np.array(calib['nav_cam_radtan']['distortion_coeffs'])
    T_CI = np.array(calib['nav_cam_extr']['T_cam_px4imu'])
    R_CI = T_CI[:3, :3]
    r_IC = -R_CI.T @ T_CI[:3, 3]
    mask = np.full((round(1542 * SCALE), round(2056 * SCALE)), 255, np.uint8)
    cv.fillPoly(mask, [np.array([[0, 0], [95, 0], [95, 28], [0, 28]]), np.array([[0, 450], [30, 450], [120, 771], [0, 771]])], 0)
    tracker = LKOpticalFlowEstimator(mask=mask)
    ns = dict(K=K, dist=dist, UNDIST=(cv.TERM_CRITERIA_COUNT | cv.TERM_CRITERIA_EPS, 10, 1e-08))

    def read_gray(z, k):
        im = cv.imdecode(np.frombuffer(z.read(f'{DATASET}_nav_cam/img/{k + 1}.png'), np.uint8), cv.IMREAD_GRAYSCALE)
        return cv.resize(im, None, fx=SCALE, fy=SCALE, interpolation=cv.INTER_AREA)
    rows = []
    count = len(cam_t) - 1
    if limit:
        count = min(count, limit)
    with zipfile.ZipFile(ZIP) as z:
        img0 = read_gray(z, 0)
        for k in range(count):
            img1 = read_gray(z, k + 1)
            ti, tk = cam_t[k:k + 2]
            tm, dt = ((ti + tk) / 2, tk - ti)
            w = (imu_t >= ti) & (imu_t <= tk)
            if dt > 0 and w.any() and (gt_t[0] <= tm <= gt_t[-1]) and (lrf_t[0] <= tm <= lrf_t[-1]):
                omega = R_CI @ imu_w[w].mean(0)
                rho = np.interp(tm, lrf_t, lrf_r)
                normal = R_CI @ attitude(tm).as_matrix().T @ np.array([0.0, 0.0, -1.0])
                try:
                    tracked = author_tracks(tracker, img0, img1, ns, dt)
                    if tracked is not None and np.isfinite(rho) and (rho > 0):
                        points, flow, n_pts = tracked
                        v_C, rank = solve_author(points, flow, omega, rho, normal, dt)
                        if rank == 3 and np.isfinite(v_C).all():
                            rows.append(dict(t_meas=tm, vC=v_C, rho=rho, n_pts=n_pts, n_C=normal, frame_index=k, dt=dt))
                except (cv.error, ValueError, np.linalg.LinAlgError) as e:
                    print(f'frame {k}: {e}', flush=True)
            img0 = img1
            if k % 500 == 0 or k == count - 1:
                print(f'{k + 1}/{count}', flush=True)
    if not rows:
        raise RuntimeError('유효 카메라 속도가 없습니다.')
    out = {key: np.array([r[key] for r in rows]).reshape(len(rows), -1) for key in rows[0]}
    out.update(ok=np.ones((len(rows), 1)), b_g=B_G.reshape(3, 1), R_CI=R_CI, r_IC=r_IC.reshape(3, 1), dataset=DATASET, t0=t0, pose_source='GT quaternion')
    OUT = Path(output) if output else data_dir / 'output' / ('CAM_VEL_author_test.mat' if limit else 'CAM_VEL_author.mat')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    savemat(OUT, out, do_compression=True)
    print(f'저자 원본 기반 카메라 속도 {len(rows)}/{count} -> {OUT}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0, help='점검할 프레임 쌍 수. 0이면 전체')
    parser.add_argument('--output', help='별도 결과 경로')
    parser.add_argument('--data', default=DATA_DIR, help='outdoor_1 데이터 폴더')
    args = parser.parse_args()
    main(args.limit, args.output, args.data)
