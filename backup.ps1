param(
    [string]$SourcePath = (Split-Path -Parent $MyInvocation.MyCommand.Path),
    # По умолчанию создаём каталог резервных копий РЯДОМ с проектом, а не внутри
    [string]$BackupRoot = (Join-Path (Split-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) -Parent) ((Split-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) -Leaf) + '_backups')),
    [int]$Keep = 20,
    [switch]$AllowInsideSource
)

# Нормализация путей
$SourcePath = (Resolve-Path -LiteralPath $SourcePath).ProviderPath
if (-not $BackupRoot) { throw 'BackupRoot path not resolved' }

# Если пользователь указал BackupRoot вручную (не дефолт), уважаем
if (Test-Path $BackupRoot) { $BackupRoot = (Resolve-Path -LiteralPath $BackupRoot).ProviderPath }

# Предотвращаем резервное копирование внутрь исходного каталога (robocopy может выдавать код 16)
if ($BackupRoot -like ($SourcePath + '*')) {
    if (-not $AllowInsideSource) {
        $parent = Split-Path $SourcePath -Parent
        $suggested = Join-Path $parent ((Split-Path $SourcePath -Leaf) + '_backups')
        Write-Host "Предупреждение: каталог резервных копий находился внутри исходного. Переношу в: $suggested" -ForegroundColor Yellow
        $BackupRoot = $suggested
    }
    else {
        Write-Host "ВНИМАНИЕ: BackupRoot находится внутри SourcePath (разрешено флагом)." -ForegroundColor Yellow
    }
}

if (-not (Test-Path $BackupRoot)) { New-Item -ItemType Directory -Path $BackupRoot | Out-Null }

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$dest = Join-Path $BackupRoot $timestamp

Write-Host "Создание резервной копии в $dest" -ForegroundColor Cyan

# Исключения (папки и файлы, которые не имеет смысла копировать)
$excludes = @('__pycache__', '.git', 'backups', '.venv', '.mypy_cache')

Write-Host "Source:   $SourcePath"
Write-Host "BackupRoot: $BackupRoot"
Write-Host "Keep: $Keep" 
Write-Host "Исключения: $($excludes -join ', ')"

# Используем robocopy для надёжного копирования структуры
$roboLog = Join-Path $BackupRoot "robocopy_$timestamp.log"
# Явно создаём каталог назначения (robocopy обычно создаёт сам, но на OneDrive иногда лучше заранее)
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null }

$excludeFull = @()
foreach ($ex in $excludes) {
    $p = Join-Path $SourcePath $ex
    if (Test-Path $p) { $excludeFull += $p }
}

$roboLogArg = "/LOG:$roboLog"
$roboArgs = @(
    $SourcePath,
    $dest,
    '/E',           # все подпапки
    '/Z',           # перезапуск при сбое
    '/R:1', '/W:1',  # меньше повторов
    '/NFL', '/NDL',  # без списков файлов/каталогов
    '/NP',          # без прогресса
    $roboLogArg,
    '/TEE',         # дублируем вывод в консоль (увидим ошибку)
    '/XJ',          # исключить точки соединения (symlink) чтобы не зациклиться
    '/FFT',         # файловая система с неточной меткой времени (OneDrive)
    '/DST'          # корректировка летнего времени
)
if ($excludeFull.Count -gt 0) {
    $roboArgs += '/XD'
    $roboArgs += $excludeFull
}

Write-Host "Команда robocopy аргументы:" -ForegroundColor DarkCyan
$roboArgs | ForEach-Object { Write-Host "  $_" }

robocopy @roboArgs
$rc = $LASTEXITCODE
# Интерпретация кода robocopy (0,1,2,3 считаются успешными вариантами)
$successCodes = 0, 1, 2, 3
$status = if ($successCodes -contains $rc) { 'OK' } else { 'FAIL' }

if ($status -eq 'OK') {
    Write-Host "Резервная копия создана: $dest (код robocopy=$rc)" -ForegroundColor Green
}
else {
    Write-Host "Ошибка: резервная копия НЕ создана корректно (код robocopy=$rc)" -ForegroundColor Red
}

# Запись истории
try {
    $historyFile = Join-Path $BackupRoot 'backup_history.log'
    $line = "$(Get-Date -Format 'u') | $status | rc=$rc | $dest"
    Add-Content -Path $historyFile -Value $line
}
catch {
    Write-Host "Не удалось записать историю: $($_.Exception.Message)" -ForegroundColor Yellow
}

if ($status -ne 'OK') {
    Write-Host "Подсказка: Код 16 часто означает: путь назначения внутри источника или проблемы с доступом/длиной пути. Попробуйте явный параметр -BackupRoot вне OneDrive или включите длинные пути в политике." -ForegroundColor Yellow
    exit 1
}

# Удаление старых
$backups = Get-ChildItem -Path $BackupRoot -Directory | Sort-Object CreationTime -Descending
if ($backups.Count -gt $Keep) {
    $toDelete = $backups[$Keep..($backups.Count - 1)]
    foreach ($d in $toDelete) {
        try {
            Remove-Item -Recurse -Force -LiteralPath $d.FullName
        }
        catch {
            Write-Host "Не удалось удалить старую копию: $($d.FullName)" -ForegroundColor Yellow
        }
    }
}

pwsh -NoProfile -ExecutionPolicy Bypass -File .\backup.ps1
Get-Content ..\aspaProj_backups\backup_history.log -Tail 3
