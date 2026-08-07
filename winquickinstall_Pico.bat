setlocal enabledelayedexpansion

@ECHO off

REM Save error status for multiple commands
set errorstatus=0

REM Go to the install directory
pushd "%~dp0\.."

REM Run in a parenthesis block so it continues to run
REM after renaming directory.
(

REM Remove any existing installation of the same name
call .\Pico_Hauntimator\winuninstall.bat >nul 2>&1

REM Rename unzipped directory to be hardware specific
ren 1031_Hauntimator Pico_Hauntimator

REM Run the install batch file
cd Pico_Hauntimator
call .\wininstall.bat Pico
if !errorlevel! NEQ 0 ( set errorstatus=1 )

REM Use a reasonable tabledefs file
cd Pico\lib
copy tabledefs.basic tabledefs

REM Run the Pico-specific install file
cd ..
call .\windo_install.bat
if !errorlevel! NEQ 0 ( set errorstatus=1 )

cd ..

REM Clean up unused install scripts
del /Q .\winquickinstall_Pololu.bat

REM Clean up other hardware
rmdir /Q /S Pololu  >nul 2>&1

REM Other cleanups
REM TARGET

if !errorstatus! EQU 0 (
    echo.
    echo Installation of Pico system apparently successful.
    echo.
) else (
    echo.
    echo Installation of Pico system had issues somewhere.
    echo.
)

pause
)

endlocal

exit /B 0
