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

Write-Host "Installing requirements and PyInstaller..."
python -m pip install --upgrade pip
if (Test-Path "requirements.txt") { python -m pip install -r requirements.txt }
python -m pip install pyinstaller

Write-Host "Building onedir distribution with PyInstaller..."
$assetsPath = Join-Path $Here "assets"
$dataPath = Join-Path $Here "data"
# PyInstaller expects a single string like "SRC;DEST" (Windows). Wrap in quotes when passing.
$add1 = "${assetsPath};assets"
$add2 = "${dataPath};data"
# include icon if present
$iconPath = Join-Path $Here "assets\icon.ico"
$iconArg = ""
if (Test-Path $iconPath) { Write-Host "Found icon: $iconPath"; python -m PyInstaller --noconfirm --onedir --windowed --name HeatSim --add-data "$add1" --add-data "$add2" --icon "$iconPath" main.py }
else { python -m PyInstaller --noconfirm --onedir --windowed --name HeatSim --add-data "$add1" --add-data "$add2" main.py }

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

$distFolder = Join-Path $Here "dist\HeatSim"
if (-Not (Test-Path $distFolder)) {
    Write-Host "Expected dist folder not found: $distFolder" -ForegroundColor Red
    exit 1
}

Write-Host "Adding recipient instructions file..."
Copy-Item -Path .\RUN_FOR_RECIPIENT.txt -Destination $distFolder -Force

Write-Host "Creating a shortcut inside distribution folder..."
# Create a .lnk shortcut pointing to HeatSim.exe (for convenience)
$WshShell = New-Object -ComObject WScript.Shell
$shortcutPath = Join-Path $distFolder "HeatSim - Ярлык.lnk"
$targetPath = Join-Path $distFolder "HeatSim.exe"
try {
    $shortcut = $WshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $targetPath
    $shortcut.WorkingDirectory = $distFolder
    $shortcut.IconLocation = $targetPath
    $shortcut.Save()
    Write-Host "Shortcut created: $shortcutPath"
}
catch {
    Write-Host "Could not create shortcut: $_" -ForegroundColor Yellow
}

Write-Host "Creating ZIP archive for distribution..."
$zipPath = Join-Path $Here "HeatSim-distribution.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $distFolder\* -DestinationPath $zipPath

Write-Host "Distribution package created: $zipPath" -ForegroundColor Green
Write-Host "You can now send $zipPath to the recipient (e.g. дедушка)."
