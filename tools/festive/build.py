# Build the Remix replacement mod VCNE_festive_lamps: festive GTA V streetlights on VCNE's vc_stolb_* lamps.
# usage: python -I build.py            (writes the mod + prints the IDE light positions)
# Geometry is replaced per Remix mesh hash: the pole part of each vc_stolb carries the whole festive model,
# every other part (base, arm, casing, cover) is replaced by nothing.
import sys, os, struct, subprocess, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, r'F:\games\VCNE_RTX\_debug')
import gta5res, ivres
from gta5res import joaat
YDR = r'E:\_tools\festive_v\ydr'
VC = r'E:\_tools\festive_v\vc'
MOD = r'F:\games\VCNE_RTX\rtx-remix\mods\VCNE_festive_lamps'
# vc model -> (festive model, uniform scale).  Festive arm points to -Y, VC arm to +X: rotate +90 deg about Z.
MAP = {
    'vc_stolb_1':  ('prop_streetlight_01', 0.72),
    'vc_stolb_1b': ('prop_streetlight_01', 0.72),
    'vc_stolb_5':  ('prop_streetlight_03', 0.755),
    'vc_stolb_3':  ('prop_streetlight_01b', 0.83),
    'vc_stolb_4':  ('prop_streetlight_03', 0.78),
    'vc_stolb_2':  ('prop_streetlight_04', 1.16),
}
MAP.update(eval(os.environ.get('FESTIVE_MAP', '{}')))
UNIT = 1   # replacement space = game units (metres); x100 came out 100 times too big in game (run k05)
EM_SPIRAL = float(os.environ.get('EM_SPIRAL', 3)); EM_BULB = float(os.environ.get('EM_BULB', 12))
H = {joaat(n): n for n in ['DiffuseSampler', 'BumpSampler', 'SpecSampler', 'emissivestrong', 'emissivenight', 'emissive', 'glass_emissivenight', 'spec', 'normal_spec', 'default']}
EMISSIVE_HASHES = {0x21abe462}     # unnamed emissive preset used by the lamp head bulb

def tex_avg(t):
    """rough average colour of a DXT1/5 texture: colour0 of its smallest mip's block (sRGB 0..1)"""
    w, h, fmt, mips, data = t
    if fmt in (21, 22): return (data[2] / 255, data[1] / 255, data[0] / 255)
    blk = data[-8:]; c0 = struct.unpack_from('<H', blk)[0]
    return ((c0 >> 11) / 31, ((c0 >> 5) & 63) / 63, (c0 & 31) / 31)

def fl(v): return '(' + ', '.join('%.6g' % x for x in v) + ')'

def material(name, sh, d, texdir_rel):
    tex = {H.get(k, k): v for k, v in sh['tex'].items()}; kind = H.get(sh['hash'], sh['hash'])
    diff = tex.get('DiffuseSampler'); L = []
    def texref(n):
        return '@%s/%s.dds@' % (texdir_rel, n) if n in d['embedded'] else None
    emis = kind in ('emissivestrong', 'emissivenight', 'emissive', 'glass_emissivenight') or sh['hash'] in EMISSIVE_HASHES
    spiral = kind == 'emissivestrong'
    if spiral:      # flat colour texture ('white' / 'pink'): constants only
        c = tex_avg(d['embedded'][diff]) if diff in d['embedded'] else (1, 1, 1)
        amber = c[2] < 0.1
        if amber: c = (1, 0.72, 0.08)   # texture is amber (255,130,0); the mod's own screenshots read yellow after GTA V's bloom
        # tint group: the runtime (dxvk-remix fork, rtx_fork_tint.cpp) takes the colour from rtx.festive.<group>Color, live in the Remix menu
        L += ['custom string fork:tintGroup = "%s"' % ('lamp' if amber else 'lamp2'), 'color3f inputs:diffuse_color_constant = %s' % fl(c), 'bool inputs:enable_emission = 1', 'color3f inputs:emissive_color_constant = %s' % fl(c),
              'float inputs:emissive_intensity = %g' % EM_SPIRAL]
    else:
        if texref(diff): L.append('asset inputs:diffuse_texture = %s' % texref(diff))
        else: L.append('color3f inputs:diffuse_color_constant = (0.5, 0.5, 0.5)')
        if emis:
            L += ['bool inputs:enable_emission = 1', 'float inputs:emissive_intensity = %g' % (EM_BULB if kind != 'emissive' else 2)]
            if kind == 'emissive' and texref(diff): L.append('asset inputs:emissive_mask_texture = %s' % texref(diff))   # ad banner
            else: L.append('color3f inputs:emissive_color_constant = (1, 0.75, 0.45)')
        else:
            L.append('bool inputs:enable_emission = 0')
            n = tex.get('BumpSampler')
            if texref(n): L += ['asset inputs:normalmap_texture = %s' % texref(n), 'int inputs:encoding = 2']
            L += ['float inputs:reflection_roughness_constant = 0.45', 'float inputs:metallic_constant = %g' % (0.6 if kind in ('spec', 'normal_spec', 0x2f4b79d0) else 0)]
    # the original draw is an emissive pass: inheriting its blend state made the pole a white ghost (run k06)
    L += ['bool inputs:use_legacy_alpha_state = 0', 'bool inputs:blend_enabled = 0', 'float inputs:opacity_constant = 1']
    body = '\n'.join('                ' + l for l in L)
    return '''        def Material "%s"
        {
            token outputs:mdl:surface.connect = </ReferenceTarget/Looks/%s/Shader.outputs:out>
            def Shader "Shader"
            {
                uniform token info:implementationSource = "sourceAsset"
                uniform asset info:mdl:sourceAsset = @AperturePBR_Opacity.mdl@
                uniform token info:mdl:sourceAsset:subIdentifier = "AperturePBR_Opacity"
%s
                token outputs:out (
                    renderType = "material"
                )
            }
        }
''' % (name, name, body), emis

