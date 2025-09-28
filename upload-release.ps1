Param(
    [string]$Owner = "gevorkyan424",
    [string]$Repo = "HeatSim",
    [string]$Tag = "v1.4",
    [string]$AssetPath = ".\dist\HeatSim.exe",
    [string]$Token = $env:GITHUB_TOKEN,
    [switch]$Publish = $false   # если поставить --Publish, релиз будет опубликован сразу
)

if (-not (Test-Path $AssetPath)) {
    Write-Error "Asset not found: $AssetPath"
    exit 1
}

if (-not $Token) {
    # Prompt for token securely if not provided as parameter or env var
    $secureToken = Read-Host -AsSecureString "Enter GitHub PAT (will not be shown)"
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    $Token = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) | Out-Null
}

# Trim whitespace/newlines that may have been copied incorrectly
$Token = $Token.Trim()

# Basic headers
$apiBase = "https://api.github.com/repos/$Owner/$Repo/releases"
$headers = @{ Authorization = "token $Token"; Accept = "application/vnd.github.v3+json"; 'User-Agent' = 'HeatSim-uploader' }

# 1) Try to find existing release by tag
try {
    $all = Invoke-RestMethod -Method Get -Uri $apiBase -Headers $headers -ErrorAction Stop
    $release = $all | Where-Object { $_.tag_name -eq $Tag }
}
catch {
    # Try to extract JSON message from the response for clearer error
    $err = $_
    $msg = $null
    try {
        $content = $_.Exception.Response.GetResponseStream() | % { [IO.StreamReader]::new($_).ReadToEnd() }
        if ($content) { $body = $content | ConvertFrom-Json -ErrorAction SilentlyContinue; if ($body -and $body.message) { $msg = $body.message } }
    }
    catch {}
    if ($msg) {
        Write-Error "Failed to list releases: $msg"
    }
    else {
        Write-Error "Failed to list releases: $_"
    }
    Write-Host "Common causes: invalid/expired PAT, missing scopes (repo/public_repo), or extra whitespace when pasting."
    Write-Host "To quickly test your token run:`n  $env:GH_TEST_TOKEN = '<TOKEN>'`n  Invoke-RestMethod -Uri https://api.github.com/user -Headers @{ Authorization = 'token ' + $env:GH_TEST_TOKEN; 'User-Agent'='test' }"
    exit 1
}

if (-not $release) {
    # create release (draft by default)
    $body = @{ tag_name = $Tag; name = $Tag; body = "Release $Tag"; draft = $true; prerelease = $false } | ConvertTo-Json
    try {
        $release = Invoke-RestMethod -Method Post -Uri $apiBase -Headers $headers -Body $body -ContentType "application/json"
        Write-Host "Created draft release $Tag (id: $($release.id))"
    }
    catch {
        Write-Error "Failed to create release: $_"
        exit 1
    }
}
else {
    Write-Host "Found existing release id $($release.id) for tag $Tag"
}

$upload_url = $release.upload_url -replace '\{.*\}', ''
$assetName = [System.IO.Path]::GetFileName($AssetPath)

# 2) If asset with same name exists, delete it
$existing = $release.assets | Where-Object { $_.name -eq $assetName }
if ($existing) {
    foreach ($a in $existing) {
        Write-Host "Deleting existing asset $($a.name) (id $($a.id))"
        try {
            Invoke-RestMethod -Method Delete -Uri "https://api.github.com/repos/$Owner/$Repo/releases/assets/$($a.id)" -Headers $headers -ErrorAction Stop
        }
        catch {
            Write-Warning "Failed to delete asset id $($a.id): $_"
        }
    }
}

# 3) Upload new asset
$uploadUri = "${upload_url}?name=${assetName}"
Write-Host "Uploading $AssetPath to $uploadUri ..."
try {
    Invoke-RestMethod -Method Post -Uri $uploadUri -Headers @{ Authorization = "token $Token"; 'Content-Type' = 'application/octet-stream'; 'User-Agent' = 'HeatSim-uploader' } -InFile $AssetPath -ErrorAction Stop
    Write-Host "Upload complete."
}
catch {
    Write-Error "Upload failed: $_"
    exit 1
}

# 4) Optionally publish (un-draft) the release
if ($Publish) {
    $update = @{ draft = $false } | ConvertTo-Json
    try {
        Invoke-RestMethod -Method Patch -Uri "$apiBase/$($release.id)" -Headers $headers -Body $update -ContentType "application/json" -ErrorAction Stop
        Write-Host "Release published."
    }
    catch {
        Write-Warning "Failed to publish release: $_"
    }
}
else {
    Write-Host "Release left as draft. Open GitHub to verify and publish manually if needed."
}

# Cleanup token in memory
Remove-Variable token -ErrorAction SilentlyContinue
Remove-Variable secureToken -ErrorAction SilentlyContinue
