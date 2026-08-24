# ============================================================
#  DRONES OF WAR - simulasyon oyununu baslatir (WINDOWS)
# ------------------------------------------------------------
#  Bu script YALNIZCA oyunu acar. Gorev baslatma isi bu scriptin
#  isi degildir; yer kontrol arayuzunden yapilir (web/).
#
#  Linux karsiligi: scripts/start_game.sh (Wine ile). Windows'ta
#  oyun native .exe oldugundan Wine YOKTUR; ayni exe dogrudan
#  calistirilir. Iki script de AYNI binary'yi, AYNI argumanlarla
#  baslatir; farki yalnizca calistirma katmanidir.
#
#  Oyun acilinca PLAY moduna gecmeyi unutma.
#
#  PENCERE MODU: kamera hatti (perception/camera.py) EKRANI yakalar
#  (mss). Oyun penceresi GORUNUR/ONDE kalmali; KENARLIKSIZ PENCERE
#  modu en saglikli sonucu verir.
#
#  NEDEN LAUNCHER DEGIL SHIPPING EXE:
#  Kok dizindeki "DronesOfWar.exe" bir launcher; once
#  Engine/Extras/Redist/en-us/UEPrereqSetup_x64.exe calistirir.
#  Windows'ta bu genelde sorunsuzdur (Linux/Wine'daki 32-bit
#  ntdll hatasi burada yok), ama gereksiz bir kurulum adimidir.
#  Varsayilan olarak asil oyun binary'sini dogrudan baslatiyoruz.
#  Launcher'i denemek istersen:  .\scripts\start_game.ps1 -Launcher
#
#  Calistirma politikasi hatasi alirsan (script imzasiz):
#      powershell -ExecutionPolicy Bypass -File .\scripts\start_game.ps1
# ============================================================
param(
    [switch]$Launcher,
    # Pencere modu / cozunurluk (istersen ez):
    #   .\scripts\start_game.ps1 -PencereArgs "-fullscreen"
    [string]$PencereArgs = "-windowed -ResX=1280 -ResY=720"
)

$ErrorActionPreference = "Stop"

$Kok       = Split-Path -Parent $PSScriptRoot          # depo koku
$OyunDizin = Join-Path $Kok "Drones of War Teknofest"
$Shipping  = Join-Path $OyunDizin "DronesOfWar\Binaries\Win64\DronesOfWar-Win64-Shipping.exe"
$LauncherExe = Join-Path $OyunDizin "DronesOfWar.exe"

if ($Launcher) {
    $Exe  = $LauncherExe
    $Args = @()
    Write-Output "NOT: launcher modu -- once UE prereq kurucusu calisabilir."
} else {
    $Exe  = $Shipping
    $Args = $PencereArgs.Split(" ") | Where-Object { $_ -ne "" }
}

if (-not (Test-Path $Exe)) {
    Write-Output "HATA: Oyun bulunamadi: $Exe"
    Write-Output "      Yarisma paketini repo kokune 'Drones of War Teknofest' klasoru olacak sekilde cikart (README)."
    exit 1
}

Write-Output "============================================================"
Write-Output "  DRONES OF WAR - baslatiliyor (Windows, native)..."
Write-Output "  Calistirilan: $Exe $($Args -join ' ')"
Write-Output "  Oyun acilinca PLAY moduna gecmeyi unutma."
Write-Output "============================================================"

# Oyunun kendi klasorunden calismasi gerekir (UE goreli yol kullanir).
Start-Process -FilePath $Exe -ArgumentList $Args -WorkingDirectory (Split-Path -Parent $Exe)
