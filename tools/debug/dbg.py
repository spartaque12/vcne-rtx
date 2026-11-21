# Minimal Win32 debugger for the 32-bit GTAIV.exe (run with 64-bit python).
# Logs module loads, OutputDebugString, exceptions with registers + stack scan resolved to module+offset.
# usage: python dbg.py [seconds] [--debugheap]   -> writes _debug\dbg.log
import ctypes as C, ctypes.wintypes as W, os, sys, time, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = open(os.path.join(ROOT, "_debug", "dbg.log"), "w", encoding="utf-8", errors="replace")
SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 240
k = C.WinDLL("kernel32", use_last_error=True)

def log(s):
    LOG.write("%s %s\n" % (time.strftime("%H:%M:%S"), s)); LOG.flush()

class STARTUPINFO(C.Structure):
    _fields_ = [("cb", W.DWORD), ("r", W.LPWSTR), ("d", W.LPWSTR), ("t", W.LPWSTR)] + [(n, W.DWORD) for n in "x y xs ys xc yc fa fl".split()] + \
               [("sw", W.WORD), ("cb2", W.WORD), ("r2", C.c_void_p), ("i", W.HANDLE), ("o", W.HANDLE), ("e", W.HANDLE)]
class PROCINFO(C.Structure):
    _fields_ = [("hProcess", W.HANDLE), ("hThread", W.HANDLE), ("pid", W.DWORD), ("tid", W.DWORD)]
class EXCREC(C.Structure):
    _fields_ = [("code", W.DWORD), ("flags", W.DWORD), ("rec", C.c_uint64), ("addr", C.c_uint64), ("nparams", W.DWORD), ("params", C.c_uint64 * 15)]
class EXCINFO(C.Structure):
    _fields_ = [("rec", EXCREC), ("first", W.DWORD)]
class CREATEPROC(C.Structure):
    _fields_ = [("hFile", W.HANDLE), ("hProcess", W.HANDLE), ("hThread", W.HANDLE), ("base", C.c_void_p), ("dio", W.DWORD), ("dis", W.DWORD),
                ("tls", C.c_void_p), ("start", C.c_void_p), ("name", C.c_void_p), ("uni", W.WORD)]
class CREATETHREAD(C.Structure):
    _fields_ = [("hThread", W.HANDLE), ("tls", C.c_void_p), ("start", C.c_void_p)]
class LOADDLL(C.Structure):
    _fields_ = [("hFile", W.HANDLE), ("base", C.c_void_p), ("dio", W.DWORD), ("dis", W.DWORD), ("name", C.c_void_p), ("uni", W.WORD)]
class UNLOADDLL(C.Structure):
    _fields_ = [("base", C.c_void_p)]
class ODS(C.Structure):
    _fields_ = [("data", C.c_void_p), ("uni", W.WORD), ("len", W.WORD)]
class EXITPROC(C.Structure):
    _fields_ = [("code", W.DWORD)]
class U(C.Union):
    _fields_ = [("exc", EXCINFO), ("cp", CREATEPROC), ("ct", CREATETHREAD), ("ld", LOADDLL), ("ud", UNLOADDLL), ("ods", ODS), ("ep", EXITPROC)]
class DEBUG_EVENT(C.Structure):
    _fields_ = [("code", W.DWORD), ("pid", W.DWORD), ("tid", W.DWORD), ("u", U)]
class WOW64_CONTEXT(C.Structure):
    _pack_ = 4
    _fields_ = [("ContextFlags", W.DWORD)] + [(n, W.DWORD) for n in "Dr0 Dr1 Dr2 Dr3 Dr6 Dr7".split()] + [("fs", C.c_byte * 112)] + \
               [(n, W.DWORD) for n in "SegGs SegFs SegEs SegDs Edi Esi Ebx Edx Ecx Eax Ebp Eip SegCs EFlags Esp SegSs".split()] + [("ext", C.c_byte * 512)]

k.GetFinalPathNameByHandleW.argtypes = [W.HANDLE, W.LPWSTR, W.DWORD, W.DWORD]
k.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
k.OpenThread.restype = W.HANDLE
k.Wow64GetThreadContext.argtypes = [W.HANDLE, C.POINTER(WOW64_CONTEXT)]

mods = {}      # base -> (name, size)
hproc = None

def rd(addr, n):
    buf = C.create_string_buffer(n); got = C.c_size_t()
    if k.ReadProcessMemory(hproc, C.c_void_p(addr), buf, n, C.byref(got)): return buf.raw[:got.value]
    return b""

def modsize(base):
    h = rd(base, 0x400)
    try:
        pe = struct.unpack_from("<I", h, 0x3C)[0]
        return struct.unpack_from("<I", h, pe + 0x50)[0]
    except Exception: return 0x100000

