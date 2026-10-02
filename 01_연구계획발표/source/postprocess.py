"""Inject the original VDEC/PNU bottom banner (master objects of the v5 deck) into the
generated 16:9 master, and set Korean East-Asian theme fonts."""
import re, shutil, sys, zipfile, os, tempfile

RAW, ORIG, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SW_OLD, SW_NEW = 9144000, 12192000

tmp = tempfile.mkdtemp()
zipfile.ZipFile(RAW).extractall(tmp)
oz = zipfile.ZipFile(ORIG)
omaster = oz.read('ppt/slideMasters/slideMaster1.xml').decode('utf8')
orels = oz.read('ppt/slideMasters/_rels/slideMaster1.xml.rels').decode('utf8')

tree = omaster[omaster.index('<p:spTree>'):omaster.index('</p:spTree>')]
# original banner elements: gradient rect, lab text box, two logo pictures
def grab(start_pat):
    i = tree.index(start_pat)
    tag = 'p:sp' if start_pat.startswith('<p:sp>') else 'p:pic'
    j = tree.index('</%s>' % tag, i) + len('</%s>' % tag)
    return tree[i:j]
parts = []
for m in re.finditer(r'<p:(sp|pic)>', tree):
    tag = m.group(1)
    j = tree.index('</p:%s>' % tag, m.start()) + len('</p:%s>' % tag)
    el = tree[m.start():j]
    if '<p:ph ' in el:
        continue
    parts.append(el)
assert len(parts) == 4, len(parts)
rid_map = {}
for rid, tgt in re.findall(r'Id="(rId\d+)"[^>]*Target="\.\./media/([^"]+)"', orels) + \
        [(a, b) for b, a in re.findall(r'Target="\.\./media/([^"]+)"[^>]*Id="(rId\d+)"', orels)]:
    rid_map[rid] = tgt

mdir = os.path.join(tmp, 'ppt/slideMasters')
mpath = os.path.join(mdir, 'slideMaster1.xml')
rpath = os.path.join(mdir, '_rels/slideMaster1.xml.rels')
master = open(mpath, encoding='utf8').read()
rels = open(rpath, encoding='utf8').read()
existing = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels)]
nxt = max(existing) + 1
media_dir = os.path.join(tmp, 'ppt/media')
os.makedirs(media_dir, exist_ok=True)
new_parts = []
ids = [int(x) for x in re.findall(r'<p:cNvPr id="(\d+)"', master)]
nid = max(ids + [1]) + 100
for el in parts:
    for rid in re.findall(r'r:embed="(rId\d+)"', el):
        src = rid_map[rid]
        dst = 'vdec_banner_' + src
        with open(os.path.join(media_dir, dst), 'wb') as f:
            f.write(oz.read('ppt/media/' + src))
        new_rid = 'rId%d' % nxt; nxt += 1
        rels = rels.replace('</Relationships>',
            '<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/%s"/></Relationships>' % (new_rid, dst))
        el = el.replace('r:embed="%s"' % rid, 'r:embed="%s"' % new_rid)
    # unique shape ids
    el = re.sub(r'<p:cNvPr id="\d+"', lambda m: '<p:cNvPr id="%d"' % (nid + len(new_parts)), el, count=1)
    # widen to 16:9: full-width bar stretches, right-anchored logo keeps its distance from the right edge
    off = re.search(r'<a:off x="(\d+)" y="(\d+)"/><a:ext cx="(\d+)" cy="(\d+)"/>', el)
    x, y, cx, cy = map(int, off.groups())
    if cx == SW_OLD:
        cx = SW_NEW
    elif x > SW_OLD / 2:
        x = SW_NEW - (SW_OLD - x)
    el = el.replace(off.group(0), '<a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/>' % (x, y, cx, cy))
    new_parts.append(el)
# insert banner right after the group properties (behind everything else)
gi = master.index('</p:grpSpPr>', master.index('<p:spTree>')) + len('</p:grpSpPr>')
master = master[:gi] + ''.join(new_parts) + master[gi:]
if 'xmlns:r=' not in master[:500]:
    master = master.replace('<p:sldMaster ', '<p:sldMaster xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ', 1)
open(mpath, 'w', encoding='utf8').write(master)
open(rpath, 'w', encoding='utf8').write(rels)

ct = os.path.join(tmp, '[Content_Types].xml')
c = open(ct, encoding='utf8').read()
if 'Extension="png"' not in c:
    c = c.replace('<Default ', '<Default Extension="png" ContentType="image/png"/><Default ', 1)
open(ct, 'w', encoding='utf8').write(c)

# theme: Latin Arial, East Asian 맑은 고딕
tdir = os.path.join(tmp, 'ppt/theme')
for fn in os.listdir(tdir):
    p = os.path.join(tdir, fn)
    t = open(p, encoding='utf8').read()
    t = re.sub(r'<a:ea typeface="[^"]*"\s*/>', '<a:ea typeface="맑은 고딕"/>', t)
    t = re.sub(r'(<a:(major|minor)Font>\s*<a:latin typeface=")[^"]*(")', r'\1Arial\3', t)
    open(p, 'w', encoding='utf8').write(t)

if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    # content types first
    z.write(ct, '[Content_Types].xml')
    for root, _, files in os.walk(tmp):
        for f in files:
            full = os.path.join(root, f)
            arc = os.path.relpath(full, tmp)
            if arc == '[Content_Types].xml':
                continue
            z.write(full, arc)
shutil.rmtree(tmp)
print('ok', OUT)
