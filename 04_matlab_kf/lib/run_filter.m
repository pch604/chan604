function est = run_filter(D, prm)
% IMU 주기로 EKF 를 돌리면서, 늦게 도착한 측정은 과거 시점으로 되돌아가
% 보정 후 현재까지 다시 전파한다 (김민수·안창선 2025, Fig.4 "re-estimation").
%
%   측정 이벤트마다 두 시각:
%     t_valid : 측정이 나타내는 상태의 시각  → 이 스텝에서 보정
%     t_avail : 필터가 측정을 받는 시각      → 이 스텝에서 재추정 시작
%   prm.delay_comp = false 이면 t_valid = t_avail 로 취급 (지연 무시, 비교용)

t = D.imu.t;  N = numel(t);

% ---------------- 측정 이벤트 목록 ----------------
%   type 1 = OF 속도,  type 2 = LRF 거리
ev = struct('type', {}, 'idx', {}, 'k_valid', {}, 'k_avail', {});
if prm.use_of
    for i = find(D.of.valid(:).' == 1)
        ev(end+1) = make_event(1, i, D.of.t_valid(i), D.of.t_avail(i), t, prm); %#ok<AGROW>
    end
end
if prm.use_lrf
    for i = 1:numel(D.lrf.t_valid)
        ev(end+1) = make_event(2, i, D.lrf.t_valid(i), D.lrf.t_avail(i), t, prm); %#ok<AGROW>
    end
end
ev = ev([ev.k_valid] >= 2 & [ev.k_avail] <= N);
k_avail = [ev.k_avail];

% ---------------- 버퍼 (각 스텝의 사후 추정값) ----------------
Xb = cell(N, 1);  Pb = zeros(15, 15, N);
Xb{1} = prm.x0;   Pb(:, :, 1) = prm.P0;
meas_at = cell(N, 1);                 % 스텝별로 '적용할' 측정 이벤트 번호
mode = 4*ones(N, 1);                  % 1: OF+LRF, 2: OF, 3: LRF, 4: 없음 (논문 Case 1~4)
of_sig = nan(numel(D.of.t_valid), 1); % 사용된 OF 속도 잡음 σ (그림용)
n_replay = 0;

for k = 2:N
    % (1) 이번 스텝에 도착한 측정 → 유효 시각 스텝에 등록
    k_start = k;
    for e = find(k_avail == k)
        kv = ev(e).k_valid;
        meas_at{kv}(end+1) = e;
        k_start = min(k_start, kv);
    end
    n_replay = n_replay + (k - k_start);

    % (2) k_start 부터 현재 k 까지 다시 예측-보정
    x = Xb{k_start-1};  P = Pb(:, :, k_start-1);
    for i = k_start:k
        dt = t(i) - t(i-1);
        [x, P] = ekf_predict(x, P, D.imu.w(i-1, :), D.imu.a(i-1, :), dt, prm);
        [x, P, mode(i), of_sig] = apply_measurements(x, P, ev(meas_at{i}), D, prm, of_sig);
        Xb{i} = x;  Pb(:, :, i) = P;
    end
end

% ---------------- 결과 정리 ----------------
est.t = t;  est.mode = mode;  est.of_sig = of_sig;  est.n_replay = n_replay;
est.p = zeros(N, 3); est.v = zeros(N, 3); est.eul = zeros(N, 3);
est.ba = zeros(N, 3); est.bg = zeros(N, 3); est.sig = zeros(N, 15);
for i = 1:N
    est.p(i, :) = Xb{i}.p.';   est.v(i, :) = Xb{i}.v.';
    est.ba(i, :) = Xb{i}.ba.'; est.bg(i, :) = Xb{i}.bg.';
    est.eul(i, :) = rot2eul(Xb{i}.R);
    est.sig(i, :) = sqrt(diag(Pb(:, :, i))).';
end
est.R_end = Xb{N}.R;
end


function e = make_event(type, idx, t_valid, t_avail, t, prm)
if ~prm.delay_comp
    t_valid = t_avail;
end
e.type = type;  e.idx = idx;
e.k_valid = find_step(t, t_valid);
e.k_avail = find_step(t, t_avail);
end


function k = find_step(t, tq)
% tq 이후 첫 IMU 스텝 (tq 가 범위 밖이면 경계값)
k = find(t >= tq, 1, 'first');
if isempty(k), k = numel(t) + 1; end
end


function [x, P, mode, of_sig] = apply_measurements(x, P, evs, D, prm, of_sig)
% 측정모델 스위칭 (논문 II.G): 이번 스텝에 있는 측정만 골라 순차 보정
has_of = false;  has_lrf = false;
for e = evs
    if e.type == 1
        of.v = [D.of.vx(e.idx) D.of.vy(e.idx) D.of.vz(e.idx)];
        of.quality = D.of.quality(e.idx);
        of.range = D.of.range(e.idx);
        of.M = [D.of.m00(e.idx) D.of.m01(e.idx) D.of.m02(e.idx);
                D.of.m10(e.idx) D.of.m11(e.idx) D.of.m12(e.idx);
                D.of.m20(e.idx) D.of.m21(e.idx) D.of.m22(e.idx)];
        if strcmp(prm.R_mode, 'adaptive') && of.quality < prm.Q_min
            continue;                              % 품질 너무 낮음 → 측정 제외
        end
        [z, h, H, R] = meas_of_velocity(x, of, prm);
        of_sig(e.idx) = sqrt(R(1, 1));
        has_of = true;
    else
        [z, h, H, R] = meas_lrf_range(x, D.lrf.range(e.idx), prm);
        has_lrf = true;
    end
    [x, P] = ekf_update(x, P, z, h, H, R);
end
mode = 4 - 3*(has_of && has_lrf) - 2*(has_of && ~has_lrf) - 1*(~has_of && has_lrf);
end
