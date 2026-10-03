%% step1_linear_kf.m  ─  1단계: 기본 선형 KF 로 같은 데이터 추종하기
%
%  main_vio_kf.m(2단계)으로 가기 전에, 가장 단순한 '예측-보정' 구조로 먼저 돌려보는 파일.
%  kalman0802.m 같은 기본 추종 KF 와 같은 모양이다.
%
%   상태      x = [p; v]  (6x1, 월드 좌표)
%   예측      x = F x + B u,   u = 월드 가속도 = R_WB * a_IMU + g
%   측정      OF  : z = R_WB * v_B  (월드 속도)   H = [0 I]
%             LRF : z = d * cos(기울기) ≈ p_z     H = [0 0 1 0 0 0]
%
%  ※ 이해용 단순화: 자세 R_WB 는 '정답(GT)'을 빌려 쓰고, 바이어스·지연은 무시한다.
%     → 2단계(main_vio_kf.m)에서 바뀌는 것
%        (1) 자세 R 을 자이로로 직접 추정 (상태에 추가)    (2) 바이어스 b_a, b_g 추정
%        (3) F, H 가 자세에 따라 변함 (EKF)                (4) 늦게 온 측정 → 과거로 돌아가 재추정

clear; close all; clc;
addpath(fullfile(fileparts(mfilename('fullpath')), 'lib'));
data_dir = fullfile(fileparts(mfilename('fullpath')), '..', 'data', 'demo');

imu = read_csv_struct(fullfile(data_dir, 'imu.csv'));
of  = read_csv_struct(fullfile(data_dir, 'of_meas.csv'));
lrf = read_csv_struct(fullfile(data_dir, 'lrf.csv'));
gt  = read_csv_struct(fullfile(data_dir, 'gt.csv'));
ex  = read_csv_struct(fullfile(data_dir, 'extrinsic.csv'));
c_B = reshape([ex.R0 ex.R1 ex.R2 ex.R3 ex.R4 ex.R5 ex.R6 ex.R7 ex.R8], 3, 3) * [0; 0; 1];  % 광축(바디)
t = imu.t;  N = numel(t);

% 정답 자세 (IMU 시각)
q = interp_gt(gt, t, {'qw','qx','qy','qz'});
Rgt = zeros(3, 3, N);
for k = 1:N, Rgt(:, :, k) = quat2rot(q(k, :)); end

%% 1. 상태 정의 / 초기값
x = [interp_gt(gt, t(1), {'px','py','pz'}); interp_gt(gt, t(1), {'vx','vy','vz'})];
P = diag([0.01 0.01 0.01 0.05 0.05 0.05].^2);

%% 2. 시스템 모델 (dt 는 IMU 주기, 거의 일정)
dt = median(diff(t));
I3 = eye(3);  Z3 = zeros(3);
F = [I3 dt*I3; Z3 I3];
B = [0.5*dt^2*I3; dt*I3];
Q = blkdiag(1e-8*I3, (0.05^2*dt)*I3);         % 가속도 잡음(+바이어스 무시분) → 속도 잡음
g = [0; 0; -9.81];

%% 3. 측정 모델
H_of  = [Z3 I3];             R_of  = (0.08^2)*I3;
H_lrf = [0 0 1 0 0 0];       R_lrf = 0.03^2;

% 측정을 가장 가까운 IMU 스텝에 배치 (1단계: 지연 무시, t_valid 그대로 사용)
k_of  = interp1(t, 1:N, of.t_valid(of.valid == 1), 'nearest', 'extrap');
i_of  = find(of.valid == 1);
k_lrf = interp1(t, 1:N, lrf.t_valid, 'nearest', 'extrap');

%% 4. 예측-보정 루프  (기본 KF 그대로)
X = zeros(N, 6);  X(1, :) = x.';
for k = 2:N
    % --- 예측 ---
    u = Rgt(:, :, k-1) * [imu.ax(k-1); imu.ay(k-1); imu.az(k-1)] + g;
    x = F*x + B*u;
    P = F*P*F.' + Q;

    % --- 보정: OF 속도 ---
    for j = i_of(k_of == k).'
        z = Rgt(:, :, k) * [of.vx(j); of.vy(j); of.vz(j)];
        K = P*H_of.' / (H_of*P*H_of.' + R_of);
        x = x + K*(z - H_of*x);
        P = (eye(6) - K*H_of)*P;
    end
    % --- 보정: LRF 고도 ---
    for j = find(k_lrf == k).'
        c = Rgt(:, :, k) * c_B;               % 광축 방향(월드)  →  cos(기울기) = -c_z
        z = lrf.range(j) * (-c(3));
        K = P*H_lrf.' / (H_lrf*P*H_lrf.' + R_lrf);
        x = x + K*(z - H_lrf*x);
        P = (eye(6) - K*H_lrf)*P;
    end
    X(k, :) = x.';
end

%% 5. 결과
Gp = interp_gt(gt, t, {'px','py','pz'});
Gv = interp_gt(gt, t, {'vx','vy','vz'});
ep = X(:, 1:3) - Gp;
fprintf('1단계 선형 KF:  위치 RMSE %.3f m,  최종 오차 %.3f m,  속도 RMSE %.3f m/s\n', ...
    sqrt(mean(sum(ep.^2, 2))), norm(ep(end, :)), sqrt(mean(sum((X(:, 4:6) - Gv).^2, 2))));

figure('Name', 'step1', 'Position', [50 50 900 380]);
subplot(1, 2, 1); hold on; grid on; axis equal;
plot(Gp(:, 1), Gp(:, 2), 'k', 'LineWidth', 2); plot(X(:, 1), X(:, 2), 'b');
xlabel('x [m]'); ylabel('y [m]'); title('Step 1: linear KF (GT attitude)'); legend('GT', 'KF');
subplot(1, 2, 2); hold on; grid on;
plot(t, sqrt(sum(ep.^2, 2)), 'b');
xlabel('t [s]'); ylabel('|p - p_{GT}| [m]'); title('Position error');
fig_dir = fullfile(fileparts(mfilename('fullpath')), 'figures');
if ~exist(fig_dir, 'dir'), mkdir(fig_dir); end
save_fig(fig_dir, 'fig0_step1_linear_kf');
