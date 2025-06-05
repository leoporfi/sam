# Configuraciones
$NSSMPath = "C:\Tools\nssm\nssm.exe"
$ServiceName = "SAMLanzadorService"
$PythonPath = "C:\RPA\sam\.venv\Scripts\python.exe"
$ScriptPath = "-m lanzador.service.main"
$WorkingDir = "C:\RPA\sam"

# Verifica que NSSM exista
if (-Not (Test-Path $NSSMPath)) {
    Write-Host "ERROR: No se encontró NSSM en $NSSMPath" -ForegroundColor Red
    exit 1
}

# Crea el servicio
& $NSSMPath install $ServiceName $PythonPath $ScriptPath
& $NSSMPath set $ServiceName AppDirectory $WorkingDir
& $NSSMPath set $ServiceName Start SERVICE_AUTO_START
& $NSSMPath set $ServiceName DisplayName "SAM Lanzador Service"
& $NSSMPath set $ServiceName Description "Servicio para lanzar la aplicación SAM"



# Inicia el servicio
Start-Service $ServiceName

Write-Host "Servicio $ServiceName instalado y ejecutándose." -ForegroundColor Green
