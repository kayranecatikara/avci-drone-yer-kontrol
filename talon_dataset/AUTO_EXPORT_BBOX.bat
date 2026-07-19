@echo off
title Talon UAV - Auto BBox Export
cd /d "%~dp0"
echo.
echo  =========================================
echo   TALON UAV - Automatic Bounding Box Export
echo  =========================================
echo   Calculates Bounding Boxes mathematically
echo   from telemetry and exports them directly.
echo  =========================================
echo.
python auto_export_bbox.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Export failed!
    pause
) else (
    echo.
    echo  Export successful! Check the dataset_auto_bbox folder.
    pause
)
