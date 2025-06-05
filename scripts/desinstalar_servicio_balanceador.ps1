$NSSMPath = "C:\Tools\nssm\nssm.exe"
$ServiceName = "SAMBalanceadorService"

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service $ServiceName -Force
    & $NSSMPath remove $ServiceName confirm
    Write-Host "Servicio $ServiceName eliminado." -ForegroundColor Yellow
} else {
    Write-Host "El servicio $ServiceName no existe." -ForegroundColor Red
}
