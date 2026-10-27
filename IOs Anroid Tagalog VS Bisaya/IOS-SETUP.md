# Tagalog vs Bisaya — iOS Setup Guide

The game was converted for iOS in two ways. **Option A works right now, from this
PC, with no Mac and no Apple Developer account.** Option B prepares the native
Xcode app for when a Mac is available.

---

## OPTION C · Download-hub website (`site/` — recommended front door)

`site/` is a ready one-folder website: a landing page with **three download
cards** (iPhone/iPad, Android, Windows) that auto-detects the visitor's OS, plus
direct `.exe`/`.apk` downloads and the guided iOS install page. See
`site/README.md` — deploy the whole folder to Netlify Drop / GitHub Pages and
share the link.

## OPTION A · Install on iPhone/iPad today (PWA — recommended)

The `web/` folder is now an iOS-ready web app. iOS has no "unzip an APK" style
install — the official way to get an app on the Home Screen for free is Safari's
**Add to Home Screen**. When added, the game:

- gets a real Home Screen icon made from `assets/icon.png` (rounded by iOS),
- launches fullscreen with no Safari address bar (standalone app mode),
- keeps scores/prefs, runs offline after first load (HTTPS required),
- shows a setup banner the first time a player opens it.

### Step 1 — Put `web/` online over HTTPS (pick one)

| Method | How |
|---|---|
| **Netlify Drop (easiest)** | Go to `app.netlify.com/drop` in a browser, **drag the `web` folder in**. You get a free `https://<name>.netlify.app` link instantly. |
| **GitHub Pages** | Create a repo, upload the **contents** of `web/`, enable Pages. Result: `https://<user>.github.io/<repo>/` |
| **Vercel / Cloudflare Pages** | Same idea: upload the `web` folder contents. |

Any free HTTPS static host works — the folder contains only HTML/JS/CSS/PNG/MP3.

### Step 2 — On the iPhone/iPad

1. Open the HTTPS link in **Safari** (not Chrome/other browsers — Apple only
   allows the install from Safari).
2. Tap the **Share** button (⤴️) in the toolbar.
3. Scroll down → tap **Add to Home Screen** → **Add**.
4. The **Tagalog vs Bisaya** icon appears on the Home Screen. Launch from there —
   it runs fullscreen like a normal iOS app, works in airplane mode (HTTPS
   install), and saves scores per device.

> Playing over your own Wi-Fi first? On the PC run
> `py -3.13 -m http.server 8000 --directory web`, find your IP with `ipconfig`,
> and open `http://<PC-IP>:8000` in Safari on the phone. Add to Home Screen
> still works over plain HTTP; only the offline mode needs HTTPS.

---

## OPTION B · Native iOS app (Xcode project — needs a Mac once)

`flutter_app/ios/` now contains a complete Xcode project (previously the app
only had an Android target). Prepared for you:

- ✅ `ios/Runner.xcworkspace` — the Xcode project (Flutter 3.47 template)
- ✅ App icon: all 15 icon slots (20→1024 px) generated from `assets/icon.png`
- ✅ Display name: **Tagalog vs Bisaya**
- ✅ Bundle ID: `com.tagalogvsbisaya.tagalogVsBisaya` (changeable in Xcode)
- ✅ `flutter analyze` passes on the Dart game code

On any Mac with Xcode + CocoaPods installed:

```bash
cd flutter_app
flutter pub get
open ios/Runner.xcworkspace   # or: flutter run with an iPhone plugged in
```

1. In Xcode: select **Runner** target → **Signing & Capabilities** → tick
   *Automatically manage signing* and pick/enter your **Apple ID team**
   (a free Apple ID sideloads to your own device; the build expires after 7
   days. A $99/yr Apple Developer account removes that and enables the
   App Store / TestFlight).
2. `flutter run` / `flutter build ipa`.

Bundling an `.ipa` and sideloading it without a Mac is not possible — Apple
requires macOS + Xcode (or App Store/TestFlight). That's why Option A exists.

---

## What was changed for iOS (this conversion)

### PWA — `web/`
| File | Change |
|---|---|
| `index.html` | Added iOS install meta tags (`apple-mobile-web-app-capable`, `black-translucent` status bar, app title) + four correctly-sized `apple-touch-icon` links + an in-game "Add to Home Screen" helper banner. |
| `assets/touch/` *(new)* | `apple-touch-icon.png` (180×180, the iPhone Home Screen icon), plus 120/152/167 px and a 1024 px source — all generated from `assets/icon.png`. |
| `assets/icons/` *(new)* | Honest 192/512 px manifest icons (the manifest previously claimed sizes the 1024 px file doesn't have). |
| `manifest.json` | `display`, real icon sizes, correct theme colours, app id/categories. |
| `sw.js` | Cache bumped to `snake-v9-ios` + new icons cached; iPhones already running the old build pick up all fixes on next visit. |
| `style.css` | No white flash on iOS launch, no long-press text selection/magnifier, double-tap safe buttons, new `#install-hint` banner styles. |
| `game.js` | Board layout respects the iPhone notch (`safe-area-inset-top`); canvas resolution capped at 2× for stable 60 fps on iPhones; **iOS audio unlock sweep** (every eat/voice/win/death clip must be gestured once or it's silent forever on iOS); swipes now turn mid-swipe instead of after finger-lift; orientation change re-runs after iOS settles dimensions; install-hint banner logic. |

### Native — `flutter_app`
| Item | Change |
|---|---|
| `ios/` *(new)* | Full Xcode/Runner project generated by Flutter. |
| `AppIcon.appiconset` | All 15 slots replaced with game art from `assets/icon.png`. |
| `Info.plist` | Display name set to *Tagalog vs Bisaya*. |

Windows-side leftovers are untouched — Android/desktop still work exactly as before
(`build_windows.bat`, the pygame build, the APK pipeline via `sync_web_to_flutter.bat`).

## Quick test from this PC (no phone needed)

```powershell
py -3.13 -m http.server 8000 --directory web
# open http://127.0.0.1:8000 and press F12 → toggle device toolbar → iPhone
```
(Chrome DevTools can't simulate the true Add-to-Home-Screen flow, but it
verifies layout, swipe controls, audio unlock and the install banner.)
