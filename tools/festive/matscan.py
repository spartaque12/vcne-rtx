# python -I matscan.py [remix-dxvk.log ...] : match the runtime's [GeometryHash] lines (rtx.debugLogGeometryHashes = True) against
# the vc_stolb geometry part hashes -> Remix material hash per part (mesh hash = geometry hash XOR material hash).
# Results accumulate in ..\out\stolb_materials.json : {"<geometry hash>": ["<material hash>", ...]}
import sys, os, re, json, subprocess, glob
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, '..', 'out', 'stolb_materials.json')
def parts():
    out = {}
    for f in sorted(glob.glob(os.path.join(HERE, '..', 'vc', '*.geo.bin'))):
        for i, l in enumerate(subprocess.run([os.path.join(HERE, 'meshhash.exe'), f], capture_output=True, text=True, check=True).stdout.splitlines()):
            h, p, ix, d, ic, vc = l.split(); out.setdefault((int(p, 16), int(ix, 16), int(d, 16)), []).append((os.path.basename(f)[:-8], i, h))
    return out
if __name__ == '__main__':
    P = parts(); db = json.load(open(DB)) if os.path.exists(DB) else {}
    rx = re.compile(r'D3D9 hash 0x(\w+) positions 0x(\w+) indices 0x(\w+) descriptor 0x(\w+) material 0x(\w+)')
    rx2 = re.compile(r'API mesh 0x\w+ key 0x(\w+) material key 0x(\w+)')
    G = {}
    for v in P.values():
        for model, gi, h in v: G.setdefault(int(h, 16), []).append((model, gi, h))
    for log in sys.argv[1:] or [r'F:\games\VCNE_RTX\rtx-remix\logs\remix-dxvk.log']:
        for l in open(log, errors='replace'):
            m = rx2.search(l)
            if m:   # same geometry drawn through the gta4-rtx Remix API path: key = geometry hash XOR material key
                k, mat = int(m.group(1), 16), int(m.group(2), 16)
                for model, gi, h in G.get(k ^ mat, []):
                    s = db.setdefault(h, [])
                    if '%016X' % mat not in s: s.append('%016X' % mat)
                    print(model, gi, h, 'API material %016X' % mat, 'replaced' if 'replaced' in l else '')
                continue
            m = rx.search(l)
            if not m: continue
            a, p, ix, d, mat = (int(x, 16) for x in m.groups())
            for model, gi, h in P.get((p, ix, d), []):
                assert int(h, 16) ^ mat == a, 'combination rule changed?'
                s = db.setdefault(h, [])
                if '%016X' % mat not in s: s.append('%016X' % mat)
                print(model, gi, h, 'material %016X' % mat, 'replaced' if 'replaced' in l else '')
    json.dump(db, open(DB, 'w'), indent=1)
    mats = sorted({m for v in db.values() for m in v}); print('materials:', mats)
    seen = {m for (k, v) in P.items() for (m, gi, h) in v if h in db}; print('models seen:', sorted(seen))
