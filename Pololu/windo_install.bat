@echo off
setlocal

pushd "%~dp0"

:: Run external script to link Pololu to other tools
call winUsePololu.bat

:: Check to make sure tabledefs has been created
echo Validating local tabledefs
..\.venv\Scripts\python.exe lib\tables.py -r >nul 2>&1
set CODE=%ERRORLEVEL%

if %CODE% GTR 1 (
    echo.
    echo Whoops - problems with tabledefs file - aborting
    echo Results of check are:
    ..\.venv\Scripts\python.exe lib\tables.py -r -v
    exit /b 1
)

endlocal
exit /b 0

