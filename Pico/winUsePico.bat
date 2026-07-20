@echo off
setlocal enabledelayedexpansion

pushd "%~dp0"

REM Convert directory path to python-friendly form
set pydir=%~dp0
set pydir=!pydir:\=/!

REM Create short python file that adds this directory to the Python path
echo import sys > "%~dp0..\src\pointer.py"
echo. >> "%~dp0..\src\pointer.py"
echo sys.path.append("%pydir%") >> "%~dp0..\src\pointer.py"
echo. >> "%~dp0..\src\pointer.py"
echo useHardware = "Pico" >> "%~dp0..\src\pointer.py"

exit /b
