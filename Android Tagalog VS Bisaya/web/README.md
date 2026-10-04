# Snake Game — Mobile Web (PWA) Edition

This folder is the Android/iOS-ready rewrite of the pygame game in pure
HTML5 Canvas + JavaScript. It is a Progressive Web App (PWA) and is meant to
be wrapped with Capacitor.

## Changes from the Windows version

- 2-player mode removed (single player only).
- Touch controls: swipe on the screen or use the on-screen D-pad
  (D-pad hides automatically on desktop/mouse devices). Arrow keys / WASD
  still work for testing on desktop.
- The game board recalculates its grid size to fit any mobile screen
  resolution and orientation (portrait or landscape).
- Scores are stored in `localStorage` instead of `scores.json`.
- Menus, name entry, leaderboard, and game-over screens are HTML overlays,
  so mobile keyboards work properly for entering a name.

## Run locally

Service workers require an HTTP origin, so don't open `index.html` directly.
Serve the folder instead:

```
cd web
npx serve .
```

## Wrap with Capacitor (Android / iOS)

From the `SnakeGame` folder:

```
npm init -y
npm install @capacitor/core @capacitor/cli @capacitor/android @capacitor/ios
npx cap init "Tagalog vs Bisaya" com.tagalogvsbisaya.snake
```

Set `webDir` to `web` in `capacitor.config.json`:

```json
{
  "appId": "com.tagalogvsbisaya.snake",
  "appName": "Tagalog vs Bisaya",
  "webDir": "web"
}
```

Then:

```
npx cap add android
npx cap add ios
npx cap sync
npx cap open android   # or: npx cap open ios
```
