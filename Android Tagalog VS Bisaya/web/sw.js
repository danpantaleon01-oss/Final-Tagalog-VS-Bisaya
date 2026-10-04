const CACHE = "snake-v3";
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
  "assets/audio/bisaya_win.mp3"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)));
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
  e.respondWith(
    caches.match(e.request).then((cached) => cached || fetch(e.request))
  );
});
