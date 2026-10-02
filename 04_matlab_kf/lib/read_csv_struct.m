function S = read_csv_struct(file)
% 헤더가 있는 CSV → 구조체 (S.열이름 = 열벡터).  MATLAB/Octave 공통.
fid = fopen(file, 'r');
if fid < 0, error('파일 없음: %s', file); end
hdr = fgetl(fid);  fclose(fid);
names = strtrim(strsplit(hdr, ','));
M = dlmread(file, ',', 1, 0);
for i = 1:numel(names)
    S.(names{i}) = M(:, i);
end
end
