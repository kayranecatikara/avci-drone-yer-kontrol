@echo off
title Talon UAV - Export Edited Frames to ZIP
cd /d "%~dp0"
echo.
echo  =========================================
echo   TALON UAV - Manual ZIP Export
echo  =========================================
echo.

if not exist "dataset_edited" (
    echo [ERROR] dataset_edited folder not found!
    echo  Run the Keypoint Editor and save some frames first.
    echo.
    pause
    exit /b 1
)

:: Count JSON files
for /f %%A in ('dir /b /a-d "dataset_edited\*.json" 2^>nul ^| find /c /v ""') do set COUNT=%%A

if "%COUNT%"=="0" (
    echo [ERROR] No .json files found in dataset_edited\
    echo  Save at least one frame in the editor first.
    echo.
    pause
    exit /b 1
)

echo  Found %COUNT% annotated frames.
echo.

:: Build timestamped ZIP name
for /f "tokens=1-6 delims=/ " %%a in ('echo %date% %time%') do (
    set YY=%%a
    set MM=%%b
    set DD=%%c
    set HH=%%d
    set MN=%%e
)
set HH=%HH: =0%
set ZIPNAME=talon_edited_export_%YY%%MM%%DD%_%HH%%MN%.zip

echo  Creating: %ZIPNAME%
echo.

python -c "
import zipfile, os, datetime
edited_dir = 'dataset_edited'
ts = datetime.datetime.now().strftime('%%Y%%m%%d_%%H%%M%%S')
zname = f'talon_edited_export_{ts}.zip'
files = [f for f in os.listdir(edited_dir) if f.endswith(('.json','.png','.txt'))]
with zipfile.ZipFile(zname, 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(files):
        zf.write(os.path.join(edited_dir, f), arcname=os.path.join('dataset_edited', f))
n = len([f for f in files if f.endswith('.json')])
print(f'[OK] Exported {n} frames → {zname}')
"

if %errorlevel% equ 0 (
    echo.
    echo  =========================================
    echo   ZIP export complete!
    echo  =========================================
) else (
    echo.
    echo [ERROR] ZIP creation failed. Is Python installed?
)

echo.
pause
