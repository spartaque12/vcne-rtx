# shared helpers: read entries of an IV IMG v3 (plain or encrypted TOC), RSC decompress, joaat hash
import struct, zlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgscan
MAGIC = 0xA94E2A52
def entries(img):
    with open(img, 'rb') as f:
        hdr = f.read(20); enc = struct.unpack('<I', hdr[:4])[0] != MAGIC
        key = imgscan.find_key() if enc else None
        if enc: hdr = imgscan.dec(hdr[:16], key) + hdr[16:]
        _, ver, n, ts, esz, unk = struct.unpack('<IIIIHH', hdr); toc = f.read(ts)
        if enc: toc = imgscan.dec(toc, key)
        names = toc[n * 16:].split(b'\0')
        return [(names[i].decode('latin1'), struct.unpack_from('<IIIHH', toc, i * 16)) for i in range(n)]
def read(img, name):
    for nm, e in entries(img):
        if nm.lower() == name.lower():
            with open(img, 'rb') as f: f.seek(e[2] * 0x800); return e, f.read(e[3] * 0x800)
    raise KeyError(name)
def rsc_raw(data): return zlib.decompressobj().decompress(data[12:])
def joaat(s):
    h = 0
    for c in s.lower().encode():
        h = (h + c) & 0xffffffff; h = (h + (h << 10)) & 0xffffffff; h ^= h >> 6
    h = (h + (h << 3)) & 0xffffffff; h ^= h >> 11; return (h + (h << 15)) & 0xffffffff
def write_img(out, items, ver=3, esz=0x10, unk=0xE9):
    """items: [(name, (flags, rtype, _, blocks, pad), data padded to 0x800)]"""
    nameblob = b''.join(n.encode('latin1') + b'\0' for n, _, _ in items)
    ts = len(items) * 16 + len(nameblob); first = (20 + ts + 0x7FF) // 0x800
    toc = b''; body = b''; off = first
    for n, e, data in items:
        assert len(data) == e[3] * 0x800
        toc += struct.pack('<IIIHH', e[0], e[1], off, e[3], e[4]); body += data; off += e[3]
    head = struct.pack('<IIIIHH', MAGIC, ver, len(items), ts, esz, unk) + toc + nameblob
    open(out, 'wb').write(head.ljust(first * 0x800, b'\0') + body)
def rsc_repack(orig, raw):
    """recompress a patched resource; returns (data padded to 0x800, blocks, padfield)"""
    comp = orig[:12] + zlib.compress(raw, 9)
    blocks = (len(comp) + 0x7FF) // 0x800; pad = blocks * 0x800 - len(comp)
    return comp.ljust(blocks * 0x800, b'\0'), blocks, 0x2000 | pad
