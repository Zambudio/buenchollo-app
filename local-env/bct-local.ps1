<#
.SYNOPSIS
  Entorno local de BuenCholloTech: web + API + Postgres + correo, aislado de producción.

.DESCRIPTION
  Comandos:
    setup      Instala todo lo necesario (una vez por PC; repetible sin riesgo).
    start      Levanta Postgres, correo local, sincronizador de usuarios, API y web.
    stop       Para todo lo que levantó `start`.
    restart    stop + start.
    status     Estado de cada servicio y URLs.
    reset-db   Borra la base local y la reconstruye con una copia fresca del catálogo.
    logs <svc> Últimas líneas del log (postgres | mail | authsync | api | web).
    users <create [n] | tokens | delete>
               Usuarios de prueba pjzambudio+local-N (cuentas reales de Supabase Auth).
    qa         Batería de pruebas en vivo contra el entorno levantado (local-env/qa).
    stress     Prueba de estrés contra el entorno levantado (local-env/qa/stress.py).

  Guía completa: docs/guides/LOCAL-ENV.md

.EXAMPLE
  .\local-env\bct-local.ps1 setup
  .\local-env\bct-local.ps1 start
#>
param(
  [Parameter(Position = 0)]
  [ValidateSet('setup', 'start', 'stop', 'restart', 'status', 'reset-db', 'logs', 'users', 'qa', 'stress', 'help')]
  [string]$Command = 'help',
  [Parameter(Position = 1)]
  [string]$Service = '',
  [Parameter(Position = 2)]
  [string]$Arg = '',
  [switch]$NoReload,
  [switch]$NoWeb
)

$ErrorActionPreference = 'Stop'

$LocalEnv = $PSScriptRoot
$Repo = Split-Path $LocalEnv -Parent
$ApiDir = Join-Path $Repo 'buenchollo-api'
$WebDir = Join-Path $Repo 'buenchollo-web'
$PyDir = Join-Path $LocalEnv 'py'

if ($env:BCT_LOCAL_HOME) { $RuntimeDir = $env:BCT_LOCAL_HOME } else { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'BuenCholloLocal' }
$PgVersion = '17.11'
$PgBin = Join-Path $RuntimeDir 'pgsql\bin'
$PgData = Join-Path $RuntimeDir 'pgdata'
$PgPort = 54329
$VenvPy = Join-Path $RuntimeDir 'api-venv\Scripts\python.exe'
$LogDir = Join-Path $RuntimeDir 'logs'
$PidDir = Join-Path $RuntimeDir 'pids'

$Config = Get-Content (Join-Path $LocalEnv 'config.json') -Raw | ConvertFrom-Json
$ApiPort = [int]$Config.api_port
$WebPort = [int]$Config.web_port
$MailSmtpPort = [int]$Config.mail_smtp_port
$MailWebPort = [int]$Config.mail_web_port

function Write-Step([string]$msg) { Write-Host "→ $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg) { Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "! $msg" -ForegroundColor Yellow }

function Assert-LastExit([string]$what) {
  if ($LASTEXITCODE -ne 0) { throw "$what falló (código $LASTEXITCODE)" }
}

# Variables que la API local recibe por entorno. Tienen prioridad sobre
# buenchollo-api/.env (pydantic-settings), así que el .env real se reutiliza
# para credenciales (Supabase Auth/Storage, Amazon) pero la base de datos,
# el correo, Telegram y el scheduler quedan desviados a local o apagados.
function Get-ApiEnv {
  return @{
    APP_ENV                  = 'local'
    DATABASE_URL             = "postgresql+asyncpg://postgres@127.0.0.1:$PgPort/buenchollo_local"
    CORS_ORIGINS             = "http://localhost:$WebPort,http://127.0.0.1:$WebPort"
    # El cleaner del scheduler usa la API REST de Supabase = base de datos de
    # PRODUCCIÓN. Debe estar apagado en local, siempre.
    SCHEDULER_ENABLED        = 'false'
    LOG_FORMAT               = 'text'
    SENTRY_DSN               = ''
    SMTP_HOST                = '127.0.0.1'
    SMTP_PORT                = "$MailSmtpPort"
    SMTP_USE_SSL             = 'false'
    SMTP_USER                = 'local'
    SMTP_PASSWORD            = 'local'
    SMTP_FROM_EMAIL          = 'info@buenchollo.local'
    ADMIN_NOTIFICATION_EMAIL = 'admin@buenchollo.local'
    TELEGRAM_BOT_TOKEN       = ''
    TELEGRAM_MAIN_CHANNEL_ID = ''
    TELEGRAM_ADMIN_CHANNEL_ID = ''
    TELEGRAM_USER_SESSION    = ''
    PYTHONUNBUFFERED         = '1'
    PYTHONIOENCODING         = 'utf-8'
    # `--reload` no recibe eventos de cambio en shares SMB: sondeo.
    WATCHFILES_FORCE_POLLING = 'true'
  }
}

function Invoke-WithEnv([hashtable]$vars, [scriptblock]$block) {
  $saved = @{}
  foreach ($k in $vars.Keys) {
    $saved[$k] = [Environment]::GetEnvironmentVariable($k, 'Process')
    [Environment]::SetEnvironmentVariable($k, $vars[$k], 'Process')
  }
  try { & $block } finally {
    foreach ($k in $saved.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k], 'Process') }
  }
}

