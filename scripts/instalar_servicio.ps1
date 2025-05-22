# Configuraciones
$NSSMPath = "C:\Tools\nssm\nssm.exe"
$ServiceName = "SAM Lanzador"
$PythonPath = "C:\RPA\rpa_sam\venv\Scripts\python.exe"
$ScriptPath = "C:\RPA\rpa_sam\lanzador\service\main.py"
$WorkingDir = "C:\RPA\rpa_sam\lanzador"

# Verifica que NSSM exista
if (-Not (Test-Path $NSSMPath)) {
    Write-Host "ERROR: No se encontró NSSM en $NSSMPath" -ForegroundColor Red
    exit 1
}

# Crea el servicio
& $NSSMPath install $ServiceName $PythonPath $ScriptPath
& $NSSMPath set $ServiceName AppDirectory $WorkingDir
& $NSSMPath set $ServiceName Start SERVICE_AUTO_START

# Inicia el servicio
Start-Service $ServiceName

Write-Host "Servicio $ServiceName instalado y ejecutándose." -ForegroundColor Green
