# cleanup_disk.ps1 — liron hapësirë në disk.
# EKZEKUTOJE SI ADMINISTRATOR:
#   Kliko djathtas mbi Start → "Windows PowerShell (Admin)" / "Terminal (Admin)"
#   pastaj:  cd C:\Users\PROVA\Desktop\DOKU ;  Set-ExecutionPolicy Bypass -Scope Process -Force ;  .\cleanup_disk.ps1

Write-Host "Hapesira e lire PARA: $([math]::Round((Get-PSDrive C).Free/1GB,2)) GB" -ForegroundColor Cyan

# 1) Cache-i i Windows Update (~5 GB) — i sigurt, Windows e rishkarkon nese duhet.
Write-Host "1) Po pastroj Windows Update cache..."
Stop-Service wuauserv, bits -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Windows\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
Start-Service wuauserv, bits -ErrorAction SilentlyContinue

# 2) Windows Temp
Write-Host "2) Po pastroj C:\Windows\Temp..."
Remove-Item "C:\Windows\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue

# 3) Hibernation (hiberfil.sys ~ madhesia e RAM-it, p.sh. 6-12 GB).
#    Hiqe komentin '#' me poshte VETEM nese nuk perdor "Hibernate".
#    Per ta rikthyer me vone:  powercfg /h on
# powercfg /h off

# 4) Optimizo (Disk Cleanup per system files) — opsionale, hap dritaren:
# cleanmgr /lowdisk

Write-Host "Hapesira e lire PAS:  $([math]::Round((Get-PSDrive C).Free/1GB,2)) GB" -ForegroundColor Green
Write-Host "Per me shume: hap 'Disk Cleanup' (cleanmgr) → 'Clean up system files' → zgjidh 'Windows Update Cleanup'." -ForegroundColor Yellow