def addmod(hfile, base):
    buf = C.create_unicode_buffer(600)
    name = buf.value if hfile and k.GetFinalPathNameByHandleW(hfile, buf, 600, 0) else "?"
    name = name.replace("\\\\?\\", "")
    mods[base] = (name, modsize(base))
    log("LOAD %08X %s" % (base, name))
    if hfile: k.CloseHandle(hfile)

def sym(a):
    for b, (n, s) in mods.items():
        if b <= a < b + s: return "%s+0x%X" % (os.path.basename(n), a - b)
    return None

def dump(tid, why):
    th = k.OpenThread(0x1FFFFF, False, tid)
    ctx = WOW64_CONTEXT(); ctx.ContextFlags = 0x10007
    if not k.Wow64GetThreadContext(th, C.byref(ctx)):
        log("  ctx failed %d" % C.get_last_error()); k.CloseHandle(th); return
    log("  %s tid=%d eip=%08X (%s) eax=%08X ebx=%08X ecx=%08X edx=%08X esi=%08X edi=%08X ebp=%08X esp=%08X" % (
        why, tid, ctx.Eip, sym(ctx.Eip), ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx, ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp))
    log("  code@eip: " + rd(ctx.Eip - 16, 32).hex())
    # ebp chain
    ebp, chain = ctx.Ebp, []
    for _ in range(40):
        d = rd(ebp, 8)
        if len(d) < 8: break
        nxt, ret = struct.unpack("<II", d); chain.append("%s" % (sym(ret) or "%08X" % ret))
        if nxt <= ebp: break
        ebp = nxt
    log("  ebp-chain: " + " <- ".join(chain))
    # raw stack scan: anything that looks like a code address
    st = rd(ctx.Esp, 0x1800); out = []
    for i in range(0, len(st) - 3, 4):
        v = struct.unpack_from("<I", st, i)[0]; s = sym(v)
        if s: out.append("[+%X] %s" % (i, s))
    log("  stack-scan: " + " | ".join(out[:160]))
    k.CloseHandle(th)

def main():
    global hproc
    if "--debugheap" not in sys.argv: os.environ["_NO_DEBUG_HEAP"] = "1"
    si = STARTUPINFO(); si.cb = C.sizeof(si); pi = PROCINFO()
    exe = os.path.join(ROOT, "GTAIV.exe")
    if not k.CreateProcessW(exe, None, None, None, False, 0x2, None, ROOT, C.byref(si), C.byref(pi)):  # DEBUG_ONLY_THIS_PROCESS
        log("CreateProcess failed %d" % C.get_last_error()); return
    hproc = pi.hProcess
    k.DebugSetProcessKillOnExit(True)
    ev = DEBUG_EVENT(); t0 = time.time(); counts = {}
    while time.time() - t0 < SECONDS:
        if not k.WaitForDebugEvent(C.byref(ev), 500): continue
        cont = 0x00010002  # DBG_CONTINUE
        c = ev.code
        if c == 3: addmod(ev.u.cp.hFile, ev.u.cp.base or 0)
        elif c == 6: addmod(ev.u.ld.hFile, ev.u.ld.base or 0)
        elif c == 7: log("UNLOAD %08X %s" % (ev.u.ud.base or 0, mods.pop(ev.u.ud.base or 0, ("?",))[0]))
        elif c == 8:
            d = rd(ev.u.ods.data, min(ev.u.ods.len * (2 if ev.u.ods.uni else 1), 2000))
            log("ODS: " + (d.decode("utf-16le", "replace") if ev.u.ods.uni else d.decode("mbcs", "replace")).rstrip("\0\r\n"))
        elif c == 5:
            log("EXIT PROCESS code=0x%X after %.1fs" % (ev.u.ep.code, time.time() - t0)); break
        elif c == 1:
            r = ev.u.exc.rec; first = ev.u.exc.first
            if r.code in (0x80000003, 0x4000001F):   # initial breakpoints
                pass
            else:
                cont = 0x80010001  # DBG_EXCEPTION_NOT_HANDLED
                key = (r.code, r.addr); counts[key] = counts.get(key, 0) + 1
                if counts[key] <= 3 or not first:
                    log("EXCEPTION %08X at %08X (%s) %s params=%s" % (r.code, r.addr, sym(r.addr), "first-chance" if first else "SECOND-CHANCE",
                        [hex(r.params[i]) for i in range(min(r.nparams, 4))]))
                    if r.code not in (0x406D1388, 0xE06D7363, 0x40010006) or not first: dump(ev.tid, "ctx")
                    elif r.code == 0xE06D7363: dump(ev.tid, "c++ throw")
        k.ContinueDebugEvent(ev.pid, ev.tid, cont)
    else:
        log("TIMEOUT - still alive after %ds" % SECONDS)
    k.TerminateProcess(hproc, 1)

main()
