/* Tagalog vs Bisaya — Snake (PWA / mobile edition)
 * Single-player only. Swipe or arrow keys to steer.
 */
"use strict";

// ── Shared rules (M4) ──────────────────────────────────────────────────────
// game_content.json (synced from <project>/shared/ by sync_web_to_flutter.bat)
// is the single source of truth for every value the three implementations
// must agree on: speed curve, animation fps + caps, sway, part fit ratio,
// popup tables, voice phrases and the food discovery rule. It is fetched
// before boot; the `let` constants below are fallbacks mirroring the
// canonical values and only apply if the fetch fails (e.g. file://).
let GAME_CONTENT = {};
window.__CONTENT = GAME_CONTENT; // exposed for debugging/verification

async function loadContent() {
  try {
    const res = await fetch("game_content.json", { cache: "no-cache" });
    if (res && res.ok) GAME_CONTENT = await res.json();
    window.__CONTENT = GAME_CONTENT;
  } catch (e) { /* file:// or offline: fallbacks keep the game running */ }
}
function contentGet(path, fallback) {
  let node = GAME_CONTENT;
  for (const key of path) {
    if (node == null || typeof node !== "object" || !(key in node)) return fallback;
    node = node[key];
  }
  return node === undefined || node === null ? fallback : node;
}
function applyContent() {
  START_FPS = contentGet(["speed", "startFps"], START_FPS);
  PART_FILL_RATIO = contentGet(["part", "fillRatio"], PART_FILL_RATIO);
  SWAY_AMOUNT = contentGet(["sway", "amount"], SWAY_AMOUNT);
  SNAKE_ANIM_FPS = contentGet(["animation", "snakeFps"], SNAKE_ANIM_FPS);
  FOOD_ANIM_FPS = contentGet(["animation", "foodFps"], FOOD_ANIM_FPS);
  const words = contentGet(["popup", "words"], null);
  if (Array.isArray(words) && words.length) POPUP_WORDS = words.map(String);
  const cols = contentGet(["popup", "colors"], null);
  if (Array.isArray(cols) && cols.length) POPUP_COLORS = cols.map(String);
  const voices = contentGet(["voices"], null);
  if (voices && typeof voices === "object") {
    // Blip stays OUT of the arrays here; playRandomEatSound composes it in
    // first, matching the desktop rotation membership exactly.
    const rebuilt = {};
    const phraseMap = {};
    for (const [team, spec] of Object.entries(voices)) {
      if (!spec || typeof spec !== "object") continue;
      rebuilt[team] = (spec.lines || []).map((e) => e.file).filter(Boolean);
      if (spec.blip && spec.blipPhrase) phraseMap[spec.blip] = spec.blipPhrase;
      for (const e of spec.lines || []) {
        if (e && e.file && e.phrase) phraseMap[e.file] = e.phrase;
      }
    }
    if (Object.keys(rebuilt).length) { VOICE_FILES = rebuilt; VOICE_PHRASES = phraseMap; }
  }
  console.log(
    "[Content] shared rules applied: startFps=" + START_FPS +
    " capFps=" + contentGet(["speed", "capFps"], 25) +
    " sway=" + SWAY_AMOUNT + " fill=" + PART_FILL_RATIO);
}

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

// roundRect polyfill for older Android WebViews
if (typeof CanvasRenderingContext2D !== "undefined" && !CanvasRenderingContext2D.prototype.roundRect) {
  CanvasRenderingContext2D.prototype.roundRect = function (x, y, w, h, r) {
    const rr = typeof r === "number" ? r : 8;
    this.moveTo(x + rr, y);
    this.arcTo(x + w, y, x + w, y + h, rr);
    this.arcTo(x + w, y + h, x, y + h, rr);
    this.arcTo(x, y + h, x, y, rr);
    this.arcTo(x, y, x + w, y, rr);
    this.closePath();
    return this;
  };
}

const COL = {
  bg: "#0c0d14", bg2: "#16182a", grid: "rgba(255,255,255,0.055)",
  gridBold: "rgba(255,255,255,0.1)", white: "#f2f3fa",
  green: "#3fe07f", head: "#8dffab", blue: "#5aa8ff",
  red: "#ff5d5d", yellow: "#ffd246", gray: "#9aa0b4",
};
let START_FPS = 8;            // fallback; canonical value = shared speed.startFps
let HUD_TOP = 52;             // px reserved for the HUD pill overlay (+ safe-area)
/* iOS standalone apps run under the notch/Dynamic Island (status-bar-style
   is black-translucent + viewport-fit=cover). env(safe-area-inset-top)
   reports that height; measure it through a probe element because JS
   cannot read env() directly. 0 on Android/desktop. */
function safeInsetTop() {
  const probe = document.createElement("div");
  probe.style.cssText = "position:fixed;top:0;left:0;visibility:hidden;pointer-events:none;width:0;height:0;padding-top:env(safe-area-inset-top, 0px);";
  document.body.appendChild(probe);
  const v = Math.round(parseFloat(getComputedStyle(probe).paddingTop) || 0);
  probe.remove();
  return v;
}

// ── Grid / part geometry ──────────────────────────────────────────────────
// Every part is pre-trimmed to its opaque pixels, then scaled to cover exactly
// one board cell, so segments meet edge to edge whatever size the art is.
// Every part is pre-trimmed to its opaque pixels, then scaled to cover exactly
// one board cell, so segments meet edge to edge whatever size the art is.
// Fallbacks mirror the canonical values in game_content.json; applyContent()
// overwrites them from the shared rules at boot.
let PART_FILL_RATIO = 3.0; // wider/taller than this and the part is letterboxed
let SWAY_AMOUNT = 0.14;    // slither amplitude as a fraction of one cell
const CORNER_IN = "1,0";      // authored elbow: enters left, exits down (right bend)
const HORIZONTAL_PARTS = new Set(["body", "tail"]); // long axis runs along travel
const PARTS = ["head", "body", "corner", "tail"];

