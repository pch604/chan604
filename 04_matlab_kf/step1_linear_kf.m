%   1단계: kalman0802.m 과 같은 구조의 선형 칼만 필터를 드론 데이터에 적용
%
%   kalman0802.m                          이 파일
%   ─────────────────────────────────    ─────────────────────────────────────────
%   상태 x = [횡속도 v; 요레이트 r]        x = [위치 p(3); 속도 v(3)]   (월드 좌표)
%   입력 u = 조향각 delta                 u = 월드 가속도 = R_WB * a_IMU + g
%   측정 z = [r; ay]  (매 스텝)           z = OF 속도(3), LRF 고도(1)  (들어올 때만)
%   차량 2DOF 모델 Ac, Bc                 등가속도 운동 Ac = [0 I; 0 0], Bc = [0; I]
%   True System 을 직접 시뮬레이션        x_true = 정답 데이터(gt.csv)
%
%   ※ 이해용 단순화: 자세 R_WB 는 정답을 빌려 쓰고, 바이어스·센서 지연은 무시.
%     → 2단계(main_vio_kf.m)에서 자세·바이어스를 추정하고 지연을 보정한다.

clear; close all; clc;
addpath(fullfile(fileparts(mfilename('fullpath')), 'lib'));
data_dir = fullfile(fileparts(mfilename('fullpath')), '..', 'data', 'demo');

%% 데이터 (kalman0802 의 '차량 파라미터' 자리)
imu = read_csv_struct(fullfile(data_dir, 'imu.csv'));       % 200 Hz 가속도·각속도
of  = read_csv_struct(fullfile(data_dir, 'of_meas.csv'));   % 20 Hz OF 속도 (Python 출력)
lrf = read_csv_struct(fullfile(data_dir, 'lrf.csv'));       % 30 Hz 지면 거리
gt  = read_csv_struct(fullfile(data_dir, 'gt.csv'));        % 정답
ex  = read_csv_struct(fullfile(data_dir, 'extrinsic.csv'));
R_BC = reshape([ex.R0 ex.R1 ex.R2 ex.R3 ex.R4 ex.R5 ex.R6 ex.R7 ex.R8], 3, 3);

t = imu.t';
N = length(t);
Ts = median(diff(t));                                       % 0.005 s

q = interp_gt(gt, t, {'qw','qx','qy','qz'});                % 정답 자세 (이해용)
R_WB = zeros(3, 3, N);
for k = 1:N, R_WB(:, :, k) = quat2rot(q(k, :)); end
x_true = [interp_gt(gt, t, {'px','py','pz'}), interp_gt(gt, t, {'vx','vy','vz'})]';

%% 연속 상태공간 -> 이산화
I3 = eye(3);  O3 = zeros(3);
Ac = [O3 I3;
      O3 O3];
Bc = [O3;
      I3];
% c2d(ss(Ac,Bc,...), Ts, 'zoh') 와 같은 값 (Control Toolbox 없이 expm 으로 계산)
E   = expm([Ac Bc; zeros(3, 9)] * Ts);
Phi = E(1:6, 1:6);      % = [I Ts*I; 0 I]
Gam = E(1:6, 7:9);      % = [Ts^2/2*I; Ts*I]

H_of  = [O3 I3];                  % OF  : 속도를 직접 측정
H_lrf = [0 0 1 0 0 0];            % LRF : 고도 (거리 × cos(기울기))

%% 노이즈 통계 Q, R / 초기 공분산
Q     = blkdiag(1e-8*I3, 0.05^2*Ts*I3);    % 가속도 잡음(바이어스 포함) → 속도 잡음
R_of  = 0.08^2 * I3;
R_lrf = 0.03^2;
P = diag([0.01 0.01 0.01 0.05 0.05 0.05].^2);

g = [0; 0; -9.81];
delta = zeros(3, N);              % 입력 u_k (kalman0802 의 delta 자리)
for k = 1:N
    delta(:, k) = R_WB(:, :, k) * [imu.ax(k); imu.ay(k); imu.az(k)] + g;
end

% 측정 → 가장 가까운 IMU 스텝 번호 (센서마다 주기가 달라 매 스텝 측정이 있지는 않음)
i_of  = find(of.valid == 1);
k_of  = interp1(t, 1:N, of.t_valid(i_of), 'nearest', 'extrap');
k_lrf = interp1(t, 1:N, lrf.t_valid, 'nearest', 'extrap');
c_B   = R_BC * [0; 0; 1];         % 카메라·LRF 광축 (바디)

%% 초기값
x_est(:, 1) = x_true(:, 1);
z_of_w = nan(3, N);               % 그림용: 월드로 바꾼 OF 측정

%% 칼만 필터
for k = 2:N

    % Predict (time update)
    x_minus = Phi*x_est(:, k-1) + Gam*delta(:, k-1);
    P_minus = Phi*P*Phi' + Q;

    % 이번 스텝에 들어온 측정만 모아서 z, H, R 구성 (없으면 예측값 그대로)
    z = [];  H = [];  R = [];
    for j = i_of(k_of == k)'
        z_k = R_WB(:, :, k) * [of.vx(j); of.vy(j); of.vz(j)];
        z = [z; z_k];  H = [H; H_of];  R = blkdiag(R, R_of);
        z_of_w(:, k) = z_k;
    end
    for j = find(k_lrf == k)'
        c = R_WB(:, :, k) * c_B;                     % 광축(월드) → cos(기울기) = -c(3)
        z = [z; lrf.range(j) * (-c(3))];  H = [H; H_lrf];  R = blkdiag(R, R_lrf);
    end

    % Update (measurement update)
    if isempty(z)
        x_est(:, k) = x_minus;
        P = P_minus;
    else
        S = H*P_minus*H' + R;
        K = P_minus*H'/S;
        x_est(:, k) = x_minus + K*(z - H*x_minus);
        P = (eye(6) - K*H)*P_minus;
    end
end

%% 결과
e = x_est - x_true;
fprintf('1단계 선형 KF:  위치 RMSE %.3f m,  최종 오차 %.3f m,  속도 RMSE %.3f m/s\n', ...
    sqrt(mean(sum(e(1:3, :).^2, 1))), norm(e(1:3, end)), sqrt(mean(sum(e(4:6, :).^2, 1))));

figure('Position', [50 50 1000 650])

subplot(221)
plot(x_true(1,:), x_true(2,:), 'b--', x_est(1,:), x_est(2,:), 'r'); grid; axis equal
xlabel('x (m)'); ylabel('y (m)')
legend('True', 'Estimated')

subplot(222)
plot(t, x_true(3,:), 'b--', t, x_est(3,:), 'r'); grid
xlabel('time (sec)'); ylabel('Altitude (m)')
legend('True', 'Estimated')

subplot(223)
ok = ~isnan(z_of_w(1,:));
plot(t(ok), z_of_w(1,ok), 'c.', t, x_true(4,:), 'b--', t, x_est(4,:), 'r'); grid
xlabel('time (sec)'); ylabel('v_x (m/sec)')
legend('Measured (OF)', 'True', 'Estimated')

subplot(224)
plot(t, sqrt(sum(e(1:3,:).^2, 1)), 'r'); grid
xlabel('time (sec)'); ylabel('Position error (m)')

fig_dir = fullfile(fileparts(mfilename('fullpath')), 'figures');
if ~exist(fig_dir, 'dir'), mkdir(fig_dir); end
save_fig(fig_dir, 'fig0_step1_linear_kf');
