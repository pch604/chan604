function [x, P] = ekf_predict(x, P, w_m, a_m, dt, prm)
% 예측 단계 (IMU 1샘플)  ── 선형 KF 의  x = F*x,  P = F*P*F' + Q  에 해당
%
%   공칭(nominal) 상태는 비선형 운동방정식으로 그대로 적분하고,
%   공분산 P 는 오차상태(error-state) 선형화 F 로 전파한다.

g = [0; 0; -prm.g];
w = w_m(:) - x.bg;                 % 바이어스 뺀 각속도 (바디)
f = a_m(:) - x.ba;                 % 바이어스 뺀 비력   (바디)
a = x.R * f + g;                   % 월드 가속도

% --- 1) 공칭 상태 적분 ---
x.p = x.p + x.v*dt + 0.5*a*dt^2;
x.v = x.v + a*dt;
x.R = x.R * so3exp(w*dt);

% --- 2) 오차상태 F (15x15),  δx = [δp δv δθ δba δbg] ---
I3 = eye(3);  Z3 = zeros(3);
Fc = [Z3  I3  Z3              Z3     Z3;
      Z3  Z3  -x.R*skew(f)    -x.R   Z3;
      Z3  Z3  -skew(w)        Z3     -I3;
      Z3  Z3  Z3              Z3     Z3;
      Z3  Z3  Z3              Z3     Z3];
F = eye(15) + Fc*dt;

% --- 3) 프로세스 잡음 Q (IMU 잡음밀도 → 이산화) ---
Q = blkdiag(1e-8*I3, ...                       % 위치 (수치 안정용)
            prm.acc_n^2*dt*I3, ...
            prm.gyro_n^2*dt*I3, ...
            prm.acc_rw^2*dt*I3, ...
            prm.gyro_rw^2*dt*I3);

P = F*P*F.' + Q;
P = 0.5*(P + P.');
end