// ctx.rotate() is clockwise-positive (y grows down), so this maps art that
// faces right onto each direction of travel.
const DIR_ANGLE = { "1,0": 0, "0,-1": -Math.PI / 2, "-1,0": Math.PI, "0,1": Math.PI / 2 };
// A right turn is clockwise on screen: east→south→west→north→east.
const RIGHT_TURN = { "1,0": "0,1", "0,1": "-1,0", "-1,0": "0,-1", "0,-1": "1,0" };
const LEFT_TURN = { "1,0": "0,-1", "0,-1": "-1,0", "-1,0": "0,1", "0,1": "1,0" };
const OPPOSITE = { "1,0": "-1,0", "-1,0": "1,0", "0,1": "0,-1", "0,-1": "0,1" };
const dirKey = (d) => d[0] + "," + d[1];

// ── Assets ────────────────────────────────────────────────────────────────
const PART_DIRS = { tagalog: "assets/p1", bisaya: "assets/p2" };
const PART_SETS = {};  // set -> part -> { frames: [canvas], rot }
const PART_SPRITES = {}; // set -> part -> [canvas] scaled to the current cell
let playerSet = "tagalog"; // "tagalog" | "bisaya"
const SOUNDS = {};
// Voice lines per snake (additive rotation for rice eats).
// Fallbacks mirror game_content.json `voices`; applyContent() overwrites.
// NOTE: unlike the desktop table these arrays do NOT include the team's
// `<team>_eat` blip — playRandomEatSound() composes it in first, giving the
// same rotation membership as desktop.
let VOICE_FILES = {
  tagalog: ["tag-arman", "tag-babalu", "tag-nenegb", "tag-tamis-malupiton"],
  bisaya: ["bis-lami", "bis-sulit", "bis-unlirice", "bis-yummy"],
};
let VOICE_PHRASES = {
  "tag-arman": "WOW ANSARAP!",
  "tag-babalu": "WOW NAMAN!",
  "tag-nenegb": "MA ANO ULAM?!",
  "tag-tamis-malupiton": "ANG TAMIS!",
  "tagalog_eat": "HALIMAW SA SARAP!",
  "bis-lami": "LAMI!",
  "bis-sulit": "SULIT!",
  "bis-unlirice": "UNLIRICE!",
  "bis-yummy": "YUMMY!",
  "bisaya_eat": "WALANG KANIN?!",
};
const VOICE_AUDIO = {};
let foodFrames = [];
let foodSprites = [];
let playerSnake = "tagalog"; // "tagalog" | "bisaya"
const music = new Audio("assets/audio/bg_music_lobby.mp3");
music.loop = true;
music.volume = 0.5;

function loadImage(src) {
  return new Promise((res) => {
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = () => res(null);
    img.src = src;
  });
}

let SNAKE_ANIM_FPS = 8;   // fallback; canonical = shared animation.snakeFps
let FOOD_ANIM_FPS = 6;    // fallback; canonical = shared animation.foodFps
function animFrame(frames, fps) {
  if (!frames || !frames.length) return null;
  if (frames.length === 1) return frames[0];
  return frames[(performance.now() / (1000 / fps) | 0) % frames.length];
}
async function loadFrames(base, part, maxN = null) {
  // supports `<part>.png` (static) AND `<part>_0.png`, `<part>_1.png`, …
  // Frame cap comes from the shared rules (animation.snakeFrameCap).
  const cap = maxN === null ? contentGet(["animation", "snakeFrameCap"], 16) : maxN;
  const frames = [];
  const first = await loadImage(`${base}/${part}.png`);
  if (first) frames.push(first);
  for (let i = 0; i < cap; i++) {
    const f = await loadImage(`${base}/${part}_${i}.png`);
    if (!f) break;
    frames.push(f);
  }
  return frames;
}

// ── Sprite preparation ────────────────────────────────────────────────────
function makeCanvas(w, h) {
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round(w));
  c.height = Math.max(1, Math.round(h));
  return c;
}
function draw2d(c) {
  const g = c.getContext("2d");
  if (g) g.imageSmoothingQuality = "high";
  return g;
}

/* Crop the transparent border away. The art is authored on big canvases with
   lots of empty space; keeping that padding is what made segments render small
   and misaligned, so it never reaches the cell scaler. */
function trimTransparent(src) {
  const w = src.naturalWidth || src.width;
  const h = src.naturalHeight || src.height;
  if (!w || !h) return null;
  const full = makeCanvas(w, h);
  draw2d(full).drawImage(src, 0, 0);
  let px;
  try {
    px = full.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, full.width, full.height).data;
  } catch (e) {
    // Readback is blocked on file:// URLs; the bundled art ships pre-trimmed,
    // so fall back to the canvas as-is.
    return { canvas: full, w: full.width, h: full.height };
  }
  let x0 = w, y0 = h, x1 = -1, y1 = -1;
  for (let y = 0; y < h; y++) {
    const row = y * w;
    for (let x = 0; x < w; x++) {
      if (px[(row + x) * 4 + 3] > 6) {
        if (x < x0) x0 = x;
        if (x > x1) x1 = x;
        if (y < y0) y0 = y;
        if (y > y1) y1 = y;
      }
    }
  }
  if (x1 < 0) return { canvas: full, w, h }; // fully transparent
  const bw = x1 - x0 + 1, bh = y1 - y0 + 1;
  if (bw === w && bh === h) return { canvas: full, w, h };
  const t = makeCanvas(bw, bh);
  draw2d(t).drawImage(full, x0, y0, bw, bh, 0, 0, bw, bh);
  return { canvas: t, w: bw, h: bh };
}

/* body/tail art is often taller than wide; turn it a quarter so the long axis
   runs along the direction of travel. Returns the baked rotation so the draw
   code can cancel it out. */
function normalizeHorizontal(sprite) {
  if (sprite.h <= sprite.w) return { sprite, rot: 0 };
  const c = makeCanvas(sprite.h, sprite.w);
  const g = draw2d(c);
  g.translate(sprite.h / 2, sprite.w / 2);
  g.rotate(Math.PI / 2);
  g.drawImage(sprite.canvas, -sprite.w / 2, -sprite.h / 2, sprite.w, sprite.h);
  return { sprite: { canvas: c, w: sprite.h, h: sprite.w }, rot: Math.PI / 2 };
}

function preparePart(images, part) {
  const frames = [];
  let rot = 0;
  for (const img of images) {
    const trimmed = trimTransparent(img);
    if (!trimmed) continue;
    const norm = HORIZONTAL_PARTS.has(part) ? normalizeHorizontal(trimmed) : { sprite: trimmed, rot: 0 };
    rot = norm.rot;
    frames.push(norm.sprite);
  }
  return { frames, rot };
}