def build_asset(fest):
    """festive ydr -> assets/<fest>.usda (model space, centimetres, Z up) ; returns dict(lights, emissive bbox list)"""
    d = gta5res.ydr(os.path.join(YDR, fest + '.ydr'))
    os.makedirs(os.path.join(MOD, 'assets', 'textures'), exist_ok=True)
    for n, t in d['embedded'].items():
        p = os.path.join(MOD, 'assets', 'textures', n + '.dds')
        if not os.path.exists(p): open(p, 'wb').write(gta5res.dds(t))
    mats = []; meshes = []; used = sorted({g['shader'] for g in d['geoms']}); info = {}
    for si in used:
        m, emis = material('m%d' % si, d['shaders'][si], d, './textures'); mats.append(m); info[si] = emis
    for gi, g in enumerate(d['geoms']):
        pts = [tuple(c * UNIT for c in p) for p in g['pos']]; idx = [i for t in g['tris'] for i in t]
        mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
        s = '''        def Mesh "g%d" (
            prepend apiSchemas = ["MaterialBindingAPI"]
        )
        {
            float3[] extent = [%s, %s]
            int[] faceVertexCounts = [%s]
            int[] faceVertexIndices = [%s]
            rel material:binding = </ReferenceTarget/Looks/m%d>
            point3f[] points = [%s]
''' % (gi, fl(mn), fl(mx), ', '.join('3' * 1 for _ in g['tris']), ', '.join(map(str, idx)), g['shader'], ', '.join(fl(p) for p in pts))
        if g['nrm']: s += '            normal3f[] normals = [%s] (\n                interpolation = "vertex"\n            )\n' % ', '.join(fl(n) for n in g['nrm'])
        if g['uv']: s += '            texCoord2f[] primvars:st = [%s] (\n                interpolation = "vertex"\n            )\n' % ', '.join(fl((u, 1 - v)) for u, v in g['uv'])
        s += '            uniform token subdivisionScheme = "none"\n        }\n'
        meshes.append(s)
    usda = '''#usda 1.0
(
    defaultPrim = "ReferenceTarget"
    metersPerUnit = 0.01
    upAxis = "Z"
)

def Xform "ReferenceTarget"
{
    def Scope "Looks"
    {
%s    }
    def Xform "geo"
    {
%s    }
}
''' % ('\n'.join(mats), '\n'.join(meshes))
    open(os.path.join(MOD, 'assets', fest + '.usda'), 'w').write(usda)
    return d

