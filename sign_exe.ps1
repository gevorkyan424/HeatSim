Param(
    [Parameter(Mandatory = $true)][string]$PfxPath,
    [Parameter(Mandatory = $true)][SecureString]$PfxPassword,
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

Write-Host "This script signs 'dist\HeatSim.exe' using signtool."
Write-Host "It is a template — run it on a machine with signtool (Windows SDK) installed."

$exePath = Join-Path $PSScriptRoot "dist\HeatSim.exe"
if (-Not (Test-Path $exePath)) { Write-Host "Executable not found: $exePath" -ForegroundColor Red; exit 1 }
if (-Not (Test-Path $PfxPath)) { Write-Host "PFX not found: $PfxPath" -ForegroundColor Red; exit 1 }

# Example command (uncomment to run). To pass password as plain text (not recommended) convert it first:
# $pwd = ConvertTo-SecureString "yourpassword" -AsPlainText -Force
# & "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe" sign /f "$PfxPath" /p (ConvertFrom-SecureString $pwd) /tr "$TimestampUrl" /td SHA256 /fd SHA256 "$exePath"

Write-Host "To sign, ensure 'signtool.exe' is on PATH and run the command above (adjust path to signtool if needed)."