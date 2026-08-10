const CACHE = "gym-pwa-v5";
const ASSETS = [
	"/gym-app",
	"/assets/gym_management/gym_pwa/css/app.css",
	"/assets/gym_management/gym_pwa/js/app.js",
	"/assets/gym_management/gym_pwa/sg-fitness-logo.png",
	"/assets/gym_management/gym_pwa/icon.svg",
	"/assets/gym_management/gym_pwa/icon-192.png",
	"/assets/gym_management/gym_pwa/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
	event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)));
	self.skipWaiting();
});

self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches.keys().then((keys) =>
			Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
		)
	);
	self.clients.claim();
});

self.addEventListener("fetch", (event) => {
	const { request } = event;
	if (request.method !== "GET") return;
	const url = new URL(request.url);
	if (url.pathname.startsWith("/api/")) return;

	if (request.mode === "navigate") {
		event.respondWith(
			fetch(request).catch(() => caches.match("/gym-app"))
		);
		return;
	}

	if (url.pathname.startsWith("/assets/gym_management/gym_pwa/")) {
		event.respondWith(
			caches.match(request).then((cached) => cached || fetch(request))
		);
	}
});
