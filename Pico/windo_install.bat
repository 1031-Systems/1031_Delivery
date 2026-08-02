@echo off
setlocal EnableDelayedExpansion

:: Go to the Pico directory where this script is located
pushd "%~dp0"

:: Run external script to link Pico to other tools
call winUsePico.bat

:: Check to make sure tabledefs has been created
echo Validating local tabledefs
..\.venv\Scripts\python.exe lib\tables.py >nul 2>&1
if errorlevel 1 (

    echo.
    echo Whoops - problems with tabledefs file - aborting
    echo Results of check are:
    ..\.venv\Scripts\python.exe lib\tables.py -r -v
    exit /b 1
)

endlocal
exit /b 0
