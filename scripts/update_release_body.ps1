Param(
    [string]$Owner = "gevorkyan424",
    [string]$Repo = "HeatSim",
    [string]$Tag = "v1.6",
    [string]$BodyPath = "",
    [string]$Token = $env:GITHUB_TOKEN
)

if (-not $Token) {
    $secureToken = Read-Host -AsSecureString "Enter GitHub PAT (will not be shown)"
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    $Token = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) | Out-Null
}
$Token = $Token.Trim()

if (-not (Test-Path $BodyPath)) {
    Write-Error "Body file not found: $BodyPath"
    exit 1
}

$bodyText = Get-Content -Path $BodyPath -Raw

$headers = @{ Authorization = "token $Token"; Accept = "application/vnd.github.v3+json"; 'User-Agent' = 'HeatSim-uploader' }
$apiBase = "https://api.github.com/repos/$Owner/$Repo/releases"

try {
    $all = Invoke-RestMethod -Method Get -Uri $apiBase -Headers $headers -ErrorAction Stop
    $release = $all | Where-Object { $_.tag_name -eq $Tag }
    if (-not $release) {
        Write-Error "Release for tag $Tag not found."
        exit 1
    }
}
catch {
    Write-Error "Failed to query releases: $_"
    exit 1
}

$payload = @{ body = $bodyText } | ConvertTo-Json
try {
    Invoke-RestMethod -Method Patch -Uri ("$apiBase/$($release.id)") -Headers $headers -Body $payload -ContentType 'application/json' -ErrorAction Stop
    Write-Host "Release body updated."
}
catch {
    Write-Error "Failed to update release body: $_"
    exit 1
}
