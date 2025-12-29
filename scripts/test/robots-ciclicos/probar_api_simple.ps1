# Script PowerShell para probar la API de programaciones cíclicas
# Ejecutar: .\probar_api_simple.ps1

$baseUrl = "http://localhost:8000"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PRUEBA DE API: Robots Cíclicos con Ventanas" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que el servidor esté disponible
Write-Host "Verificando servidor..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/docs" -Method GET -TimeoutSec 5 -UseBasicParsing
    Write-Host "[OK] Servidor web disponible" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] No se pudo conectar a $baseUrl" -ForegroundColor Red
    Write-Host "Asegurate de que el servicio web esté corriendo." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Obtener RobotId y EquipoId válidos
Write-Host "Obteniendo robots y equipos disponibles..." -ForegroundColor Yellow
$robotId = 1
$equipoId = 1

try {
    $robotsResponse = Invoke-RestMethod -Uri "$baseUrl/api/robots" -Method GET -TimeoutSec 5
    if ($robotsResponse -is [array] -and $robotsResponse.Count -gt 0) {
        $robotId = $robotsResponse[0].RobotId
        Write-Host "[OK] Usando RobotId: $robotId" -ForegroundColor Green
    } elseif ($robotsResponse.robots -is [array] -and $robotsResponse.robots.Count -gt 0) {
        $robotId = $robotsResponse.robots[0].RobotId
        Write-Host "[OK] Usando RobotId: $robotId" -ForegroundColor Green
    } else {
        Write-Host "[ADVERTENCIA] No se pudieron obtener robots, usando RobotId: $robotId" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ADVERTENCIA] No se pudieron obtener robots, usando RobotId: $robotId" -ForegroundColor Yellow
}

try {
    $equiposResponse = Invoke-RestMethod -Uri "$baseUrl/api/devices" -Method GET -TimeoutSec 5
    if ($equiposResponse -is [array] -and $equiposResponse.Count -gt 0) {
        $equipoId = $equiposResponse[0].EquipoId
        Write-Host "[OK] Usando EquipoId: $equipoId" -ForegroundColor Green
    } elseif ($equiposResponse.devices -is [array] -and $equiposResponse.devices.Count -gt 0) {
        $equipoId = $equiposResponse.devices[0].EquipoId
        Write-Host "[OK] Usando EquipoId: $equipoId" -ForegroundColor Green
    } else {
        Write-Host "[ADVERTENCIA] No se pudieron obtener equipos, usando EquipoId: $equipoId" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ADVERTENCIA] No se pudieron obtener equipos, usando EquipoId: $equipoId" -ForegroundColor Yellow
}

Write-Host ""

# Prueba 1: Programación cíclica simple
Write-Host "PRUEBA 1: Programación Cíclica Simple" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Cyan

$body1 = @{
    RobotId = $robotId
    TipoProgramacion = "Diaria"
    HoraInicio = "09:00:00"
    HoraFin = "17:00:00"
    Tolerancia = 15
    Equipos = @($equipoId)
    EsCiclico = $true
    IntervaloEntreEjecuciones = 30
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/schedules" -Method POST -Body $body1 -ContentType "application/json"
    Write-Host "[OK] Programación cíclica creada exitosamente!" -ForegroundColor Green
    Write-Host "Respuesta: $($response | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] No se pudo crear la programación" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
}

Write-Host ""

# Prueba 2: Programación cíclica con ventana de fechas
Write-Host "PRUEBA 2: Programación Cíclica con Ventana de Fechas" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Cyan

$body2 = @{
    RobotId = $robotId
    TipoProgramacion = "Semanal"
    DiasSemana = "Lun,Mar,Mie,Jue,Vie"
    HoraInicio = "08:00:00"
    HoraFin = "18:00:00"
    Tolerancia = 10
    Equipos = @($equipoId)
    EsCiclico = $true
    FechaInicioVentana = "2025-01-01"
    FechaFinVentana = "2025-12-31"
    IntervaloEntreEjecuciones = 60
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/schedules" -Method POST -Body $body2 -ContentType "application/json"
    Write-Host "[OK] Programación cíclica con fechas creada exitosamente!" -ForegroundColor Green
    Write-Host "Respuesta: $($response | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] No se pudo crear la programación" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
}

Write-Host ""

# Prueba 3: Retrocompatibilidad
Write-Host "PRUEBA 3: Retrocompatibilidad (Programación Tradicional)" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Cyan

$body3 = @{
    RobotId = $robotId
    TipoProgramacion = "Diaria"
    HoraInicio = "10:00:00"
    Tolerancia = 15
    Equipos = @($equipoId)
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/schedules" -Method POST -Body $body3 -ContentType "application/json"
    Write-Host "[OK] Programación tradicional creada exitosamente!" -ForegroundColor Green
    Write-Host "Respuesta: $($response | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] No se pudo crear la programación" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PRUEBAS COMPLETADAS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

