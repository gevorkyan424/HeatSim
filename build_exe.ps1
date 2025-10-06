Param(
    [switch]$CreateVenv
)

$Here = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $Here

if ($CreateVenv) {
    if (-Not (Test-Path ".venv")) {
        Write-Host "Creating virtual environment .venv..."
        python -m venv .venv
    }
    Write-Host "Activating .venv..."
    & .\.venv\Scripts\Activate.ps1
}
else {
    Write-Host "Using current Python environment."
}

Write-Host "Upgrading pip and installing requirements..."
python -m pip install --upgrade pip
if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt
}

Write-Host "Ensuring PyInstaller is installed..."
python -m pip install pyinstaller

# Prepare --add-data arguments for assets, data, i18n and top-level files
$assets = Join-Path $Here "assets"
$data = Join-Path $Here "data"
$i18n = Join-Path $Here "i18n"
$versionFile = Join-Path $Here "VERSION"
$licenseRu = Join-Path $Here "Лицензионное_соглашение.txt"

# PyInstaller on Windows expects paths in the form "SRC;DEST"
$addData = @()
if (Test-Path $assets) { $addData += @("${assets};assets") }
if (Test-Path $data) { $addData += @("${data};data") }
if (Test-Path $i18n) { $addData += @("${i18n};i18n") }
if (Test-Path $versionFile) { $addData += @("${versionFile};VERSION") }
if (Test-Path $licenseRu) { $addData += @("${licenseRu};Лицензионное_соглашение.txt") }

Write-Host "Running PyInstaller via module to avoid PATH issues..."
$pyargs = @("--noconfirm", "--onefile", "--windowed", "--name", "HeatSim")
foreach ($ad in $addData) { $pyargs += @("--add-data", $ad) }
# include icon if present
$iconPath = Join-Path $Here "assets\icon.ico"
if (Test-Path $iconPath) { $pyargs += @("--icon", $iconPath) }
$pyargs += @("main.py")
python -m PyInstaller @pyargs

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build succeeded. See the executable in the 'dist' folder." -ForegroundColor Green

    # Path to produced exe
    $exePath = Join-Path $Here "dist\HeatSim.exe"

    # Copy LICENSE and RU license agreement text into dist for distribution
    $filesToCopy = @("LICENSE", "Лицензионное_соглашение.txt")
    foreach ($f in $filesToCopy) {
        $src = Join-Path $Here $f
        if (Test-Path $src) {
            Write-Host "Copying $f to dist..."
            Copy-Item -Path $src -Destination (Join-Path $Here 'dist') -Force
        }
    }

}
else {
    Write-Host "Build finished with errors (exit code $LASTEXITCODE)." -ForegroundColor Yellow
}

Write-Host "Note: If your app still fails to start, try running the executable from a console to see missing DLL/plugin errors."
