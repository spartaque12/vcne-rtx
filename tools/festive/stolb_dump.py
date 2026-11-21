# python -I stolb_dump.py : extract vc_stolb_*.wft + vc_stolbs.wtd from VCNE's img, print structure
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, r'F:\games\VCNE_RTX\_debug')
import imglib, ivres
IMG = r'F:\games\VCNE_RTX\update\1. Various Map Edits\1. VariousMapEdits.img'
OUT = r'E:\_tools\festive_v\vc'
os.makedirs(OUT, exist_ok=True)
R = lambda v: tuple(round(x, 3) for x in v)
for n in ['vc_stolb_1', 'vc_stolb_1b', 'vc_stolb_2', 'vc_stolb_3', 'vc_stolb_4', 'vc_stolb_5']:
    e, data = imglib.read(IMG, n + '.wft'); open(os.path.join(OUT, n + '.wft'), 'wb').write(data)
    d = ivres.load(data); print(n, 'shaders', [(s['name'], s['sps']) for s in d['shaders']])
    for b in d['bones']: print('  bone', b['idx'], b['id'], b['name'], 'local', R(b['local'][12:15]), 'world', R(b['world'][12:15]))
    for mi, m in enumerate(d['models']):
        print('  model', mi, m['hdr'].hex())
        for g in m['geoms']:
            pos = [struct.unpack_from('<3f', g['v'], i * g['stride']) for i in range(g['vcount'])]; xs = list(zip(*pos))
            print('    geom sh', g['shader'], 'stride', g['stride'], 'fvf', hex(g['fvf']), 'v', g['vcount'], 'idx', len(g['i']), g['gcounts'], 'min', R(map(min, xs)), 'max', R(map(max, xs)))
try:
    e, data = imglib.read(IMG, 'vc_stolbs.wtd'); open(os.path.join(OUT, 'vc_stolbs.wtd'), 'wb').write(data); print('wtd ok', len(data))
except KeyError as x: print('no wtd in img', x)
