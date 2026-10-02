function h = shade(iv, yl)
% 저하 구간 음영.  데이터보다 '먼저' 그려야 선이 가려지지 않음.
h = patch(nan(1, 4), nan(1, 4), [1 0.85 0.6], 'EdgeColor', 'none');   % 범례용
for i = 1:size(iv, 1)
    patch(iv(i, [1 2 2 1]), yl([1 1 2 2]), [1 0.85 0.6], 'EdgeColor', 'none');
end
ylim(yl);
end
