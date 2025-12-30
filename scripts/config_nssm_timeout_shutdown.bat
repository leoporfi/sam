@echo off
REM ============================================================
REM Script MODIFICADO para configurar timeouts de NSSM
REM Acepta el nombre del servicio como argumento.
REM Ejecutar como Administrador
REM ============================================================

SET SERVICE_NAME=%1

REM --- Validacion de argumento ---
IF "%SERVICE_NAME%"=="" (
    echo [ERROR] No se proporciono un nombre de servicio.
    echo.
    echo MODO DE USO: %0 [nombre_del_servicio]
    echo EJEMPLO:   %0 sam_lanzador
    GOTO :EOF
)

echo Configurando timeouts para el servicio: %SERVICE_NAME%...
echo.

REM --- Inicio de Configuracion (copiado del original) ---

REM Timeout para Ctrl+C (Console) - 30 segundos
nssm set %SERVICE_NAME% AppStopMethodConsole 30000
echo [OK] Timeout Console (Ctrl+C): 30 segundos

REM Timeout para mensaje WM_CLOSE (Window) - 30 segundos
nssm set %SERVICE_NAME% AppStopMethodWindow 30000
echo [OK] Timeout Window (WM_CLOSE): 30 segundos

REM Timeout antes de enviar WM_QUIT - 1.5 segundos
nssm set %SERVICE_NAME% AppStopMethodThreads 1500
echo [OK] Timeout Threads (WM_QUIT): 1.5 segundos

REM No usar TerminateProcess inmediatamente (0 = esperar)
nssm set %SERVICE_NAME% AppKillProcessTree 0
echo [OK] KillProcessTree: deshabilitado (espera señales)

REM Configurar rotación de logs (opcional)
nssm set %SERVICE_NAME% AppStdoutCreationDisposition 4
nssm set %SERVICE_NAME% AppStderrCreationDisposition 4
echo [OK] Rotacion de logs configurada

REM Reinicio automático en caso de fallo
nssm set %SERVICE_NAME% AppExit Default Restart
nssm set %SERVICE_NAME% AppRestartDelay 5000
echo [OK] Reinicio automatico: habilitado (5 seg delay)

echo.
echo ============================================================
echo Configuracion completa para %SERVICE_NAME%. Verificando...
echo ============================================================
echo.
nssm status %SERVICE_NAME%
nssm dump %SERVICE_NAME%

echo.
echo Proceso finalizado.

:EOF
