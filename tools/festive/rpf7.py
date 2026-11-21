# minimal RPF7 "OPEN" (unencrypted) extractor: python -I rpf7.py <in.rpf> <outdir>
import struct, sys, os
def main(rpf, out):
    f = open(rpf, 'rb'); magic, n, nl, enc = struct.unpack('<4sII4s', f.read(16))
    assert magic == b'7FPR' and enc == b'OPEN', (magic, enc)
    toc = f.read(n * 16); names = f.read(nl)
    nm = lambda o: names[o:names.index(b'\0', o)].decode('latin1')
    def walk(i, path):
        e = toc[i*16:i*16+16]; a, b, c, d = struct.unpack('<IIII', e)
        if b == 0x7FFFFF00:
            for j in range(c, c + d): walk(j, os.path.join(path, os.path.basename(nm(a))))
            return
        name = os.path.basename(nm(a & 0xFFFF)); size = int.from_bytes(e[2:5], 'little'); off = int.from_bytes(e[5:8], 'little')
        res = bool(off & 0x800000); off = (off & 0x7FFFFF) * 512
        os.makedirs(path, exist_ok=True); f.seek(off)
        if res:
            hdr = f.read(16)
            if size == 0xFFFFFF: size = (hdr[2] << 24) | (hdr[5] << 16) | (hdr[14] << 8) | hdr[7]
            ver = ((c >> 28) & 0xF) << 4 | ((d >> 28) & 0xF)
            data = struct.pack('<4sIII', b'RSC7', ver, c, d) + f.read(size - 16)
        else:
            data = f.read(size or c)   # size==0 -> stored uncompressed, length = c
            # shortcut: compressed binary entries are written as-is (raw deflate); none expected here
        open(os.path.join(path, name), 'wb').write(data); print(name, len(data), 'res' if res else 'bin', hex(c), hex(d))
    walk(0, out)
main(*sys.argv[1:3])
