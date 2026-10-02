function e = rot2eul(R)
% 회전행렬(R_WB) → [roll pitch yaw] (ZYX)
e = [atan2(R(3,2), R(3,3)), -asin(max(-1, min(1, R(3,1)))), atan2(R(2,1), R(1,1))];
end
