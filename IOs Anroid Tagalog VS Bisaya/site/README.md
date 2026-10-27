# Download Hub Site (`site/`)

This folder is the **one-folder, drag-and-drop website** that presents the game
and routes visitors to the right installer. Deploy it as-is.

## What's inside

| Path | Purpose |
|---|---|
| `index.html` | Landing page — game showcase + **3 download cards** (iPhone/iPad, Android, Windows). Detects the visitor's OS and flags the matching card. |
| `ios.html` | **iOS download page.** Apple doesn't allow websites to hand out installer files, so this page *is* the installer: its **INSTALL button opens the iOS share sheet**, the player taps *Add to Home Screen*, and the game lands on the Home Screen with the icon, fullscreen, offline. If the player opens the site from the installed icon, it auto-jumps into `game/`. |
| `android.html` | Direct download of `downloads/tagalog-vs-bisaya.apk` + the one-time "allow installs" walkthrough. |
| `windows.html` | Direct download of `downloads/Tagalog-VS-Bisaya-PC.exe` + SmartScreen walkthrough. |
| `game/` | A full copy of the playable `web/` PWA (with all iOS fixes) — linked as "play in browser" and as the target of the installed iOS icon. |
| `downloads/` | The two binary artifacts: the 18 MB Windows `.exe` and the 52 MB Android `.apk` (release build). |
| `assets/` | Icons generated from `assets/icon.png` (used across these pages). |

## Deploy (Netlify Drop — free, ~1 minute)

1. Zip or upload the **whole `site/` folder** at [app.netlify.com/drop](https://app.netlify.com/drop).
2. Share the HTTPS link it gives you (e.g. `https://tvsb-game.netlify.app`).
3. iPhone users open it in Safari → tap the iOS card → **Add to Home Screen**. Done.

GitHub Pages / Vercel / Cloudflare Pages work the same way (upload folder contents).

> The folder is 81 MB total (exe + apk + game assets). Free hosts are fine with
> that (Netlify cap is 250 MB per site).

## Keeping `site/game/` in sync

`site/game/` is a **copy** of the project's `web/` folder. After editing the web
game, refresh the copy:

```bat
robocopy "..\web" "game" /MIR /XF .git
```

Also replace `downloads/tagalog-vs-bisaya.apk` with a new build from
`flutter_app` (`flutter build apk --release`), and `downloads/Tagalog-VS-Bisaya-PC.exe`
from a new `build_windows.bat` run.

## Swapping the iOS page for an App Store / TestFlight link later

If you ever publish a native build (needs a Mac + Apple Developer account), edit
the green iOS card link in `index.html`:

```html
<a class="go" href="https://apps.apple.com/...">📱 INSTALL FROM APP STORE</a>
```
or a TestFlight link — nothing else needs to change. The steps page keeps
working for everyone else free.
