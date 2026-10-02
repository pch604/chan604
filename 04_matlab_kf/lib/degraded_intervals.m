function iv = degraded_intervals(of, q_thr, gap, min_len)
% OF 품질 < q_thr 이거나 측정이 gap[s] 이상 끊긴 구간 → [시작 끝] (n x 2)
% min_len[s] 보다 짧은 구간(경계의 순간적 저하)은 버림
tt  = of.t_valid(:);
bad = of.quality(:) < q_thr | of.valid(:) == 0;
iv  = zeros(0, 2);
i = 1;
while i <= numel(tt)
    if bad(i)
        j = i;
        while j < numel(tt) && bad(j+1), j = j + 1; end
        iv(end+1, :) = [tt(max(i-1, 1)) tt(min(j+1, numel(tt)))]; %#ok<AGROW>
        i = j + 1;
    else
        i = i + 1;
    end
end
k = find(diff(tt) > gap);
iv = [iv; tt(k) tt(k+1)];
iv = iv(iv(:, 2) - iv(:, 1) >= min_len, :);
end
