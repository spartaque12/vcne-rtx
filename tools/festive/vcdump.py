# python -I vcdump.py <model> [...] : extract <model>.wft from VCNE's VariousMapEdits.img to ..\vc and print bones + parts
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, r'F:\games\VCNE_RTX\_debug')
import imglib, ivres
IMG = r'F:\games\VCNE_RTX\update\1. Various Map Edits\1. VariousMapEdits.img'
OUT = r'E:\_tools\festive_v\vc'
R = lambda v: tuple(round(x, 2) for x in v)
for n in sys.argv[1:]:
    e, data = imglib.read(IMG, n + '.wft'); open(os.path.join(OUT, n + '.wft'), 'wb').write(data)
    d = ivres.load(data); r = d['res']; print(n, [s['name'][4:] for s in d['shaders']])
    by = {b['ptr']: b for b in d['bones']}
    def wpos(b):
        p = [0, 0, 0]
        while b: p = [a + c for a, c in zip(p, b['pos'])]; b = by.get(b['parent'])
        return p
    for i, b in enumerate(d['bones']): print('  bone', i, b['id'], b['name'], 'world', R(wpos(b)), 'q', R(b['quat']))
    vft = r.u(d['D'], 'I')
    for o in range(0, len(r.sys) - 0x80, 4):
        if struct.unpack_from('<I', r.sys, o)[0] == vft and struct.unpack_from('<I', r.sys, o + 0x40)[0] >> 28 == 5 and 0x50000000 + o != d['D']:
            for m in ivres.drawable(r, 0x50000000 + o)['models']:
                for g in m['geoms']:
                    xs = list(zip(*[struct.unpack_from('<3f', g['v'], i * g['stride']) for i in range(g['vcount'])]))
                    print('  child', m['hdr'][3], 'sh', g['shader'], d['shaders'][g['shader']]['name'][4:], 'v', g['vcount'], 'i', len(g['i']), 'min', R(map(min, xs)), 'max', R(map(max, xs)))
