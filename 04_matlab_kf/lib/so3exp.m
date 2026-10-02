function R = so3exp(phi)
% 회전벡터 phi [rad] → 회전행렬 (Rodrigues 공식)
th = norm(phi);
if th < 1e-10
    R = eye(3) + skew(phi);
    return;
end
a = phi / th;
R = cos(th)*eye(3) + (1 - cos(th))*(a*a.') + sin(th)*skew(a);
end