/* Scale one prepared sprite so it covers a px x px cell, keeping its aspect.
   Anything past 3:1 would need to overflow to fill, so it is centred instead. */
function fitCell(sprite, px, fillRatio) {
  const ratio = fillRatio == null ? PART_FILL_RATIO : fillRatio;
  const out = makeCanvas(px, px);
  const g = draw2d(out);
  const aspect = sprite.w / sprite.h;
  let dw, dh;
  if (aspect < 1 / ratio) {           // too tall: letterbox, centred
    dh = out.height;
    dw = Math.max(1, Math.round(dh * aspect));
  } else {                            // fill the cell
    dw = out.width;
    dh = Math.max(1, Math.round(dw / aspect));
  }
  g.drawImage(sprite.canvas, (out.width - dw) / 2, (out.height - dh) / 2, dw, dh);
  return out;
}

function buildSprites() {
  const px = Math.max(1, Math.round(cell * dpr));
  for (const set of Object.keys(PART_SETS)) {
    PART_SPRITES[set] = {};
    for (const part of PARTS) {
      const rec = PART_SETS[set][part];
      PART_SPRITES[set][part] = rec ? rec.frames.map((f) => fitCell(f, px)) : [];
    }
  }
  foodSprites = foodFrames.map((f) => fitCell(f, px));
}

async function loadAssets() {
  for (const set of Object.keys(PART_DIRS)) {
    PART_SETS[set] = {};
    for (const p of PARTS) PART_SETS[set][p] = preparePart(await loadFrames(PART_DIRS[set], p), p);
  }
  // food: discovery by rule from the shared table (food.known + a numbered
  // food_0..food_(probeCount-1) sweep) — renaming the food file is a
  // ONE-LINE edit in game_content.json, same as on desktop/flutter.
  const images = [];
  const knownFood = contentGet(["food", "known"],
    ["785058659_1053053574250803_8373239390610118887_n.png"]);
  for (const name of Array.isArray(knownFood) ? knownFood : [knownFood]) {
    const img = await loadImage(`assets/food/${name}`);
    if (img) images.push(img);
  }
  const probeCount = contentGet(["food", "probeCount"], 16);
  for (let i = 0; i < probeCount; i++) {
    const f = await loadImage(`assets/food/food_${i}.png`);
    if (!f) break;
    images.push(f);
  }
  const genericFood = await loadImage("assets/food/food.png");
  if (genericFood && !images.length) images.push(genericFood);
  foodFrames = [];
  for (const img of images) {
    const t = trimTransparent(img);
    if (t) foodFrames.push(t);
  }
  for (const n of ["tagalog_eat", "tagalog_death", "tagalog_win",
                   "bisaya_eat", "bisaya_death", "bisaya_win"]) {
    const a = new Audio(`assets/audio/${n}.mp3`);
    a.volume = 0.5;
    SOUNDS[n] = a;
  }
  // ── Voice lines (ADDITIVE — old SOUNDS above are untouched) ──
  // tag-*.mp3 = Tagalog, bis-*.mp3 = Bisaya. Every eat plays ONE random
  // sound from the team's full rotation (classic blip + these lines).
  // To rotate in a new file: drop it in assets/audio/ and add its base
  // name + phrase below. Nothing else needs to change.
  for (const [team, names] of Object.entries(VOICE_FILES)) {
    for (const n of names) {
      try {
        const a = new Audio(`assets/audio/${n}.mp3`);
        a.volume = 0.7;
        a.load(); // warm it now so the first bite has no lag
        VOICE_AUDIO[n] = a;
      } catch (e) { /* missing file: skipped, rotation continues */ }
    }
  }
}
function play(name) {
  if (muted) return;
  const s = SOUNDS[name];
  if (s) { s.currentTime = 0; s.play().catch(() => {}); }
}

// One random eat sound per bite (classic blip included in the rotation).
// Cuts any still-ringing eat sound first so phrases never overlap.
// Returns the phrase to pop up, or null.
let lastEatAudio = null;
function playRandomEatSound(team) {
  if (muted) return null;
  const options = [`${team}_eat`, ...(VOICE_FILES[team] || [])];
  const pick = options[(Math.random() * options.length) | 0];
  try {
    if (lastEatAudio && !lastEatAudio.ended) lastEatAudio.pause();
  } catch (e) {}
  const audio = SOUNDS[pick] || VOICE_AUDIO[pick];
  if (audio) {
    lastEatAudio = audio;
    audio.currentTime = 0;
    audio.play().catch(() => {});
  }
  return VOICE_PHRASES[pick] || null;
}

// ── Board / sizing ────────────────────────────────────────────────────────
let cols = 30, rows = 20, cell = 20, offX = 0, offY = 0;
/* Cap the backing resolution at 2x. iPhone/iPad report devicePixelRatio 2–3,
   and 3x canvases make the shadow-heavy board redraw crawl on older
   devices; 2x keeps every device inside a stable requestAnimationFrame. */
let dpr = Math.min(2, Math.max(1, window.devicePixelRatio || 1));

function resizeCanvas(recalcGrid) {
  dpr = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
  HUD_TOP = 52 + safeInsetTop(); // keep the board clear of the notch
  canvas.width = innerWidth * dpr;
  canvas.height = innerHeight * dpr;
  canvas.style.width = innerWidth + "px";
  canvas.style.height = innerHeight + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (recalcGrid) computeGrid();
  fitBoard();
}

function computeGrid() {
  const target = 26; // aim ~26 css px per cell
  cols = Math.min(60, Math.max(12, Math.round(innerWidth / target)));
  rows = Math.min(60, Math.max(12, Math.round((innerHeight - HUD_TOP) / target)));
}

function fitBoard() {
  cell = Math.floor(Math.min(innerWidth / cols, (innerHeight - HUD_TOP) / rows));
  offX = Math.floor((innerWidth - cols * cell) / 2);
  offY = HUD_TOP + Math.floor((innerHeight - HUD_TOP - rows * cell) / 2);
  buildSprites(); // cell size may have changed
}
window.addEventListener("resize", () => resizeCanvas(state === "menu"));
window.addEventListener("orientationchange", () => {
  // iOS reports the OLD viewport while orientationchange fires; the real
  // size only lands a beat later, so re-run once it has settled.
  resizeCanvas(state === "menu");
  setTimeout(() => resizeCanvas(state === "menu"), 350);
});

