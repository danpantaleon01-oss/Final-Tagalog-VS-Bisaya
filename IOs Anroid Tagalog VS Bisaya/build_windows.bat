@echo off
REM =====================================================================
REM  Tagalog VS Bisaya - portable Windows build
REM
REM  Zero privilege by design: this script NEVER elevates, NEVER writes
REM  outside this project tree, and NEVER touches the system PATH or
REM  C:\Program Files. Dependencies live in a project-local .venv, and
REM  the resulting EXE in dist\ is standalone - copy it anywhere and it
REM  just runs (scores/prefs land in %LOCALAPPDATA%\TagalogVsBisaya).
REM =====================================================================

cd /d "%~dp0"

REM ---- Python 3.13 (pygame has no prebuilt wheel for 3.14 yet) ----
py -3.13 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.13 was not found on this machine.
    echo Install it from https://www.python.org/downloads/ , or:
    echo     winget install --id Python.Python.3.13 --scope user
    echo Then run this script again.
    pause
    exit /b 1
)

REM ---- Isolated dependency set inside .venv (nothing global) ----
if not exist .venv (
    echo [Setup] Creating an isolated build environment in .venv ...
    py -3.13 -m venv .venv
)
set "VPY=.venv\Scripts\python.exe"
echo [Setup] Installing dependencies into .venv ...
"%VPY%" -m pip install --disable-pip-version-check --quiet -r requirements.txt
"%VPY%" -m pip install --disable-pip-version-check --quiet pyinstaller

REM ---- Fresh build every time ----
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
REM A running copy of the game locks dist\*.exe; catch that instead of
REM silently "succeeding" with the stale EXE of the previous build.
if exist dist (
    echo [ERROR] dist\ could not be removed - the game EXE is running or
    echo         locked by another program. Close it and run this again.
    pause
    exit /b 1
)
if exist "Tagalog VS Bisaya.spec" del /f /q "Tagalog VS Bisaya.spec"
if exist SnakeGame.spec del /f /q SnakeGame.spec

echo [Build] Packaging the portable EXE ...
"%VPY%" -m PyInstaller --noconfirm --onefile --windowed --icon=icon.ico ^
 --add-data "assets;assets" ^
 --add-data "shared/game_content.json;." ^
 --name "Tagalog VS Bisaya" main.py

if not exist "dist\Tagalog VS Bisaya.exe" (
    echo [ERROR] Build did not produce dist\"Tagalog VS Bisaya.exe".
    pause
    exit /b 1
)

echo.
echo ===================================================
echo  Build complete. The EXE is portable:
echo     dist\"Tagalog VS Bisaya.exe"
echo  Run it from anywhere - no install, no admin rights.
echo ===================================================

REM ---- Optional convenience: a shortcut for the CURRENT user only ----
choice /C YN /N /M "Create a shortcut in your own Start Menu (no admin)? [y/n] "
if errorlevel 2 goto :done

set "SSCRIPT=%TEMP%\%RANDOM%-%RANDOM%.vbs"
> "%SSCRIPT%" echo Set oWS = WScript.CreateObject("WScript.Shell")
>> "%SSCRIPT%" echo Set oLnk = oWS.CreateShortcut(oWS.SpecialFolders("StartMenu") ^& "\Programs\Tagalog VS Bisaya.lnk")
>> "%SSCRIPT%" echo oLnk.TargetPath = "%~dp0dist\Tagalog VS Bisaya.exe"
>> "%SSCRIPT%" echo oLnk.WorkingDirectory = "%~dp0dist"
>> "%SSCRIPT%" echo oLnk.IconLocation = "%~dp0dist\Tagalog VS Bisaya.exe, 0"
>> "%SSCRIPT%" echo oLnk.Save
cscript /nologo "%SSCRIPT%"
del "%SSCRIPT%"
echo Shortcut created (per-user; remove it like any other Start Menu item).

:done
pause