function Test-Port([int]$port) {
  $c = New-Object Net.Sockets.TcpClient
  try { $c.Connect('127.0.0.1', $port); return $true } catch { return $false } finally { $c.Dispose() }
}

function Wait-Port([int]$port, [string]$name, [int]$seconds = 60) {
  $deadline = (Get-Date).AddSeconds($seconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-Port $port) { return }
    Start-Sleep -Milliseconds 500
  }
  throw "$name no respondió en el puerto $port tras $seconds s. Mira: .\local-env\bct-local.ps1 logs $($name.ToLower())"
}

function Get-SavedPid([string]$name) {
  $f = Join-Path $PidDir "$name.pid"
  if (Test-Path $f) { return [int](Get-Content $f) }
  return $null
}

# El PID guardado solo cuenta si sigue siendo nuestro python/node y no un
# proceso cualquiera que haya reutilizado el número tras morir el servicio.
function Get-OwnProcess([string]$name) {
  $savedPid = Get-SavedPid $name
  if (-not $savedPid) { return $null }
  $proc = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
  if (-not $proc -or $proc.ProcessName -notin @('python', 'node')) { return $null }
  $stamp = (Get-Item (Join-Path $PidDir "$name.pid")).LastWriteTime
  if ($proc.StartTime -gt $stamp.AddSeconds(5)) { return $null }
  return $proc
}

function Test-Running([string]$name) {
  return [bool](Get-OwnProcess $name)
}

function Start-Svc([string]$name, [string]$exe, [string[]]$arguments, [string]$workDir, [hashtable]$vars) {
  if (Test-Running $name) { Write-Ok "$name ya estaba en marcha"; return }
  New-Item -ItemType Directory -Force $LogDir, $PidDir | Out-Null
  # spawn.py y no Start-Process: ver el docstring de py/spawn.py.
  $spawnArgs = @((Join-Path $PyDir 'spawn.py'), (Join-Path $LogDir $name), $workDir, $exe) + $arguments
  $newPid = Invoke-WithEnv $vars { & $VenvPy @spawnArgs }
  Assert-LastExit "El arranque de $name"
  Set-Content -Path (Join-Path $PidDir "$name.pid") -Value ([int]"$newPid".Trim())
}

