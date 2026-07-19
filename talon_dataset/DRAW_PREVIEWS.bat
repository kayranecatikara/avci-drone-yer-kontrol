@echo off
title Talon UAV - Draw Annotated Previews
cd /d "%~dp0"
echo.
echo  =========================================
echo   TALON UAV - Draw Keypoint Previews
echo  =========================================
echo   Reads from: dataset\
echo   Writes to : dataset_annotated\
echo  =========================================
echo.
python draw_keypoints.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] draw_keypoints.py failed. Check Python/Pillow.
    pause
) else (
    echo.
    echo  Done! Check dataset_annotated\ for results.
    echo.
    pause
)