def vc_parts(name):
    """-> [(hash, child index, bone world pos, is_pole)] for every geometry of the vc_stolb fragment"""
    data = open(os.path.join(VC, name + '.wft'), 'rb').read(); d = ivres.load(data); r = d['res']
    bones = d['bones']; by_ptr = {b['ptr']: b for b in bones}
    def wpos(b):
        p = [0, 0, 0]
        while b: p = [a + c for a, c in zip(p, b['pos'])]; b = by_ptr.get(b['parent'])
        return p
    vft = r.u(d['D'], 'I'); geoms = []
    for o in range(0, len(r.sys) - 0x80, 4):
        if struct.unpack_from('<I', r.sys, o)[0] == vft and struct.unpack_from('<I', r.sys, o + 0x40)[0] >> 28 == 5 and 0x50000000 + o != d['D']:
            for m in ivres.drawable(r, 0x50000000 + o)['models']:
                child = m['hdr'][3]
                for g in m['geoms']: geoms.append((child, g))
    blob = struct.pack('<I', len(geoms)) + b''.join(struct.pack('<III', g['stride'], g['vcount'], len(g['i'])) + g['v'] + struct.pack('<%dH' % len(g['i']), *g['i']) for _, g in geoms)
    tmp = os.path.join(VC, name + '.geo.bin'); open(tmp, 'wb').write(blob)
    hashes = subprocess.run([os.path.join(HERE, 'meshhash.exe'), tmp], capture_output=True, text=True, check=True).stdout.splitlines()
    hashes = [l.split()[0] for l in hashes]; assert len(hashes) == len(geoms)
    out = []
    for h, (child, g) in zip(hashes, geoms):
        zs = [struct.unpack_from('<f', g['v'], i * g['stride'] + 8)[0] for i in range(g['vcount'])]
        out.append({'hash': h, 'child': child, 'bone': bones[child], 'wpos': wpos(bones[child]), 'height': max(zs) - min(zs), 'v': g['vcount']})
    return out, bones, wpos

# ---- traffic lights: VCNE's vc2_svetafors1/2 keep their own pole, arm and signal heads (the game drives the heads);
# only the festive spirals of prop_traffic_01b are added, fitted to the VC pole and arm.
TRAFFIC_SRC = r'E:\_tools\festive_v\yft\prop_traffic_01b.yft'
POLE_Z = (0.15, 6.05); POLE_R = 1.1          # spiral span on the VC pole (model space), radial scale (festive radius 0.24 m)
ARM_X = (-12.3, -0.35); ARM_R = 1.15         # spiral span along the VC arm (model space)
def spiral_usda(name, pts, nrm, tris, color, group):
    usda = '''#usda 1.0
(
    defaultPrim = "ReferenceTarget"
    upAxis = "Z"
)

def Xform "ReferenceTarget"
{
    def Scope "Looks"
    {
        def Material "spiral"
        {
            token outputs:mdl:surface.connect = </ReferenceTarget/Looks/spiral/Shader.outputs:out>
            def Shader "Shader"
            {
                uniform token info:implementationSource = "sourceAsset"
                uniform asset info:mdl:sourceAsset = @AperturePBR_Opacity.mdl@
                uniform token info:mdl:sourceAsset:subIdentifier = "AperturePBR_Opacity"
                custom string fork:tintGroup = "%s"
                color3f inputs:diffuse_color_constant = %s
                bool inputs:enable_emission = 1
                color3f inputs:emissive_color_constant = %s
                float inputs:emissive_intensity = %g
                bool inputs:use_legacy_alpha_state = 0
                bool inputs:blend_enabled = 0
                float inputs:opacity_constant = 1
                token outputs:out (
                    renderType = "material"
                )
            }
        }
    }
    def Mesh "spiral" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        int[] faceVertexCounts = [%s]
        int[] faceVertexIndices = [%s]
        rel material:binding = </ReferenceTarget/Looks/spiral>
        point3f[] points = [%s]
        normal3f[] normals = [%s] (
            interpolation = "vertex"
        )
        uniform token subdivisionScheme = "none"
    }
}
''' % (group, fl(color), fl(color), EM_SPIRAL, ', '.join('3' for _ in tris), ', '.join(str(i) for t in tris for i in t), ', '.join(fl(p) for p in pts), ', '.join(fl(n) for n in nrm))
    open(os.path.join(MOD, 'assets', name + '.usda'), 'w').write(usda)

