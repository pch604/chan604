function [x, P, nis] = ekf_update(x, P, z, h, H, R)
% 보정 단계 ── 선형 KF 와 같은 식.  다른 점은 마지막 '주입(injection)' 뿐.
y = z - h;                                 % 잔차 (innovation)
S = H*P*H.' + R;
K = P*H.' / S;                             % 칼만 이득
dx = K*y;                                  % 오차상태 추정
I_KH = eye(15) - K*H;
P = I_KH*P*I_KH.' + K*R*K.';               % Joseph form (수치적으로 안정)
P = 0.5*(P + P.');
nis = y.' / S * y;                         % 정규화 잔차 (일관성 확인용)

% 주입: x ← x ⊕ δx   (회전은 곱으로 더함)
x.p  = x.p  + dx(1:3);
x.v  = x.v  + dx(4:6);
x.R  = x.R  * so3exp(dx(7:9));
x.ba = x.ba + dx(10:12);
x.bg = x.bg + dx(13:15);
end
