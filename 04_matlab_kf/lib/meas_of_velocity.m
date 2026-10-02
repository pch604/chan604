function [z, h, H, R] = meas_of_velocity(x, of, prm)
% OF 속도 측정모델:  z = v_B (Python 출력, 회전·레버암 보정 완료)
%
%   h(x) = R' v   +   M b_g
%          ─┬──      ──┬──
%           │          └ Python 이 '바이어스 낀 자이로'로 회전을 뺐기 때문에 남는 가짜 속도.
%           │            M (3x3) 은 Python 이 같은 최소제곱으로 계산해 넘겨줌
%           │            (화각이 좁으면 M ≈ Z·skew(광축) — PX4 EKF2 의 flow gyro bias 와 같은 이유)
%           └ 바디 좌표 속도
%   H    = [0   R'   skew(R'v)   0   M]
z  = of.v(:);
vb = x.R.' * x.v;
h  = vb + of.M * x.bg;
H  = [zeros(3)  x.R.'  skew(vb)  zeros(3)  of.M];

% 측정잡음 R: flow 각속도 잡음 [rad/s] × 거리 = 속도 잡음 [m/s]   (PX4 EKF2 와 동일 개념)
switch prm.R_mode
    case 'fixed'                         % 방법 B: 고정 R (정상 영상에 맞춘 값)
        sig_flow = prm.sig_flow_best;
    case 'adaptive'                      % 방법 C: 품질 Q 로 선형보간 (PX4 calcOptFlowMeasVar)
        w = (of.quality - prm.Q_min) / (1 - prm.Q_min);
        w = max(0, min(1, w));
        sig_flow = w*prm.sig_flow_best + (1 - w)*prm.sig_flow_worst;
end
sig_v = sig_flow * of.range;
R = diag([sig_v, sig_v, prm.vz_scale*sig_v].^2);
end
