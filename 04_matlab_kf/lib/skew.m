function S = skew(w)
% 벡터 → 반대칭행렬:  skew(a)*b = cross(a, b)
S = [   0   -w(3)  w(2);
      w(3)    0   -w(1);
     -w(2)  w(1)    0  ];
end
