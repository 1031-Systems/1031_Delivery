@echo off
setlocal enabledelayedexpansion

REM Go to the directory where we unzipped the file
pushd "%~dp0\.."

REM Get optional tool name from argument
set TOOLNAME=Hauntimator
if NOT "%1"=="" set "TOOLNAME=%1"

REM Get path to this script (equivalent to SCRIPTPATH in bash)
set SCRIPTPATH=%~dp0
REM Remove trailing backslash
if "%SCRIPTPATH:~-1%"=="\" set SCRIPTPATH=%SCRIPTPATH:~0,-1%
echo Path:%SCRIPTPATH%
echo Version:__VERSION__

REM Set up the virtual environment
cd /d "%SCRIPTPATH%"
python -m venv .venv
if errorlevel 1 (
    echo WHOOPS - Need to install venv tools
    exit /b %errorlevel%
)

REM Activate the virtual environment
call "%SCRIPTPATH%\.venv\Scripts\activate.bat"

REM Install and update dependencies
python -m pip install -U pip
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

REM Installing rshell seems to install pyreadline2 as a dependency.
REM That messes up python which gives a bunch of errors and causes
REM rshell to not even run.  Needs pyreadline3.

REM Clean up pyreadline from rshell
pip uninstall -y pyreadline
pip install pyreadline3

echo.
set /p "CREATE_SHORTCUT=Do you want to install phoneme-based speech recognition tools? (y/N): "
if /i "%CREATE_SHORTCUT%"=="y" (
    echo Installing vosk python module
    pip install vosk

    REM Go to the directory where data files live
    pushd src\plugins\Phoneme_data

    echo.
    echo Installing vosk American English language model
    curl https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip -o "%USERPROFILE%/Downloads/vosk-model-small-en-us-0.15.zip"
    tar -xvf "%USERPROFILE%/Downloads/vosk-model-small-en-us-0.15.zip"
    rd vosk-model 2>null
    mklink /J "vosk-model" "vosk-model-small-en-us-0.15"

    echo.
    echo Installing CMU Phoneme dictionary
    curl https://svn.code.sf.net/p/cmusphinx/code/trunk/cmudict/sphinxdict/cmudict_SPHINX_40 -O
    del dictionary 2>null
    mklink /H "dictionary" "cmudict_SPHINX_40"

    popd
) else (
    pushd src\plugins
    rmdir /s /q "Phoneme_data"
    del /F "Phonemes*"
)


REM Set VIRTUAL_ENV path for use in wrapper scripts below
set VIRTUAL_ENV=%SCRIPTPATH%\.venv

REM Create wrapper .bat files (equivalent to the shell wrapper scripts)

REM --- Hauntimator ---
(
    echo @echo off
    echo "%VIRTUAL_ENV%\Scripts\python.exe" "%SCRIPTPATH%\src\Hauntimator.py" %%*
    echo if errorlevel 1 ^(
    echo     echo Whoops - Hauntimator terminated unnaturally
    echo     echo Check for error messages, take a screenshot, or
    echo     echo copy the output, if any, and submit it with a bug report.
    echo     pause
    echo ^)
) > "%SCRIPTPATH%\Hauntimator.bat"

REM --- joysticking ---
(
    echo @echo off
    echo "%VIRTUAL_ENV%\Scripts\python.exe" "%SCRIPTPATH%\src\joysticking.py" %%*
) > "%SCRIPTPATH%\joysticking.bat"

REM --- Maestro_Animator ---
(
    echo @echo off
    echo set PYTHONPATH=%SCRIPTPATH%\Pololu;%SCRIPTPATH%\Pololu\lib
    echo "%VIRTUAL_ENV%\Scripts\python.exe" "%SCRIPTPATH%\src\Maestro_Animator.py" %%*
) > "%SCRIPTPATH%\Maestro_Animator.bat"

echo.
echo Installation complete. Wrapper scripts created as .bat files.
echo.

REM --- Optionally Create Desktop Shortcuts ---
REM Have to set variables outside conditional to have effect
set res=F
if "%1"=="" set res=T
if "%1"=="Pololu" set res=T

set /p "CREATE_SHORTCUT=Create desktop shortcuts? (y/N): "
if /i "%CREATE_SHORTCUT%"=="y" (
    REM Call function for each shortcut to be created
    CALL :CreateShortcut "%TOOLNAME%" , "Hauntimator", "Hlogo.ico"
    if "%res%"=="T" (
        CALL :CreateShortcut "Maestro_Animator" , "Maestro_Animator" , "CElogo.ico"
    )
    REM CALL :CreateShortcut "%TOOLNAME%_Joy" , "joysticking" , "jlogo.ico"
)

goto :eof

:CreateShortcut
setlocal
REM Call with linkname , appname , logo.ico
(
    echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
    echo Set oLink = oWS.CreateShortcut^("%USERPROFILE%\Desktop\%~1.lnk"^)
    echo oLink.TargetPath = "%SCRIPTPATH%\%~2.bat"
    echo oLink.Arguments = "-a "
    echo oLink.IconLocation = "%SCRIPTPATH%\src\docs\images\%~3"
    echo oLink.WorkingDirectory = "%SCRIPTPATH%"
    echo oLink.Save
) > "%TEMP%\CreateShortcut.vbs"
cscript //nologo "%TEMP%\CreateShortcut.vbs"
del "%TEMP%\CreateShortcut.vbs"

endlocal
EXIT /B 0

