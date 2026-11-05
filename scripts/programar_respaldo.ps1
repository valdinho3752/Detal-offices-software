# Programa la copia de seguridad diaria en el Programador de tareas de Windows.
# Ejecutar en el servidor de la clínica, en PowerShell como administrador:
#   .\scripts\programar_respaldo.ps1 -Carpeta "D:\RespaldosClinica" -Hora "21:00"
param(
    [Parameter(Mandatory = $true)][string]$Carpeta,
    [string]$Hora = "21:00",
    [int]$Conservar = 30
)

$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz "venv\Scripts\python.exe"
$script = Join-Path $raiz "scripts\respaldar.py"

$accion = New-ScheduledTaskAction -Execute $python -Argument "`"$script`" --carpeta `"$Carpeta`" --conservar $Conservar" -WorkingDirectory $raiz
$disparador = New-ScheduledTaskTrigger -Daily -At $Hora
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

Register-ScheduledTask -TaskName "ClinicaDental-Respaldo" -Action $accion -Trigger $disparador -Settings $opciones -User "SYSTEM" -RunLevel Highest -Force
Write-Output "Copia diaria programada a las $Hora en $Carpeta"
