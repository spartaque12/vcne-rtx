# VCNE lamp models: swap the FusionFix 'gta_normal_spec_reflect_emissive' shader for plain 'gta_normal_spec'
# (same textures, no emission) so only the gta_emissivenight bulb glows under Remix.
# usage: python lamp_patch.py <src.img> <out.img> <model.wft> [...]
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imglib
OLD, NEW = 'gta_normal_spec_reflect_emissive', 'gta_normal_spec'
src, out, models = sys.argv[1], sys.argv[2], sys.argv[3:]
items = []
for m in models:
    e, data = imglib.read(src, m); raw = imglib.rsc_raw(data); n0 = len(raw)
    h_old, h_new = struct.pack('<I', imglib.joaat(OLD)), struct.pack('<I', imglib.joaat(NEW))
    nh = raw.count(h_old); raw = raw.replace(h_old, h_new)
    ns = 0
    for suffix in (b'.sps\0', b'\0'):     # longer string first; pad with zeros to keep every offset
        o, n = OLD.encode() + suffix, NEW.encode() + suffix
        ns += raw.count(o); raw = raw.replace(o, n.ljust(len(o), b'\0'))
    assert len(raw) == n0 and nh and ns, (m, nh, ns)
    assert imglib.rsc_raw(imglib.rsc_repack(data, raw)[0]) == raw     # round trip
    packed, blocks, pad = imglib.rsc_repack(data, raw)
    items.append((m, (e[0], e[1], 0, blocks, pad), packed))
    print('%s: %d shader hashes, %d strings patched' % (m, nh, ns))
imglib.write_img(out, items)
