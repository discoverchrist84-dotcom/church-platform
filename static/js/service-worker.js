/* Service worker: makes the site installable and resilient offline.
 *
 * Strategy
 *  - Pages (navigations): network first, fall back to cache, then /offline/.
 *  - Static files:        stale-while-revalidate.
 *  - API, admin, media:   never cached here (always live).
 * Bump VERSION when you change this file to clear old caches.
 */
const VERSION = "v7";
const PAGES = `pages-${VERSION}`;
const ASSETS = `assets-${VERSION}`;
const PRIVATE = /^\/(give|notifications)\/|^\/books\/(cart|checkout|orders|library|download)\/|^\/branches\/[^/]+\/(board|groups|prayer|moderation|events\/new|announcements\/new|sermons\/new)\//;
const PRECACHE = ["/offline/", "/static/css/app.css", "/static/js/app.js", "/static/icons/icon-192.png", "/static/img/logo.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(ASSETS).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => ![PAGES, ASSETS].includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (/^\/(api|admin|media|accounts)\//.test(url.pathname) || url.pathname.startsWith("/ws/")) return;

  // Personal pages (giving, notifications, member-only branch areas) are never stored on the
  // device, so nothing private lingers on a shared phone after sign-out.
  if (PRIVATE.test(url.pathname)) {
    if (req.mode === "navigate") {
      event.respondWith(fetch(req).catch(() => caches.match("/offline/")));
    }
    return;
  }

  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(PAGES).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req).then((hit) => hit || caches.match("/offline/")))
    );
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.open(ASSETS).then((cache) =>
        cache.match(req).then((hit) => {
          const refresh = fetch(req)
            .then((res) => {
              if (res.ok) cache.put(req, res.clone());
              return res;
            })
            .catch(() => hit);
          return hit || refresh;
        })
      )
    );
  }
});
