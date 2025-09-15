# clean.ps1 — безопасная очистка артефактов сборки
# Запуск из корня проекта: .\clean.ps1

Write-Host "Dry-run: перечисляю артефакты, которые будут удалены..." -ForegroundColor Cyan
$items = @()

# Always ignore the virtual environment directory early
$excludeVenv = Join-Path (Get-Location) ".venv"

if (Test-Path .\_test_unpack) { $items += Get-ChildItem .\_test_unpack -Recurse -Force }
if (Test-Path .\aspaProj-distribution.zip) { $items += Get-Item .\aspaProj-distribution.zip }
if (Test-Path .\aspaProj.spec) { $items += Get-Item .\aspaProj.spec }
if (Test-Path .\build) { $items += Get-ChildItem .\build -Recurse -Force }

# Collect __pycache__ directories and .pyc files but explicitly exclude any under .venv
$pyc = Get-ChildItem -Path . -Include __pycache__, *.pyc -Recurse -Force -ErrorAction SilentlyContinue |
Where-Object { $_.FullName -notlike "$excludeVenv*" -and $_.FullName -notmatch "\\\?" }
$items += $pyc

if ($items.Count -eq 0) {
    Write-Host "No artifacts found to remove." -ForegroundColor Yellow
    exit 0
}

$items | Select-Object FullName, Length, PSIsContainer | Format-Table -AutoSize

$confirm = Read-Host "Удалить перечисленные файлы и папки? (y/N)"
if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Host "Отменено пользователем." -ForegroundColor Yellow
    exit 0
}

foreach ($it in $items) {
    try {
        if ($it.PSIsContainer) { Remove-Item -LiteralPath $it.FullName -Recurse -Force -ErrorAction Stop }
        else { Remove-Item -LiteralPath $it.FullName -Force -ErrorAction Stop }
        Write-Host "Removed: $($it.FullName)" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to remove: $($it.FullName) — $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "Cleanup finished." -ForegroundColor Cyan
