Param(
    [switch]$CreateVenv,
    [string]$SignPfx = "",         # Path to .pfx certificate for signing (optional)
    [string]$SignPassword = "",    # Password for the .pfx (optional)
    [switch]$Timestamp = $true      # Use RFC3161 timestamp server when signing
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

    # Optional signing step (temporarily disabled)
    # To enable signing later, uncomment the block below and provide -SignPfx and -SignPassword when running the script.
    #if ($SignPfx -and (Test-Path $SignPfx)) {
    #    Write-Host "Signing executable using PFX: $SignPfx"
    #    $signtool = Get-Command signtool -ErrorAction SilentlyContinue
    #    if ($signtool) {
    #        $tsArg = ""
    #        if ($Timestamp) { $tsArg = "/tr http://timestamp.digicert.com /td sha256" }
    #        try {
    #            & signtool sign /f $SignPfx /p $SignPassword $tsArg /fd sha256 $exePath
    #            if ($LASTEXITCODE -eq 0) { Write-Host "SignTool: signing succeeded." -ForegroundColor Green }
    #            else { Write-Warning "SignTool: signing finished with exit code $LASTEXITCODE" }
    #        }
    #        catch {
    #            Write-Warning "SignTool signing failed: $_"
    #        }
    #    }
    #    else {
    #        try {
    #            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($SignPfx, $SignPassword, [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
    #            if ($cert) {
    #                if ($Timestamp) {
    #                    $timestampServer = "http://timestamp.digicert.com"
    #                    $sig = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -TimestampServer $timestampServer
    #                }
    #                else {
    #                    $sig = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert
    #                }
    #                if ($sig.Status -eq 'Valid') { Write-Host "Authenticode: signing succeeded." -ForegroundColor Green }
    #                else { Write-Warning "Authenticode: signing status: $($sig.Status)" }
    #            }
    #        }
    #        catch {
    #            Write-Warning "Authenticode signing failed: $_"
    #        }
    #    }
    #}
    #else {
    #    Write-Host "No signing certificate provided or file not found; skipping signing." -ForegroundColor Yellow
    #}
}
else {
    Write-Host "Build finished with errors (exit code $LASTEXITCODE)." -ForegroundColor Yellow
}

Write-Host "Note: If your app still fails to start, try running the executable from a console to see missing DLL/plugin errors."
