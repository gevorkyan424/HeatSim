Param(
    [string]$Root = (Get-Location).Path,
    [switch]$DryRun
)

Write-Host "Scanning for empty files and empty folders..." -ForegroundColor Cyan

# Exclusions: directories we never touch
$excludePatterns = @(
    "\\.venv\\",
    "\\.git\\",
    "\\.vscode\\"
)

function Test-Excluded([string]$path) {
    foreach ($pat in $excludePatterns) { if ($path -match $pat) { return $true } }
    return $false
}

# 1) Find zero-byte files (excluding common placeholders and excluded dirs)
$emptyFiles = Get-ChildItem -Path $Root -File -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Length -eq 0 -and
        -not (Test-Excluded $_.FullName) -and
        $_.Name -notin @('.gitkeep', '.keep')
    }

# 2) Find empty directories (from deepest first)
$allDirs = Get-ChildItem -Path $Root -Directory -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { -not (Test-Excluded $_.FullName) }

# Helper: check if a directory is truly empty (no files or subdirs)
function Test-DirEmpty([string]$dir) {
    $items = Get-ChildItem -Force -LiteralPath $dir -ErrorAction SilentlyContinue
    if ($null -eq $items) { return $true }
    return ($items.Count -eq 0)
}

# Collect empty dirs; re-evaluate after deletions if not DryRun
$emptyDirs = @()
foreach ($d in $allDirs) {
    if (Test-DirEmpty $d.FullName) { $emptyDirs += $d }
}

Write-Host ("Empty files: {0}" -f $emptyFiles.Count) -ForegroundColor Yellow
Write-Host ("Empty dirs:  {0}" -f $emptyDirs.Count) -ForegroundColor Yellow

if ($DryRun) {
    if ($emptyFiles.Count -gt 0) { $emptyFiles | Select-Object FullName | Format-Table -AutoSize }
    if ($emptyDirs.Count -gt 0) { $emptyDirs | Select-Object FullName | Sort-Object { $_.FullName.Length } -Descending | Format-Table -AutoSize }
    Write-Host "Dry-run complete. Nothing deleted." -ForegroundColor Cyan
    exit 0
}

# Delete empty files
foreach ($f in $emptyFiles) {
    try {
        Remove-Item -LiteralPath $f.FullName -Force -ErrorAction Stop
        Write-Host "Removed file: $($f.FullName)" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed file: $($f.FullName) — $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Delete empty dirs (deepest first)
foreach ($d in ($emptyDirs | Sort-Object { $_.FullName.Length } -Descending)) {
    try {
        if (Test-DirEmpty $d.FullName) {
            Remove-Item -LiteralPath $d.FullName -Recurse -Force -ErrorAction Stop
            Write-Host "Removed dir:  $($d.FullName)" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "Failed dir:  $($d.FullName) — $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "Cleanup finished." -ForegroundColor Cyan
