# minimal GTA IV .wft/.wdr reader (RSC5): drawable -> skeleton bones, models, geometries (raw vertex/index bytes), shaders
import struct, zlib
class Res:
    def __init__(self, data):
        magic, self.type, fl = struct.unpack_from('<4sII', data); assert magic == b'RSC\x05', magic
        raw = zlib.decompress(data[12:]); ss = (fl & 0x7FF) << (((fl >> 11) & 0xF) + 8)
        self.sys, self.gfx = raw[:ss], raw[ss:]
    def seg(self, p):
        t = p >> 28; assert t in (5, 6), hex(p)
        return (self.sys if t == 5 else self.gfx), p & 0x0FFFFFFF
    def u(self, p, fmt):
        b, o = self.seg(p); r = struct.unpack_from('<' + fmt, b, o); return r if len(r) > 1 else r[0]
    def bytes(self, p, n): b, o = self.seg(p); return b[o:o + n]
    def str(self, p):
        if not p: return ''
        b, o = self.seg(p); return b[o:b.index(b'\0', o)].decode('latin1')
    def coll(self, p):   # pgPtrCollection at p
        ptr, n = self.u(p, 'IH'); return list(self.u(ptr, '%dI' % n)) if n > 1 else [self.u(ptr, 'I')] if n else []
S = 0x50000000
def drawable(r, D):
    out = {'bones': [], 'models': [], 'shaders': []}
    sg, sk = r.u(D + 8, 'II')
    if sg:
        for s in r.coll(sg + 8):
            # grmShaderFx: name / sps pointers live at fixed offsets
            out['shaders'].append({'ptr': s, 'name': r.str(r.u(s + 0x44, 'I')) if r.u(s + 0x44, 'I') >> 28 == 5 else '', 'sps': r.str(r.u(s + 0x48, 'I')) if r.u(s + 0x48, 'I') >> 28 == 5 else ''})
    if sk:
        bp, _, _, _, _, nb = r.u(sk, 'IIIIIH')
        for i in range(nb):
            b = bp + i * 0xE0
            out['bones'].append({'name': r.str(r.u(b, 'I')), 'idx': r.u(b + 0x14, 'H'), 'id': r.u(b + 0x16, 'H'), 'parent': r.u(b + 0x10, 'I'), 'ptr': b,
                                 'pos': r.u(b + 0x20, '3f'), 'quat': r.u(b + 0x40, '4f'), 'wpos': r.u(b + 0x70, '3f')})
    lod = r.u(D + 0x40, 'I')
    for m in (r.coll(lod) if lod else []):
        geoms = r.coll(m + 4); smap = r.u(m + 0x10, 'I'); n = len(geoms)
        sm = r.u(smap, '%dH' % n) if n > 1 else (r.u(smap, 'H'),)
        hdr = r.bytes(m + 0x14, 8); gs = []
        for g, si in zip(geoms, sm):
            vb = r.u(g + 0x0C, 'I'); ib = r.u(g + 0x1C, 'I'); ic, fc, vc = r.u(g + 0x2C, 'IIH'); stride = r.u(g + 0x3C, 'H')
            vcount = r.u(vb + 4, 'H'); vstride = r.u(vb + 0x0C, 'I'); decl = r.u(vb + 0x10, 'I'); vdata = r.u(vb + 0x18, 'I') or r.u(vb + 8, 'I')
            icount = r.u(ib + 4, 'I'); idata = r.u(ib + 8, 'I')
            gs.append({'shader': si, 'stride': vstride, 'fvf': r.u(decl, 'I'), 'types': r.u(decl + 8, 'Q'), 'vcount': vcount, 'faces': fc,
                       'v': r.bytes(vdata, vcount * vstride), 'i': struct.unpack('<%dH' % icount, r.bytes(idata, icount * 2)), 'gcounts': (ic, fc, vc, stride)})
        out['models'].append({'hdr': hdr, 'geoms': gs})
    return out
def load(data):
    r = Res(data)
    D = S if r.type == 0x6E else r.u(S + 0xB4, 'I')   # wdr: drawable at 0; wft: fragType -> main drawable
    d = drawable(r, D); d['res'] = r; d['D'] = D; return d