def traffic_overs(seen):
    d = gta5res.ydr(TRAFFIC_SRC); out = []
    def geom(texname):
        for g in d['geoms']:
            if texname in d['shaders'][g['shader']]['tex'].values() and H.get(d['shaders'][g['shader']]['hash']) == 'emissivestrong': return g
        raise KeyError(texname)
    def keep(g, ok):   # sub-mesh of the triangles whose vertices all pass ok()
        tris = [t for t in g['tris'] if all(ok(g['pos'][i]) for i in t)]; used = sorted({i for t in tris for i in t}); re = {v: k for k, v in enumerate(used)}
        return [g['pos'][i] for i in used], [g['nrm'][i] for i in used], [[re[i] for i in t] for t in tris]
    parts = {n: vc_parts(n) for n in ('vc2_svetafors1', 'vc2_svetafors2')}
    # pole: straight part of the amber spiral (below the bend to the streetlight arm), squeezed to the VC pole height
    g = geom('COLOR'); P, N, T = keep(g, lambda p: p[2] <= 8.45)
    z0, z1 = min(p[2] for p in P), max(p[2] for p in P); kz = (POLE_Z[1] - POLE_Z[0]) / (z1 - z0)
    pole = max(parts['vc2_svetafors1'][0], key=lambda p: p['height']); pw = pole['wpos']
    spiral_usda('traffic_pole_spiral', [(p[0] * POLE_R - pw[0], p[1] * POLE_R - pw[1], POLE_Z[0] + (p[2] - z0) * kz - pw[2]) for p in P], N, T, (1, 0.72, 0.08), 'trafficPole')
    anchors = [(pole, 'traffic_pole_spiral')]
    # arm: white spiral; the festive arm rises in a curve, the VC arm is straight -> subtract the local axis (mean over one helix turn)
    g = geom('white'); P, N, T = keep(g, lambda p: True)
    xs = sorted(p[0] for p in P); x0, x1 = xs[0], xs[-1]; kx = (ARM_X[1] - ARM_X[0]) / (x1 - x0)
    bins = {}
    for p in P: bins.setdefault(round(p[0] * 4), []).append(p)   # 25 cm bins
    def axis(x):
        q = [p for b in range(round(x * 4) - 2, round(x * 4) + 3) for p in bins.get(b, [])]
        return sum(p[1] for p in q) / len(q), sum(p[2] for p in q) / len(q)
    for n in parts:
        arm = max((p for p in parts[n][0] if p['child'] == 2), key=lambda p: p['v']); aw = arm['wpos']
        pts = []
        for p in P:
            ay, az = axis(p[0]); pts.append((ARM_X[0] + (p[0] - x0) * kx - aw[0], (p[1] - ay) * ARM_R, (p[2] - az) * ARM_R))
        spiral_usda('traffic_arm_spiral', pts, N, T, (1, 1, 1), 'trafficArm')   # both arms share the bone offset, one asset is enough
        anchors.append((arm, 'traffic_arm_spiral'))
    for part, asset in anchors:
        for mat in (MATS.get(part['hash']) or ALLMATS + TRAFFIC_MATS):
            h = '%016X' % (int(part['hash'], 16) ^ int(mat, 16))
            if h in seen: continue
            seen[h] = asset
            out.append('''        over "mesh_%s"
        {
            custom bool preserveOriginalDrawCall = 1
            def Xform "%s" (
                prepend references = @./assets/%s.usda@
            )
            {
            }
        }
''' % (h, asset, asset))
    print('traffic lights: %d mesh keys (pole %s, arms %s)' % (len(out), pole['hash'], [a[0]['hash'] for a in anchors[1:]]))
    return out

import json
TRAFFIC_MATS = []
MATS =json.load(open(os.path.join(HERE, '..', 'out', 'stolb_materials.json')))
ALLMATS = sorted({m for v in MATS.values() for m in v})

