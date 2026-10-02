function [z, h, H, R] = meas_lrf_range(x, rng, prm)
% LRF 거리 측정모델 (평평한 지면 z=0, LRF 는 카메라 광축 방향)
%   d = p_z,LRF / s,   p_z,LRF = e3'(p + R r_BC),   s = -e3' R c   (c = R_BC e3: 광축, 바디)
e3 = [0; 0; 1];
c  = prm.R_BC * e3;
r  = prm.r_BC;
pz = e3.' * (x.p + x.R*r);
s  = -e3.' * x.R * c;                 % = cos(기울기)

z = rng;
h = pz / s;

% ∂(e3' R a)/∂δθ = -e3' R skew(a)
dpz_dth = -e3.' * x.R * skew(r);
ds_dth  =  e3.' * x.R * skew(c);
H = zeros(1, 15);
H(3)   = 1 / s;                                   % ∂/∂p_z
H(7:9) = dpz_dth / s - pz / s^2 * ds_dth;         % ∂/∂δθ
R = prm.sig_lrf^2;
end
