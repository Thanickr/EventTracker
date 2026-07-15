// Event Tracker service worker
// Version 0.2
//
// Caches the static application shell so the logger can open offline.

const CACHE_NAME = "event-tracker-v0-5";

const STATIC_ASSETS = [
    "./",
    "./index.html",
    "./style.css",
    "./db.js",
    "./app.js",
    "./manifest.json",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );

    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((cacheName) => cacheName !== CACHE_NAME)
                    .map((cacheName) => caches.delete(cacheName))
            );
        })
    );

    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    if (event.request.method !== "GET") {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                const responseCopy = response.clone();

                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, responseCopy);
                });

                return response;
            })
            .catch(() => caches.match(event.request))
    );
});