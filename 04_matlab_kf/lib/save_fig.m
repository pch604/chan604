function save_fig(d, name)
print(gcf, fullfile(d, [name '.png']), '-dpng', '-r130');
end
