@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This installer requires Administrative privileges to configure system applications.
    echo Please right-click this .bat file and select 'Run as administrator'.
    pause
    exit /b
)

cd /d "%~dp0"

REM Check if Python 3.13 is installed, if not, install it using winget
py -3.13 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [System] Python 3.13 was not found. Installing Python 3.13 automatically...
    winget install --id Python.Python.3.13 --exact --silent --accept-source-agreements --accept-package-agreements
    
    REM Refresh path for the current session
    for /f "tokens=2*" %%A in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set "SYS_PATH=%%B"
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path') do set "USER_PATH=%%B"
    set "PATH=%SYS_PATH%;%USER_PATH%"
)

REM Uses Python 3.13 because pygame has no prebuilt wheel for 3.14 yet.
py -3.13 -m pip install -r requirements.txt
py -3.13 -m pip install pyinstaller

REM Clean up old build artifacts to ensure a fresh build
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "Tagalog VS Bisaya.spec" del /f /q "Tagalog VS Bisaya.spec"
if exist SnakeGame.spec del /f /q SnakeGame.spec

py -3.13 -m PyInstaller --noconfirm --onefile --windowed --icon=icon.ico --add-data "assets;assets" --name "Tagalog VS Bisaya" main.py
echo.
echo Build complete. Your EXE is in the dist folder:
echo dist\"Tagalog VS Bisaya.exe"

if not exist "dist\Tagalog VS Bisaya.exe" (
    echo [ERROR] Compilation target could not be verified. Skipping system registration.
    pause
    exit /b
)

echo [SYSTEM] Provisioning application inside protected root assets...
if exist "C:\Program Files\TagalogVsBisayaGame" rmdir /s /q "C:\Program Files\TagalogVsBisayaGame"
mkdir "C:\Program Files\TagalogVsBisayaGame"
copy /Y "dist\Tagalog VS Bisaya.exe" "C:\Program Files\TagalogVsBisayaGame\"

echo [SYSTEM] Binding executable to the Global Environment Path...
setx /M PATH "%PATH%;C:\Program Files\TagalogVsBisayaGame"

echo [SYSTEM] Deploying shortcut link across all user profiles...
set SCRIPT="%TEMP%\%RANDOM%-%RANDOM%-%RANDOM%-%RANDOM%.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%
echo sLinkFile = "%ProgramData%\Microsoft\Windows\Start Menu\Programs\Tagalog VS Bisaya.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "C:\Program Files\TagalogVsBisayaGame\Tagalog VS Bisaya.exe" >> %SCRIPT%
echo oLink.WorkingDirectory = "C:\Program Files\TagalogVsBisayaGame" >> %SCRIPT%
echo oLink.IconLocation = "C:\Program Files\TagalogVsBisayaGame\Tagalog VS Bisaya.exe, 0" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%

echo ===================================================
echo [COMPLETE] System Application Configuration Finished!
echo ===================================================
echo The game is now accessible via the global system 'Run' menu (Win+R) by typing: Tagalog VS Bisaya
echo It has also been pinned system-wide across all user Start Menus.
pause
