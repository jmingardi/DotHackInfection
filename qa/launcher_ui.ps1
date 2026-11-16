param([switch]$InspectOnly)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class LauncherWindow {
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h,IntPtr dc,uint flags);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out Rect rect);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h,uint msg,IntPtr a,IntPtr b);
 [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h,uint msg,IntPtr a,IntPtr b);
 public struct Rect {public int Left,Top,Right,Bottom;}
}
'@
$projectRoot = Split-Path $PSScriptRoot -Parent
$qaDirectory = Join-Path $projectRoot ('evidence/qa-launcher-gui-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff'))
$profileDirectory = Join-Path $qaDirectory 'profile'
New-Item -ItemType Directory -Path $profileDirectory -Force | Out-Null
$personalKeys = Join-Path $projectRoot 'saves/keys.ini'
$originalKeysHash = (Get-FileHash -LiteralPath $personalKeys -Algorithm SHA256).Hash
Copy-Item -LiteralPath $personalKeys -Destination (Join-Path $profileDirectory 'keys.ini')
Add-Content -LiteralPath (Join-Path $profileDirectory 'keys.ini') -Value '# Launcher QA preservation marker'
$start = New-Object System.Diagnostics.ProcessStartInfo
$start.FileName = Join-Path $projectRoot 'DotHackInfection.exe'
$start.WorkingDirectory = $projectRoot
$start.Arguments = '--profile-dir "' + $profileDirectory + '" --qa-frames 600'
$start.UseShellExecute = $false
$process = [System.Diagnostics.Process]::Start($start)
$condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,$process.Id)
$window = $null
$deadline = [DateTime]::UtcNow.AddSeconds(30)
while (-not $window -and [DateTime]::UtcNow -lt $deadline) {
 $window = [System.Windows.Automation.AutomationElement]::RootElement.FindFirst([System.Windows.Automation.TreeScope]::Children,$condition)
 if (-not $window) { Start-Sleep -Milliseconds 200 }
}
if (-not $window) { throw 'Launcher window did not open' }
function Find-Control([string]$id) {
 $byId = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty,$id)
 $element = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$byId)
 if (-not $element) {
  $aliases = @{PlayGame='Play';SaveSettings='Save settings';ReloadSettings='Reload';KeyBindings='Keyboard and mouse bindings';InternalResolution='Native (1x)'}
  if ($aliases.ContainsKey($id)) { $id = $aliases[$id] }
  $byName = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,$id)
  $element = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$byName)
 }
 if (-not $element -and $id -eq 'Native (1x)') {
  $boxes = @($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition) | Where-Object { $_.Current.ClassName -match 'COMBOBOX' } | Sort-Object {$_.Current.BoundingRectangle.Top})
  if ($boxes.Count -eq 4) { $element = $boxes[1] }
 }
 if (-not $element) { throw "Control not found: $id" }
 return $element
}
function Invoke-Control([string]$id) {
 $element = Find-Control $id
 $pattern = $null
 if ($element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$pattern)) { $pattern.Invoke() }
 else { [LauncherWindow]::SendMessage([IntPtr]$element.Current.NativeWindowHandle,0xF5,[IntPtr]::Zero,[IntPtr]::Zero) | Out-Null }
}
function Select-Tab([string]$name) {
 $tab = @($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition) | Where-Object {$_.Current.ClassName -match 'SysTabControl32'})[0]
 $x = @{Game=25;Display=78;Controls=137}[$name]
 $point = [IntPtr](($x -band 65535) -bor (10 -shl 16))
 [LauncherWindow]::SendMessage([IntPtr]$tab.Current.NativeWindowHandle,0x201,[IntPtr]1,$point) | Out-Null
 [LauncherWindow]::SendMessage([IntPtr]$tab.Current.NativeWindowHandle,0x202,[IntPtr]::Zero,$point) | Out-Null
 Start-Sleep -Milliseconds 200
}
function Save-Window([string]$name) {
 $handle = [IntPtr]$window.Current.NativeWindowHandle
 $rect = New-Object LauncherWindow+Rect
 [LauncherWindow]::GetWindowRect($handle,[ref]$rect) | Out-Null
 $bitmap = New-Object System.Drawing.Bitmap(($rect.Right-$rect.Left),($rect.Bottom-$rect.Top))
 $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
 $dc = $graphics.GetHdc()
 try { [LauncherWindow]::PrintWindow($handle,$dc,2) | Out-Null }
 finally { $graphics.ReleaseHdc($dc); $graphics.Dispose() }
 $bitmap.Save((Join-Path $qaDirectory $name),[System.Drawing.Imaging.ImageFormat]::Png)
 $bitmap.Dispose()
}
Start-Sleep -Milliseconds 600
$elements = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
$tree = @($elements | ForEach-Object { [pscustomobject]@{name=$_.Current.Name; id=$_.Current.AutomationId; type=$_.Current.ControlType.ProgrammaticName} })
$tree | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $qaDirectory 'controls.json') -Encoding UTF8
Write-Output "QA directory: $qaDirectory"
if ($InspectOnly) {
 Save-Window 'home.png'
 $tree | Where-Object { $_.type -match 'Button|TabItem|ComboBox|Edit|ProgressBar' } | Select-Object -First 24 | ConvertTo-Json
 [LauncherWindow]::PostMessage([IntPtr]$window.Current.NativeWindowHandle,0x10,[IntPtr]::Zero,[IntPtr]::Zero) | Out-Null
 exit
}
$deadline = [DateTime]::UtcNow.AddSeconds(90)
while (-not (Find-Control 'PlayGame').Current.IsEnabled -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 300 }
if (-not (Find-Control 'PlayGame').Current.IsEnabled) { throw 'Disc validation did not enable Play' }
Save-Window 'home.png'
Select-Tab 'Controls'
[LauncherWindow]::SetForegroundWindow([IntPtr]$window.Current.NativeWindowHandle) | Out-Null
(Find-Control 'KeyBindings').SetFocus()
[System.Windows.Forms.SendKeys]::SendWait('^{HOME}{DOWN 12}{RIGHT 2} ')
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait('g')
Start-Sleep -Milliseconds 300
Save-Window 'controls.png'
Select-Tab 'Display'
(Find-Control 'InternalResolution').SetFocus()
$resolutionBox = Find-Control 'InternalResolution'
[LauncherWindow]::SendMessage([IntPtr]$resolutionBox.Current.NativeWindowHandle,0x14E,[IntPtr]1,[IntPtr]::Zero) | Out-Null
Save-Window 'display.png'
Invoke-Control 'SaveSettings'
$text = Get-Content -LiteralPath (Join-Path $profileDirectory 'keys.ini') -Raw
if ($text -notmatch '(?m)^cross\s*=\s*G\s*$') { throw 'Keyboard rebind did not persist through the GUI' }
if ($text -notmatch '(?m)^scale\s*=\s*2\s*$') { throw 'Resolution setting did not persist through the GUI' }
if ($text -notmatch 'Launcher QA preservation marker') { throw 'Unrelated keys.ini comment was lost' }
Select-Tab 'Game'
Invoke-Control 'PlayGame'
$deadline = [DateTime]::UtcNow.AddSeconds(180)
$runtimeLog = $null
while ([DateTime]::UtcNow -lt $deadline) {
 $runtimeLog = Get-ChildItem -LiteralPath (Join-Path $profileDirectory 'launcher-logs') -Filter '*.log' -ErrorAction SilentlyContinue | Select-Object -Last 1
 if ($runtimeLog -and (Get-Content -LiteralPath $runtimeLog.FullName -Raw) -match 'Game exit code:') { break }
 Start-Sleep -Milliseconds 500
}
if (-not $runtimeLog) { throw 'Play did not create a native game log' }
$logText = Get-Content -LiteralPath $runtimeLog.FullName -Raw
if ($logText -notmatch 'Game exit code: 0') { throw 'Native game did not close cleanly within the QA limit' }
if ($logText -notmatch 'frame limit reached') { throw 'Native game did not reach its frame limit' }
if ($logText -notmatch 'resolution 2x') { throw 'Runtime did not apply the launcher resolution setting' }
Start-Sleep -Milliseconds 500
if ((Get-FileHash -LiteralPath $personalKeys -Algorithm SHA256).Hash -ne $originalKeysHash) { throw 'Personal bindings were changed' }
$report = [pscustomobject]@{launcher_pid=$process.Id; gui_keyboard_binding='Cross=G'; resolution=2; preserved_comment=$true; personal_bindings_unchanged=$true; native_exit=0; native_frame_limit=600; log=$runtimeLog.FullName; scope='Real launcher controls and native boot; not campaign QA'}
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $qaDirectory 'report.json') -Encoding UTF8
$report | ConvertTo-Json
[LauncherWindow]::PostMessage([IntPtr]$window.Current.NativeWindowHandle,0x10,[IntPtr]::Zero,[IntPtr]::Zero) | Out-Null
if (-not $process.WaitForExit(10000)) { throw 'Launcher did not close after the game ended' }