// ── Scores (localStorage replaces scores.json) ────────────────────────────
// Validate like desktop (isinstance-style): a corrupted or hand-edited
// localStorage entry must not break the leaderboard screen.
function loadScores() {
  try {
    const data = JSON.parse(localStorage.getItem("snake_scores"));
    if (!Array.isArray(data)) return [];
    const out = [];
    for (const e of data) {
      if (!e || typeof e !== "object") continue;
      const score = Math.floor(Number(e.score));
      if (!Number.isFinite(score) || score <= 0) continue;
      const name = String(e.name || "").slice(0, 12) || "Player";
      out.push({ name, score });
    }
    return out;
  } catch { return []; }
}
function addScore(name, score) {
  const scores = loadScores();
  scores.push({ name: (name || "Player").slice(0, 12), score });
  scores.sort((a, b) => b.score - a.score);
  localStorage.setItem("snake_scores", JSON.stringify(scores.slice(0, 10)));
}
function bestScore() {
  const scores = loadScores();
  return scores.length ? Math.max(...scores.map((s) => s.score | 0)) : 0;
}

// ── Remembered prefs (name + snake), mirroring desktop prefs.json ──────────
function loadPrefs() {
  try { return JSON.parse(localStorage.getItem("snake_prefs")) || {}; }
  catch { return {}; }
}
function savePrefs(p) {
  try { localStorage.setItem("snake_prefs", JSON.stringify(p)); } catch {}
}

// ── Sound mute (HUD speaker pill + M key), saved in snake_prefs ───────────
// Menu/gameplay music and every effect go silent while muted; the choice
// survives reloads just like the desktop's prefs.json "muted" flag.
let muted = false;
function applyMuted() {
  const b = document.getElementById("hud-mute");
  if (!b) return;
  b.textContent = muted ? "🔇" : "🔊";
  b.setAttribute("aria-label", muted ? "Unmute sound" : "Mute sound");
}
function toggleMute() {
  muted = !muted;
  const p = loadPrefs(); p.muted = muted; savePrefs(p);
  applyMuted();
}
function menuMusic() {
  if (!muted) music.play().catch(() => {});
}

/* iOS unlocks audio per-element: an <audio> only becomes programmatic after
   its play() ran inside a user gesture once. Eat/voice/win/death clips fire
   from game ticks (NOT gestures), so on the first touch we sweep every clip
   with a muted play/pause inside the gesture itself. Music is handled by the
   generic pointerdown starter below and is deliberately excluded, because
   the sweep's async pause would race (and kill) its gesture-started play. */
let audioUnlocked = false;
function unlockAllAudio() {
  if (audioUnlocked) return;
  audioUnlocked = true;
  const sweep = (a) => {
    if (!a) return;
    const vol = a.volume;
    try { a.muted = true; a.volume = 0; } catch (e) {}
    const p = a.play();
    if (p && p.then) {
      p.then(() => {
        try { a.pause(); a.currentTime = 0; } catch (e) {}
        try { a.muted = false; a.volume = vol; } catch (e) {}
      }).catch(() => {
        try { a.muted = false; a.volume = vol; } catch (e) {}
      });
    }
  };
  for (const k of Object.keys(SOUNDS)) sweep(SOUNDS[k]);
  for (const k of Object.keys(VOICE_AUDIO)) sweep(VOICE_AUDIO[k]);
}

// ── Snake drawing ─────────────────────────────────────────────────────────
function partSprite(part, idx = null) {
  const list = PART_SPRITES[playerSet] && PART_SPRITES[playerSet][part];
  let img;
  if (idx != null && list && list.length) {
    img = list[((idx % list.length) + list.length) % list.length];
  } else {
    img = animFrame(list, SNAKE_ANIM_FPS);
  }
  if (!img) return null;
  const rec = PART_SETS[playerSet][part];
  return { img, rot: (rec && rec.rot) || 0 };
}

/* Angle for `part` to point along `dir`. Cancels the quarter turn baked in by
   normalizeHorizontal, and mirrors across the vertical axis for the hand of
   turn the authored elbow was not drawn for. */
function partAngle(dir, part, mirror) {
  const rec = PART_SETS[playerSet] && PART_SETS[playerSet][part];
  const rot = (rec && rec.rot) || 0;
  return DIR_ANGLE[dir] - rot - (mirror ? Math.PI : 0);
}
function cornerFor(incoming, outgoing) {
  const mirror = RIGHT_TURN[incoming] !== outgoing;
  return { mirror, angle: partAngle(incoming, "corner", mirror) };
}

function smoothstep(t) { return t * t * (3 - 2 * t); }
function blendDir(dx, dy, tx, ty, t) {
  const len = Math.hypot(dx, dy);
  if (!len) return [tx, ty];
  const a = dx / len, b = dy / len;
  const ux = tx * t + a * (1 - t), uy = ty * t + b * (1 - t);
  const m = Math.hypot(ux, uy) || 1;
  return [ux / m, uy / m];
}

/* Visual-only slither: the head stays locked to its cell and the wave ramps
   towards the tail. Each segment leans into the bend it is on, so corners no
   longer snap off the path. */
function swayOffsets(snake) {
  const n = snake.length;
  const out = [];
  for (let i = 0; i < n; i++) out.push([0, 0]);
  if (n <= 1) return out;
  const dirs = [];
  for (let i = 0; i < n; i++) {
    dirs.push(i === 0
      ? [snake[0][0] - snake[1][0], snake[0][1] - snake[1][1]]
      : [snake[i][0] - snake[i - 1][0], snake[i][1] - snake[i - 1][1]]);
  }
  const perps = dirs.map(([dx, dy]) => [-dy, dx]);
  const phase = performance.now() / 1000;
  for (let i = 1; i < n - 1; i++) {
    let [dx, dy] = dirs[i];
    let [px, py] = perps[i];
    if (i + 1 < n - 1) {
      const t = smoothstep(0.45);
      [dx, dy] = blendDir(dx, dy, dirs[i + 1][0], dirs[i + 1][1], t);
      [px, py] = blendDir(px, py, perps[i + 1][0], perps[i + 1][1], t);
    }
    const ramp = i / (n - 1);
    const s = Math.sin(phase * 4.2 - i * 0.5) * SWAY_AMOUNT * cell * ramp;
    out[i] = [px * s, py * s];
  }
  return out;
}

