# Tagalog vs Bisaya — Polish Plan

12 milestones, ordered **big → small**. Each one is a complete, shippable unit and is
treated as equally important — none is "cleanup to do later if there's time."

Legend for effort: **S** ≈ under an hour · **M** ≈ half a day · **L** ≈ 1–2 days.
Risk: what could break.

---

## M1 — Crash-proofing: the "it must never freeze or die" pass
**Why first:** every other milestone is worthless if the game can crash or wedge.
Three of these are confirmed reproducible defects, not hypotheticals.

### Confirmed defects
- **Flutter port crashed every run at ~step 4 (fixed 2026-10-17, verified live on emulator).**
  `SnakeGame.step()` (`game_logic.dart:93-113`) rolled a per-segment look id only
  when the snake *ate*, but popped one id off `variantIds` on every normal step,
  so the parallel list drained 3→2→1→0 and the next `removeLast()` threw
  `RangeError (length): Invalid value: Valid value range is empty: -1`. Because
  `_GameHomeState._tick` bumps `_lastStepMs` *before* the throw, `setState` never
  ran, so the board froze on its last frame while the ticker crash-looped every
  `stepMs` (~131 ms cadence confirmed in logcat). Diagnosed by driving the game in
  the Android emulator, then reproduced offline with the copied module
  (variants 3→2→1→0 → throw). Fix: roll an id for the new head on *every* step,
  keep the 1:1 invariant with a self-healing repair pass (mirrors the guard
  desktop `main.py` already has), and make `step()` on an empty snake return
  `died` instead of throwing. Regression tests added (`widget_test.dart`).
- **`F11` fullscreen is broken.** `toggle_fullscreen(screen)` (`main.py:921-931`)
  calls `pygame.display.set_mode(...)` and binds the new surface to a *local*
  variable. The return value is discarded at the only call site
  (`main.py:988-989`). The old surface becomes invalid, so every subsequent
  `screen.blit(...)` draws to a dead surface — the game freezes visually while
  still running. Fix: have the function return the new surface and reassign
  `screen` in `main()`, threading it through every screen/loop function that
  holds a surface reference.
