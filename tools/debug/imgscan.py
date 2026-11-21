# scan IV IMG v3 archives: list entries whose name matches a regex and print the .sps presets / shader + texture names in each WDR/WFT/WDD
# usage: python imgscan.py <name-regex> [img ...]   (default: every .img under the game dir)
import sys, re, struct, zlib, glob, os, hashlib, functools
from Crypto.Cipher import AES
@functools.lru_cache(None)
def find_key():
    d = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'GTAIV.exe'), 'rb').read()
    want = bytes.fromhex('DEA375EF1E6EF2223A1221C2C575C47BF17EFA5E')
    for i in range(0, len(d) - 32, 4):   # key is dword aligned in the image
        if hashlib.sha1(d[i:i+32]).digest() == want: return d[i:i+32]
def dec(b, key):
    c = AES.new(key, AES.MODE_ECB); n = len(b) & ~15; h = b[:n]
    for _ in range(16): h = c.decrypt(h)
    return h + b[n:]
KEY = None
def main():
    global KEY
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rx = re.compile(sys.argv[1], re.I)
    imgs = sys.argv[2:] or glob.glob(os.path.join(ROOT, '**', '*.img'), recursive=True)
    for img in imgs:
        if '_vcne_1080_files' in img or os.path.isdir(img): continue
        with open(img, 'rb') as f:
            hdr = f.read(20); enc = struct.unpack('<I', hdr[:4])[0] != 0xA94E2A52
            if enc:
                KEY = KEY or find_key(); hdr = dec(hdr[:16], KEY) + hdr[16:]
                if struct.unpack('<I', hdr[:4])[0] != 0xA94E2A52: print('skip (unknown header)', img); continue
            _, ver, n, tsize, isz = struct.unpack('<IIIIH', hdr[:18])
            toc = f.read(tsize)
            if enc: toc = dec(toc, KEY)
            names = toc[n * 16:].split(b'\0')
            for i in range(n):
                size, rtype, off, blocks, pad = struct.unpack_from('<IIIHH', toc, i * 16)
                name = names[i].decode('latin1')
                if not rx.search(name): continue
                f.seek(off * 0x800); data = f.read(blocks * 0x800)
                info = ''
                if data[:3] == b'RSC':
                    try: raw = zlib.decompressobj().decompress(data[12:])
                    except Exception as e: raw = b''; info = 'zlib fail %s' % e
                    strs = set(m.group().decode() for m in re.finditer(rb'[A-Za-z0-9_\-]{3,40}\.sps', raw))
                    tex = set(m.group().decode() for m in re.finditer(rb'[A-Za-z0-9_\-]{3,40}(?=\x00)', raw) if b'_' in m.group() or m.group().islower())
                    info += ' sps=%s' % sorted(strs)
                    if '-v' in sys.argv: info += ' strs=%s' % sorted(tex)[:60]
                print('%s :: %s%s' % (os.path.basename(img), name, info))

if __name__ == '__main__':
    main()
