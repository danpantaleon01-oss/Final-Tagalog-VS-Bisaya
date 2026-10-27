# Tagalog vs Bisaya — Flutter mobile app (native)

Native Flutter port of the `web/` PWA / desktop Pygame snake game.
No WebView — the game is Dart + `CustomPainter` (60fps arena, swipe +
D-pad + keyboard), sounds via `audioplayers`, scores via
`shared_preferences`.

```
flutter_app/lib/
  main.dart          <- screens: menu / select / name / game / game-over
  game_logic.dart    <- pure rules: queueTurn, step, randomFood, speed curve
  board_painter.dart <- arena + snake + food + motes + popups painter
  scores.dart        <- top-10 store (shared_preferences)
  sounds.dart        <- lobby loop + tagalog/bisaya eat/death/win
flutter_app/assets/www/assets/audio/  <- bundled mp3s (served as assets)
```

## Prerequisites

1. Flutter SDK 3.13+ — https://docs.flutter.dev/get-started/install
2. Android Studio + SDK + licenses:
   ```
   flutter doctor
   flutter doctor --android-licenses
   ```
3. Phone with USB debugging, or an emulator.

## Build (release APK)

```
cd flutter_app
flutter pub get
flutter test
flutter build apk --release
```

APK output:

```
flutter_app\build\app\outputs\flutter-apk\app-release.apk
```

Copy to your phone and tap to install (allow "install unknown apps").

## Quick test run (debug, over USB)

```
cd flutter_app
flutter pub get
flutter run
```

## How it works

- `SnakeGame` holds snake/dir/food/score; `stepMs` follows the
  `START_FPS 8 → cap 25` curve from `web/game.js`.
- `BoardPainter` draws gradient + glow + dot lattice + motes +
  vignette + snake (sway wave, glow, eyes) + pulsing food + floating
  `SARAP! / LAMI! / …` popups.
- Swipe on the board steers (24px threshold, continuous re-anchor);
  on-screen D-pad + arrows/WASD also work; ESC quits to menu.
- Sounds: `assets/www/assets/audio/*.mp3` played with `audioplayers`
  (`www/assets/audio/` prefix since pubspec bundles `assets/www/`).
- Scores: `snake_scores` key in `shared_preferences`, top 10 only —
  replaces desktop `scores.json` / web `localStorage`.

## Notes / limitations

- Mobile build is intentionally **single-player + leaderboard** only
  (Tagalog/Bisaya snake select). The desktop Pygame `main.py` 2-player
  shared-keyboard mode was deliberately not ported — no shared keyboard
  exists on a phone.
- Package ID: `com.tagalogvsbisaya.tagalog_vs_bisaya`, label "Tagalog vs Bisaya".
