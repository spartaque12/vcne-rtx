# disassemble around an RVA: python dis.py <file> <rva hex> [bytes before=48] [bytes after=32]
import sys, pefile, capstone
pe = pefile.PE(sys.argv[1], fast_load=True)
rva = int(sys.argv[2], 16); before = int(sys.argv[3]) if len(sys.argv) > 3 else 48; after = int(sys.argv[4]) if len(sys.argv) > 4 else 32
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
# shortcut: linear sweep from a few start offsets, keep the one that lands exactly on rva
for back in range(before, before + 16):
    data = pe.get_data(rva - back, back + after)
    ins = list(md.disasm(data, base + rva - back))
    if any(i.address == base + rva for i in ins):
        for i in ins: print("%s%08X  %-8s %s" % (">" if i.address == base + rva else " ", i.address, i.mnemonic, i.op_str))
        break
