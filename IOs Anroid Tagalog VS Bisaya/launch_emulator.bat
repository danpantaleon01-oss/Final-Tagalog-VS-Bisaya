@echo off
REM Double-click to boot the Snake emulator and auto-launch the game.
set EMU=%LOCALAPPDATA%\Android\Sdk\emulator\emulator.exe
set ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe

"%ADB%" devices | findstr /C:"emulator-5554	device" >nul
if %errorlevel% equ 0 (
  echo Emulator already running. Launching game...
  goto launch
)

echo Booting Pixel_Snake_Test (first boot after a reboot takes ~1 min)...
start "Snake Emulator" "%EMU%" -avd Pixel_Snake_Test
"%ADB%" wait-for-device >nul

:waitboot
for /f "delims=" %%b in ('"%ADB%" shell getprop sys.boot_completed 2^>nul') do set "BOOT=%%b"
if not "%BOOT:~0,1%"=="1" (
  timeout /t 3 /nobreak >nul
  goto waitboot
)
echo Emulator ready.

:launch
"%ADB%" shell monkey -p com.tagalogvsbisaya.tagalog_vs_bisaya -c android.intent.category.LAUNCHER 1 >nul
echo Game launched on the emulator.