/* Draws a prepared sprite centred on its cell. Returns false when the art is
   missing so the caller can fall back to a rectangle. */
function drawPart(part, angle, gridPos, mirror, ox, oy, glow, idx = null) {
  const sprite = partSprite(part, idx);
  if (!sprite) return false;
  const x = offX + gridPos[0] * cell + ox;
  const y = offY + gridPos[1] * cell + oy;
  ctx.save();
  ctx.translate(x + cell / 2, y + cell / 2);
  if (mirror) ctx.scale(-1, 1);
  ctx.rotate(angle);
  if (glow) { ctx.shadowColor = glow; ctx.shadowBlur = 10; }
  ctx.drawImage(sprite.img, -cell / 2, -cell / 2, cell, cell);
  ctx.restore();
  return true;
}

function drawSnake(snake) {
  const n = snake.length;
  if (n === 0) return;
  const base = snakeColor();
  const glow = playerSnake === "bisaya" ? "rgba(90,168,255,0.9)" : "rgba(63,224,127,0.9)";
  const sway = swayOffsets(snake);
  // tail: its attach side faces the rest of the body
  if (n >= 2) {
    const d = dirKey([snake[n - 2][0] - snake[n - 1][0], snake[n - 2][1] - snake[n - 1][1]]);
    const [ox, oy] = sway[n - 1];
    const ok = drawPart("tail", partAngle(d, "tail", false), snake[n - 1], false, ox, oy, glow);
    if (!ok) fallback(snake[n - 1], base, false, ox, oy);
  }
  // body
  for (let i = 1; i < n - 1; i++) {
    const inc = dirKey([snake[i][0] - snake[i - 1][0], snake[i][1] - snake[i - 1][1]]);
    const out = dirKey([snake[i + 1][0] - snake[i][0], snake[i + 1][1] - snake[i][1]]);
    const [ox, oy] = sway[i];
    const variant = i < variants.length ? variants[i] : null;
    let ok;
    if (inc !== out) {
      const { mirror, angle } = cornerFor(inc, out);
      ok = drawPart("corner", angle, snake[i], mirror, ox, oy, glow, variant);
    } else {
      ok = drawPart("body", partAngle(inc, "body", false), snake[i], false, ox, oy, glow, variant);
    }
    if (!ok) fallback(snake[i], base, false, ox, oy);
  }
  // head stays grid-locked so aiming/eating feels precise
  const hd = n >= 2
    ? dirKey([snake[0][0] - snake[1][0], snake[0][1] - snake[1][1]])
    : "1,0";
  if (!drawPart("head", partAngle(hd, "head", false), snake[0], false, 0, 0, glow)) {
    fallback(snake[0], "#c8ffe0", true);
  }
}
function snakeColor() {
  return playerSnake === "bisaya" ? COL.blue : COL.green;
}
function fallback(pos, color, isHead, ox = 0, oy = 0) {
  const x = offX + pos[0] * cell + ox, y = offY + pos[1] * cell + oy;
  const r = Math.min(cell * 0.32, 8);
  ctx.save();
  ctx.shadowColor = color;
  ctx.shadowBlur = isHead ? 14 : 8;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(x, y, cell, cell, r);
  ctx.fill();
  ctx.shadowBlur = 0;
  // glossy highlight
  ctx.fillStyle = "rgba(255,255,255,0.28)";
  ctx.beginPath();
  ctx.roundRect(x + 1, y + 1, cell - 2, (cell - 2) * 0.38, [r, r, 0, 0]);
  ctx.fill();
  ctx.restore();
}
const MOTES = [];
function initMotes() {
  MOTES.length = 0;
  const tints = ["63,224,127", "90,168,255", "255,210,70"];
  for (let i = 0; i < 42; i++) {
    MOTES.push({
      x0: Math.random(), y0: Math.random(),
      vx: -0.008 + Math.random() * 0.02, vy: -0.010 + Math.random() * 0.014,
      r: 1.5 + Math.random() * 2.8, ph: Math.random() * 6.28,
      c: tints[i % tints.length],
    });
  }
}
function drawMotes(now) {
  const t = now / 1000;
  for (const m of MOTES) {
    const x = ((m.x0 + m.vx * t) % 1 + 1) % 1 * innerWidth;
    const y = ((m.y0 + m.vy * t) % 1 + 1) % 1 * innerHeight;
    const tw = 0.5 + 0.5 * Math.sin(t * 1.6 + m.ph);
    ctx.save();
    ctx.globalAlpha = 0.10 + 0.22 * tw;
    ctx.fillStyle = `rgb(${m.c})`;
    ctx.shadowColor = `rgba(${m.c},0.9)`;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(x, y, m.r * (0.8 + 0.4 * tw), 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}
function drawBoard() {
  const now = performance.now();
  // soft arena gradient (no harsh grid)
  const g = ctx.createLinearGradient(0, 0, 0, innerHeight);
  g.addColorStop(0, "#1a1e35");
  g.addColorStop(0.45, COL.bg2);
  g.addColorStop(1, COL.bg);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, innerWidth, innerHeight);
  // soft center glow
  const rg = ctx.createRadialGradient(
    innerWidth / 2, innerHeight / 2, 10,
    innerWidth / 2, innerHeight / 2, Math.max(innerWidth, innerHeight) * 0.65);
  rg.addColorStop(0, "rgba(90,140,255,0.07)");
  rg.addColorStop(0.5, "rgba(63,224,127,0.05)");
  rg.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = rg;
  ctx.fillRect(0, 0, innerWidth, innerHeight);

  const bw = cols * cell, bh = rows * cell;
  // board panel
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,0.6)";
  ctx.shadowBlur = 30;
  ctx.shadowOffsetY = 10;
  ctx.fillStyle = "rgba(10,11,20,0.72)";
  ctx.beginPath();
  ctx.roundRect(offX - 8, offY - 8, bw + 16, bh + 16, 14);
  ctx.fill();
  ctx.restore();

  ctx.save();
  ctx.beginPath();
  ctx.roundRect(offX, offY, bw, bh, 8);
  ctx.clip();
  // faint dot lattice every 2 cells (calm, no lines)
  ctx.fillStyle = "rgba(255,255,255,0.07)";
  for (let y = 0; y <= rows; y += 2) {
    for (let x = 0; x <= cols; x += 2) {
      ctx.beginPath();
      ctx.arc(offX + x * cell, offY + y * cell, 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.restore();
  drawMotes(now);
  // vignette over everything
  const vg = ctx.createRadialGradient(
    innerWidth / 2, innerHeight / 2, Math.min(innerWidth, innerHeight) * 0.35,
    innerWidth / 2, innerHeight / 2, Math.max(innerWidth, innerHeight) * 0.75);
  vg.addColorStop(0, "rgba(0,0,0,0)");
  vg.addColorStop(1, "rgba(0,0,0,0.42)");
  ctx.fillStyle = vg;
  ctx.fillRect(0, 0, innerWidth, innerHeight);
  // crisp arena border with snake-tinted glow
  ctx.save();
  ctx.strokeStyle = playerSnake === "bisaya" ? "rgba(90,168,255,0.45)" : "rgba(63,224,127,0.45)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.roundRect(offX - 1, offY - 1, bw + 2, bh + 2, 9);
  ctx.stroke();
  ctx.restore();
}
function drawFood(food) {
  if (!food) return;
  const cx = offX + food[0] * cell + cell / 2;
  const cy = offY + food[1] * cell + cell / 2;
  const pulse = 1 + Math.sin(performance.now() / 280) * 0.07;
  const frame = animFrame(foodSprites, FOOD_ANIM_FPS);
  if (frame) {
    const s = cell * pulse;
    ctx.save();
    ctx.shadowColor = "rgba(255,90,90,0.8)";
    ctx.shadowBlur = 16;
    ctx.drawImage(frame, cx - s / 2, cy - s / 2, s, s);
    ctx.restore();
    return;
  }
  ctx.save();
  ctx.shadowColor = COL.red;
  ctx.shadowBlur = 16;
  ctx.fillStyle = COL.red;
  ctx.beginPath();
  ctx.arc(cx, cy, (cell / 2 - 2) * pulse, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
  ctx.fillStyle = "rgba(255,255,255,0.55)";
  ctx.beginPath();
  ctx.arc(cx - cell * 0.12, cy - cell * 0.14, cell * 0.11, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// ── Game state ────────────────────────────────────────────────────────────
let state = "menu"; // menu | name | playing | paused | over | leaderboard | snake-select
let snake, dir, nextDir, food, score, stepMs, lastStep, playerName;
let runBest = 0; // leaderboard best at run start (HUD reference)
let variants = []; // per-segment look ids, kept parallel to `snake`

function randomFood() {
  const free = [];
  const occupied = new Set(snake.map(([x, y]) => x + "," + y));
  for (let x = 0; x < cols; x++) for (let y = 0; y < rows; y++)
    if (!occupied.has(x + "," + y)) free.push([x, y]);
  return free.length ? free[(Math.random() * free.length) | 0] : null;
}

function startGame() {
  computeGrid(); fitBoard();
  const cx = cols >> 1, cy = rows >> 1;
  snake = [[cx, cy], [cx - 1, cy], [cx - 2, cy]];
  dir = [1, 0]; nextDir = dir;
  score = 0;
  variants = [0, 0, 0];
  runBest = bestScore();
  stepMs = 1000 / START_FPS;
  food = randomFood();
  state = "playing";
  lastStep = performance.now(); // a fresh run must not inherit a stale tick
  document.getElementById("hud-player").textContent = playerName;
  document.getElementById("hud-score").textContent = "Score: 0 · Best: " + runBest;
  show(null, ["hud"]);
  music.pause();
}

/* One turn per tick, and never back onto yourself: the move in flight decides
   what is legal, and a turn already queued is never swapped or chained. */
function queueTurn(pending, committed, desired) {
  const c = dirKey(committed);
  const legal = (d) => OPPOSITE[dirKey(d)] !== c;
  if (dirKey(pending) !== c && legal(pending)) return pending;
  return legal(desired) ? desired : (legal(pending) ? pending : committed);
}

function step() {
  dir = nextDir;
  const [hx, hy] = snake[0];
  const nx = hx + dir[0], ny = hy + dir[1];
  const hitWall = nx < 0 || nx >= cols || ny < 0 || ny >= rows;
  const willEat = food && nx === food[0] && ny === food[1];
  const body = willEat ? snake : snake.slice(0, -1);
  const hitSelf = body.some(([x, y]) => x === nx && y === ny);
  if (hitWall || hitSelf) {
    play(playerSnake + "_death");
    endGame();
    return;
  }
  snake.unshift([nx, ny]);
  if (willEat) {
    variants.unshift((Math.random() * 0x40000000) | 0);
    const phrase = playRandomEatSound(playerSnake);
    spawnPopup(nx, ny, phrase);
    score += 10;
    stepMs = Math.max(1000 / 25, 1000 / (START_FPS + Math.floor(score / 50)));
    document.getElementById("hud-score").textContent =
      "Score: " + score + " · Best: " + Math.max(runBest, score);
    food = randomFood();
    if (food === null) {
      // Every cell of the board is a snake segment: the run is CLEARED.
      // Victory, not death — gold YOU WIN screen + the team's win sound.
      play(playerSnake + "_win");
      endGame(true);
      return;
    }
  } else {
    snake.pop();
    variants.pop();
  }
}

function endGame(won = false) {
  state = "over";
  const prevBest = bestScore();
  const isBest = score > 0 && score > prevBest;
  if (score > 0) addScore(playerName, score);
  document.getElementById("final-score").textContent = "Score: " + score;
  document.getElementById("new-best").classList.toggle("hidden", !isBest);
  const title = document.querySelector("#game-over h2");
  title.textContent = won ? "YOU WIN" : "GAME OVER";
  title.classList.toggle("danger", !won);
  title.classList.toggle("win", won);
  show("game-over", ["hud"]);
  menuMusic();
}

// ── Pause (mirrors desktop P / overlay / auto-pause) ───────────────────────
function pauseGame() {
  if (state !== "playing") return;
  state = "paused";
  show("pause", ["hud"]);
}
function resumeGame() {
  if (state !== "paused") return;
  state = "playing";
  lastStep = performance.now(); // don't bill the paused time as one long tick
  show(null, ["hud"]);
}
function quitToMenu() {
  state = "menu";
  show("menu");
  menuMusic();
}

let POPUP_WORDS = ["SARAP!", "LAMI!", "YUMMY!", "NOM NOM!", "TAMIS!", "LAMON!", "+10", "SHEESH!"]; // fallback; canonical = shared popup.words
let POPUP_COLORS = ["#ffd246", "#3fe07f", "#ffffff", "#ff9d9d", "#a8d4ff"]; // fallback; canonical = shared popup.colors
const popups = [];
function spawnPopup(gx, gy, text) {
  const isPhrase = typeof text === "string" && text.length > 0;
  popups.push({
    gx, gy,
    text: isPhrase
      ? text
      : POPUP_WORDS[(Math.random() * POPUP_WORDS.length) | 0],
    color: isPhrase
      ? (playerSnake === "bisaya" ? "#5aa8ff" : "#3fe07f")
      : POPUP_COLORS[(Math.random() * POPUP_COLORS.length) | 0],
    born: performance.now(), life: 950,
  });
}
function drawPopups() {
  const now = performance.now();
  for (let i = popups.length - 1; i >= 0; i--) {
    const p = popups[i];
    const age = now - p.born;
    if (age >= p.life) { popups.splice(i, 1); continue; }
    const t = age / p.life;
    const rise = cell * 1.8 * t;
    const scale = 1 + 0.6 * Math.exp(-age / 130);
    const alpha = t < 0.6 ? 1 : 1 - (t - 0.6) / 0.4;
    const cx = offX + p.gx * cell + cell / 2;
    const cy = offY + p.gy * cell - rise;
    const size = Math.max(15, cell * 0.85) * scale;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.font = `900 ${size}px system-ui, Arial, sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.lineWidth = Math.max(2, size * 0.12);
    ctx.strokeStyle = "rgba(0,0,0,0.85)";
    ctx.strokeText(p.text, cx, cy);
    ctx.fillStyle = p.color;
    ctx.shadowColor = p.color; ctx.shadowBlur = 12;
    ctx.fillText(p.text, cx, cy);
    ctx.restore();
  }
}

let rafId = null;
function loop(t) {
  rafId = requestAnimationFrame(loop);
  if (state !== "playing") return;
  if (t - lastStep >= stepMs) {
    lastStep = t;
    step();
  }
  drawBoard();
  drawFood(food);
  drawSnake(snake);
  drawPopups();
}

// ── Input ─────────────────────────────────────────────────────────────────
const KEY_DIR = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
function setDir(name) {
  if (state !== "playing") return; // frozen while paused
  const v = KEY_DIR[name];
  if (v) nextDir = queueTurn(nextDir, dir, v);
}
window.addEventListener("keydown", (e) => {
  if (e.key === "m" || e.key === "M") { toggleMute(); return; }
  if (e.key === "p" || e.key === "P") {
    if (state === "playing") pauseGame();
    else if (state === "paused") resumeGame();
    return;
  }
  if (e.key === "r" || e.key === "R") {
    if (state === "over") { lastStep = performance.now(); startGame(); }
    return;
  }
  if (state === "paused") {
    if (e.key === "Escape") quitToMenu();
    return;
  }
  if (state !== "playing") return;
  const map = { ArrowUp: "up", w: "up", W: "up", ArrowDown: "down", s: "down", S: "down",
                ArrowLeft: "left", a: "left", A: "left", ArrowRight: "right", d: "right", D: "right" };
  if (map[e.key]) { setDir(map[e.key]); e.preventDefault(); }
  if (e.key === "Escape") { pauseGame(); }
});
// Auto-pause when the tab loses visibility (mirrors desktop focus-loss pause).
document.addEventListener("visibilitychange", () => {
  if (document.hidden) pauseGame();
});
let touchStart = null;
let touchConsumed = false;
canvas.addEventListener("touchstart", (e) => {
  touchStart = [e.touches[0].clientX, e.touches[0].clientY];
  touchConsumed = false;
}, { passive: true });
// Commit the turn as soon as the swipe crosses ~one cell of screen — waiting
// for the lift made steering feel a half-step late on touch devices.
canvas.addEventListener("touchmove", (e) => {
  if (!touchStart || touchConsumed) return;
  const dx = e.touches[0].clientX - touchStart[0];
  const dy = e.touches[0].clientY - touchStart[1];
  if (Math.abs(dx) < 24 && Math.abs(dy) < 24) return;
  touchConsumed = true;
  setDir(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up"));
}, { passive: true });
canvas.addEventListener("touchend", (e) => {
  // flicks that never crossed the move threshold still count
  if (!touchConsumed && touchStart) {
    const dx = e.changedTouches[0].clientX - touchStart[0];
    const dy = e.changedTouches[0].clientY - touchStart[1];
    if (Math.abs(dx) >= 20 || Math.abs(dy) >= 20) {
      setDir(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up"));
    }
  }
  touchStart = null;
  touchConsumed = false;
}, { passive: true });
// iOS: long-press / 3D-touch on the canvas must not open anything
canvas.addEventListener("contextmenu", (e) => e.preventDefault());

// ── Exit button ───────────────────────────────────────────────────────────
// iOS (Add to Home Screen) and most browsers refuse to let a page close
// itself — window.close() silently does nothing there. So "quit" degrades
// gracefully: attempt the hard close, and when that doesn't stick, explain
// the platform's own exit gesture and land the player safely in the menu.
function showExitTip(standalone) {
  var tip = document.getElementById("exit-tip");
  var msg = standalone
    ? "👋 To exit, swipe up from the bottom edge of the screen."
    : "👋 Exit needs the browser — close the tab to leave the game.";
  if (!tip) {
    tip = document.createElement("div");
    tip.id = "exit-tip";
    tip.style.cssText = "position:fixed;left:50%;transform:translateX(-50%);" +
      "bottom:calc(24px + env(safe-area-inset-bottom, 0px));" +
      "background:rgba(10,14,26,.92);color:#fff;padding:12px 18px;" +
      "border:1px solid rgba(255,255,255,.25);border-radius:999px;" +
      "max-width:86vw;text-align:center;z-index:50;" +
      "font:600 14px/1.3 system-ui,-apple-system,'Segoe UI',sans-serif;" +
      "box-shadow:0 10px 30px rgba(0,0,0,.5);opacity:0;transition:opacity .25s;";
    document.body.appendChild(tip);
  }
  tip.textContent = msg;
  requestAnimationFrame(function () { tip.style.opacity = "1"; });
  clearTimeout(showExitTip._hide);
  showExitTip._hide = setTimeout(function () { tip.style.opacity = "0"; }, 3600);
}
function exitGame() {
  // Native Android host (APK webview) may expose a real exit hook.
  if (window.AndroidHost && typeof window.AndroidHost.exitApp === "function") {
    try { window.AndroidHost.exitApp(); return; } catch (err) {}
  }
  // window.close() only ever works for script-opened windows.
  window.close();
  setTimeout(function () {
    // Still open means the platform blocked the close. iPhone home-screen
    // apps can only be exited with Apple's own gesture — coach it.
    var standalone =
      window.navigator.standalone === true ||
      (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches);
    showExitTip(standalone || isIOS());
    show("menu");
  }, 180);
}

// ── UI wiring ─────────────────────────────────────────────────────────────
const overlays = ["menu", "snake-select", "name-screen", "leaderboard", "game-over", "pause"];
function show(overlayId, alsoShow = []) {
  for (const id of overlays) document.getElementById(id).classList.add("hidden");
  document.getElementById("hud").classList.add("hidden");
  if (overlayId) document.getElementById(overlayId).classList.remove("hidden");
  for (const id of alsoShow) document.getElementById(id).classList.remove("hidden");
}
document.querySelectorAll("[data-action]").forEach((el) => {
  el.addEventListener("click", () => {
    const a = el.dataset.action;
    if (a === "play") {
      // Instant rematch from game-over reuses name + snake; from menu it
      // starts the normal snake-select flow.
      if (state === "over") { lastStep = performance.now(); startGame(); }
      else { state = "snake-select"; markLastSnake(); show("snake-select"); }
    }
    else if (a === "snake") { state = "snake-select"; markLastSnake(); show("snake-select"); }
    else if (a === "resume") { resumeGame(); }
    else if (a === "quit-to-menu") { quitToMenu(); }
    else if (a === "leaderboard") { renderScores(); state = "leaderboard"; show("leaderboard"); }
    else if (a === "back" || a === "menu") { state = "menu"; show("menu"); }
    else if (a === "back-to-snake") { state = "snake-select"; markLastSnake(); show("snake-select"); }
    else if (a === "quit") { exitGame(); }
  });
});
// Highlight the remembered snake so repeat players see their last pick.
function markLastSnake() {
  document.querySelectorAll("[data-snake]").forEach((el) => {
    el.classList.toggle("primary", el.dataset.snake === playerSnake);
  });
}
document.getElementById("hud-pause").addEventListener("click", () => pauseGame());
document.getElementById("hud-mute").addEventListener("click", toggleMute);
document.querySelectorAll("[data-snake]").forEach((el) => {
  el.addEventListener("click", () => {
    playerSnake = el.dataset.snake; // "tagalog" or "bisaya"
    playerSet = playerSnake === "bisaya" ? "bisaya" : "tagalog";
    state = "name";
    show("name-screen");
    document.getElementById("name-input").focus();
  });
});
document.getElementById("name-ok").addEventListener("click", () => {
  playerName = document.getElementById("name-input").value.trim() || "Player";
  savePrefs({ name: playerName, snake: playerSnake });
  lastStep = performance.now();
  startGame();
});
document.getElementById("name-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") document.getElementById("name-ok").click();
});
function renderScores() {
  const list = document.getElementById("scores-list");
  list.innerHTML = "";
  const scores = loadScores();
  if (!scores.length) list.innerHTML = "<li>No scores yet.</li>";
  scores.forEach((s, i) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${i + 1}. ${s.name}</span><span>${s.score}</span>`;
    list.appendChild(li);
  });
}

// ── iOS "Add to Home Screen" helper ───────────────────────────────────────
// iOS Safari never shows an automatic install prompt. Detect it and coach
// the one gesture that puts the game icon on the Home Screen. Once the game
// runs from the icon, both standalone signals report true and it skips.
const INSTALL_FLAG = "snake_install_hint";
function isIOS() {
  return /iP(hone|od|ad)/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1); // iPadOS desktop UAs
}
function initInstallHint() {
  const banner = document.getElementById("install-hint");
  if (!banner) return;
  const installed =
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
  let dismissed = false;
  try { dismissed = localStorage.getItem(INSTALL_FLAG) === "1"; } catch (e) {}
  if (!isIOS() || installed || dismissed) return;
  setTimeout(() => banner.classList.remove("hidden"), 900);
  document.getElementById("install-hint-close").addEventListener("click", () => {
    banner.classList.add("hidden");
    try { localStorage.setItem(INSTALL_FLAG, "1"); } catch (e) {}
  });
}

// ── Boot ──────────────────────────────────────────────────────────────────
(async function init() {
  // Shared rules first: every table below is built from game_content.json.
  await loadContent();
  applyContent();
  await loadAssets();
  initMotes();
  // Remembered name + snake (mirrors desktop prefs.json).
  try {
    const prefs = loadPrefs();
    muted = prefs.muted === true;
    if (prefs.name) {
      playerName = prefs.name;
      document.getElementById("name-input").value = prefs.name;
    }
    if (prefs.snake === "bisaya" || prefs.snake === "tagalog") {
      playerSnake = prefs.snake;
      playerSet = prefs.snake;
    }
  } catch {}
  applyMuted();
  resizeCanvas(true);
  show("menu");
  initInstallHint();
  // Browsers require a user gesture before audio can play. On iOS every
  // individual clip must be gestured once; the sweep runs before this.
  document.addEventListener("pointerdown", unlockAllAudio, { once: true, capture: true });
  document.addEventListener("pointerdown", () => {
    if ((state === "menu" || state === "over") && !muted) music.play().catch(() => {});
  }, { once: false });
  if ("serviceWorker" in navigator) {
    // Inside the Flutter APK the game is served from a localhost server
    // backed by bundled assets — the service worker would only serve
    // stale code after an app update, so skip it there.
    const isLocalApk = /^(127\.0\.0\.1|localhost)$/.test(location.hostname);
    if (isLocalApk) {
      navigator.serviceWorker.getRegistrations()
        .then((regs) => regs.forEach((r) => r.unregister().catch(() => {})))
        .catch(() => {});
    } else {
      navigator.serviceWorker.register("sw.js").catch(() => {});
    }
  }
  rafId = requestAnimationFrame(loop);
})();