# Vite no resuelve paquetes desde rutas UNC (\\NAS\share\...). Si el repo
# está en un share, se usa la letra de unidad que ya lo tenga mapeado o se
# mapea una libre para esta sesión.
function Resolve-DrivePath([string]$path) {
  if (-not $path.StartsWith('\\')) { return $path }
  # Z: primero: en el PC principal el share está mapeado como N: y Z: a la
  # vez y arrancar desde N: rompe el SSR (.claude/memory/project_entorno_local_nas_drive.md).
  $drives = Get-PSDrive -PSProvider FileSystem | Sort-Object { $_.Name -ne 'Z' }, Name
  foreach ($d in $drives) {
    $root = $d.DisplayRoot
    if ($root -and $path.StartsWith($root.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
      return "$($d.Name):" + $path.Substring($root.TrimEnd('\').Length)
    }
  }
  $parts = $path.TrimStart('\').Split('\')
  $share = "\\$($parts[0])\$($parts[1])"
  $free = [char[]]([int][char]'R'..[int][char]'Y') | Where-Object { -not (Test-Path "$($_):\") } | Select-Object -First 1
  if (-not $free) { throw "No hay letra de unidad libre para mapear $share (Vite no funciona con rutas UNC)" }
  net use "$($free):" $share /persistent:no | Out-Null
  Assert-LastExit "net use $($free): $share"
  Write-Warn "Mapeada $($free): → $share para la web (Vite no admite rutas UNC)"
  return "$($free):" + $path.Substring($share.Length)
}

function Stop-Svc([string]$name) {
  $proc = Get-OwnProcess $name
  if ($proc) {
    # Árbol de procesos de ESE PID (uvicorn --reload y vite lanzan hijos).
    # Nunca matar por nombre de imagen: mataría otros python/node del PC.
    taskkill /PID $proc.Id /T /F | Out-Null
    Write-Ok "$name parado"
  }
  Remove-Item -Force (Join-Path $PidDir "$name.pid") -ErrorAction SilentlyContinue
}

function Find-Python {
  foreach ($v in @('3.11', '3.12', '3.13')) {
    $null = & py "-$v" -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) { return @('py', "-$v") }
  }
  throw 'Necesitas Python 3.11+ (recomendado 3.11, el de producción). Instálalo desde python.org con el "py launcher".'
}

function Invoke-Setup {
  Write-Step "Repositorio: $Repo (rama $(git -C $Repo rev-parse --abbrev-ref HEAD))"
  Write-Step "Estado local: $RuntimeDir"
  New-Item -ItemType Directory -Force $RuntimeDir, $LogDir, $PidDir | Out-Null

  foreach ($f in @("$ApiDir\.env", "$WebDir\.env")) {
    if (-not (Test-Path $f)) { throw "Falta $f. Cópialo desde el NAS (docs/guides/LOCAL-ENV.md, sección 'Otro PC')." }
  }

  $nodeVersion = (node -v) -replace '^v', ''
  if ([int]($nodeVersion.Split('.')[0]) -lt 20) { throw "Necesitas Node 20+ (tienes $nodeVersion)" }
  Write-Ok "Node $nodeVersion"

  if (-not (Test-Path (Join-Path $PgBin 'postgres.exe'))) {
    $zip = Join-Path $RuntimeDir "downloads\postgresql-$PgVersion-1-windows-x64-binaries.zip"
    if (-not (Test-Path $zip)) {
      Write-Step "Descargando PostgreSQL $PgVersion portable (~330 MB, una sola vez)"
      New-Item -ItemType Directory -Force (Split-Path $zip) | Out-Null
      curl.exe -fSL -o $zip "https://get.enterprisedb.com/postgresql/postgresql-$PgVersion-1-windows-x64-binaries.zip"
      Assert-LastExit 'La descarga de PostgreSQL'
    }
    Write-Step 'Descomprimiendo PostgreSQL'
    tar -xf $zip -C $RuntimeDir pgsql/bin pgsql/lib pgsql/share
    Assert-LastExit 'La descompresión de PostgreSQL'
  }
  Write-Ok "PostgreSQL $(& (Join-Path $PgBin 'postgres.exe') --version)"

  if (-not (Test-Path $VenvPy)) {
    $py = Find-Python
    Write-Step "Creando venv de Python ($($py -join ' '))"
    & $py[0] $py[1] -m venv (Join-Path $RuntimeDir 'api-venv')
    Assert-LastExit 'La creación del venv'
  }
  Write-Step 'Instalando dependencias de Python'
  & $VenvPy -m pip install -q --disable-pip-version-check -r (Join-Path $LocalEnv 'requirements.txt')
  Assert-LastExit 'pip install'
  Write-Ok "Python $(& $VenvPy -c 'import sys; print(sys.version.split()[0])')"

  if (-not (Test-Path (Join-Path $WebDir 'node_modules\vite'))) {
    Write-Step 'Instalando dependencias de la web (npm ci)'
    Push-Location $WebDir
    try { npm ci --no-audit --no-fund; Assert-LastExit 'npm ci' } finally { Pop-Location }
  }
  Write-Ok 'Dependencias de la web'

  if (-not (Test-Path (Join-Path $PgData 'PG_VERSION'))) {
    Write-Step 'Inicializando el clúster de Postgres (locale ICU en-US, como producción)'
    & (Join-Path $PgBin 'initdb.exe') -D $PgData -U postgres --auth=trust -E UTF8 `
      --locale-provider=icu --icu-locale=en-US --locale=en-US | Out-Null
    Assert-LastExit 'initdb'
  }

  Start-Postgres
  $state = Join-Path $RuntimeDir 'state.json'
  if (-not (Test-Path $state) -or -not ((Get-Content $state -Raw) -match 'snapshot_at')) {
    Invoke-DbSetup
  } else {
    Write-Ok 'La base local ya existe (usa reset-db para reconstruirla)'
  }
  Write-Ok 'Setup completado. Siguiente: .\local-env\bct-local.ps1 start'
}

function Invoke-DbSetup {
  Write-Step 'Construyendo la base local (esquema + copia del catálogo de producción)'
  Invoke-WithEnv @{ PYTHONIOENCODING = 'utf-8'; PYTHONUTF8 = '1' } {
    & $VenvPy (Join-Path $PyDir 'db_setup.py')
  }
  Assert-LastExit 'db_setup.py'
}

function Start-Postgres {
  if (Test-Port $PgPort) { Write-Ok "Postgres en 127.0.0.1:$PgPort"; return }
  New-Item -ItemType Directory -Force $LogDir | Out-Null
  # Start-Process y no `& pg_ctl | Out-Null`: postgres hereda los handles de
  # salida de pg_ctl y la tubería de PowerShell no se cerraría nunca.
  $pgArgs = @('-D', "`"$PgData`"", '-l', "`"$(Join-Path $LogDir 'postgres.log')`"",
    '-o', "`"-p $PgPort -c listen_addresses=127.0.0.1 -c max_connections=200`"", 'start')
  Start-Process -FilePath (Join-Path $PgBin 'pg_ctl.exe') -ArgumentList $pgArgs -WindowStyle Hidden | Out-Null
  Wait-Port $PgPort 'Postgres' 60
  Write-Ok "Postgres en 127.0.0.1:$PgPort"
}

function Stop-Postgres {
  if (Test-Port $PgPort) {
    & (Join-Path $PgBin 'pg_ctl.exe') -D $PgData -m fast -w stop | Out-Null
    Write-Ok 'postgres parado'
  }
}

function Invoke-Start {
  if (-not (Test-Path $VenvPy) -or -not (Test-Path (Join-Path $PgData 'PG_VERSION'))) {
    throw 'Primero ejecuta: .\local-env\bct-local.ps1 setup'
  }
  $branch = git -C $Repo rev-parse --abbrev-ref HEAD
  Write-Step "Levantando el entorno local con la rama '$branch'"

  Start-Postgres

  $pyEnv = @{ PYTHONUNBUFFERED = '1'; PYTHONIOENCODING = 'utf-8'; PYTHONUTF8 = '1' }
  Start-Svc 'mail' $VenvPy @((Join-Path $PyDir 'mail_catcher.py'), '--smtp-port', $MailSmtpPort, '--web-port', $MailWebPort) $PyDir $pyEnv
  Wait-Port $MailSmtpPort 'Mail'
  Write-Ok "Correo local en http://localhost:$MailWebPort"

  Start-Svc 'authsync' $VenvPy @((Join-Path $PyDir 'auth_sync.py'), '--loop') $PyDir $pyEnv
  Write-Ok 'Sincronizador de usuarios en marcha'

  $apiArgs = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', $ApiPort)
  if (-not $NoReload) { $apiArgs += @('--reload', '--reload-dir', 'app') }
  Start-Svc 'api' $VenvPy $apiArgs $ApiDir (Get-ApiEnv)
  Wait-Port $ApiPort 'Api' 120
  Write-Ok "API en http://localhost:$ApiPort  (docs: http://localhost:$ApiPort/docs)"

  if (-not $NoWeb) {
    $webEnv = @{ VITE_API_URL = "http://localhost:$ApiPort"; LOCAL_API_PROXY_TARGET = '' }
    # node directo y no npm.cmd: cmd.exe tampoco admite directorios UNC.
    Start-Svc 'web' 'node' @('node_modules/vite/bin/vite.js', 'dev', '--port', "$WebPort", '--strictPort') `
      (Resolve-DrivePath $WebDir) $webEnv
    # En frío sobre el share, Vite tarda hasta ~3,5 min en abrir el puerto.
    Wait-Port $WebPort 'Web' 420
    Write-Ok "Web en http://localhost:$WebPort"
  }
  Write-Host ''
  Write-Host "Listo. Abre http://localhost:$WebPort · correos en http://localhost:$MailWebPort" -ForegroundColor Green
  Write-Host 'Para parar: .\local-env\bct-local.ps1 stop'
}

function Invoke-Stop {
  foreach ($s in @('web', 'api', 'authsync', 'mail')) { Stop-Svc $s }
  Stop-Postgres
}

function Invoke-Status {
  $rows = @(
    @{ Name = 'postgres'; Port = $PgPort; Url = "127.0.0.1:$PgPort/buenchollo_local" },
    @{ Name = 'mail'; Port = $MailWebPort; Url = "http://localhost:$MailWebPort" },
    @{ Name = 'authsync'; Port = 0; Url = '' },
    @{ Name = 'api'; Port = $ApiPort; Url = "http://localhost:$ApiPort/docs" },
    @{ Name = 'web'; Port = $WebPort; Url = "http://localhost:$WebPort" }
  )
  foreach ($r in $rows) {
    if ($r.Port) { $up = Test-Port $r.Port } else { $up = Test-Running $r.Name }
    if ($up) { $mark = 'UP  ' ; $color = 'Green' } else { $mark = 'DOWN'; $color = 'Red' }
    Write-Host ("{0}  {1,-9} {2}" -f $mark, $r.Name, $r.Url) -ForegroundColor $color
  }
  Write-Host "Rama: $(git -C $Repo rev-parse --abbrev-ref HEAD) · estado en $RuntimeDir"
}

function Show-Logs {
  if (-not $Service) { throw 'Indica el servicio: postgres | mail | authsync | api | web' }
  foreach ($f in @("$Service.log", "$Service.err.log")) {
    $p = Join-Path $LogDir $f
    if (Test-Path $p) { Write-Host "── $f" -ForegroundColor Cyan; Get-Content $p -Tail 60 }
  }
}

switch ($Command) {
  'setup' { Invoke-Setup }
  'start' { Invoke-Start }
  'stop' { Invoke-Stop }
  'restart' { Invoke-Stop; Invoke-Start }
  'status' { Invoke-Status }
  'reset-db' {
    foreach ($s in @('api', 'authsync')) { Stop-Svc $s }
    Start-Postgres
    Invoke-DbSetup
    Write-Ok 'Base reconstruida. Vuelve a levantar con: .\local-env\bct-local.ps1 start'
  }
  'logs' { Show-Logs }
  'qa' {
    Invoke-WithEnv @{ PYTHONIOENCODING = 'utf-8'; PYTHONUTF8 = '1' } {
      & $VenvPy -m pytest (Join-Path $LocalEnv 'qa') -v -rf --tb=short
    }
    Assert-LastExit 'qa'
  }
  'stress' {
    Invoke-WithEnv @{ PYTHONIOENCODING = 'utf-8'; PYTHONUTF8 = '1' } {
      & $VenvPy (Join-Path $LocalEnv 'qa\stress.py')
    }
    Assert-LastExit 'stress'
  }
  'users' {
    if (-not $Service) { throw 'Uso: users create [n] | users tokens | users delete' }
    $userArgs = @((Join-Path $PyDir 'test_users.py'), $Service)
    if ($Arg) { $userArgs += $Arg }
    Invoke-WithEnv @{ PYTHONIOENCODING = 'utf-8'; PYTHONUTF8 = '1' } { & $VenvPy @userArgs }
    Assert-LastExit "users $Service"
  }
  default { Get-Help $PSCommandPath -Detailed }
}
