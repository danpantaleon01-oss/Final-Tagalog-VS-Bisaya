/* Tagalog vs Bisaya — Snake (PWA / mobile edition)
 * Single-player only. Swipe or arrow keys to steer.
 */
"use strict";

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

const COL = {
  bg: "#121218", grid: "#1e1e26", white: "#f0f0f5",
  green: "#50dc78", head: "#78ff96", red: "#f55050",
  yellow: "#ffd246", gray: "#9696a0",
};
const START_FPS = 8;
const HUD_TOP = 36; // px reserved for HUD overlay

// ── Assets ────────────────────────────────────────────────────────────────
const IMGS_TAGALOG = {}, IMGS_BISAYA = {};
let IMGS = IMGS_TAGALOG; // sprites of the selected snake (used by drawSnake)
const SOUNDS = {};
let foodImg = null;
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

async function loadAssets() {
  const parts = ["head", "body", "corner", "tail"];
  for (const p of parts) {
    IMGS_TAGALOG[p] = await loadImage(`assets/p1/${p}.png`);
    IMGS_BISAYA[p] = await loadImage(`assets/p2/${p}.png`);
  }
  foodImg = await loadImage(
    "assets/food/785058659_1053053574250803_8373239390610118887_n.png"
  );
  for (const n of ["tagalog_eat", "tagalog_death", "tagalog_win",
                   "bisaya_eat", "bisaya_death", "bisaya_win"]) {
    const a = new Audio(`assets/audio/${n}.mp3`);
    a.volume = 0.5;
    SOUNDS[n] = a;
  }
}
function play(name) {
  const s = SOUNDS[name];
  if (s) { s.currentTime = 0; s.play().catch(() => {}); }
}

// ── Board / sizing ────────────────────────────────────────────────────────
let cols = 30, rows = 20, cell = 20, offX = 0, offY = 0;
let dpr = Math.max(1, window.devicePixelRatio || 1);

function resizeCanvas(recalcGrid) {
  dpr = Math.max(1, window.devicePixelRatio || 1);
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
}
window.addEventListener("resize", () => resizeCanvas(state === "menu"));
window.addEventListener("orientationchange", () => resizeCanvas(state === "menu"));

// ── Scores (localStorage replaces scores.json) ────────────────────────────
function loadScores() {
  try { return JSON.parse(localStorage.getItem("snake_scores")) || []; }
  catch { return []; }
}
function addScore(name, score) {
  const scores = loadScores();
  scores.push({ name: (name || "Player").slice(0, 12), score });
  scores.sort((a, b) => b.score - a.score);
  localStorage.setItem("snake_scores", JSON.stringify(scores.slice(0, 10)));
}

// ── Snake drawing with rotated assets ─────────────────────────────────────
const TURN_ANGLE = {
  right: { "1,0": 0, "0,-1": -Math.PI / 2, "-1,0": Math.PI, "0,1": Math.PI / 2 },
  left:  { "1,0": 0, "0,1": -Math.PI / 2, "-1,0": Math.PI, "0,-1": Math.PI / 2 },
};
function drawPart(img, gridPos, angle) {
  const x = offX + gridPos[0] * cell;
  const y = offY + gridPos[1] * cell;
  ctx.save();
  ctx.translate(x + cell / 2, y + cell / 2);
  ctx.rotate(angle);
  ctx.drawImage(img, -cell / 2, -cell / 2, cell, cell);
  ctx.restore();
}
function dirAngle(d) {
  return d === "1,0" ? 0 : d === "0,-1" ? -Math.PI / 2 : d === "-1,0" ? Math.PI : Math.PI / 2;
}
function drawSnake(snake) {
  const n = snake.length;
  if (n === 0) return;
  // tail: direction from tail toward the rest of the body (authored facing-left png)
  if (n >= 2) {
    const d = [snake[n - 2][0] - snake[n - 1][0], snake[n - 2][1] - snake[n - 1][1]];
    if (IMGS.tail) drawPart(IMGS.tail, snake[n - 1], dirAngle(d.join(",")));
    else fallback(snake[n - 1], COL.green);
  }
  // body
  for (let i = 1; i < n - 1; i++) {
    const inc = [snake[i][0] - snake[i - 1][0], snake[i][1] - snake[i - 1][1]].join(",");
    const out = [snake[i + 1][0] - snake[i][0], snake[i + 1][1] - snake[i][1]].join(",");
    const incD = inc.split(",").map(Number), outD = out.split(",").map(Number);
    const isCorner = incD[0] !== outD[0] || incD[1] !== outD[1];
    if (isCorner && IMGS.corner) {
      const rightMap = { "1,0": "0,1", "0,1": "-1,0", "-1,0": "0,-1", "0,-1": "1,0" };
      const kind = rightMap[inc] === out ? "right" : "left";
      drawPart(IMGS.corner, snake[i], TURN_ANGLE[kind][inc] || 0);
    } else if (IMGS.body) {
      drawPart(IMGS.body, snake[i], dirAngle(inc));
    } else fallback(snake[i], COL.green);
  }
  // head
  const hd = n >= 2
    ? [snake[0][0] - snake[1][0], snake[0][1] - snake[1][1]].join(",")
    : "1,0";
  if (IMGS.head) drawPart(IMGS.head, snake[0], dirAngle(hd));
  else fallback(snake[0], COL.head);
}
function fallback(pos, color) {
  ctx.fillStyle = color;
  ctx.fillRect(offX + pos[0] * cell + 2, offY + pos[1] * cell + 2, cell - 4, cell - 4);
}
function drawBoard() {
  ctx.fillStyle = COL.bg;
  ctx.fillRect(0, 0, innerWidth, innerHeight);
  ctx.strokeStyle = COL.grid;
  ctx.lineWidth = 1;
  for (let x = 0; x <= cols; x++) {
    ctx.beginPath();
    ctx.moveTo(offX + x * cell, offY);
    ctx.lineTo(offX + x * cell, offY + rows * cell);
    ctx.stroke();
  }
  for (let y = 0; y <= rows; y++) {
    ctx.beginPath();
    ctx.moveTo(offX, offY + y * cell);
    ctx.lineTo(offX + cols * cell, offY + y * cell);
    ctx.stroke();
  }
}
function drawFood(food) {
  if (!food) return;
  if (foodImg) {
    ctx.drawImage(foodImg, offX + food[0] * cell, offY + food[1] * cell, cell, cell);
  } else {
    ctx.fillStyle = COL.red;
    ctx.beginPath();
    ctx.arc(offX + food[0] * cell + cell / 2, offY + food[1] * cell + cell / 2,
            cell / 2 - 2, 0, Math.PI * 2);
    ctx.fill();
  }
}

