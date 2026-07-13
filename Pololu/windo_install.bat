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

REM Run external script to make symlink last
winUsePololu

