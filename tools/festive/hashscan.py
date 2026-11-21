# python -I hashscan.py <known_hashes.txt> <img> [...] : hash every geometry of every wdr/wft in the imgs, report hits in the known set
# (offline check that meshhash.exe reproduces the hashes existing Remix mods use)
import sys, os, struct, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, r'F:\games\VCNE_RTX\_debug')
import imglib, ivres
def all_geoms(data, wft):
    d = ivres.load(data); r = d['res']; ms = list(d['models'])
    if wft:
        vft = r.u(d['D'], 'I')
        for o in range(0, len(r.sys) - 0x80, 4):
            if struct.unpack_from('<I', r.sys, o)[0] == vft and struct.unpack_from('<I', r.sys, o + 0x40)[0] >> 28 == 5 and 0x50000000 + o != d['D']:
                ms += ivres.drawable(r, 0x50000000 + o)['models']
    return [g for m in ms for g in m['geoms']]
def hashes(geoms, tmp):
    blob = struct.pack('<I', len(geoms)) + b''.join(struct.pack('<III', g['stride'], g['vcount'], len(g['i'])) + g['v'] + struct.pack('<%dH' % len(g['i']), *g['i']) for g in geoms)
    open(tmp, 'wb').write(blob)
    return subprocess.run([os.path.join(HERE, 'meshhash.exe'), tmp], capture_output=True, text=True, check=True).stdout.split()
if __name__ == '__main__':
    known = set(l.strip().replace('mesh_', '') for l in open(sys.argv[1])); tot = 0; hits = []; errs = 0
    for img in sys.argv[2:]:
        geoms = []; names = []
        for nm, e in imglib.entries(img):
            if not nm.lower().endswith(('.wdr', '.wft')): continue
            with open(img, 'rb') as f: f.seek(e[2] * 0x800); data = f.read(e[3] * 0x800)
            try:
                for g in all_geoms(data, nm.lower().endswith('.wft')): geoms.append(g); names.append(nm)
            except Exception: errs += 1
        hs = hashes(geoms, os.path.join(HERE, '..', 'out', 'scan.bin')); tot += len(hs)
        hits += [(os.path.basename(img), n, h, g['stride'], g['vcount']) for n, h, g in zip(names, hs, geoms) if h in known]
    print(tot, 'geoms', errs, 'parse errors', len(hits), 'hits')
    for h in hits[:40]: print(' ', h)