def main():
    assets = {}; overs = []; seen = {}; report = []
    for vc, (fest, s) in MAP.items():
        if fest not in assets: assets[fest] = build_asset(fest)
        parts, bones, wpos = vc_parts(vc)
        pole = max(parts, key=lambda p: p['height'])
        for p0 in parts:
          # Remix mesh hash = geometry hash XOR material hash; material hashes come from the runtime log (matscan.py).
          # Parts never seen in a log get one candidate per known lamp material (unmatched overs are harmless).
          for mat in (MATS.get(p0['hash']) or ALLMATS):
            p = dict(p0, hash='%016X' % (int(p0['hash'], 16) ^ int(mat, 16)))
            role = (fest, s) if p0 is pole else None
            if p['hash'] in seen:
                assert seen[p['hash']] == role, 'hash %s shared between models with different roles (%s)' % (p['hash'], vc)
                continue
            seen[p['hash']] = role
            if role is None:
                # an empty over did not hide the part (run k08): replace it by a 1 mm triangle instead
                overs.append('''        over "mesh_%s"
        {
            custom bool preserveOriginalDrawCall = 0
            def Xform "hidden" (
                prepend references = @./assets/empty.usda@
            )
            {
            }
        }
''' % p['hash'])
            else:
                t = [-c * UNIT for c in p['wpos']]
                overs.append('''        over "mesh_%s"
        {
            custom bool preserveOriginalDrawCall = 0
            def Xform "festive_%s" (
                prepend references = @./assets/%s.usda@
            )
            {
                double3 xformOp:rotateXYZ = (0, 0, 90)
                double3 xformOp:scale = (%g, %g, %g)
                double3 xformOp:translate = %s
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
            }
        }
''' % (p['hash'], vc, fest, s, s, s, fl(t)))
        # where the festive bulbs end up in vc model space: Rz(90)(x, y) = (-y, x), then scale
        lights = []
        for l in assets[fest]['lights']:      # bulb = just below the lamp head geometry around the festive light
            lx, ly, lz = l['pos']
            zs = [q[2] for g in assets[fest]['geoms'] for q in g['pos'] if abs(q[0] - lx) < 0.5 and abs(q[1] - ly) < 0.5 and abs(q[2] - lz) < 0.6]
            lights.append((-ly * s, lx * s, (min(zs) - 0.06) * s))
        report.append((vc, fest, s, pole['hash'], [p['hash'] for p in parts if p is not pole and p['hash'] not in MATS], lights, {b['id']: wpos(b) for b in bones}))
    os.makedirs(MOD, exist_ok=True)
    overs += traffic_overs(seen)
    open(os.path.join(MOD, 'assets', 'empty.usda'), 'w').write('''#usda 1.0
(
    defaultPrim = "ReferenceTarget"
    upAxis = "Z"
)

def Xform "ReferenceTarget"
{
    def Mesh "nothing"
    {
        int[] faceVertexCounts = [3]
        int[] faceVertexIndices = [0, 1, 2]
        point3f[] points = [(0, 0, 0), (0.001, 0, 0), (0, 0.001, 0)]
        uniform token subdivisionScheme = "none"
    }
}
''')
    open(os.path.join(MOD, 'mod.usda'), 'w').write('''#usda 1.0
(
    customLayerData = {
        string lightspeed_game_name = "Grand Theft Auto IV"
        string lightspeed_layer_type = "replacement"
    }
    metersPerUnit = 0.01
    upAxis = "Z"
)

over "RootNode"
{
    over "meshes"
    {
%s    }
}
''' % '\n'.join(overs))
    for vc, fest, s, ph, hidden, lights, bw in report:
        print(vc, '->', fest, 'scale', s, 'pole geometry', ph, '| parts with guessed material:', len(hidden))
        print('   festive bulbs (vc model space):', [tuple(round(x, 3) for x in l) for l in lights])
        print('   bones:', {k: tuple(round(x, 3) for x in v) for k, v in bw.items()})
    patch_ide(report)
    return report

IDE = r'F:\games\VCNE_RTX\update\pc\data\maps\vc_generic\vcDE_generic.ide'
IDE_ORIG = r'F:\games\VCNE_RTX\_debug\vcDE_generic.ide.before'
def patch_ide(report):
    """move the 2dfx light of every vc_stolb to the festive bulb (the offset is relative to the light's bone); always starts from VCNE's original ide"""
    rep = {r[0]: r for r in report}; out = []; n = 0
    for line in open(IDE_ORIG, encoding='latin1', newline='').read().split('\n'):
        t = [x.strip() for x in line.split(',')]
        if t[0] in rep and len(t) > 30 and '"corona"' in t:
            vc, fest, s, ph, hidden, lights, bw = rep[t[0]]; bone = bw[int(t[-4])]
            l = min(lights, key=lambda l: (l[0] - bone[0]) ** 2 + (l[1] - bone[1]) ** 2)      # the bulb on this bone's side
            t[1:4] = ['%.6f' % (a - b) for a, b in zip(l, bone)]; line = ', '.join(t); n += 1
        out.append(line)
    assert n == 7, n     # 5 single lamps + 2 lights of the double lamp
    open(IDE, 'w', encoding='latin1', newline='').write('\n'.join(out))
    print('ide: moved', n, 'lights')
if __name__ == '__main__': main()
