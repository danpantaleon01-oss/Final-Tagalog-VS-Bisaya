const CACHE = "snake-v6";
const FILES = [
  "./",
  "index.html",
  "style.css",
  "game.js",
  "manifest.json",
  "assets/icon.png",
  "assets/p1/head.png",
  "assets/p1/body.png",
  "assets/p1/corner.png",
  "assets/p1/tail.png",
  "assets/p2/head.png",
  "assets/p2/body.png",
  "assets/p2/corner.png",
  "assets/p2/tail.png",
  "assets/food/785058659_1053053574250803_8373239390610118887_n.png",
  "assets/audio/bg_music_lobby.mp3",
  "assets/audio/tagalog_eat.mp3",
  "assets/audio/tagalog_death.mp3",
  "assets/audio/tagalog_win.mp3",
  "assets/audio/bisaya_eat.mp3",
  "assets/audio/bisaya_death.mp3",
  "assets/audio/bisaya_win.mp3",
  "assets/audio/tag-arman.mp3",
  "assets/audio/tag-babalu.mp3",
  "assets/audio/tag-nenegb.mp3",
  "assets/audio/tag-tamis-malupiton.mp3",
  "assets/audio/bis-lami.mp3",
  "assets/audio/bis-sulit.mp3",
  "assets/audio/bis-unlirice.mp3",
  "assets/audio/bis-yummy.mp3"
];

const SHELL = ["index.html", "style.css", "game.js", "manifest.json"];

// The shell carries the code, so it must not be served stale. Art and audio
// are big and immutable, so those stay cache-first.
function isShell(url) {
  if (url.origin !== location.origin) return false;
  const path = url.pathname;
  if (path.endsWith("/") || path.endsWith("/index.html")) return true;
  return SHELL.indexOf(path.slice(path.lastIndexOf("/") + 1)) !== -1;
}

self.addEventListener("install", (e) => {
  // addAll is all-or-nothing, so cache core files individually and skip
  // missing future animation frames instead of failing the whole install.
  e.waitUntil(
    caches.open(CACHE).then(async (c) => {
      await Promise.all(
        FILES.map((f) => c.add(f).catch(() => {}))
      );
    })
  );
  self.skipWaiting();
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  let url;
  try { url = new URL(req.url); } catch (err) { return; }

  // network first, so a new game.js/index.html lands on the next visit
  if (isShell(url)) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() =>
          caches.match(req).then((hit) => hit || caches.match("index.html"))
        )
    );
    return;
  }

  // cache first, then runtime-cache same-origin GETs (so future food_N / head_N
  // Aseprite frames work offline after first load).
  e.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((res) => {
        if (res && res.ok && url.origin === location.origin) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      });
    })
  );
});