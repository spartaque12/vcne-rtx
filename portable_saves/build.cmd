@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86 >nul
cd /d "F:\games\VCNE_RTX\_debug\portable_saves"
cl /nologo /O2 /W3 /LD /MT portable_saves.c /Fe:PortableSaves.asi /link user32.lib shell32.lib
