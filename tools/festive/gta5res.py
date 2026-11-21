# minimal GTA V (gen8 PC) .ydr / .ytd reader - enough for static props. No deps beyond stdlib.
import struct, zlib
def joaat(s):
    h = 0
    for c in s.lower().encode():
        h = (h + c) & 0xffffffff; h = (h + (h << 10)) & 0xffffffff; h ^= h >> 6
    h = (h + (h << 3)) & 0xffffffff; h ^= h >> 11; return (h + (h << 15)) & 0xffffffff
def _size(fl):
    s = ((fl >> 27) & 1) + (((fl >> 26) & 1) << 1) + (((fl >> 25) & 1) << 2) + (((fl >> 24) & 1) << 3) + (((fl >> 17) & 0x7F) << 4) \
        + (((fl >> 11) & 0x3F) << 5) + (((fl >> 7) & 0xF) << 6) + (((fl >> 5) & 3) << 7) + (((fl >> 4) & 1) << 8)
    return (0x200 << (fl & 0xF)) * s
class Res:
    def __init__(self, path):
        d = open(path, 'rb').read(); magic, self.ver, sf, gf = struct.unpack_from('<4sIII', d)
        assert magic == b'RSC7', magic
        raw = zlib.decompress(d[16:], -15); self.ss = _size(sf); self.sys = raw[:self.ss]; self.gfx = raw[self.ss:]
    def seg(self, p):
        t = p >> 28
        assert t in (5, 6), hex(p)
        return (self.sys if t == 5 else self.gfx), p & 0x0FFFFFFF
    def u(self, p, fmt):
        b, o = self.seg(p); r = struct.unpack_from('<' + fmt, b, o); return r if len(r) > 1 else r[0]
    def bytes(self, p, n): b, o = self.seg(p); return b[o:o + n]
    def str(self, p):
        if not p: return ''
        b, o = self.seg(p); return b[o:b.index(b'\0', o)].decode('latin1')
    def ptrlist(self, p):  # ResourcePointerList64 at p
        ptr, n = self.u(p, 'QH'); return list(struct.unpack_from('<%dQ' % n, *self.seg(ptr))) if n else []
