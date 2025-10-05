param(
    [string]$Lang = "en",
    [string]$LReleasePath
)

$ErrorActionPreference = 'Stop'

# Find pylupdate5 and lrelease in PATH or common Qt locations
function Find-Tool($names) {
    foreach ($n in $names) {
        $p = (Get-Command $n -ErrorAction SilentlyContinue).Path
        if ($p) { return $p }
    }
    return $null
}

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $workspace
$i18n = Join-Path $root 'i18n'

$tsFile = Join-Path $i18n ("HeatSim_" + $Lang + ".ts")
$qmFile = Join-Path $i18n ("HeatSim_" + $Lang + ".qm")

if (-not (Test-Path $tsFile)) {
    Write-Error "TS file not found: $tsFile"
}

# Try lrelease first (it compiles .ts -> .qm)
$lrelease = $null
if ($LReleasePath) {
    if (Test-Path $LReleasePath) {
        $lrelease = $LReleasePath
    }
    else {
        Write-Warning "Provided lrelease path does not exist: $LReleasePath"
    }
}
if (-not $lrelease) {
    $lrelease = Find-Tool @('lrelease.exe', 'lrelease', 'lrelease6', 'lrelease-qt5', 'lrelease-qt6', 'pyside6-lrelease')
}
if (-not $lrelease) {
    Write-Warning 'lrelease not found in PATH. Install Qt Linguist tools or add them to PATH.'
    exit 1
}

& $lrelease $tsFile -qm $qmFile
if ($LASTEXITCODE -ne 0) {
    Write-Error "lrelease failed with exit code $LASTEXITCODE"
}
else {
    Write-Host "OK: Generated $qmFile"
}
