@echo off
setlocal enabledelayedexpansion

REM Get path to this script (equivalent to SCRIPTPATH in bash)
set SCRIPTPATH=%~dp0
REM Remove trailing backslash
if "%SCRIPTPATH:~-1%"=="\" set SCRIPTPATH=%SCRIPTPATH:~0,-1%
echo Path:%SCRIPTPATH%
echo Version:__VERSION__

REM Set up the virtual environment
cd /d "%SCRIPTPATH%"
python -m venv --system-site-packages .venv
if errorlevel 1 (
    echo WHOOPS - Need to install venv tools
    exit /b %errorlevel%
)

REM Activate the virtual environment
call "%SCRIPTPATH%\.venv\Scripts\activate.bat"

REM Install and update dependencies
pip install -U pip
pip install -U PyQt5
if errorlevel 1 (
    echo WHOOPS - Need to install PyQt6
    pip install -U PyQt6==6.5
    if errorlevel 1 (
        echo WHOOPS - Unable to install PyQt
        exit /b %errorlevel%
    )
)
pip install -U PythonQwt
pip install -U pygame-ce
pip install -U rshell
REM pip install -U pocketsphinx

REM Set VIRTUAL_ENV path for use in wrapper scripts below
set VIRTUAL_ENV=%SCRIPTPATH%\.venv

REM Create wrapper .bat files (equivalent to the shell wrapper scripts)

REM --- Hauntimator ---
(
    echo @echo off
    echo "%VIRTUAL_ENV%\Scripts\python.exe" "%SCRIPTPATH%\src\Hauntimator.py" %%*
) > "%SCRIPTPATH%\Hauntimator.bat"

REM --- joysticking ---
(
    echo @echo off
    echo "%VIRTUAL_ENV%\Scripts\python.exe" "%SCRIPTPATH%\src\joysticking.py" %%*
) > "%SCRIPTPATH%\joysticking.bat"

REM --- Pico\rshell ---
(
    echo @echo off
    echo "%VIRTUAL_ENV%\Scripts\rshell.exe" %%*
) > "%SCRIPTPATH%\Pico\rshell.bat"

REM --- Pico\verifyload ---
(
    echo @echo off
    echo "%VIRTUAL_ENV%\Scripts\python.exe" "%SCRIPTPATH%\Pico\verifyload.py" %%*
) > "%SCRIPTPATH%\Pico\verifyload.bat"

REM --- Maestro_Animator ---
(
    echo @echo off
    echo set PYTHONPATH=%SCRIPTPATH%\Pololu;%SCRIPTPATH%\Pololu\lib
    echo "%VIRTUAL_ENV%\Scripts\python.exe" "%SCRIPTPATH%\src\Maestro_Animator.py" %%*
) > "%SCRIPTPATH%\Maestro_Animator.bat"

echo.
echo Installation complete. Wrapper scripts created as .bat files.
REM --- Hauntimator ---
(
    echo @echo off
    echo "%VIRTUAL_ENV%\Scripts\python.exe" "%SCRIPTPATH%\src\Hauntimator.py" %%*
) > "%SCRIPTPATH%\Hauntimator.bat"

REM --- Optionally Create Desktop Shortcuts ---

set /p "CREATE_SHORTCUT=Create desktop shortcuts? (y/N): "
if /i "%CREATE_SHORTCUT%"=="y" (
    REM Call function for each shortcut to be created
    CALL :CreateShortcut "Hauntimator" , "-f" , "Hlogo.ico"
    CALL :CreateShortcut "Maestro_Animator" , "-p" , "CElogo.ico"
    REM ALL :CreateShortcut "joysticking" , "-a" , "jlogo.ico"
)

goto :eof

:CreateShortcut
setlocal
REM Call with Hauntimator , -f , Hlogo.ico
(
    echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
    echo Set oLink = oWS.CreateShortcut^("%USERPROFILE%\Desktop\%~1.lnk"^)
    echo oLink.TargetPath = "%SCRIPTPATH%\%~1.bat"
    echo oLink.Arguments = "%~2 "
    echo oLink.IconLocation = "%SCRIPTPATH%\src\docs\images\%~3"
    echo oLink.WorkingDirectory = "%SCRIPTPATH%"
    echo oLink.Save
) > "%TEMP%\CreateShortcut.vbs"
cscript //nologo "%TEMP%\CreateShortcut.vbs"
del "%TEMP%\CreateShortcut.vbs"
endlocal
EXIT /B 0


endlocal