S = 0x50000000
FOURCC = {21: None, 20: None}
def textures(r, dictptr):
    """-> {name: (w, h, fmt, mips, data)}"""
    out = {}
    for t in r.ptrlist(dictptr + 0x30):
        name = r.str(r.u(t + 0x28, 'Q')); w, h, depth, stride, fmt = r.u(t + 0x50, 'HHHHI'); mips = r.u(t + 0x5D, 'B'); dp = r.u(t + 0x70, 'Q')
        fc = struct.pack('<I', fmt)
        bs = {b'DXT1': 8, b'ATI1': 8, b'DXT3': 16, b'DXT5': 16, b'ATI2': 16, b'BC7 ': 16}.get(fc)
        n = 0; mw, mh = w, h
        for _ in range(mips):
            n += max(1, (mw + 3) // 4) * max(1, (mh + 3) // 4) * bs if bs else stride * mh * 0 + mw * mh * (4 if fmt in (21, 22, 32) else 1)
            mw = max(1, mw // 2); mh = max(1, mh // 2)
        out[name] = (w, h, fmt, mips, r.bytes(dp, n))
    return out
def dds(tex):
    w, h, fmt, mips, data = tex; fc = struct.pack('<I', fmt)
    if fc.strip().isalnum() and fmt > 0xFFFF:
        pf = struct.pack('<II4s5I', 32, 4, fc if fc != b'BC7 ' else b'DX10', 0, 0, 0, 0, 0)
        ext = struct.pack('<5I', 98, 3, 0, 1, 0) if fc == b'BC7 ' else b''
    elif fmt in (21, 22): pf = struct.pack('<II4s5I', 32, 0x41, b'\0' * 4, 32, 0xFF0000, 0xFF00, 0xFF, 0xFF000000); ext = b''
    elif fmt == 50: pf = struct.pack('<II4s5I', 32, 0x20000, b'\0' * 4, 8, 0xFF, 0, 0, 0); ext = b''   # L8
    elif fmt == 28: pf = struct.pack('<II4s5I', 32, 2, b'\0' * 4, 8, 0, 0, 0, 0xFF); ext = b''         # A8
    else: raise ValueError('fmt %r' % fmt)
    return b'DDS ' + struct.pack('<7I44x', 124, 0x1007 | (0x20000 if mips > 1 else 0), h, w, 0, 0, mips) + pf + struct.pack('<5I', 0x1000 | (0x400008 if mips > 1 else 0), 0, 0, 0, 0) + ext + data
def ytd(path):
    r = Res(path); return textures(r, S + 0)
SIZES = {0: 0, 1: 4, 2: 4, 3: 8, 4: 0, 5: 8, 6: 12, 7: 16, 8: 4, 9: 4, 10: 4}
FMTS = {1: '2e', 2: 'f', 3: '4e', 5: '2f', 6: '3f', 7: '4f', 8: '4B', 9: '4B', 10: 'I'}
def ydr(path):
    """-> dict(name, shaders=[{name, hash, tex:{param: texname}, params}], embedded={tex}, geoms=[{shader, pos, nrm, uv, col, tris}] (high LOD), lights=[(pos, raw)], bbox)"""
    r = Res(path); D = S
    if path.lower().endswith('.yft'): D = r.u(S + 0x30, 'Q')   # fragType -> main drawable (no light attributes read from fragments)
    sg = r.u(D + 0x10, 'Q'); out = {'name': r.str(r.u(D + 0xA8, 'Q')) if D == S else '', 'bbox': (r.u(D + 0x30, '3f'), r.u(D + 0x40, '3f')), 'shaders': [], 'geoms': [], 'lights': []}
    td = r.u(sg + 8, 'Q'); out['embedded'] = textures(r, td) if td else {}
    sp, sn = r.u(sg + 0x10, 'QH')
    for i in range(sn):
        s = r.u(sp + i * 8, 'Q'); pp, nh = r.u(s, 'QI'); pc = r.u(s + 0x10, 'B'); fh = r.u(s + 0x18, 'I')
        ps = [r.u(pp + j * 16, 'BBHIQ') for j in range(pc)]
        ho = pc * 16 + sum(16 * p[0] for p in ps); hs = r.u(pp + ho, '%dI' % pc) if pc > 1 else (r.u(pp + ho, 'I'),) if pc else ()
        tex = {}; vals = {}
        for p, h in zip(ps, hs):
            if p[0] == 0: tex[h] = r.str(r.u(p[4] + 0x28, 'Q')) if p[4] else None
            else: vals[h] = r.u(p[4], '4f')
        out['shaders'].append({'hash': nh, 'file': fh, 'tex': tex, 'vals': vals})
    hi = r.u(D + 0x50, 'Q')
    for m in r.ptrlist(hi):
        gp, gn = r.u(m + 8, 'QH'); smap = r.u(r.u(m + 0x20, 'Q'), '%dH' % gn); smap = smap if gn > 1 else (smap,)
        for gi in range(gn):
            g = r.u(gp + gi * 8, 'Q'); vb = r.u(g + 0x18, 'Q'); ib = r.u(g + 0x38, 'Q')
            stride = r.u(vb + 8, 'H'); vp = r.u(vb + 0x10, 'Q'); vn = r.u(vb + 0x18, 'I'); decl = r.u(vb + 0x30, 'Q')
            flags, dstride, _, cnt, types = r.u(decl, 'IHBBQ'); assert dstride == stride
            vd = r.bytes(vp, vn * stride); comp = {}; off = 0
            for bit in range(16):
                if flags >> bit & 1:
                    t = (types >> (bit * 4)) & 0xF; comp[bit] = (off, FMTS[t]); off += SIZES[t]
            assert off == stride, (off, stride, hex(flags), hex(types))
            def col(bit, n=None):
                if bit not in comp: return None
                o, f = comp[bit]; return [struct.unpack_from('<' + f, vd, i * stride + o)[:n] for i in range(vn)]
            ic = r.u(ib + 8, 'I'); idx = r.u(r.u(ib + 0x10, 'Q'), '%dH' % ic)
            out['geoms'].append({'shader': smap[gi], 'pos': col(0, 3), 'nrm': col(3, 3), 'col': col(4), 'uv': col(6, 2), 'uv1': col(7, 2),
                                 'tris': [idx[i:i + 3] for i in range(0, ic, 3)]})
    lp, ln = r.u(D + 0xB0, 'QH') if D == S else (0, 0)
    for i in range(ln):
        b = r.bytes(lp + i * 0xA8, 0xA8)
        out['lights'].append({'pos': struct.unpack_from('<3f', b, 8), 'rgb': tuple(b[0x18:0x1B]), 'flash': b[0x1B], 'intensity': struct.unpack_from('<f', b, 0x1C)[0],
                              'bone': struct.unpack_from('<H', b, 0x24)[0], 'type': b[0x26], 'dir': struct.unpack_from('<3f', b, 0x44), 'falloff': struct.unpack_from('<f', b, 0x38)[0]})
    return out
