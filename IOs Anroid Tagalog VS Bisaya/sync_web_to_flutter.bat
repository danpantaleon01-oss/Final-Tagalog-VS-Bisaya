@echo off
REM =====================================================================
REM  Sync the shared content + game assets into the two consumers.
REM
REM  1. shared\game_content.json  ->  web\game_content.json          (PWA)
REM                               ->  flutter_app\assets\...         (APK)
REM     All three copies must be byte-identical: drift on the rules
REM     tables dies HERE, at build time, instead of inside one platform.
REM
REM  2. web\assets\*  ->  flutter_app\assets\www\assets\* (art + audio
REM     only). The PWA's index.html / game.js / style.css / sw.js /
REM     manifest.json are NOT mirrored on purpose: the Flutter app is
REM     pure Dart and never reads them, so bundling them would be dead
REM     APK weight (pubspec.yaml declares the same set explicitly).
REM =====================================================================

setlocal
set "CANON=%~dp0shared\game_content.json"
set "WJ=%~dp0web\game_content.json"
set "DJ=%~dp0flutter_app\assets\game_content.json"
set "SRC=%~dp0web\assets"
set "DST=%~dp0flutter_app\assets\www\assets"

if not exist "%CANON%" (
    echo [ERROR] %CANON% is missing - the shared rules file was deleted?
    exit /b 1
)

copy /y "%CANON%" "%WJ%" >nul
copy /y "%CANON%" "%DJ%" >nul

fc /b "%CANON%" "%WJ%" >nul
if errorlevel 1 (
    echo [ERROR] web copy of game_content.json differs from the canonical file.
    exit /b 1
)
fc /b "%CANON%" "%DJ%" >nul
if errorlevel 1 (
    echo [ERROR] flutter copy of game_content.json differs from the canonical file.
    exit /b 1
)
echo [OK] game_content.json: canonical -^> web + flutter assets, hashes agree

echo Syncing %SRC% -^> %DST%
if not exist "%SRC%\p1" echo [ERROR] %SRC%\p1 is missing - web tree broken? & exit /b 1
if not exist "%SRC%\p2" echo [ERROR] %SRC%\p2 is missing - web tree broken? & exit /b 1
if not exist "%SRC%\audio" echo [ERROR] %SRC%\audio is missing - web tree broken? & exit /b 1
if not exist "%SRC%\food" echo [ERROR] %SRC%\food is missing - web tree broken? & exit /b 1

robocopy "%SRC%" "%DST%" /MIR /XD .git /XF .DS_Store
if %errorlevel% GEQ 8 (
    echo [ERROR] robocopy failed with code %errorlevel%.
    exit /b %errorlevel%
)

REM ---- Fail loudly if pubspec and the sync disagree ----
if not exist "%DST%\icon.png"  echo [ERROR] icon.png  did not sync. & exit /b 1
if not exist "%DST%\audio\bg_music_lobby.mp3" echo [ERROR] lobby music did not sync. & exit /b 1
if not exist "%DST%\p1\head.png" echo [ERROR] p1 art did not sync. & exit /b 1
if not exist "%DST%\p2\head.png" echo [ERROR] p2 art did not sync. & exit /b 1
if not exist "%DST%\food" echo [ERROR] food art did not sync. & exit /b 1

echo Done. PWA is ready to serve from web\.
echo For the APK: cd flutter_app ^&^& flutter pub get ^&^& flutter build apk --release
endlocal
