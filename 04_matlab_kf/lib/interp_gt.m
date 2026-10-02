function y = interp_gt(gt, tq, names)
% GT 열(names)을 시각 tq 로 선형보간.  tq 가 스칼라면 열벡터 반환.
y = zeros(numel(tq), numel(names));
for i = 1:numel(names)
    y(:, i) = interp1(gt.t, gt.(names{i}), tq(:), 'linear', 'extrap');
end
if numel(tq) == 1, y = y(:); end
end
