Param(
    [string]$ProjectRoot = (Split-Path -Parent $MyInvocation.MyCommand.Definition)
)

Set-Location $ProjectRoot

# Read version from VERSION
if (-Not (Test-Path "$ProjectRoot\VERSION")) {
    Write-Error "VERSION file not found in $ProjectRoot"
    exit 1
}
$AppVersion = (Get-Content "$ProjectRoot\VERSION" -Raw).Trim()
if (-Not $AppVersion) { $AppVersion = "1.0.0" }

# Ensure EXE exists
$exePath = Join-Path $ProjectRoot "dist\HeatSim.exe"
if (-Not (Test-Path $exePath)) {
    Write-Error "Executable not found: $exePath. Build it first (build_exe.ps1)."
    exit 1
}

# Find Inno Setup Compiler (ISCC)
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) {
    $defaultIscc = "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"
    if (Test-Path $defaultIscc) { $iscc = $defaultIscc }
}
if (-not $iscc) {
    Write-Error "Inno Setup Compiler (ISCC) not found. Install Inno Setup 6 or add ISCC to PATH."
    exit 1
}

# Compile installer
$issPath = Join-Path $ProjectRoot "installer\HeatSim.iss"
if (-Not (Test-Path $issPath)) {
    Write-Error "Installer script not found: $issPath"
    exit 1
}

Write-Host "Building installer v$AppVersion via Inno Setup..."
& $iscc /Qp /DAppVersion=$AppVersion /DProjectRoot="$ProjectRoot" "$issPath"
if ($LASTEXITCODE -ne 0) {
    Write-Error "ISCC exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# Output path mirrors OutputDir from .iss (dist)
$setupPath = Join-Path $ProjectRoot ("dist/HeatSim-Setup-v{0}.exe" -f $AppVersion)
if (Test-Path $setupPath) {
    Write-Host "Installer created: $setupPath" -ForegroundColor Green
} else {
    Write-Warning "Installer not found at expected path: $setupPath"
}
