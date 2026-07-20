@echo off
setlocal EnableDelayedExpansion

goto :main

:usage
    echo.
    echo Usage: %~nx0 [-/-h/-help] [-v/-verbose]
    echo     This tool installs all the code on the Pico.
    echo -/-h/-help          :Print this helpful info
    echo -v/-verbose         :Run more verbosely
    echo.
    goto :eof

:main
:: Set initial/default values
set "out=nul"
set "verbose=0"

:: Parse arguments
:parse_args
if "%~1"=="" goto :done_parsing
    echo Processing arg:%~1
    if "%~1"=="-" (
        call :usage
    ) else if "%~1"=="-h" (
        call :usage
    ) else if "%~1"=="-help" (
        call :usage
    ) else if "%~1"=="-v" (
        set "out=CON"
        set "verbose=1"
    ) else if "%~1"=="-verbose" (
        set "out=CON"
        set "verbose=1"
    ) else (
        echo.
        echo Whoops - Unrecognized argument:%~1
        call :usage
    )
    shift
    goto :parse_args
:done_parsing

:: Enter the virtual environment
echo Entering venv
pushd "%~dp0"
echo In: "%~dp0"
call ..\.venv\Scripts\activate

:: Make needed symlink with external script
call winUsePico.bat

:: Check to make sure tabledefs has been created
echo Validating local tabledefs
..\.venv\Scripts\python.exe lib\tables.py >nul 2>&1
if errorlevel 1 (

    echo.
    echo Whoops - problems with tabledefs file - aborting
    echo Results of check are:
    python lib\tables.py -r -v
    exit /b 1
)

:: Determine which rshell to use
echo Checking rshell
set "rshell=rshell"
where rshell >nul 2>&1
if errorlevel 1 (
    if exist "..\rshell.exe" (
        set "rshell=..\rshell"
    ) else if exist "..\rshell" (
        set "rshell=..\rshell"
    ) else if exist ".\rshell.exe" (
        set "rshell=.\rshell"
    ) else if exist ".\rshell" (
        set "rshell=.\rshell"
    ) else (
        echo Whoops - Unable to find rshell tool needed for installation
        exit /b 10
    )
)

:: Get the port used by rshell
:: Note: This requires 'findstr' and basic parsing; adjust grep/sed logic as needed
for /f "tokens=*" %%L in ('!rshell! -l 2^>nul ^| findstr /i "2e8a:"') do (
    set "portline=%%L"
)
:: Extract port from line (text after @ and before next space)
for /f "tokens=2 delims=@" %%A in ("!portline!") do (
    for /f "tokens=1" %%B in ("%%A") do set "port=%%B"
)
if "!verbose!"=="1" echo Using port: !port!

set /p "answer=Do you want to remove all existing animations (y/N)? "
if /i "!answer!"=="y" (
    echo Removing existing animations (May take more than 1 minute^)
    call !rshell! --quiet rm "/pyboard/sd/anims/*"
    call !rshell! --quiet rm "/pyboard/anims/*"
)

echo Check for available Raspberry Pi-type device
call !rshell! -l

echo Prepping Pico filesystem
call !rshell! --quiet rm /pyboard/boot.py >!out! 2>&1
call !rshell! --quiet repl "~ import machine ~ machine.reset() ~" >!out! 2>&1
timeout /t 5 /nobreak >nul

echo Installing libraries
call !rshell! --quiet mkdir /pyboard/lib >!out! 2>&1
call !rshell! --quiet mkdir /pyboard/anims >!out! 2>&1
call !rshell! --quiet cp lib/servo.py lib/wave.py lib/pca9685.py lib/sdcard.py lib/memstats.py lib/tables.py lib/tabledefs lib/helpers.py lib/maestro.py /pyboard/lib

echo Installing main.py
call !rshell! --quiet cp main.py /pyboard

echo.
echo.
set /p "reply=Install demo/diagnostic animations (y/N): "
echo.

if /i "!reply!"=="y" (
    pushd anims
    for %%F in (*) do (
        call !rshell! --quiet cp "%%F" /pyboard/anims
    )
    popd
)

:: Check on the results
call !rshell! --quiet repl "~ import memstats ~" >!out! 2>&1

:: Install boot.py last as rshell runs really slowly once it's there
echo Installing boot.py
call !rshell! --quiet cp boot.py /pyboard

:: Record the port locally for commlib to pick up
echo|set /p="!port!" > .portid

:: Reboot the Pico
echo Resetting Pico
call !rshell! --quiet repl "~ import machine ~ machine.reset() ~" >!out! 2>&1
timeout /t 5 /nobreak >nul

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

endlocal
exit /b 0

