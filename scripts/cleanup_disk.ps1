# Liron hapesire ne disk duke pastruar VETEM cache/mbeturina te sigurta qe Windows i
# rigjeneron sipas nevojes:
#   - Cache i Windows Update (SoftwareDistribution\Download)  <- fituesi i madh
#   - Mbeturinat e Windows Update (C:\$WINDOWS.~BT)
#   - Temp i perdoruesit dhe Windows Temp
#   - Recycle Bin (te gjitha llogarite)
#   - Hibernation off (hiberfil.sys)
#
# NUK prek modelet e projektit DOKU:
#   - HuggingFace cache (bge-m3)  ~  %USERPROFILE%\.cache\huggingface
#   - Ollama models (qwen2.5/gemma2) ~ %USERPROFILE%\.ollama\models
#
# Kerkon Administrator - ngrihet automatikisht me UAC nese nisesh normalisht.

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

$ErrorActionPreference = "SilentlyContinue"
$log = Join-Path $PSScriptRoot "..\cleanup_disk.log"
Start-Transcript -Path $log -Force | Out-Null

function FreeGB { [math]::Round((Get-PSDrive C).Free / 1GB, 2) }
$before = FreeGB
Write-Output "Hapesire e lire para pastrimit: $before GB"

Write-Output "`n[1/5] Cache i Windows Update (SoftwareDistribution\Download)..."
Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
Stop-Service -Name bits     -Force -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Windows\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
Start-Service -Name wuauserv -ErrorAction SilentlyContinue
Start-Service -Name bits     -ErrorAction SilentlyContinue

Write-Output "[2/5] Mbeturinat e Windows Update (C:\`$WINDOWS.~BT)..."
Remove-Item -Path 'C:\$WINDOWS.~BT' -Recurse -Force -ErrorAction SilentlyContinue

Write-Output "[3/5] Temp (perdorues + Windows)..."
Remove-Item -Path "$env:LOCALAPPDATA\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Windows\Temp\*"        -Recurse -Force -ErrorAction SilentlyContinue

Write-Output "[4/5] Recycle Bin..."
Clear-RecycleBin -DriveLetter C -Force -Confirm:$false -ErrorAction SilentlyContinue

Write-Output "[5/5] Hibernation off (hiberfil.sys)..."
powercfg /hibernate off

$after = FreeGB
Write-Output "`nGati. Hapesire e lire: $before GB -> $after GB (liruar ~$([math]::Round($after-$before,2)) GB)."
Write-Output "Per ta riaktivizuar hibernation me vone: powercfg /hibernate on"
Stop-Transcript | Out-Null
