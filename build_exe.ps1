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

# Prepare --add-data arguments for assets and data folders
$assets = Join-Path $Here "assets"
$data = Join-Path $Here "data"

# PyInstaller on Windows expects paths in the form "SRC;DEST"
$add1 = "${assets};assets"
$add2 = "${data};data"

Write-Host "Running PyInstaller via module to avoid PATH issues..."
$pyargs = @("--noconfirm", "--onefile", "--windowed", "--name", "aspaProj", "--add-data", $add1, "--add-data", $add2)
# include icon if present
$iconPath = Join-Path $Here "assets\icon.ico"
if (Test-Path $iconPath) { $pyargs += @("--icon", $iconPath) }
$pyargs += @("main.py")
python -m PyInstaller @pyargs

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build succeeded. See the executable in the 'dist' folder." -ForegroundColor Green
}
else {
    Write-Host "Build finished with errors (exit code $LASTEXITCODE)." -ForegroundColor Yellow
}

Write-Host "Note: If your app still fails to start, try running the executable from a console to see missing DLL/plugin errors."n
