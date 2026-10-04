function [x, P] = ekf_predict(x, P, w_m, a_m, dt, prm)
% 예측 단계 (IMU 1샘플)  ── kalman0802 의
%     x_minus = Phi*x + Gam*u,   P_minus = Phi*P*Phi' + Q   에 해당
%
%   공칭(nominal) 상태는 비선형 운동방정식으로 그대로 적분하고,
%   공분산 P 는 오차상태(error-state) 선형화 Phi 로 전파한다.
%   차이: Phi 가 상수가 아니라 현재 자세 R 과 IMU 값에 따라 매 스텝 바뀜

g = [0; 0; -prm.g];
w = w_m(:) - x.bg;                 % 바이어스 뺀 각속도 (바디)
f = a_m(:) - x.ba;                 % 바이어스 뺀 비력   (바디)
a = x.R * f + g;                   % 월드 가속도

% --- 1) 공칭 상태 적분 ---
x.p = x.p + x.v*dt + 0.5*a*dt^2;
x.v = x.v + a*dt;
x.R = x.R * so3exp(w*dt);

% --- 2) 오차상태 Phi (15x15),  δx = [δp δv δθ δba δbg] ---
I3 = eye(3);  Z3 = zeros(3);
Fc = [Z3  I3  Z3              Z3     Z3;
      Z3  Z3  -x.R*skew(f)    -x.R   Z3;
      Z3  Z3  -skew(w)        Z3     -I3;
      Z3  Z3  Z3              Z3     Z3;
      Z3  Z3  Z3              Z3     Z3];
Phi = eye(15) + Fc*dt;                     % 1차 이산화 (Ts 가 작아 expm 과 거의 같음)

% --- 3) 프로세스 잡음 Q (IMU 잡음밀도 → 이산화) ---
Q = blkdiag(1e-8*I3, ...                       % 위치 (수치 안정용)
            prm.acc_n^2*dt*I3, ...
            prm.gyro_n^2*dt*I3, ...
            prm.acc_rw^2*dt*I3, ...
            prm.gyro_rw^2*dt*I3);

P = Phi*P*Phi.' + Q;
P = 0.5*(P + P.');
end
