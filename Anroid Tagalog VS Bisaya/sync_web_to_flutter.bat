@echo off
REM Sync web\ -> flutter_app\assets\www\ before every Flutter build.
REM Run from the MidTerms_tagalogvsbisaya_mobile-main folder:
REM   sync_web_to_flutter.bat
set SRC=%~dp0web
set DST=%~dp0flutter_app\assets\www
echo Syncing %SRC% -^> %DST%
robocopy "%SRC%" "%DST%" /MIR /XD .git /XF .DS_Store
echo Done. Now run: cd flutter_app ^&^& flutter pub get ^&^& flutter build apk --release
