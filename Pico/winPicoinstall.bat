@echo off
setlocal EnableDelayedExpansion


:: Enter the virtual environment
echo Entering venv
pushd "%~dp0"
REM echo In: "%~dp0"
call ..\.venv\Scripts\activate

:: Check to make sure tabledefs has been created
:: echo.
echo Validating local tabledefs
..\.venv\Scripts\python.exe lib\tables.py >nul 2>&1
if errorlevel 1 (

    echo.
    echo Whoops - problems with tabledefs file - aborting
    echo Results of check are:
    python lib\tables.py -r -v
    pause
    exit /b 1
)

:: Determine which rshell to use
echo.
echo Checking rshell
where rshell >nul 2>&1
if errorlevel 1 (
    echo.
    echo Whoops - Unable to find rshell tool needed for installation
    pause
    exit /b 10
)

:: Get the port used by rshell
:: Note: This requires 'findstr' and basic parsing; adjust grep/sed logic as needed
for /f "tokens=*" %%L in ('rshell -l 2^>nul ^| findstr /i "2e8a:"') do (
    set "portline=%%L"
)
:: Extract port from line (text after @ and before next space)
for /f "tokens=2 delims=@" %%A in ("!portline!") do (
    for /f "tokens=1" %%B in ("%%A") do set "port=%%B"
)

if not defined port (
    echo.
    echo Whoops - No Pico found attached to system 
    echo rshell reports the following devices:
    call rshell -l
    echo.
    echo Aborting installation of software to Pico
    pause
    exit /b 0
) else (
    echo.
    echo Found Pico on port: !port!
)

echo.
set /p "answer=Do you want to remove all existing animations (y/N)? "
if /i "!answer!"=="y" (
    echo Removing existing animations (May take more than 1 minute^)
    call rshell --quiet rm "/pyboard/sd/anims/*"
    call rshell --quiet rm "/pyboard/anims/*"
)

echo.
echo Check for available Raspberry Pi-type device
call rshell -l

echo Prepping Pico filesystem
call rshell --quiet rm "/pyboard/boot.py" > nul 2>&1
call rshell --quiet repl "~ import machine ~ machine.reset() ~" > nul 2>&1
timeout /t 5 /nobreak >nul

echo.
echo Installing libraries
call rshell --quiet mkdir "/pyboard/lib" > nul 2>&1
call rshell --quiet mkdir "/pyboard/anims" > nul 2>&1
call rshell --quiet cp lib/servo.py lib/wave.py lib/pca9685.py lib/sdcard.py lib/memstats.py lib/tables.py lib/tabledefs lib/helpers.py lib/maestro.py "/pyboard/lib"

echo Installing main.py
call rshell --quiet cp main.py /pyboard

echo.
echo.
set /p "reply=Install demo/diagnostic animations (y/N): "
echo.

if /i "!reply!"=="y" (
    pushd anims
    for %%F in (*) do (
        call rshell --quiet cp "%%F" /pyboard/anims
    )
    popd
)

:: Check on the results
call rshell --quiet repl "~ import memstats ~" > nul 2>&1

:: Install boot.py last as rshell runs really slowly once it's there
echo.
echo Installing boot.py
call rshell --quiet cp boot.py /pyboard

:: Record the port locally for commlib to pick up
echo|set /p="!port!" > .portid

:: Reboot the Pico
echo Resetting Pico
call rshell --quiet repl "~ import machine ~ machine.reset() ~" > nul 2>&1
timeout /t 10 /nobreak >nul

:: Verify installation
echo.
echo Verifying installation
echo.

if exist ".\verifyload.exe" (
    .\verifyload -p !port!
) else (
    python verifyload.py -p !port!
)
if not errorlevel 1 (
    echo All python files validate
)

:: Validate installed diagnostic animations
if /i "!reply!"=="y" (
    echo.
    :: Build file list from anims\*
    set "animfiles="
    pushd anims
    for %%F in (*) do set "animfiles=!animfiles! anims/%%F"
    popd

    if exist ".\verifyload.exe" (
        .\verifyload -p !port! -fl !animfiles!
    ) else (
        python verifyload.py -p !port! -fl !animfiles!
    )
    if not errorlevel 1 (
        echo Diagnostic anim files validate
    )
)

pause
endlocal
exit /b 0

