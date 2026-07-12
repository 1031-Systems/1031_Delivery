@echo off
setlocal

pushd "%~dp0"

echo Validating local tabledefs
..\.venv\Scripts\python.exe lib\tables.py -r >nul 2>&1
set CODE=%ERRORLEVEL%

if %CODE% GTR 1 (
    echo.
    echo Whoops - problems with tabledefs file - aborting
    echo Results of check are:
    ..\.venv\Scripts\python.exe lib\tables.py -r -v
    exit /b
)

REM ----------------------------------------------------------------
REM Making the symlink requires admin rights on Windows.
REM Request elevation now, immediately before the delete/link step.
REM ----------------------------------------------------------------

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList 'elevated' -Verb RunAs"

    exit /b
)

REM Delete the old link to commlib in the src directory
del /f /q "%~dp0..\src\commlib.py"
REM Make the new link to commlib in the src directory
mklink "%~dp0..\src\commlib.py" "%~dp0commlib.py"

exit /b

