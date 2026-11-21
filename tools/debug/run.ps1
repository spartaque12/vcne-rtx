# Headless-ish test run: launch GTAIV.exe, watch it, screenshot, collect dialogs + crash events, kill.
# usage: pwsh run.ps1 [-Tag name] [-Seconds 210] [-Exe GTAIV.exe]
param([string]$Tag = (Get-Date -Format 'HHmmss'), [int]$Seconds = 210, [int]$ShotEvery = 30, [string]$Launcher = '', [int]$SkipUntil = 0, [int]$CaptureAt = 0, [string]$Hold = '', [switch]$NewGame, [string]$ConfAppend = '', [string]$GameArgs = '')   # -GameArgs: optional command line (replaces commandline.txt; '-windowed -width 1280 -height 720' needs the commandline.txt switches in front)   # -NewGame: SkipMenu = 1 for this run only; -ConfAppend 'rtx.x = y': extra rtx.conf line for this run only   # -Hold '85:0x11:20,110:0x1E:3' = at 85 s hold scancode 0x11 (W) for 20 s, ...   # -SkipUntil n: tap Enter every loop until n seconds (skips the new-game intro cutscenes)
$root = Split-Path $PSScriptRoot -Parent
$out  = $PSScriptRoot
Add-Type -AssemblyName System.Drawing, UIAutomationClient, UIAutomationTypes
Add-Type @'
using System; using System.Runtime.InteropServices; using System.Text; using System.Collections.Generic;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsHungAppWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f); [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  public static List<IntPtr> Wins(HashSet<uint> pids) {
    var l = new List<IntPtr>();
    EnumWindows((h, x) => { uint p; GetWindowThreadProcessId(h, out p); if (pids.Contains(p) && IsWindowVisible(h)) l.Add(h); return true; }, IntPtr.Zero);
    return l;
  }
  public static string Title(IntPtr h){ var s=new StringBuilder(512); GetWindowText(h,s,512); return s.ToString(); }
  public static string Class(IntPtr h){ var s=new StringBuilder(256); GetClassName(h,s,256); return s.ToString(); }
}
'@
[W]::SetProcessDPIAware() | Out-Null
function Log($m) { $l = "{0:HH:mm:ss} {1}" -f (Get-Date), $m; $l; Add-Content "$out\run_$Tag.log" $l }
function KillAll { Get-Process GTAIV, NvRemixBridge, WerFault -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue }

# one test run at a time (several agents share this script); temporary config edits live inside the lock and are always undone
$mtx = New-Object System.Threading.Mutex($false, 'Global\VCNE_run_ps1'); try { [void]$mtx.WaitOne() } catch [System.Threading.AbandonedMutexException] { }
while (Get-Process GTAIV -ErrorAction SilentlyContinue) { Start-Sleep 5 }   # someone is playing: wait, do not kill
$cfg = "$root\plugins\GTAIV.EFLC.FusionFix.cfg"; $conf = "$root\rtx.conf"; $cfg0 = $null; $conf0 = $null
function Restore { if ($null -ne $script:cfg0) { [IO.File]::WriteAllText($cfg, $script:cfg0); $script:cfg0 = $null }; if ($null -ne $script:conf0) { [IO.File]::WriteAllText($conf, $script:conf0); $script:conf0 = $null }; try { $mtx.ReleaseMutex() } catch { } }
trap { Restore; break }
if ($NewGame) { $cfg0 = [IO.File]::ReadAllText($cfg); [IO.File]::WriteAllText($cfg, $cfg0.Replace('SkipMenu = 0', 'SkipMenu = 1')) }
if ($ConfAppend) { $conf0 = [IO.File]::ReadAllText($conf); [IO.File]::WriteAllText($conf, $conf0.TrimEnd() + "`n$ConfAppend`n") }
KillAll; Start-Sleep 1
$start = Get-Date
if ($Launcher) { Start-Process -FilePath $Launcher -WorkingDirectory $root }   # e.g. the debugger, which spawns the game itself
else { $sp = @{ FilePath = "$root\GTAIV.exe"; WorkingDirectory = $root; PassThru = $true }; if ($GameArgs) { $sp.ArgumentList = $GameArgs }; $gp = Start-Process @sp }
$result = 'TIMEOUT_ALIVE'; $seen = $false; $lastShot = -20; $dialogs = @{}; $held = @{}; $focused = $false
while (((Get-Date) - $start).TotalSeconds -lt $Seconds) {
  Start-Sleep 3
  $t = [int]((Get-Date) - $start).TotalSeconds
  $procs = @(Get-Process GTAIV, WerFault -ErrorAction SilentlyContinue)
  $game = @($procs | Where-Object Name -eq 'GTAIV')
  if ($game) { $seen = $true } elseif ($seen -or $t -gt 30) { $result = "EXITED at ${t}s code=0x{0:X}" -f $(if ($gp) { $gp.ExitCode }); break }
  $pids = [System.Collections.Generic.HashSet[uint32]]::new(); $procs | ForEach-Object { [void]$pids.Add([uint32]$_.Id) }
  $main = [IntPtr]::Zero
  foreach ($h in [W]::Wins($pids)) {
    $cls = [W]::Class($h); $title = [W]::Title($h)
    if ($cls -eq '#32770') {   # dialog box: dump its text once
      $txt = try { ([System.Windows.Automation.AutomationElement]::FromHandle($h).FindAll('Descendants', [System.Windows.Automation.Condition]::TrueCondition) | ForEach-Object { $_.Current.Name }) -join ' | ' } catch { "uia failed: $_" }
      $k = "$title :: $txt"; if (-not $dialogs[$k]) { $dialogs[$k] = 1; Log "DIALOG [$title] $txt" }
    } elseif ($title -and $cls -ne 'ConsoleWindowClass' -and ($cls -eq 'grcWindow' -or $main -eq [IntPtr]::Zero)) { $main = $h; if ([W]::IsHungAppWindow($h)) { Log "window hung at ${t}s" } }
  }
  if ($dialogs.Count -and $result -eq 'TIMEOUT_ALIVE') { $result = "DIALOG at ${t}s"; Start-Sleep 2; break }
  if ($main -ne [IntPtr]::Zero -and -not $focused -and ($SkipUntil -or $Hold) -and $t -gt 50) { $focused = $true; [W]::SetForegroundWindow($main) | Out-Null }   # once; injected keys need the game in front
  $fg = [W]::GetForegroundWindow() -eq $main   # never type into another application
  if ($fg -and $main -ne [IntPtr]::Zero -and $t -gt 54 -and $t -lt $SkipUntil) { foreach ($f in 8, 10) { [W]::keybd_event(0x0D, 0x1C, $f, [UIntPtr]::Zero); Start-Sleep -Milliseconds 80 } }   # scancode Enter down/up
  if ($fg -and $main -ne [IntPtr]::Zero -and $Hold) { foreach ($h in $Hold.Split(',')) { $q = $h.Split(':'); $t0 = [int]$q[0]; $sc = [byte][Convert]::ToInt32($q[1], 16); $t1 = $t0 + [int]$q[2]
      if ($t -ge $t0 -and $t -lt $t1 -and -not $held[$h]) { $held[$h] = 1; [W]::keybd_event(0, $sc, 8, [UIntPtr]::Zero) }
      elseif ($t -ge $t1 -and $held[$h] -eq 1) { $held[$h] = 2; [W]::keybd_event(0, $sc, 10, [UIntPtr]::Zero) } } }
  if ($fg -and $CaptureAt -and $t -ge $CaptureAt -and $main -ne [IntPtr]::Zero) { $CaptureAt = 0; Log 'remix capture hotkey (Ctrl+Shift+Q)'; foreach ($k in (0x1D,8),(0x2A,8),(0x10,8),(0x10,10),(0x2A,10),(0x1D,10)) { [W]::keybd_event(0, $k[0], $k[1], [UIntPtr]::Zero); Start-Sleep -Milliseconds 60 } }
  if ($main -ne [IntPtr]::Zero -and ($t - $lastShot) -ge $ShotEvery) {
    $lastShot = $t
    if ([W]::IsIconic($main)) { [W]::ShowWindow($main, 4) | Out-Null; Start-Sleep -Milliseconds 800 }
    $r = New-Object W+RECT; [W]::GetWindowRect($main, [ref]$r) | Out-Null
    $w = $r.R - $r.L; $hh = $r.B - $r.T
    if ($w -gt 50 -and $hh -gt 50) {
      $bmp = New-Object System.Drawing.Bitmap $w, $hh
      $g = [System.Drawing.Graphics]::FromImage($bmp); $dc = $g.GetHdc(); [W]::PrintWindow($main, $dc, 2) | Out-Null; $g.ReleaseHdc($dc); $g.Dispose()   # PW_RENDERFULLCONTENT: works while occluded
      # downscale so the png stays small enough to inspect
      $sw = [Math]::Min($w, 1280); $sh = [int]($hh * $sw / $w)
      $small = New-Object System.Drawing.Bitmap $bmp, $sw, $sh
      $f = "$out\shot_${Tag}_{0:000}s.png" -f $t; $small.Save($f); $bmp.Dispose(); $small.Dispose()
      Log "shot $f (${w}x${hh}) title='$([W]::Title($main))' mem=$([int]($game[0].WorkingSet64/1MB))MB"
    }
  }
}
Log "RESULT: $result"
KillAll; Start-Sleep 2
Restore
Get-WinEvent -FilterHashtable @{LogName = 'Application'; Id = 1000, 1026; StartTime = $start } -ErrorAction SilentlyContinue |
  Where-Object Message -match 'GTAIV|NvRemix' | ForEach-Object { Log ("CRASH EVENT: " + (($_.Message -split "`n" | Select-Object -First 5) -join ' ; ')) }



