# Configuraciones
$NSSMPath = "C:\Tools\nssm\nssm.exe"
$ServiceName = "SAMCallbackServer"
$PythonPath = "C:\RPA\sam\.venv\Scripts\python.exe"
$ScriptPath = "-m lanzador.service.callback_server"
$WorkingDir = "C:\RPA\sam"

# Verifica que NSSM exista
if (-Not (Test-Path $NSSMPath)) {
    Write-Host "ERROR: No se encontró NSSM en $NSSMPath" -ForegroundColor Red
    exit 1
}

# Crea el servicio
& $NSSMPath install $ServiceName $PythonPath $ScriptPath
& $NSSMPath set $ServiceName AppDirectory $WorkingDir
# & $NSSMPath set $ServiceName AppStdout C:\RPA\sam\logs\callback_service.log
# & $NSSMPath set $ServiceName AppStderr C:\RPA\sam\logs\callback_service_error.log
& $NSSMPath set $ServiceName Description "Servicio para el servidor de callbacks de SAM"
& $NSSMPath set $ServiceName DisplayName "SAM Callback Server Service"
& $NSSMPath set $ServiceName Start SERVICE_AUTO_START

# Inicia el servicio
Start-Service $ServiceName

Write-Host "Servicio $ServiceName instalado y ejecutándose." -ForegroundColor Green
