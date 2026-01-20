# =========================
# FUNCIÓN PARA CARGAR .env
# =========================
function Load-EnvFile {
    param(
        [string]$Path = ".env"
    )

    if (-not (Test-Path $Path)) {
        throw "Archivo $Path no encontrado"
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()

        # Ignorar líneas vacías y comentarios
        if ($line -eq "" -or $line.StartsWith("#")) {
            return
        }

        # Debe contener =
        if ($line -notmatch "=") {
            return
        }

        $parts = $line.Split("=", 2)
        $name = $parts[0].Trim()
        $value = $parts[1]

        if ([string]::IsNullOrWhiteSpace($name)) {
            return
        }

        # Permitir variables vacías, pero no null
        if ($null -eq $value) {
            $value = ""
        }

        [System.Environment]::SetEnvironmentVariable(
            $name,
            $value.Trim(),
            "Process"
        )
    }
}


# =========================
# CARGAR VARIABLES
# =========================
Load-EnvFile "database/.env"

# Validar
$required = "SQL_SERVER", "SQL_DATABASE", "SQL_USER", "SQL_PASSWORD"
foreach ($v in $required) {
    if (-not [System.Environment]::GetEnvironmentVariable($v)) {
        throw "Variable $v no cargada"
    }
}

# =========================
# CONFIG
# =========================
$ServerName = $env:SQL_SERVER
$DatabaseName = $env:SQL_DATABASE
$OutputDir = ".\database"

Import-Module SqlServer -ErrorAction Stop

# =========================
# CONEXIÓN
# =========================
$server = New-Object Microsoft.SqlServer.Management.Smo.Server $ServerName

# ESTO ES CLAVE
$server.ConnectionContext.LoginSecure = $false
$server.ConnectionContext.Login = $env:SQL_USER
$server.ConnectionContext.Password = $env:SQL_PASSWORD

# (opcional pero recomendado)
$server.ConnectionContext.DatabaseName = "master"

try {
    $server.ConnectionContext.Connect()
    Write-Host "Conectado a SQL Server correctamente"
}
catch {
    Write-Error "Error de conexión: $($_.Exception.Message)"
    exit 1
}



$db = $server.Databases[$DatabaseName]
if (-not $db) {
    $server.Databases | ForEach-Object { Write-Host "DB:" $_.Name }

    throw "No se encontró la base $DatabaseName"
}

# =========================
# OPCIONES (SSMS LIKE)
# =========================
$options = New-Object Microsoft.SqlServer.Management.Smo.ScriptingOptions

# General
$options.AnsiPadding = $true
$options.IncludeIfNotExists = $true
$options.SchemaQualify = $true
$options.SchemaQualifyForeignKeysReferences = $true
$options.ScriptBatchTerminator = $true
$options.NoCollation = $true

# Qué scriptar
$options.ScriptDrops = $false   # CREATE (por default)
$options.Indexes = $true
$options.Triggers = $true
$options.DriPrimaryKey = $true
$options.DriForeignKeys = $true
$options.DriUniqueKeys = $true
$options.DriChecks = $true
$options.ExtendedProperties = $true
$options.Permissions = $true

# Qué NO scriptar
$options.FullTextIndexes = $false
$options.ChangeTracking = $false
# $options.DataCompression          = $false
$options.XmlIndexes = $false

# =====================================
# FUNCIÓN DE EXPORTACIÓN
# =====================================
function Script-Objects {
    param ($Objects, $Folder)

    $path = Join-Path $OutputDir $Folder
    New-Item -ItemType Directory -Force -Path $path | Out-Null

    $count = 0
    foreach ($obj in $Objects | Where-Object { -not $_.IsSystemObject }) {
        $file = "$path\$($obj.Schema)_$($obj.Name).sql"
        try {
            $scriptCollection = $obj.Script($options)
            if ($scriptCollection) {
                # Unir todo en un solo string
                $text = $scriptCollection -join "`r`n"

                # 1. Agregar GO después de SET ANSI_NULLS ON
                $text = $text -replace "(SET ANSI_NULLS ON)", "`$1`r`nGO"

                # 2. Agregar GO después de SET QUOTED_IDENTIFIER ON
                $text = $text -replace "(SET QUOTED_IDENTIFIER ON)", "`$1`r`nGO"

                # 3. Agregar GO entre el bloque idempotente (END) y el ALTER/CREATE
                #    Busca "END" seguido de saltos de línea y luego "ALTER" o "CREATE"
                $text = $text -replace "(?ms)^END\s+(ALTER|CREATE)", "END`r`nGO`r`n`$1"

                # 4. Asegurar GO al final
                if (-not $text.Trim().EndsWith("GO")) {
                    $text += "`r`nGO"
                }

                $text | Out-File $file -Encoding UTF8
                $count++
            }
        }
        catch {
            Write-Warning "Error al exportar $($obj.Schema).$($obj.Name): $($_.Exception.Message)"
        }
    }
    return $count
}

# =====================================
# EXPORTAR
# =====================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "EXPORTANDO ESTRUCTURA DE BASE DE DATOS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Base de datos: $DatabaseName" -ForegroundColor Yellow
Write-Host "Directorio: $OutputDir" -ForegroundColor Yellow
Write-Host ""

$startTime = Get-Date

Write-Host "Exportando tablas..." -ForegroundColor Green
$tableCount = ($db.Tables | Where-Object { -not $_.IsSystemObject }).Count
Script-Objects $db.Tables "tables"
Write-Host "   $tableCount tablas exportadas" -ForegroundColor Gray

Write-Host "Exportando vistas..." -ForegroundColor Green
$viewCount = ($db.Views | Where-Object { -not $_.IsSystemObject }).Count
Script-Objects $db.Views "views"
Write-Host "   $viewCount vistas exportadas" -ForegroundColor Gray

Write-Host "Exportando stored procedures..." -ForegroundColor Green
$procCount = ($db.StoredProcedures | Where-Object { -not $_.IsSystemObject }).Count
Script-Objects $db.StoredProcedures "procedures"
Write-Host "   $procCount procedimientos exportados" -ForegroundColor Gray

Write-Host "Exportando funciones..." -ForegroundColor Green
$funcCount = ($db.UserDefinedFunctions | Where-Object { -not $_.IsSystemObject }).Count
Script-Objects $db.UserDefinedFunctions "functions"
Write-Host "   $funcCount funciones exportadas" -ForegroundColor Gray

Write-Host "Exportando triggers..." -ForegroundColor Green
$triggerCount = ($db.Triggers | Where-Object { -not $_.IsSystemObject }).Count
Script-Objects $db.Triggers "triggers"
Write-Host "   $triggerCount triggers exportados" -ForegroundColor Gray

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "EXPORT FINALIZADO CORRECTAMENTE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tiempo total: $($duration.TotalSeconds.ToString("F2")) segundos" -ForegroundColor Gray
Write-Host "Total objetos: $($tableCount + $viewCount + $procCount + $funcCount + $triggerCount)" -ForegroundColor Gray
Write-Host ""
