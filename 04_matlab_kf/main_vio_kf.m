%% main_vio_kf.m  ─  하향 카메라 OF + IMU + LRF 융합 EKF (위치/속도/자세 추정)
%
%  입력 : Python(of_velocity.py) 이 만든 표준 CSV  (data/demo 또는 data/insane)
%         imu.csv, of_meas.csv, lrf.csv, extrinsic.csv, gt.csv(평가용)
%  출력 : RMSE 표 + figures/*.png
%
%  ── 기본 선형 KF(예: kalman0802.m 같은 '추종' 필터)에서 무엇이 바뀌었나 ──
%   기본 KF                          이 코드 (Error-State EKF)
%   x = [p; v]                       x = {p, v, R, b_a, b_g},  오차 δx 15차
%   x = F x + B u  (u: 가속도 명령)   IMU 가속도/각속도로 비선형 적분     → ekf_predict.m
%   F, Q 고정                        F, Q 를 매 스텝 현재 자세로 계산    → ekf_predict.m
%   z = H x  (위치 측정)             z = v_B (OF 속도), d (LRF 거리)    → meas_*.m
%   R 고정                           R = (σ_flow·거리)²,  σ_flow 를 영상 품질 Q 로 조절
%   x = x + K(z - Hx)                p,v,b 는 더하고 R 은 R·Exp(δθ)     → ekf_update.m
%   측정은 매 스텝 동시에            주기·지연이 다른 측정 → 과거로 돌아가 재추정 → run_filter.m
%
%  비교하는 방법 (연구계획서와 동일)
%   A : IMU 단독 (관성항법)
%   B : IMU + OF(고정 R) + LRF
%   C : IMU + OF(품질 기반 적응 R, 저품질 제외) + LRF      ← 제안
%   C0: C 와 같지만 지연 보정 없음 (논문의 delay compensation 효과 확인용)

clear; close all; clc;
addpath(fullfile(fileparts(mfilename('fullpath')), 'lib'));

%% Step 0. 데이터 불러오기 ------------------------------------------------
data_dir = fullfile(fileparts(mfilename('fullpath')), '..', 'data', 'demo');
fig_dir  = fullfile(fileparts(mfilename('fullpath')), 'figures');
if ~exist(fig_dir, 'dir'), mkdir(fig_dir); end

imu = read_csv_struct(fullfile(data_dir, 'imu.csv'));
D.imu.t = imu.t;
D.imu.w = [imu.wx imu.wy imu.wz];          % 자이로 [rad/s]   (바디)
D.imu.a = [imu.ax imu.ay imu.az];          % 가속도계 [m/s^2] (바디, 비력)
D.of  = read_csv_struct(fullfile(data_dir, 'of_meas.csv'));
D.lrf = read_csv_struct(fullfile(data_dir, 'lrf.csv'));
gt    = read_csv_struct(fullfile(data_dir, 'gt.csv'));
ex    = read_csv_struct(fullfile(data_dir, 'extrinsic.csv'));
R_BC  = reshape([ex.R0 ex.R1 ex.R2 ex.R3 ex.R4 ex.R5 ex.R6 ex.R7 ex.R8], 3, 3);
r_BC  = [ex.rx; ex.ry; ex.rz];

fprintf('IMU %d개(%.0f Hz), OF %d개, LRF %d개, %.1f s\n', numel(D.imu.t), ...
    1/median(diff(D.imu.t)), sum(D.of.valid), numel(D.lrf.t_valid), D.imu.t(end));

%% Step 1. 상태 정의 ------------------------------------------------------
%   공칭 상태 x (구조체)                오차 상태 δx (15x1, 공분산 P 의 대상)
%     x.p  : 위치      [m]   (월드)       δx(1:3)   = δp
%     x.v  : 속도      [m/s] (월드)       δx(4:6)   = δv
%     x.R  : 자세 R_WB (3x3)              δx(7:9)   = δθ  (R_true = R·Exp(δθ))
%     x.ba : 가속도계 바이어스            δx(10:12) = δb_a
%     x.bg : 자이로 바이어스              δx(13:15) = δb_g
%   월드: z-up (중력 = [0 0 -9.81]),  바디: IMU 축

% 초기값: 첫 시점 GT (평가용 정답은 초기화에만 사용)
x0.p  = interp_gt(gt, D.imu.t(1), {'px','py','pz'});
x0.v  = interp_gt(gt, D.imu.t(1), {'vx','vy','vz'});
x0.R  = quat2rot(interp_gt(gt, D.imu.t(1), {'qw','qx','qy','qz'}));
x0.ba = zeros(3, 1);
x0.bg = zeros(3, 1);

P0 = diag([0.01*[1 1 1], 0.05*[1 1 1], deg2rad(1)*[1 1 1], ...
           0.10*[1 1 1], 0.02*[1 1 1]].^2);

%% Step 2. 시스템 모델 파라미터 (Q) --------------------------------------
%   IMU 잡음밀도: 데이터시트/Allan variance 값 (실데이터는 INSANE 제공 값 사용)
prm.g       = 9.81;
prm.acc_n   = 0.004;     % 가속도 잡음밀도   [m/s^2/sqrt(Hz)]
prm.gyro_n  = 0.0005;    % 자이로 잡음밀도   [rad/s/sqrt(Hz)]
prm.acc_rw  = 1e-3;      % 가속도 바이어스 random walk
prm.gyro_rw = 1e-4;      % 자이로 바이어스 random walk
prm.x0 = x0;  prm.P0 = P0;

%% Step 3. 측정 모델 파라미터 (R) ----------------------------------------
prm.R_BC = R_BC;  prm.r_BC = r_BC;
prm.sig_lrf        = 0.03;   % LRF 잡음 [m]
prm.sig_flow_best  = 0.02;   % 품질 최고일 때 flow 잡음 [rad/s]  (B 는 항상 이 값)
prm.sig_flow_worst = 0.15;   % 품질 최저일 때
prm.Q_min          = 0.03;   % 이보다 낮으면 OF 제외 (C)
prm.vz_scale       = 2.0;    % v_z 는 발산(divergence)으로 구해져 더 부정확

%% Step 4. 방법별 실행 ----------------------------------------------------
algs = struct( ...
  'name',       {'A: IMU only', 'B: fixed R', 'C: adaptive R', 'C0: no delay comp.'}, ...
  'use_of',     {false,  true,    true,       true}, ...
  'use_lrf',    {false,  true,    true,       true}, ...
  'R_mode',     {'fixed','fixed', 'adaptive', 'adaptive'}, ...
  'delay_comp', {true,   true,    true,       false});

for m = 1:numel(algs)
    p = prm;
    for f = {'use_of', 'use_lrf', 'R_mode', 'delay_comp'}
        p.(f{1}) = algs(m).(f{1});
    end
    tic;
    E(m) = run_filter(D, p); %#ok<SAGROW>
    fprintf('%-20s 완료 (%.1f s, 재추정 스텝 %d)\n', algs(m).name, toc, E(m).n_replay);
end

%% Step 5. 평가 (GT 를 IMU 시각으로 보간) --------------------------------
t = D.imu.t;
G.p = interp_gt(gt, t, {'px','py','pz'});
G.v = interp_gt(gt, t, {'vx','vy','vz'});
G.eul = zeros(numel(t), 3);
q = interp_gt(gt, t, {'qw','qx','qy','qz'});
for i = 1:numel(t), G.eul(i, :) = rot2eul(quat2rot(q(i, :))); end

% 영상 저하 구간: OF 품질 < 0.3 이거나 0.2 s 이상 끊긴 구간 (그림 음영, 0.25 s 이상만)
bad = degraded_intervals(D.of, 0.3, 0.2, 0.25);

fprintf('\n%-20s %10s %10s %10s %10s\n', '방법', 'RMSE_p[m]', 'RMSE_xy', 'final[m]', 'RMSE_v');
for m = 1:numel(E)
    ep = E(m).p - G.p;  ev = E(m).v - G.v;
    E(m).err = sqrt(sum(ep.^2, 2));
    fprintf('%-20s %10.3f %10.3f %10.3f %10.3f\n', algs(m).name, ...
        sqrt(mean(sum(ep.^2, 2))), sqrt(mean(sum(ep(:, 1:2).^2, 2))), ...
        E(m).err(end), sqrt(mean(sum(ev.^2, 2))));
end

%% Step 6. 그림 (그림 글자는 영어: 논문/보고서에 바로 사용) -------------------
C = E(3);  B = E(2);
col = [0 0 0; 0.85 0.33 0.10; 0.00 0.45 0.74; 0.47 0.67 0.19; 0.49 0.18 0.56];
lab = 'xyz';

% (1) 궤적
figure('Name', 'trajectory', 'Position', [50 50 900 420]);
subplot(1, 2, 1); hold on; grid on; axis equal;
plot(G.p(:, 1), G.p(:, 2), 'k', 'LineWidth', 2);
plot(B.p(:, 1), B.p(:, 2), '--', 'Color', col(2, :), 'LineWidth', 1.2);
plot(C.p(:, 1), C.p(:, 2), 'Color', col(3, :), 'LineWidth', 1.2);
plot(G.p(1, 1), G.p(1, 2), 'ko', 'MarkerFaceColor', 'g');
xlabel('x [m]'); ylabel('y [m]'); title('XY trajectory');
legend('GT', 'B: fixed R', 'C: adaptive R', 'start', 'Location', 'best');
subplot(1, 2, 2); hold on; grid on;
plot(D.lrf.t_valid, D.lrf.range, '.', 'Color', [0.6 0.6 0.6], 'MarkerSize', 3);
plot(t, G.p(:, 3), 'k', 'LineWidth', 2);
plot(t, C.p(:, 3), 'Color', col(3, :));
xlabel('t [s]'); ylabel('z [m]'); title('Altitude');
legend('LRF range', 'GT', 'C', 'Location', 'best');
save_fig(fig_dir, 'fig1_trajectory');

% (2) 위치 성분 + C 의 오차와 ±3σ (필터 일관성 확인)
figure('Name', 'position', 'Position', [60 60 1000 600]);
for a = 1:3
    subplot(2, 3, a); hold on; grid on;
    plot(t, G.p(:, a), 'k', 'LineWidth', 1.5);
    plot(t, C.p(:, a), 'Color', col(3, :));
    ylabel(['p_' lab(a) ' [m]']); xlabel('t [s]');
    if a == 1, legend('GT', 'C'); end
    subplot(2, 3, 3 + a); hold on; grid on;
    e_a = C.p(:, a) - G.p(:, a);
    hs = shade(bad, 1.2*max(abs([e_a; 3*C.sig(:, a)]))*[-1 1]);
    h1 = plot(t, e_a, 'Color', col(3, :));
    h2 = plot(t, 3*C.sig(:, a), 'r:');  plot(t, -3*C.sig(:, a), 'r:');
    ylabel(['e_' lab(a) ' [m]']); xlabel('t [s]');
    if a == 1, legend([h1 h2 hs], 'error', '\pm3\sigma', 'degraded'); end
end
save_fig(fig_dir, 'fig2_position_error_3sigma');

% (3) 속도: OF 측정(월드로 회전) vs GT vs 추정
figure('Name', 'velocity', 'Position', [70 70 1000 600]);
of_ok = D.of.valid == 1;
vb_of = [D.of.vx(of_ok) D.of.vy(of_ok) D.of.vz(of_ok)];
k_of  = interp1(t, 1:numel(t), D.of.t_valid(of_ok), 'nearest', 'extrap');
vw_of = zeros(size(vb_of));
for j = 1:numel(k_of)          % 그림용: GT 자세로 OF 바디속도를 월드로 회전
    vw_of(j, :) = (quat2rot(q(k_of(j), :)) * vb_of(j, :).').';
end
for a = 1:3
    subplot(3, 1, a); hold on; grid on;
    hs = shade(bad, [min(vw_of(:, a)) max(vw_of(:, a))] + 0.2*[-1 1]);
    h1 = plot(D.of.t_valid(of_ok), vw_of(:, a), '.', 'Color', [0.6 0.6 0.6], 'MarkerSize', 5);
    h2 = plot(t, G.v(:, a), 'k', 'LineWidth', 1.5);
    h3 = plot(t, C.v(:, a), 'Color', col(3, :));
    ylabel(['v_' lab(a) ' [m/s]']);
    if a == 1
        legend([h1 h2 h3 hs], 'OF meas.', 'GT', 'C', 'degraded', 'Location', 'best');
        title('Velocity (world frame)');
    end
end
xlabel('t [s]');
save_fig(fig_dir, 'fig3_velocity');

% (4) 방법별 위치 오차 (log)
figure('Name', 'error', 'Position', [80 80 900 400]); hold on; grid on;
set(gca, 'YScale', 'log');
hs = shade(bad, [1e-3 1e3]);
hm = [];
for m = 1:numel(E)
    hm = [hm, plot(t, max(E(m).err, 1e-3), 'Color', col(m + 1, :), 'LineWidth', 1.2)]; %#ok<AGROW>
end
xlabel('t [s]'); ylabel('|p - p_{GT}| [m]'); title('Position error by method');
legend([hm hs], [{algs.name}, {'degraded'}], 'Location', 'northwest');
save_fig(fig_dir, 'fig4_error_compare');

% (5) OF 품질 → 측정잡음 R → 측정모델 스위칭  (논문 Fig.4 형식)
figure('Name', 'quality', 'Position', [90 90 1000 650]);
subplot(3, 1, 1); hold on; grid on;
hs = shade(bad, [0 1]);
h1 = plot(D.of.t_valid, D.of.quality, '.-', 'Color', col(3, :), 'MarkerSize', 4);
h2 = plot([t(1) t(end)], prm.Q_min*[1 1], 'r--');
ylabel('Q'); title('OF quality'); legend([h1 h2 hs], 'Q', 'Q_{min}', 'degraded');
subplot(3, 1, 2); hold on; grid on;
plot(D.of.t_valid, B.of_sig, '.', 'Color', col(2, :), 'MarkerSize', 5);
plot(D.of.t_valid, C.of_sig, '.', 'Color', col(3, :), 'MarkerSize', 5);
ylabel('\sigma_v [m/s]'); title('OF velocity noise used in R (= \sigma_v^2), NaN = rejected');
legend('B: fixed', 'C: adaptive');
subplot(3, 1, 3); hold on; grid on;
km = find(C.mode < 4);
plot(t(km), C.mode(km), '.', 'Color', col(3, :), 'MarkerSize', 6);
set(gca, 'YTick', 1:3, 'YTickLabel', {'OF+LRF', 'OF', 'LRF'}); ylim([0.5 3.5]);
xlabel('t [s]'); title('Measurement model switching (C)');
save_fig(fig_dir, 'fig5_quality_R_mode');

% (6) 바이어스 추정 (합성 데이터면 참값 점선)
figure('Name', 'bias', 'Position', [100 100 900 500]);
tb_file = fullfile(data_dir, 'truth_bias.csv');
has_tb = exist(tb_file, 'file') == 2;
if has_tb, tb = read_csv_struct(tb_file); end
for a = 1:3
    subplot(2, 3, a); hold on; grid on;
    plot(t, C.bg(:, a), 'Color', col(3, :));
    if has_tb, plot(t([1 end]), tb.(['bg' lab(a)])*[1 1], 'k--'); end
    title(['b_{g,' lab(a) '} [rad/s]']);
    subplot(2, 3, 3 + a); hold on; grid on;
    plot(t, C.ba(:, a), 'Color', col(3, :));
    if has_tb, plot(t([1 end]), tb.(['ba' lab(a)])*[1 1], 'k--'); end
    title(['b_{a,' lab(a) '} [m/s^2]']); xlabel('t [s]');
end
save_fig(fig_dir, 'fig6_bias');

fprintf('\n그림 저장: %s\n', fig_dir);
