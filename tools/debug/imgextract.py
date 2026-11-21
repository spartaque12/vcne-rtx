# build a new (unencrypted) IV IMG v3 from entries of other imgs, optionally renamed
# usage: python imgextract.py <out.img> <src1.img> <map1.txt> [<src2.img> <map2.txt> ...]
#   map lines: name[=newname]   (case-insensitive source name; '#' comments)
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgscan
MAGIC = 0xA94E2A52
out = sys.argv[1]; picked = []; meta = None
for src, mapf in zip(sys.argv[2::2], sys.argv[3::2]):
    want = {}
    for l in open(mapf):
        l = l.split('#')[0].strip()
        if l: a, _, b = l.partition('='); want[a.strip().lower()] = (b.strip() or a.strip())
    with open(src, 'rb') as f:
        hdr = f.read(20); enc = struct.unpack('<I', hdr[:4])[0] != MAGIC
        key = imgscan.find_key() if enc else None
        if enc: hdr = imgscan.dec(hdr[:16], key) + hdr[16:]
        assert struct.unpack('<I', hdr[:4])[0] == MAGIC, 'unknown img header: ' + src
        _, ver, n, tsize, esz, unk = struct.unpack('<IIIIHH', hdr); meta = meta or (ver, esz, unk)
        toc = f.read(tsize)
        if enc: toc = imgscan.dec(toc, key)
        names = toc[n * 16:].split(b'\0'); found = set()
        for i in range(n):
            e = struct.unpack_from('<IIIHH', toc, i * 16); nm = names[i].decode('latin1').lower()
            if nm in want:
                f.seek(e[2] * 0x800); picked.append((e, want[nm].encode('latin1'), f.read(e[3] * 0x800))); found.add(nm)
        for m in sorted(set(want) - found): print('NOT FOUND in', os.path.basename(src), ':', m)
ver, esz, unk = meta; m = len(picked)
nameblob = b''.join(nm + b'\0' for _, nm, _ in picked)
tsize2 = m * 16 + len(nameblob); first = (20 + tsize2 + 0x7FF) // 0x800
body = b''; entries = b''; off = first
for e, nm, data in picked:
    entries += struct.pack('<IIIHH', e[0], e[1], off, e[3], e[4]); body += data; off += e[3]
head = struct.pack('<IIIIHH', MAGIC, ver, m, tsize2, esz, unk) + entries + nameblob
open(out, 'wb').write(head.ljust(first * 0x800, b'\0') + body)
assert os.path.getsize(out) == off * 0x800   # self-check: layout matches the TOC
print('wrote', out, m, 'entries')
