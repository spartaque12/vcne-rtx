// Portable saves for this GTA IV install: GTAIV.exe's calls to SHGetFolderPath(CSIDL_PERSONAL) return
// <game folder>\Profiles\Documents instead of the user's Documents, so savegames/settings live in
// <game>\Profiles\Documents\Rockstar Games\GTA IV\... and stay separate from other GTA IV installs.
// Only the exe's own import table is patched; other modules still see the real Documents folder.
#include <windows.h>
#include <shlobj.h>
#include <string.h>
#include <stdio.h>
#include <wchar.h>

static wchar_t g_docsW[MAX_PATH];
static char g_docsA[MAX_PATH];
static HRESULT (WINAPI *realW)(HWND, int, HANDLE, DWORD, LPWSTR);
static HRESULT (WINAPI *realA)(HWND, int, HANDLE, DWORD, LPSTR);

static HRESULT WINAPI hookW(HWND h, int csidl, HANDLE tok, DWORD flags, LPWSTR out) {
    if ((csidl & 0xFF) == CSIDL_PERSONAL) {
        if (csidl & CSIDL_FLAG_CREATE) CreateDirectoryW(g_docsW, NULL);
        wcscpy_s(out, MAX_PATH, g_docsW);
        return S_OK;
    }
    return realW(h, csidl, tok, flags, out);
}

static HRESULT WINAPI hookA(HWND h, int csidl, HANDLE tok, DWORD flags, LPSTR out) {
    if ((csidl & 0xFF) == CSIDL_PERSONAL) {
        if (csidl & CSIDL_FLAG_CREATE) CreateDirectoryA(g_docsA, NULL);
        strcpy_s(out, MAX_PATH, g_docsA);
        return S_OK;
    }
    return realA(h, csidl, tok, flags, out);
}

// returns 1 if patched
static int patch_iat(HMODULE mod, const char* dll, const char* fn, void* hook, void** orig) {
    BYTE* base = (BYTE*)mod;
    IMAGE_NT_HEADERS* nt = (IMAGE_NT_HEADERS*)(base + ((IMAGE_DOS_HEADER*)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress) return 0;
    for (IMAGE_IMPORT_DESCRIPTOR* d = (IMAGE_IMPORT_DESCRIPTOR*)(base + dir.VirtualAddress); d->Name; d++) {
        if (_stricmp((char*)(base + d->Name), dll) != 0 || !d->OriginalFirstThunk) continue;
        IMAGE_THUNK_DATA* names = (IMAGE_THUNK_DATA*)(base + d->OriginalFirstThunk);
        IMAGE_THUNK_DATA* addrs = (IMAGE_THUNK_DATA*)(base + d->FirstThunk);
        for (; names->u1.AddressOfData; names++, addrs++) {
            if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal)) continue;
            IMAGE_IMPORT_BY_NAME* ibn = (IMAGE_IMPORT_BY_NAME*)(base + names->u1.AddressOfData);
            if (strcmp((char*)ibn->Name, fn) != 0) continue;
            DWORD old;
            VirtualProtect(&addrs->u1.Function, sizeof(void*), PAGE_READWRITE, &old);
            *orig = (void*)addrs->u1.Function;
            addrs->u1.Function = (ULONG_PTR)hook;
            VirtualProtect(&addrs->u1.Function, sizeof(void*), old, &old);
            return 1;
        }
    }
    return 0;
}

static void log_line(const wchar_t* dir, const char* msg) {
    wchar_t p[MAX_PATH];
    swprintf_s(p, MAX_PATH, L"%s\\portable_saves.log", dir);
    HANDLE f = CreateFileW(p, FILE_APPEND_DATA, FILE_SHARE_READ, NULL, OPEN_ALWAYS, 0, NULL);
    if (f == INVALID_HANDLE_VALUE) return;
    DWORD w;
    WriteFile(f, msg, (DWORD)strlen(msg), &w, NULL);
    CloseHandle(f);
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID r) {
    if (reason != DLL_PROCESS_ATTACH) return TRUE;
    DisableThreadLibraryCalls(inst);

    wchar_t game[MAX_PATH];
    GetModuleFileNameW(NULL, game, MAX_PATH);
    wchar_t* slash = wcsrchr(game, L'\\');
    if (slash) *slash = 0;
    swprintf_s(g_docsW, MAX_PATH, L"%s\\Profiles\\Documents", game);
    WideCharToMultiByte(CP_ACP, 0, g_docsW, -1, g_docsA, MAX_PATH, NULL, NULL);
    CreateDirectoryW(g_docsW, NULL);

    HMODULE exe = GetModuleHandleW(NULL);
    int w = patch_iat(exe, "SHELL32.dll", "SHGetFolderPathW", (void*)hookW, (void**)&realW);
    int a = patch_iat(exe, "SHELL32.dll", "SHGetFolderPathA", (void*)hookA, (void**)&realA);
    char msg[512];
    sprintf_s(msg, sizeof msg, "portable_saves: W=%d A=%d -> %s\r\n", w, a, g_docsA);
    log_line(g_docsW, msg);
    return TRUE;
}