// ── Game state ────────────────────────────────────────────────────────────
let state = "menu"; // menu | name | playing | over | leaderboard
let snake, dir, nextDir, food, score, stepMs, lastStep, playerName;

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
  stepMs = 1000 / START_FPS;
  food = randomFood();
  state = "playing";
  document.getElementById("hud-player").textContent = playerName;
  document.getElementById("hud-score").textContent = "Score: 0";
  show(null, ["hud"]);
  music.pause();
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
    play(playerSnake + "_eat");
    score += 10;
    stepMs = Math.max(1000 / 25, 1000 / (START_FPS + Math.floor(score / 50)));
    document.getElementById("hud-score").textContent = "Score: " + score;
    food = randomFood();
    if (food === null) { endGame(); return; }
  } else {
    snake.pop();
  }
}

function endGame() {
  state = "over";
  if (score > 0) addScore(playerName, score);
  document.getElementById("final-score").textContent = "Score: " + score;
  show("game-over", ["hud"]);
  music.play().catch(() => {});
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
}

// ── Input ─────────────────────────────────────────────────────────────────
function setDir(d) {
  const opposites = { up: [0, 1], down: [0, -1], left: [1, 0], right: [-1, 0] };
  const v = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }[d];
  const opp = opposites[d];
  if (dir[0] !== opp[0] || dir[1] !== opp[1]) nextDir = v;
}
window.addEventListener("keydown", (e) => {
  if (state !== "playing") return;
  const map = { ArrowUp: "up", w: "up", W: "up", ArrowDown: "down", s: "down", S: "down",
                ArrowLeft: "left", a: "left", A: "left", ArrowRight: "right", d: "right", D: "right" };
  if (map[e.key]) { setDir(map[e.key]); e.preventDefault(); }
  if (e.key === "Escape") { endGame(); }
});
let touchStart = null;
canvas.addEventListener("touchstart", (e) => {
  touchStart = [e.touches[0].clientX, e.touches[0].clientY];
}, { passive: true });
canvas.addEventListener("touchend", (e) => {
  if (!touchStart) return;
  const dx = e.changedTouches[0].clientX - touchStart[0];
  const dy = e.changedTouches[0].clientY - touchStart[1];
  touchStart = null;
  if (Math.abs(dx) < 20 && Math.abs(dy) < 20) return;
  setDir(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up"));
}, { passive: true });

// ── UI wiring ─────────────────────────────────────────────────────────────
const overlays = ["menu", "snake-select", "name-screen", "leaderboard", "game-over"];
function show(overlayId, alsoShow = []) {
  for (const id of overlays) document.getElementById(id).classList.add("hidden");
  document.getElementById("hud").classList.add("hidden");
  if (overlayId) document.getElementById(overlayId).classList.remove("hidden");
  for (const id of alsoShow) document.getElementById(id).classList.remove("hidden");
}
document.querySelectorAll("[data-action]").forEach((el) => {
  el.addEventListener("click", () => {
    const a = el.dataset.action;
    if (a === "play") { state = "snake-select"; show("snake-select"); }
    else if (a === "leaderboard") { renderScores(); state = "leaderboard"; show("leaderboard"); }
    else if (a === "back" || a === "menu") { state = "menu"; show("menu"); }
    else if (a === "back-to-snake") { state = "snake-select"; show("snake-select"); }
    else if (a === "quit") { show("menu"); }
  });
});
document.querySelectorAll("[data-snake]").forEach((el) => {
  el.addEventListener("click", () => {
    playerSnake = el.dataset.snake; // "tagalog" or "bisaya"
    IMGS = playerSnake === "bisaya" ? IMGS_BISAYA : IMGS_TAGALOG;
    state = "name";
    show("name-screen");
    document.getElementById("name-input").focus();
  });
});
document.getElementById("name-ok").addEventListener("click", () => {
  playerName = document.getElementById("name-input").value.trim() || "Player";
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

// ── Boot ──────────────────────────────────────────────────────────────────
(async function init() {
  await loadAssets();
  resizeCanvas(true);
  show("menu");
  // Browsers require a user gesture before audio can play.
  document.addEventListener("pointerdown", () => {
    if (state === "menu" || state === "over") music.play().catch(() => {});
  }, { once: false });
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
  rafId = requestAnimationFrame(loop);
})();
