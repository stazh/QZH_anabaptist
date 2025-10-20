from pathlib import Path
from lxml import etree

outdir = Path(r"C:\QZH_anabaptist\outputs")
files = sorted(outdir.glob('QZH_*.xml'))
files_checked = 0
files_with = 0
total_filled = 0
examples = []

ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

for fp in files:
    try:
        tree = etree.parse(str(fp))
    except Exception as e:
        continue
    files_checked += 1
    filled_here = []
    for pn in tree.xpath('.//tei:persName', namespaces=ns):
        txt = (pn.text or '').strip()
        if txt:
            filled_here.append((fp.name, pn.get('ref'), txt))
    if filled_here:
        files_with += 1
        total_filled += len(filled_here)
        for t in filled_here[:5]:
            examples.append(t)

print('--- persName count ---')
print(f'files_checked: {files_checked}')
print(f'files_with_filled_persName: {files_with}')
print(f'total_filled_persName: {total_filled}')
print('examples (file, ref, text):')
for f, ref, txt in examples[:10]:
    print(f"{f}\t{ref}\t{txt}")
