%   칼만 필터. 상태 x = [횡속도 v; 요레이트 r], 측정 z = [r; ay]
%   (zeros 미리 확보 없이, 초기값을 직접 지정한 버전)
%% 차량 파라미터 (Lecture 4, 2DOF 모델)
a = 1.034;  b = 1.491;
m = 1573;   Iz = 2782.7;
Caf = 66366*2.2;  Car = 52812*2.2;
u0 = 20;

%% 연속 상태공간 -> 이산화
Ac = [-(Caf+Car)/(m*u0),      (b*Car-a*Caf)/(m*u0)-u0;
       (b*Car-a*Caf)/(Iz*u0), -(a^2*Caf+b^2*Car)/(Iz*u0)];
Bc = [Caf/m;
      a*Caf/Iz];
Cc = [0 1;
      Ac(1,:) + u0*[0 1]];
Dc = [0;
      Bc(1)];

Ts = 0.01;
sysd = c2d(ss(Ac,Bc,Cc,Dc), Ts, 'zoh');
Phi = sysd.A;   % Phi_{k-1}
Gam = sysd.B;   % Gamma_{k-1}
H   = sysd.C;   % H_k
Du  = sysd.D;

%% 노이즈 통계 (슬라이드 34: Q, R) / 초기 공분산
Q = diag([0.001 0.001]);
R = diag([0.01 0.1]);
P = diag([1 0.04]);      % 초기 추정오차 [1; 0.2]의 분산 = [1^2; 0.2^2]

t = 0:Ts:10;
N = length(t);

delta = zeros(1,N);      % 1초에 0.05 rad 스텝
delta(t >= 1) = 0.05;

%% 초기값 
x_true(:,1) = [0; 0];    % 진짜 차 : 직진 중 (횡속도 0, 요레이트 0)
x_est(:,1)  = [1; 0.2];  % 필터    : 일부러 틀린 초기 추정

z_meas(:,1) = H*x_true(:,1) + Du*delta(1) + chol(R,'lower')*randn(2,1);
% x_k = Phi*x_{k-1} + Gam*u_{k-1} + w_{k-1}   (True System)
% z_k = H*x_k + Du*u_k + v_k                  (Measurement)
%% True System 시뮬레이션 + 칼만 필터
for k = 2:N            % 

    % True System (w_k, v_k 노이즈 포함)
    w = chol(Q,'lower')*randn(2,1);     % 플랜트 노이즈 w ~ N(0,Q)
    x_true(:,k) = Phi*x_true(:,k-1) + Gam*delta(k-1) + w;

    nu = chol(R,'lower')*randn(2,1);    % 측정 노이즈 nu ~ N(0,R)
    z_meas(:,k) = H*x_true(:,k) + Du*delta(k) + nu;

    % Predict (time update)
    x_minus = Phi*x_est(:,k-1) + Gam*delta(k-1);
    P_minus = Phi*P*Phi' + Q;
%Q , R은 설계값임
    % Update (measurement update)
    S = H*P_minus*H' + R * 10;
    K = P_minus*H'/S;
    x_est(:,k) = x_minus + K*(z_meas(:,k) - (H*x_minus + Du*delta(k)));
    P = (eye(2) - K*H)*P_minus;

end

%% 결과
Z_est = H*x_est + Du*delta;

figure

subplot(221)
plot(t,x_true(1,:),'b--',t,x_est(1,:),'r'); grid
xlabel('time (sec)'); ylabel('Lateral speed (m/sec)')
legend('True','Estimated')

subplot(222)
plot(t,z_meas(1,:)*180/pi,'b',t,x_est(2,:)*180/pi,'r'); grid
xlabel('time (sec)'); ylabel('Yaw rate (deg/sec)')
legend('Measured','Estimated')

subplot(223)
plot(t,z_meas(2,:),'b',t,Z_est(2,:),'r'); grid
xlabel('time (sec)'); ylabel('Lat. Accel. (m/sec^2)')
legend('Measured','Estimated')

subplot(224)
plot(t,delta*180/pi,'r'); grid
xlabel('time (sec)'); ylabel('Steering (deg)')
