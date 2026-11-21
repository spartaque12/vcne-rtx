# python -I wplscan.py : find vc_stolb_* placements (position) in every .wpl of the VCNE_RTX install (loose files + inside .img, incl. stream wpls)
import sys, os, struct, zlib
sys.path.insert(0, r'F:\games\VCNE_RTX\_debug')
import imglib
ROOT = r'F:\games\VCNE_RTX'
names = sys.argv[1:] or ['vc_stolb_1', 'vc_stolb_1b', 'vc_stolb_2', 'vc_stolb_3', 'vc_stolb_4', 'vc_stolb_5']
H = {struct.pack('<I', imglib.joaat(n)): n for n in names}
def scan(data, src, out):
    for h, n in H.items():
        o = data.find(h)
        while o >= 28:
            x, y, z = struct.unpack_from('<3f', data, o - 28); q = struct.unpack_from('<4f', data, o - 16)
            if all(abs(v) < 5000 for v in (x, y, z)) and abs(sum(c * c for c in q) - 1) < 0.01: out.append((n, round(x, 2), round(y, 2), round(z, 2), src))
            o = data.find(h, o + 4)
out = []
for dp, dn, fn in os.walk(ROOT):
    if '_debug' in dp or '_vcne_1080' in dp: continue
    for f in fn:
        p = os.path.join(dp, f)
        try:
            if f.lower().endswith('.wpl'): scan(open(p, 'rb').read(), f, out)
            elif f.lower().endswith('.img'):
                for nm, e in imglib.entries(p):
                    if nm.lower().endswith('.wpl'):
                        with open(p, 'rb') as fh: fh.seek(e[2] * 0x800); scan(fh.read(e[3] * 0x800), f + '/' + nm, out)
        except Exception as x: print('ERR', p, repr(x)[:60])
from collections import Counter
print(Counter(o[0] for o in out))
for o in out: print(*o)
