// vrijewetgeving.nl service worker — offline, volledig same-origin
const CACHE = 'vw-v1';
const SHELL = [
  'index.html','over.html','api.html','wet.html',
  'bevoegdheden.html','bevoegdhedenketen.html','rechten.html',
  'style.css','vendor/fonts.css','vendor/marked.min.js','vendor/minisearch.min.js',
  'manifest.webmanifest','icon.svg'
];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE)
    .then(c => c.addAll(SHELL.map(u => new Request(u, {cache:'reload'}))))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;          // er is niets externs
  const isData = /\.(json|xml|md)$/.test(url.pathname);
  if (isData) {                                         // data: vers eerst, cache als terugval
    e.respondWith(fetch(req)
      .then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); return r; })
      .catch(() => caches.match(req)));
  } else {                                              // shell: cache eerst
    e.respondWith(caches.match(req)
      .then(c => c || fetch(req).then(r => { const cp = r.clone(); caches.open(CACHE).then(ch => ch.put(req, cp)); return r; })));
  }
});
