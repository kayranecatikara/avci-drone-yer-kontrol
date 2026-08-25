param(
    [switch]$Launcher,
    [string]$PencereArgs = "-windowed -ResX=1280 -ResY=720"
)

$ErrorActionPreference = "Stop"

$Root       = Split-Path -Parent $PSScriptRoot
$Path = Join-Path $Root "Drones of War Teknofest"
$Shipping  = Join-Path $Path "DronesOfWar\Binaries\Win64\DronesOfWar-Win64-Shipping.exe"
$LauncherExe = Join-Path $Path "DronesOfWar.exe"

if ($Launcher) {
    $Exe  = $LauncherExe
    $Args = @()
} else {
    $Exe  = $Shipping
    $Args = $PencereArgs.Split(" ") | Where-Object { $_ -ne "" }
}

if (-not (Test-Path $Exe)) {
    Write-Output "Error (Game is not found): $Exe"
    exit 1
}

Write-Output "============================================================"
Write-Output "  DRONES OF WAR - Starting "
Write-Output "  Run: $Exe $($Args -join ' ')"
Write-Output "============================================================"

Start-Process -FilePath $Exe -ArgumentList $Args -WorkingDirectory (Split-Path -Parent $Exe)
