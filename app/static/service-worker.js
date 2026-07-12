// Event Tracker service worker
// Version 0.1
//
// This service worker is intentionally minimal.
// It supports basic PWA installation behavior.
// Offline logging is not implemented yet.

const CACHE_NAME = "event-tracker-v0-2";

const STATIC_ASSETS = [
    "/",
    "/static/style.css",
    "/static/app.js",
    "/static/manifest.json"
];

const STATIC_ASSETS = [
    "/",
    "/static/style.css",
    "/static/db.js",
    "/static/app.js",
    "/static/manifest.json"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
});

self.addEventListener("fetch", (event) => {
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});