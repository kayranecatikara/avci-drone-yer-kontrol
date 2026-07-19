@echo off
title Talon UAV - Keypoint Editor
cd /d "%~dp0"
echo.
echo  =========================================
echo   TALON UAV - Keypoint Editor
echo  =========================================
echo   Dataset: dataset\
echo   Edited output: dataset_edited\
echo  =========================================
echo.
python keypoint_editor.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python returned error code %errorlevel%
    echo Make sure Python and Pillow are installed:
    echo   pip install pillow
    pause
)
