# python -I dump.py <files .ydr/.ytd> : print structure
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gta5res import ydr, ytd, joaat
SH = ('default normal normal_spec spec emissive emissivenight emissivestrong normal_spec_emissive emissive_alpha emissivenight_alpha '
      'glass glass_emissive glass_emissivenight glass_emissive_alpha glass_emissivenight_alpha normal_spec_decal normal_decal decal cutout '
      'emissive_additive_alpha emissive_speclum normal_spec_reflect spec_reflect reflect emissive_tnt emissive_clip normal_spec_alpha alpha '
      'glass_spec glass_normal_spec_reflect glass_reflect emissivestrong_alpha normal_spec_cutout emissive_additive_uv_alpha normal_alpha '
      'spec_alpha default_tnt normal_spec_tnt normal_tnt cutout_fence normal_cutout spec_decal').split()
PR = ('DiffuseSampler BumpSampler SpecSampler EmissiveMultiplier bumpiness specularIntensityMult specularFalloffMult HardAlphaBlend '
      'UseTessellation specularFresnel specMapIntMask globalAnimUV0 globalAnimUV1 wetnessMultiplier DiffuseSampler2 TextureSampler '
      'EnvironmentSampler reflectivePower').split()
H = {joaat(n): n for n in SH + [n + '.sps' for n in SH] + PR}
N = lambda h: H.get(h, hex(h))
R = lambda v: tuple(round(x, 2) for x in v)
if __name__ == '__main__':
    for p in sys.argv[1:]:
        b = os.path.basename(p)
        if p.endswith('.ytd'):
            for n, t in ytd(p).items(): print(b, n, t[0], t[1], struct.pack('<I', t[2]), t[3], len(t[4]))
            continue
        d = ydr(p); print(b, d['name'], 'bbox', [R(x) for x in d['bbox']], 'emb', list(d['embedded']))
        for i, s in enumerate(d['shaders']):
            print('  sh', i, N(s['hash']), N(s['file']), {N(k): v for k, v in s['tex'].items()}, {N(k): R(v) for k, v in s['vals'].items()})
        for g in d['geoms']:
            xs = list(zip(*g['pos']))
            print('  geom sh', g['shader'], 'v', len(g['pos']), 't', len(g['tris']), 'min', [round(min(a), 2) for a in xs], 'max', [round(max(a), 2) for a in xs])
        for l in d['lights']: print('  light', {k: (R(v) if isinstance(v, tuple) and isinstance(v[0], float) else v) for k, v in l.items()})
