@echo off
setlocal EnableDelayedExpansion

:: Go to the Pico directory where this script is located
pushd "%~dp0"

:: Enter the virtual environment
REM echo In: "%~dp0"
call ..\.venv\Scripts\activate

:: Check to make sure tabledefs has been created
echo Validating local tabledefs
python lib\tables.py >nul 2>&1
if errorlevel 1 (

    echo.
    echo Whoops - problems with tabledefs file - aborting
    echo Results of check are:
    python lib\tables.py -r -v
    exit /b 1
)

echo.
echo tabledefs file appears valid
echo.

:: Install tabledefs file only
call rshell --quiet cp lib/tabledefs "/pyboard/lib"

if errorlevel 1 (
    echo.
    echo Installation failed
) else (
    echo.
    echo Installation of table definitions file appears successful
)
echo.

:: Restart the Pico
echo Restarting Pico
call rshell --quiet repl "~ import machine ~ machine.reset() ~" > nul 2>&1
pause

endlocal
exit /b 0
