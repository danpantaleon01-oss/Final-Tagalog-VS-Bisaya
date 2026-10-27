# Getting the game onto an iPhone as a REAL installed application

Three ways exist, ranked by how easily you can do them right now:

| # | Path | Result | Cost | Mac needed |
|---|------|--------|------|-----------|
| A | PWA "Add to Home Screen" (`site/ios.html` — already live on your test server) | Icon on Home Screen, fullscreen, offline | Free | No — **done already** |
| B | Cloud-built native `.ipa` + **Sideloadly** (this guide) | A true native app installed on the phone (app switcher, Settings → storage, real bundle) | Free | No |
| C | TestFlight / App Store | Most official; classmates install from a normal link | $99/yr Apple Developer | No (needs paid account) |

Apple's policy — no website can hand you an installer file — forces *some*
step outside Safari. Path B's extra step is a one-time USB signing, which is
exactly what makes it a genuine installed app rather than a web shortcut.

---

## Path B — free native .ipa on your iPhone (do once, re-sign weekly)

### Step 1 · Push the project to GitHub (~10 min, no Mac)

The repo already contains `.github/workflows/build-ios-ipa.yml` — that workflow
is the "cloud Mac". On `github.com`:

1. Sign in → **New repository** → name it e.g. `tagalog-vs-bisaya` → **Create**
   (Private is fine — the free plan has enough build minutes for this).
2. Upload the project **except the heavy folders** (they're already excluded by
   `.gitignore`), e.g. with GitHub Desktop: *Add existing repository* → open
   this folder → *Publish*; or via commands:

   ```bash
   git remote add origin https://github.com/<your-username>/tagalog-vs-bisaya.git
   git push -u origin main
   ```

   Make sure `flutter_app/**` and `.github/workflows/build-ios-ipa.yml` get
   pushed — those are all the build needs. Don't let `site/downloads/` in
   (it's git-ignored now).

### Step 2 · The cloud Mac builds the .ipa (~15–25 min, automatic)

- Repo page → **Actions** tab → workflow **build-ios-ipa** runs on push
  (or click *Run workflow* manually).
- When it finishes → click the run → **Artifacts** → download
  `Tagalog-vs-Bisaya-unsigned-ipa` → unzip → you get
  `Tagalog-vs-Bisaya-unsigned.ipa`.

### Step 3 · Sign & install from this Windows PC (one-time setup)

1. Install **Sideloadly** → https://sideloadly.io (free).
2. Install Apple's USB driver once — the **"Apple Devices" app from the
   Microsoft Store** (or classic iTunes from apple.com).
3. Connect the iPhone with a cable → tap **Trust This Computer** on the phone.
4. Open Sideloadly → drag in the `.ipa` →
   **Apple ID / Password** = any free Apple ID (it only creates a personal
   signing certificate, nothing is charged) → **Start**.
5. On the phone: **Settings → General → VPN & Device Management** → tap your
   Apple ID entry → **Trust**.
6. **Tagalog vs Bisaya** now sits on the Home Screen as a normal installed app.

### The one caveat (and how to remove it)

- A free Apple ID signatures expire **after 7 days** → the app stops launching
  until you re-run Sideloadly once with the same cable setup (2 minutes).
  Remove that permanently by installing **AltStore** (auto-renews while your
  PC and phone share Wi-Fi).
- Free Apple IDs allow **3 sideloaded apps at once**.

### For the class presentation

Install it the evening before. Record a 20-second screen capture of the
launch → home screen icon → playing, as backup evidence.

---

## Path C — the "official" route (optional upgrade)

1. Enroll: https://developer.apple.com/programs ($99/year).
2. Apple emails you access to TestFlight/App Store Connect.
3. The same GitHub workflow builds a **signed** build once the certificate
   (`.p8` key) is added as a repo secret; students then all install your real
   game from a normal **TestFlight link** on any iPhone.

---

## Why the big download-hub site still Route A on iOS

`site/ios.html` is not wrong — it *is* the zero-cost route and stays online
as the friendly installer page. Path B is simply the stronger evidence that
"we made a native iOS application" when a rubric requires that distinction.
Both were prepared.
