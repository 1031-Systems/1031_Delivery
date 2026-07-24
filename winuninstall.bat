@echo off

setlocal enabledelayedexpansion

pushd "%~dp0"

:: No arguments
:: Get path to this script and thus to the install directory
set "SCRIPTPATH=%~dp0"
:: Remove trailing backslash
if "%SCRIPTPATH:~-1%"=="\" set "SCRIPTPATH=%SCRIPTPATH:~0,-1%"

echo Uninstalling %SCRIPTPATH%

:: Remove Windows desktop shortcuts that point to this repo
for %%a in ("%cd%") do set "LastDir=%%~nxa"
for %%f in ("%USERPROFILE%\Desktop\*.lnk") do (
    findstr /m /i "%SCRIPTPATH%" "%%f" >nul 2>&1
    if not errorlevel 1 (
        del /f "%%f"
    )
)

:: Delete everything (move up one directory first, then delete)
cd /d "%SCRIPTPATH%\.."
rd /s /q "%SCRIPTPATH%"