- **Score save can crash the game at game-over.** `SCORES_FILE = Path("scores.json")`
  (`main.py:14`) resolves against the **current working directory**, not the
  executable. `build_windows.bat` installs to `C:\Program Files\TagalogVsBisayaGame\`
  and sets that as the shortcut's working directory — a location a normal user
  cannot write to. `save_scores()` (`main.py:186-188`) has **no `try/except`**, so
  the very first game-over raises `PermissionError` and the game dies with a
  traceback. Fix: write to a per-user location (`%LOCALAPPDATA%\TagalogVsBisaya\`),
  fall back to CWD, and wrap all IO in `try/except OSError`. Delete the dead
  `scores_file`/`music_file`/`icon_file` module globals (`main.py:38-41`) that
  were meant to do this job.
- **No audio device = no game.** `pygame.mixer.init()` (`main.py:942`) is
  unguarded. On a machine with no output device it raises and the game never
  starts. Fix: try `pre_init` + `init`, on failure set a dummy mixer so every
  `play_sound` becomes a no-op (they already guard `sound is not None`).

### Also in this milestone
- `load_prefs`/`save_prefs` already guard `OSError`; make `load_scores` match
  (it catches `FileNotFoundError`/`JSONDecodeError` but not `OSError`).
- Web `loadScores()` (`web/game.js:317-330`) trusts whatever is in
  `localStorage`. Desktop validates `isinstance(data, list)`; Dart has a
  `try/catch`. Give the web version the same validation so a corrupted entry
  can't break the leaderboard screen.
- Web `startGame()` never initialises `lastStep` (`web/game.js:620-635`); every
  caller happens to set it first. Set it inside `startGame()` so the fragile
  contract can't be broken by the next person who adds a restart path.
- Desktop: `import os` / `import sys` appear twice (`main.py:1-8` and `23-24`).
  Clean up.

**Done when:** F11 toggles cleanly in both directions; the game survives a
read-only CWD, a missing audio device, and a corrupted `scores.json` /
`localStorage` without a traceback; the Flutter app survives long runs with
`variantIds.length == snake.length` at every tick (parity + post-death
regression tests).
**Effort:** M · **Risk:** low-medium (the fullscreen fix touches every function
that receives `screen`).

---

## M2 — Win state, and audio you can control
**Why:** filling the board currently shows **"GAME OVER"**. There is no win
condition on mobile at all, and the win sounds are dead code on 2 of 3 platforms.

### Confirmed defects
- **Board-full reads as a loss.** Desktop `main.py:629-630` returns
  `score, True` (`died=True`) when `random_food()` returns `None`, so
  `game_over_screen()` announces "GAME OVER" for a perfect run.
- **Win sounds are never played on mobile.** `web/game.js:240` loads
  `tagalog_win.mp3` / `bisaya_win.mp3` into `SOUNDS` and nothing ever reads
  them. `sounds.dart:218` defines `playWin()` and `main.dart` never calls it.
  Only the desktop 2-player screen uses them (`main.py:843-858`).
- **Nothing in the game can be muted.** No volume, SFX or music toggle exists on
  any platform. For an audio-heavy game (voice lines on every bite, lobby music)
  this is the most-complained-about omission in any playtest.

### Work
- Add an explicit win state: `won` flag alongside `died` in all three
  implementations; a distinct "YOU WIN" screen (board cleared, final score,
  gold treatment, win sound, **R** for instant rematch). Share the layout with
  the existing game-over screen so it's one code path with a variant, not a copy.
- Wire `playWin` into Flutter and the win sounds into the web PWA.
- Add an audio toggle in all three: a mute button/pill (web HUD, Flutter HUD,
  desktop as a small speaker glyph or **M** key) plus a persisted preference —
  `prefs.json` / `localStorage` / `shared_preferences` already exist, so this is
  additive only. Mute must cover music *and* SFX; remember the choice across
  launches.
- 2-player: keep the existing win logic, but stop double-writing the
  leaderboard. `main.py:1041-1044` writes **two** entries per match (one per
  player), so a 2P match pollutes the top-10 twice. Write a single match entry
  ("P1 vs P2") or record the winner only.

**Done when:** a board-clear shows a win screen with sound on all three
platforms, mute survives a restart, and one 2P match produces one leaderboard row.
**Effort:** M · **Risk:** low.

### Implementation log — M2 shipped 2026-10-17 ✅

All work below is implemented and gated on all three platforms (desktop `py_compile`,
Flutter `analyze` + `test`, live verification on desktop/web; Android detail below).

- **Win state.** Board-clear is now a distinct gold **YOU WIN / !BOARD CLEARED!**
  screen with the win sound at the clearing moment, sharing one code path with the
  loss screen:
  - Desktop: `game()` returns `(score, died, won)`; `game_over_screen(..., won=True)`
    renders the gold variant; `f"{team}_win"` plays when the board clears.
  - Web: `step()` board-fill branch calls `endGame(won=True)`, plays
    `playerSnake + "_win"`, overlays get the gold `h2.win` treatment. Verified live:
    board forced to 713/713 → *"YOU WIN"* + `.win` class, zero console errors.
  - Flutter: `StepResult.won` → `_endGame(won: res.won)` → `playWin(_team)` and the
    gold overlay in `_buildGameOver`; regression-tested (`widget_test.dart`,
    board-fill reports won, not died).
- **Mute everywhere.** `M` key + a visible toggle persists across restarts on all
  three (desktop `prefs.json` "muted", web `snake_prefs.muted` via localStorage,
  Flutter `PrefsStore` key `snake_muted`). Gates sit in the central play paths:
  desktop `play_sound`/`play_random_eat_sound`/`lobby_music_start`, web `play()`/
  `menuMusic()`, Flutter `SoundService.setMuted` + every scheduled sound. Verified
  live on the web (HUD pill 🔊→🔇, M key flips, reload restores muted boot) and on
  the desktop driver (toggle, prefs round-trip, muted play = no-op).
- **2P leaderboard.** Desktop now records the winner only (one row per match);
  ties record nothing. Driver check: 2P match → exactly `[('NAME_P1', 30)]`.
- Service-worker cache bumped (`snake-v7`) so the PWA update lands for installs.

### Tail orientation — defect found & fixed during M2

**Ground truth (alpha-probe proven on all three renderers).** Both snake tails are
authored with the *flush attach edge on +x (right)* and the *taper/tip on −x (left)*:
p1/tail renders `col_taper [0.74, 1.0, 1.0, 1.0]` (thin on the left), p2/tail
314×201 with the same right-flush profile. The float convention everywhere is:
**attach edge → inward direction (toward the next segment), tip → outward.**

- **Desktop was wrong**: `images.py::_normalize_horizontal` baked `rotate(270)` into
  the near-square-tall p1/tail (123×128, aspect 0.96 — art slop, not vertical
  authoring), while `_rotated_idx` composes `_ccw_angle(CORNER_IN, direction)`
  assuming the art's +x means "90° sideways" in every direction. Net effect: the
  tail's taper pointed along the snake. Fix: `_normalize_horizontal(surface,
  min_ratio=1.25)` only pre-rotates genuinely tall art (aspect ≥ 1.25); near-square
  counts as slop and is left untouched. Docstrings updated to document the authored
  convention. Render probe re-run confirms correct orientation in all four
  directions (e.g. moving right → taper left, flush-right attach).
- **Web & Flutter were already correct** and are now probe-verified: web
  bakes the 90° into the prepared sprite and cancels it in `partAngle`
  (`DIR_ANGLE[d] − rot`; browser canvas probe: moving right → `cols [0.78,1,1,1]`,
  flushL 0.45 = tip, flushR 1.0 = attach ✓; moving down → taper up ✓).
  Flutter's `atan2(inward)` mapping verified visually on the emulator.

### Android (emulator) note — mute flow verified on-device via integration test

The emulator (`Medium_Phone_API_37.0`) ran the release APK fine in one long session
(gameplay, death, UI); afterward its **adb touch-injection pipe wedged** (`input tap`
produced no kernel events; keyboard `input keyevent` still worked — the app was
never frozen; screenshots only looked static because the menu motes were the only
pixels that ever differed). On-device M2 verification therefore runs as a Flutter
integration test (`integration_test/mute_flow_test.dart`, driven by Flutter's own
gesture pipeline — no adb input involved), which **passes** (`00:06 +2`):

1. fresh boot → PLAY → TAGALOG → START GAME, asserts `volume_up`, taps the HUD
   speaker, asserts `volume_off` and that `PrefsStore` persisted `snake_muted=true`;
2. a second boot asserts the restored muted choice renders `volume_off`
   immediately, then taps back to leave the device unmuted by default.

The win path on Android is covered by the unit test (`widget_test.dart`: board-fill
reports won, not died + the gold overlay path in `_buildGameOver`); the visual was
verified live on desktop and web.

Worth recording: the integration test caught a real M2 regression the faster
release session never surfaced — with the new mute button the HUD `Row`'s chips +
three IconButtons could overflow ~28 px on narrow phones / long names / big scores
(release builds just silently clip; test builds fail). Fixed by wrapping both HUD
chips in `Flexible` + `FittedBox(fit: BoxFit.scaleDown)` (name hugs left, score
hugs right, flex 2 favours the score chip) — identical look with slack space,
graceful shrink otherwise. Analyze + unit tests re-run green after the fix.

---

## M3 — Motion that feels the same everywhere
**Why:** this is the largest *feel* gap in the project. Desktop steps and renders
at the same 8–25 fps, so the snake visibly judders; mobile steps at 8–25 fps but
renders at 60 fps and interpolates visually. The same game feels like two
different products.

### Work
- **Desktop: decouple simulation from rendering.** Render at a fixed 60 fps
  (`clock.tick(60)`) and step the grid on an accumulator
  (`while acc >= step_ms: step()`). Interpolate each segment's screen position
  by the leftover fraction so the snake glides instead of snapping.
- This interacts well with the existing sway code (`images.py:416`): sway is
  already time-based and per-segment, so interpolation is additive and the head
  can stay grid-locked for precise aiming, exactly as documented.
- Watch for the coupling this exposes: the desktop HUD chips, popups, and
  `variants` bookkeeping are all currently inside the step loop and must move to
  the render loop.

**Done when:** desktop movement is as smooth as mobile, and gameplay timing is
identical at 60/120/144 Hz (it currently depends on monitor refresh rate).
**Effort:** L · **Risk:** medium (restructuring the main loop).

### Implementation log — M3 shipped 2026-10-17 ✅

- **Motion model note (plan-text correction, recorded).** The work bullet said to
  "interpolate each segment's screen position by the leftover fraction", but the
  reference builds do **not** lerp positions — verified: web `game.js::loop()` and
  Flutter `board_painter` draw grid-locked cells every frame and get their fluid
  feel from continuous-time decorations (sway sinusoids, motes, food pulse, popup
  rise/fade). Desktop now matches that model exactly. Positional glide stays off
  the table so the three platforms keep agreeing; if a glide is ever wanted it is
  an M12-style delight item that must land on all three at once.
- **Desktop changes** (`main.py`): new `RENDER_FPS = 60`; `game()` and
  `two_player_game()` keep their step bodies verbatim inside a ms accumulator
  (`acc += now - last_ms` → `while acc >= step_ms: acc -= step_ms`), with
  `speed = min(25, FPS + score // 50)` still driving `step_ms = 1000.0 / speed`
  on the ramp; a bounded-ahead clamp (`acc = min(acc, step_ms * 4)`) plus an
  explicit accumulator reset after every pause-menu return (WINDOWFOCUSLOST, P,
  ESC) so stalls can never replay as a burst of steps; the render block
  (board + motes, food pulse, snake sway, popups, HUD chips, flip) now runs
  every frame at `clock.tick(RENDER_FPS)`. The draw paths were already
  time-based internally (`pygame.time.get_ticks()` inside `draw_image_snake`,
  `draw_food`, `draw_popups`, `_draw_motes`), so they animate continuously
  without modification; HUD chips render per frame sizes as before; the snake
  stays grid-locked like web/Flutter.
- **Verification** (`%TEMP%\opencode\m3_cadence_probe.py`, SDL dummy driver,
  runs both REAL restructured loops, exit 0):
  - 1P no-input run: clean wall death at **3.18 s vs 3.17 s expected**
    (step cadence exactly 12 Hz) while the loop **rendered 59 fps** — the two
    rates are decoupled;
  - two consecutive frames (16.7 ms apart) differ in **523 sampled pixels**
    (per-frame animation alive; the pre-fix loop rendered once per step, so
    between-step frames were byte-identical);
  - 2P no-input run (the M2 driver *stubs* `two_player_game`, so this
    properly exercises the restructured 2P loop): both snakes die, termination
    at 3.52 s vs 3.42 s expected, 59 fps renders, scores untouched.
- **Gates**: `py -3.13 -m py_compile main.py images.py` OK; M2 offline driver
  re-run post-restructure with its full verdict **ALL OK** (mute/prefs,
  win/death screens, 2P winner-only row); desktop EXE rebuilt with the loop.

---

## M4 — One source of truth for everything that is duplicated three times
**Why:** the same tables, constants and rules are hand-maintained in Python, JS
and Dart. They have already drifted. This milestone is what stops the drift from
becoming a bug.

### Confirmed drift
| Thing | Desktop | Web | Flutter |
|---|---|---|---|
| Start speed | `FPS = 12` (`main.py:13`) | `START_FPS = 8` | `startFps = 8` |
| Animation frame cap | 64 (`images.py:250`) | 16 (`web/game.js:97`) | 8 (`sprites.dart:68`) |
| Food asset lookup | scans all PNGs in folder | **hardcoded filename** (`web/game.js:224-226`) | hardcoded candidate list (`sprites.dart:81-90`) |
| Sway direction blend | averages both axes | blends at `smoothstep(0.45)` | per-segment only, no blend (`board_painter.dart:220-247`) |
| Elongated-sprite fit | letterbox past 3:1 | letterbox past 3:1 | width-locked cover, **no letterbox guard** (`_drawImage`) |

- The food filename appears verbatim in **four** places (`web/game.js`,
  `sw.js`, `sprites.dart`, `test/assets_test.dart`). Rename or add
  `food_0.png` and it silently breaks in a way that is hard to trace.

### Work
- Create `shared/game_content.json` as the single authored source for:
  `POPUP_WORDS`, `VOICE_PHRASES`, colour palette, speed curve (start fps, cap,
  ramp), animation fps + frame caps, part fill ratio, sway amount, and the food
  asset **discovery rule** (not a filename).
- Have `sync_web_to_flutter.bat` grow into a real sync script that (a) mirrors
  `web/` → `flutter_app/assets/www/`, (b) copies the shared JSON into both, and
  (c) **fails loudly** if the two trees have drifted or a referenced asset is
  missing — so this class of bug is caught at build time instead of at runtime.
- Port the letterbox guard and the sway blend into Dart so all three renderers
  agree.
- Document the convention (in `assets/README.txt`) that adding art/audio needs
  **no code change** — which is already true in Dart via `AssetManifest`
  discovery, and should be made true everywhere.

**Done when:** changing the start speed or a popup word is a one-file edit;
all three implementations provably agree on the rules table.
**Effort:** M · **Risk:** medium (touches all three codebases — but each change
is mechanical).

### Implementation log — M4 shipped 2026-10-17 ✅

- **`shared/game_content.json` is live and authoritative.** One table holds:
  the speed curve (`speed.startFps/capFps/rampScorePerStep`), animation
  cadence + caps (`animation.snakeFps/foodFps/snakeFrameCap`), the part fit
  ratio (`part.fillRatio`), sway (`sway.amount/blendAt`), popup words/colors/
  life (`popup.*`), the voice rotation + phrases (`voices.*`), the food
  discovery rule (`food.known/probeCount` + folder scan) and the shared
  accent palette (`palette.*`). User decided **12 fps start everywhere**
  (desktop's pace) — the web/Flutter apps speed up slightly, cap/ramp must
  stay identical by construction.
- **All three runtime-read the same file.** Desktop: `images.py` loads it at
  import (`content_value()` nested lookup; fallbacks mirror the canonical
  values). Web: `game.js` fetches `game_content.json` before boot
  (`applyContent()`; the `let` tables keep mirror-fallbacks; `sw.js`
  precaches it network-first, cache v8). Flutter: `lib/content.dart`
  (`GameContent`) loads in `main()` before `runApp`, and `pubspec.yaml`
  declares the synced copy. Blast radius per platform:
  desktop — `FPS/FPS_CAP/RAMP_SCORE_PER_STEP`, both ramp call-sites,
  `VOICE_FILES`/`VOICE_PHRASES` rebuild, `load_sounds` stems, `POPUP_WORDS`,
  popup colors (unified to the web/dart hexes — desktop had drifted at
  `#ffaaaa/#aad7ff`), `FoodAssets` dir+fps, `SnakeAssets.ANIM_FPS`,
  frame cap (unified 64→16), `PART_FILL_RATIO`, `SWAY_AMOUNT`;
  web — START_FPS, fill/sway/anim fps, loadFrames cap, popup tables,
  voice rebuild, food probes;
  Flutter — `stepMs`, `_loadFrames` cap, `loadFoodSprite`, voice phrase
  lookup, popup words/colors/life, mote tints + team accents (`teamGreen/
  teamBlue` from `palette`), HUD accent sites in `main.dart`.
- **Renderer agreement (the two Flutter gaps from the drift table) closed:**
  - sway blend ported verbatim from `web/game.js swayOffsets` — interior
    segments blend direction + perpendicular towards the NEXT segment at
    `smoothstep(sway.blendAt)` (result normalized); heads/tails stay
    grid-locked (`board_painter._sway` + `_blendDir`/`_smoothstep`).
  - letterbox guard ported from `images.py::_fit_cell`/web `fitCell` into
    `board_painter._drawImageEx`: art within `part.fillRatio` (3.0)
    stretches across the whole cell so segments meet flush; more elongated
    art letterboxes centred (previously width-locked cover left the
    near-square p2 art a hair short of the cell).
- **Food lookup is now rule-based everywhere.** `sprites.loadFoodSprite`
  scans the `AssetManifest` for any PNG under `assets/food` (alphabetical
  order, same as the desktop folder scan) with `food.known` as the probe
  fallback; web probes `food.known` + `food_0..probeCount`; desktop keeps
  its folder scan. Renaming the food file is now a one-line JSON edit on
  every platform — the four-site hardcode is gone.
- **Drift dies at build time, from two directions.**
  `sync_web_to_flutter.bat` copies canonical → `web/` + `flutter_app/assets/`
  and byte-`fc`-verifies both copies before mirroring assets; and
  `flutter_app/test/shared_content_test.dart` pins that the web copy is
  byte-identical, every `GameContent` accessor matches the canonical
  numbers, and every voice file in the table resolves its phrase (a
  `debugInject` test hook exercises the loaded path under the plain test
  binding).
- **Verification:** desktop — `py_compile` clean, M3 cadence probe ALL OK
  (12 Hz step + decoupled render intact after the re-plumb), M2
  screen/leaderboard driver all-PASS. Web — live-served page logged
  `[Content] shared rules applied: startFps=12 capFps=25 sway=0.14 fill=3`,
  menu screenshot clean, only the pre-existing optional-frame probe 404s
  in the log. Device — `mute_flow_test` 2/2 on the emulator, rebuilt APK
  boots with all sprites + food (via the new manifest scan) + 4+4 voice
  lines and no fallback warnings. EXE rebuilt through `build_windows.bat`
  (now `--add-data`-bundles the shared file; verified inside the onefile
  TOC: `bundled entries: ['game_content.json']`). The rebuild also
  hardened the bat: a locked `dist\` (running game copy) used to let the
  script "succeed" on the stale previous EXE — it now detects that and
  fails loudly.
- **Deliberately still code-side (documented in `assets/README.txt`):** the
  Flutter HUD's gold-text/button-gradient shades (const-context derived
  colors), CSS chrome colors, and desktop's vector-fallback tuples — the
  platform-specific chrome around the shared accents.

**Done-when check:** changing the start speed or a popup word is a one-file
edit (`shared/game_content.json` → sync → rebuild) ✅; all three
implementations agree on the rules table — web/desktop by construction
(they fetch/import the shared file), Flutter by pinned tests (fallback ==
canonical == what the loader serves) ✅.

---

## M5 — Parity: close the two big capability gaps
**Why:** the platforms should not feel like different games.

- **Desktop has no snake select.** `main.py:959` offers
  `1 PLAYER / 2 PLAYER / LEADERBOARD / EXIT`, and 1P is hardwired to the green
  Tagalog snake (`assets_p1`). Web and Flutter both let you pick 🟢 Tagalog or
  🔵 Bisaya. Add the select step to desktop 1P, persisted in `prefs.json`
  (which already stores `name`, so add `snake`). Blue snake + blue HUD accent +
  blue arena glow, as the other two platforms do.
- **The PWA has no D-pad.** `web/README.md:12` promises "swipe on the screen or
  use the on-screen D-pad (D-pad hides automatically on desktop/mouse
  devices)" — I grepped: there is **no D-pad markup, CSS or JS** in `web/`.
  Flutter has one (`main.dart:624-647`). Add the same D-pad to the PWA with the
  documented auto-hide behaviour (show on coarse pointers / touch devices,
  hide on hover-capable devices), or amend the README. My recommendation is to
  **build it** — swipe-only is genuinely hard to play one-handed on a large phone.
- Desktop background/menu artwork: `images.UIAssets` (`images.py:648-720`)
  supports custom backgrounds, a menu background, a logo and button art, and
  `assets/README.txt:111-117` documents an in-game BACKGROUND picker — but
  **neither `assets/background/` nor `assets/menu/` exists**, and
  `background_picker_screen()` exists in `main_backup.py` but was **deleted** from
  `main.py`. Either restore the picker + create a starter background, or delete the
  dormant loader and the doc section. A menu background is the single cheapest
  visual upgrade available, and the machinery is already written and unused.

**Done when:** a player can pick either snake and play either platform, and the
mobile PWA is playable without a keyboard.
**Effort:** M (desktop select + D-pad) / S (background picker restore)
**Risk:** low.

---

## M6 — Performance: remove per-frame garbage
**Why:** not a crash risk, but wasted battery and dropped frames on phones —
the exact thing reviewers notice.

### Confirmed per-frame allocations
- **Desktop motes:** `_draw_motes` creates a fresh `SRCALPHA` `Surface` **per
  mote, per frame** (`main.py:426-429`) — 45 surfaces per frame at 60 fps, each
  blitted. Pre-render one soft-dot sprite per tint at startup and blit it scaled.
- **Desktop food glow:** a new `CELL*2` SRCALPHA surface every frame
  (`main.py:460-463`). Pre-render once.
- **Desktop popups:** `pygame.transform.smoothscale` on both the outline and the
  base surface for every live popup, every frame (`main.py:351`). The scale
  animation is a known curve — bake a small strip of pre-scaled frames, or
  quantise the scale so results are cacheable.
- **Web board:** `drawBoard()` builds a linear gradient, **two** radial gradients
  and a board panel **every frame** (`web/game.js:516-574`). Cache them as
  offscreen canvases keyed on size; only the motes/vignette need per-frame work.
- **Web asset trim:** `trimTransparent` runs a per-pixel JS loop
  (`web/game.js:140-157`) over every art file at startup. On a 512² body
  texture that's ~260k iterations per part. Use `drawImage` + a downscaled
  `getImageData` probe (e.g. 64²) to find the bounds, then re-blit at full res.
- **Flutter:** `shouldRepaint` is hardcoded `true` (`board_painter.dart:515`) so
  the painter repaints at 60 fps even while paused. Return `false` when nothing
  that matters changed.

**Done when:** no `Surface`/`Surface`-equivalent is constructed inside a draw
loop; Flutter idles at ~0 fps while paused; PWA frame time is flat across a run.
**Effort:** M · **Risk:** low (pure optimisation, output must be pixel-identical
— verify by screenshot diff before/after).

---

## M7 — Visual polish & art direction
**Why:** the game already looks good; these are the flaws a reviewer notices in
the first 10 seconds.

- **HUD chips cover the play area.** The desktop board is fullscreen
  (row 0 = y 0–40) and the chips are drawn at `y = 14` with ~74 px of height
  (`main.py:644-650`), so food and snake in the top row sit **under** the chips.
  Web already solves this with `HUD_TOP = 52` (`web/game.js:30`). Reserve an
  equivalent top band on desktop (inset the arena) or move the chips into the
  safe margin.
- **2-player "X is out!" text is drawn on top of the Best chip** — both centred
  at y=14 (`main.py:827-830`). Move it or merge it into the chip row.
- **Desktop menus are flat translucent panels**; the PWA uses
  `backdrop-filter: blur(10px)` with layered radial glows (`style.css:61-72`) and
  Flutter uses gradient buttons with a hard drop shadow. Unify: add a cheap
  darkening + gradient/blur pass to the desktop `draw_panel` so all three share
  one look.
- **Default font everywhere.** `pygame.font.Font(None, …)` / `system-ui` /
  Roboto. A single branded display face for the title would lift the whole
  project — and the "SNAKE VERSUS" gradient-clipped title already exists in CSS
  and Flutter, so it's mostly a desktop port.
- **Glow/audio-visual tuning pass:** unify the head/body glow radii, the food
  pulse amplitude (`1 ± 0.07`, `board_painter.dart:186`), and the vignette
  strength across platforms so the arena reads identically.
- **Sway cross-check:** the swerve axis blending differs per platform (see M4).
  Align it, then check a long snake making a hard corner — that's the frame
  where the current implementations diverge most visibly.

**Done when:** a screenshot of any platform's menu, mid-game and game-over would
be hard to tell apart in style.
**Effort:** M · **Risk:** low, but this is taste-based — iterate on screenshots.

---

## M8 — Branding, version, About screen
**Why:** the project currently has **eight different names for itself**, which is
the most "unfinished" signal a reviewer can pick up on.

| Where | Name |
|---|---|
| Window caption (`main.py:944`) | `Esneyk Geym` |
| EXE | `Tagalog VS Bisaya` |
| Desktop menu title | `SNAKE VERSUS` |
| Web `<title>` / manifest `name` | `Tagalog vs Bisaya - Snake` |
| PWA `short_name` (`manifest.json:3`) | **`SnakeGame`** |
| Flutter app title | `Tagalog vs Bisaya` |
| Distribution zip | `Tagalog-Vs-Bisaya-PWA.zip` |
| README.txt heading | `SNAKE GAME - PYTHON WINDOWS APP` |

### Work
- Pick one product name and one tagline. Apply it to: window caption, EXE name,
  menu title, web title, `manifest.json` (`name` **and** `short_name`), Flutter
  title, launcher label, zip name, and every README. Keep "Esneyk Geym" only if
  it's a deliberate in-joke, in which case use it consistently everywhere.
- **Fix the launch colour mismatch:** `manifest.json` uses `#121218` but the CSS
  `--bg0` is `#0c0d14` (`style.css:3`). A wrong `background_color` shows as a
  flash of the wrong colour on every cold start. Match them to the app's darkest
  colour.
- Add a **version string** in one shared place, surfaced in an **About / Credits**
  screen (credits for the art, audio and the midterms attribution already implied
  by the "MIDTERMS EDITION" eyebrow). Show it on the menu and in the About screen
  in all three platforms.
- Add a `CHANGELOG.md` and start it with the current state.

**Done when:** one name, one colour, one version, visible on all three platforms.
**Effort:** S–M · **Risk:** low (mechanical), but touches every user-visible string.

---

## M9 — Repo hygiene & release engineering
**Why:** two of the biggest real risks in this project are operational, not
code-level.

### Two genuine safety problems in `build_windows.bat`
- **`setx /M PATH "%PATH%;C:\Program Files\TagalogVsBisayaGame"` (line 51)
  writes the machine-wide PATH from the current shell's PATH.** `setx`
  **truncates at 1024 characters** and does not expand the full registry value.
  On a machine with a long PATH this silently corrupts the *system* PATH for
  every user on the box. A game installer should never do this. Replace with a
  shortcut-only install, or append via a small registry-safe script.
- **The installer demands Administrator**, auto-installs Python 3.13 via
  `winget`, and writes into `C:\Program Files`. For a midterms project this is
  disproportionate and will simply fail on a managed/school machine.

### Work
- Split the build into **two paths**: a zero-privilege **portable build**
  (PyInstaller → `dist\`, run from anywhere, no admin, no PATH edits, no
  Program Files) and a clearly-labelled **optional installer** that only creates
  a Start Menu shortcut. Portable should be the default; the admin path should be
  opt-in, not the default.
- **`.gitignore`** — there is none at the repo root. Add one covering `build/`,
  `dist/`, `__pycache__/`, `*.spec`, `*.exe`, `scores.json`, `prefs.json`.
- **`git init` + first commit.** The workspace is not a repo, which is why there
  are four copies of `assets/`, `build/`, `dist/` and `_art_backup_untrimmed/`
  (both at the workspace root *and* inside the project folder). One repo, one
  copy, everything else either ignored or deleted deliberately.
- **APK size:** `flutter_app/assets/www/` bundles the whole PWA — but the Flutter
  app is pure Dart and only reads `assets/www/assets/{audio,p1,p2,food}` from it.
  `index.html`, `game.js`, `style.css`, `sw.js` and `README.md` (5 of 34 synced
  files) are dead weight in the APK. Add robocopy exclusions + verify the
  `pubspec.yaml` asset list still covers everything `sounds.dart`/`sprites.dart`
  load, and measure the APK before/after.
- Make the build reproducible: verify `flutter test`, `flutter analyze`, and a
  `py -3.13 -m py_compile main.py images.py` gate before packaging.

**Done when:** a clean clone builds on a machine without admin rights, the
system PATH is never touched, and there is exactly one copy of every file.
**Effort:** M · **Risk:** medium for the `.bat` rewrite (test the installer path
in a throwaway VM or skip shipping it).

### Implementation log — M9 shipped 2026-10-17 ✅ (chooser-scope trim agreed)

- **Version control is live.** Git installed (winget Git.Git 2.55.0), repo rooted
  at the project folder. First commit `b69206d` = the full M1–M3 state (168
  files, 10.8 k lines), `.gitignore` covers build/dist/`*.spec`/pycache,
  per-user files (`scores.json`, `prefs.json`), the distribution zip,
  `_user_data/`, `.venv/`, Flutter build state (`.dart_tool/`, `.gradle/`,
  `local.properties`, `*.iml`). Second commit `8c47274` = the M9 changes below.
  Every future milestone is now diffable and revertible.
- **`build_windows.bat` rewritten as a portable-only, zero-privilege build.**
  Removed entirely: the admin check, `setx /M PATH` (the 1024-char machine-PATH
  corruption), the Program Files install, the all-users Start-Menu deployment,
  and the winget Python auto-install (replaced with a clear "get Python 3.13
  (winget … --scope user)" message). Dependencies now live in a project-local
  **`.venv`** (`pip install -r requirements.txt` pins `pygame>=2.6.0`), the
  PyInstaller command is unchanged, and the only optional post-build extra is a
  per-user Start-Menu shortcut behind a `choice` prompt. Dogfooded end-to-end:
  script built `dist\Tagalog VS Bisaya.exe` (18.6 MB) and the EXE ran a clean
  14 s menu loop under SDL dummy (plain pygame 2.6.1 — new dep set).
- **Clean-clone acceptance (the done-when):** a fresh `git clone` into `%TEMP%`
  ran the new script and produced the same EXE, which boots cleanly — no admin
  anywhere. (First attempt cloned the pre-M9 commit by mistake and hit the OLD
  admin gate, harmlessly refusing; commit-then-reclone was the fix.)
- **Per-user prefs (small legacy defect fixed in passing).** `PREFS_FILE` was
  still CWD-relative while scores got the `%LOCALAPPDATA%` treatment in M1 —
  a portable EXE launched from a read-only folder would silently lose its
  remembered name/mute. `main.py` now resolves both through a shared
  `_per_user_file()` helper (`%LOCALAPPDATA%\TagalogVsBisaya` first, CWD
  fallback).
- **APK bundle trimmed to exactly what the app reads.** `pubspec.yaml` no longer
  declares `assets/www/` (which swept index.html/game.js/style.css/sw.js/
  manifest.json/README into the APK where nothing can execute them); the
  explicit game-asset entries remain. `sync_web_to_flutter.bat` now mirrors
  **only** `web\assets` → `flutter_app\assets\www\assets` and **fails loudly**
  if a required asset dir (p1/p2/audio/food/icon) is missing or did not sync —
  first slice of M4's fail-loud sync. Flutter tree went 34 → 28 files; gates
  green (`analyze` clean, 9/9 tests incl. the bundling test), rebuilt APK
  boot-verified on the emulator (sprite + audio preload logs all clean).
- **Honest measurement:** APK size 52.2 → **52.2 MB** — the dropped PWA files
  were ~text-level bytes; the weight is libflutter.so + the (required) game
  art. The real win is correctness: the bundle list can no longer drift from
  what `sounds.dart`/`sprites.dart` read. (If a smaller delivery is ever
  wanted, `flutter build apk --split-per-abi` is the lever, not asset pruning.)
- **Deferred, per agreed scope:** the "exactly one copy of every file" declutter
  — the workspace root is already clean (single project folder), and the
  remaining duplicates are ignored build artifacts (`build/`, `dist/`,
  `_art_backup_untrimmed/` = 1.5 MB source originals, deliberately committed).

---

## M10 — Make the documentation true
**Why:** three READMEs currently describe features that don't exist. For a
graded project this is the cheapest credibility to earn — and I verified each one.

- `README.txt` — heading says "SNAKE GAME - PYTHON WINDOWS APP"; the feature
  list doesn't mention the Tagalog/Bisaya theme, 2-player, voice lines or
  popups; and it tells you the EXE is `dist\SnakeGame.exe` when
  `build_windows.bat:37` produces `dist\"Tagalog VS Bisaya.exe"`.
- `web/README.md:9-14` — "2-player mode removed (single player only)" ✅, but
  "or use the on-screen D-pad (D-pad hides automatically on desktop)" ❌ (no
  D-pad exists), and it refers to "the `SnakeGame` folder" which doesn't exist
  (it also repeats the wrong `dist\SnakeGame.exe` name from line 13's parent).
- `assets/README.txt:105-142` — documents an in-game **BACKGROUND** picker and
  `assets/background/` + `assets/menu/` layouts; neither the folders nor the
  picker exist in `main.py` (only in the deleted-from-main backup). Also says
  food PNGs "play as an animation in alphabetical order" — true on desktop, but
  the web/Flutter builds hardcode one filename instead.
- `flutter_app/README.md:61` says "ESC quits to menu"; the code **pauses** on ESC
  (`main.dart:329-332`), and quitting is the ✕ button.
- `sprites.dart:15-18` has a comment about `tail1.png`/`tail2.png` — those
  files don't exist in the bundle. Trim the archaeology from comments.

Rewriting all of these to match reality (or making reality match) is a
self-contained milestone. Add screenshots/GIFs and a short "how to play" with
the control table.

**Effort:** S · **Risk:** none.

---

## M11 — Tests for the rules that are duplicated three times
**Why:** `queue_turn` is implemented three times and is the single rule most
likely to cause an unfair death (chained 180° into your own neck). It's already
tested in Dart (`widget_test.dart:23-28`) and untested in Python and JS.

- Create `shared/test_vectors.json` — inputs and expected outputs for
  `queue_turn`, collision-with-tail-vacating, the speed curve, `random_food`
  bounds, score sorting/trimming. Assert **all three** implementations agree.
  This is the real payoff of M4: a rule can no longer drift silently.
- Add `tests/test_main.py` (pure-python, no pygame display needed): queue_turn,
  score add/sort/top-10 trim, `best_score`, prefs round-trip, corrupt-JSON
  handling (ties into M1).
- Add a minimal headless harness for `web/game.js` (the pure functions can be
  exported behind a guard) covering the same vectors.
- Keep and extend `flutter_app/test/assets_test.dart` — it's genuinely good
  (it asserts every PNG decodes and every MP3 is bundled, which guards a real
  AssetManifest pitfall).

**Effort:** M · **Risk:** low.

---

## M12 — Delight: the small stuff that makes it memorable
**Why last, but not least** — these are what people remember. Each is
independent; pick the ones that land.

- **Countdown `3 · 2 · 1 · GO!`** before the snake moves, in all three. The single
  highest-impact "this feels like a real game" addition.
- **Screen shake on death**, decaying over ~300 ms (all three — cheap, and it's
  the moment people feel).
- **Confetti / gold burst on a win** (pairs with M2).
- **Combo on fast bites:** eat again within N ticks → `×2`, `×3` with a bigger
  popup and a higher-pitched blip.
- **Last-food warning:** when only one free cell remains, pulse the remaining
  food and tint the vignette — a great tension builder for free.
- **Milestone flashes** every 100 points (`"100!"`, `"200!"`).
- **High-score ceremony:** a dedicated "NEW RECORD" moment (the text exists in
  all three; give it a proper beat).
- **Personal best line on the menu** — `BEST: 340` before you even start.
- **Colour-blind / reduced-motion respect:** honour
  `prefers-reduced-motion` in the PWA (skip shake and sway) — one CSS media
  query plus a flag.
- **Pause on blur is already done** ✅ — add the same for a locked phone
  (`ESC` on desktop, lifecycle on mobile) ✅ already there too. Consider a
  "tap to resume" affordance.
- **Leaderboard polish:** show the player's own rank highlighted, and date/time
  stamps. Consider a team column (Tagalog/Bisaya) so the theme shows up in data.
- **`+10` as a popup word** (`main.py:298`) is odd next to voice phrases — every
  eat is +10. Replace it with something thematic or drop it.

**Effort:** S each · **Risk:** low.

---

## Suggested order & dependencies

```
M1 (crash-proofing)      ──┐
M9 (repo + safe build)   ──┼── do these two first: they de-risk everything else
M10 (docs true)          ──┘

M4 (single source)  ──► M2 (win + audio)   M11 (shared test vectors)
M3 (motion)        ──► M6 (performance) ──► M7 (visual polish)
M5 (parity)        ──► M8 (branding/About) ──► M12 (delight)
```

- **M4 before M2/M11** — both consume the shared content tables, and doing M4
  first means the win screen and the tests get written once, not three times.
- **M3 before M6** — interpolation changes what "per frame" means; do the loop
  restructure first, then profile.
- **M7 and M8 before M12** — polish the frame before adding effects to it.
- **M1 and M9 are independent** and can go in parallel with everything else.

Each milestone is independently shippable and independently valuable — if you
only ever do four, do **M1, M9, M2, M4**.

---

## Implementation log — user art refresh 2026-10-17 ✅ (out-of-band, not a milestone)

- **Bisaya `p2` snake art refreshed** (workspace `assets/p2/`): new `body.png`,
  `corner.png`, `tail.png` (square 128×128 frames from the user's Aseprite
  sources, also committed next to them). `head.png` and the food set are
  untouched. No code change anywhere — the art drop-in conventions from
  `assets/README.txt` hold on all three platforms.
- **Propagation:** the three PNGs were copied desktop → `web/assets/p2/` and
  then mirrored by `sync_web_to_flutter.bat` into the APK asset tree
  (hash-verified as always). Desktop/web/mobile each render the same new files.
- **Verification:**
  - *Desktop:* a real `main.game()` loop ran under the SDL dummy display
    driving the actual game with the new `SnakeAssets("assets/p2", …)` —
    frames captured through a 90° bend and a straight run show sprites at
    every orientation, no vector fallback. Rebuilt the EXE through
    `build_windows.bat`; the onefile TOC carries the three new PNGs
    (`assets\p2\body.png` / `corner.png` / `tail.png` + the `.aseprite`
    sources, which the runtime ignores).
  - *Mobile:* new APK (52.2 MB) built, installed, and booted on
    `Medium_Phone_API_37.0` — sprite logs show the 128×128 p2 files loaded;
    a new `flutter_app/integration_test/p2_art_drive_test.dart` drives the
    REAL app Menu → PLAY → BISAYA → name → game on-device (tap-based, immune
    to the emulator's wedged adb input pipe), steers the snake through the
    D-pad buttons while an external `adb shell screencap` loop screenshots
    mid-gameplay, mutes first so no audioplayers frame-updater callback is
    left dangling at dispose, then clears only the persisted mute pref.
    `flutter test integration_test/p2_art_drive_test.dart -d emulator-5554`
    = **green** ([Audio] voice lines 4 tagalog / 4 bisaya still resolve).
- **Emulator note:** system-level touch/key injection (`input tap`,
  `input keyevent`) into the app is dead on this AVD; Flutter-test taps are
  the only reliable UI driver — this test file is the reusable pattern for
  future on-device art/flow checks.
