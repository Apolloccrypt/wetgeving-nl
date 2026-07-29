// vrijewetgeving.nl service worker — offline, volledig same-origin
// Twee caches: een lichte app-shell en een aparte bak voor zware data (zoekindex 36 MB),
// zodat quota-eviction van de data de shell niet meesleept.
const SHELL_CACHE = 'vw-shell-v4';
const DATA_CACHE  = 'vw-data-v4';
const BEHOUD = [SHELL_CACHE, DATA_CACHE];

const SHELL = [
  'index.html','over.html','api.html','wet.html',
  'bevoegdheden.html','bevoegdhedenketen.html','rechten.html',
  'style.css','vendor/fonts.css','vendor/marked.min.js','vendor/minisearch.min.js','vendor/purify.min.js',
  'manifest.webmanifest','icon.svg',
  // zelf-gehoste fonts, zodat de eerste offline render niet naar systeemfont valt
  'vendor/fonts/Inter-400-latin.woff2','vendor/fonts/Inter-500-latin.woff2',
  'vendor/fonts/Inter-600-latin.woff2','vendor/fonts/Inter-700-latin.woff2',
  'vendor/fonts/DMMono-400-latin.woff2','vendor/fonts/DMMono-500-latin.woff2'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL_CACHE)
    .then(c => c.addAll(SHELL.map(u => new Request(u, {cache:'reload'}))))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => !BEHOUD.includes(k)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;          // er is niets externs

  const isData = /\.(json|xml|md)$/.test(url.pathname);
  if (isData) {
    // stale-while-revalidate: cache direct serveren (ook de 36 MB-index niet opnieuw
    // over de lijn), en op de achtergrond verversen. Geen cache -> wacht op netwerk.
    e.respondWith(caches.open(DATA_CACHE).then(c =>
      c.match(req).then(hit => {
        const netwerk = fetch(req).then(r => { if (r && r.ok) c.put(req, r.clone()); return r; })
          .catch(() => hit);
        return hit || netwerk;
      })
    ));
  } else {
    // shell: cache eerst. ignoreSearch zodat wet.html?id=BWB... ook offline de
    // voorgecachete wet.html-shell krijgt i.p.v. een browser-foutpagina.
    e.respondWith(caches.open(SHELL_CACHE).then(async c => {
      const hit = await c.match(req, {ignoreSearch:true});
      if (hit) return hit;
      try {
        const r = await fetch(req);
        if (r && r.ok) c.put(req, r.clone());
        return r;
      } catch (fout) {
        // Offline en niets in de cache. De shell is opgeslagen onder
        // 'index.html', dus een bezoek aan '/' (de start_url uit het manifest)
        // matcht nergens op en werd een browserfoutpagina. Elke navigatie
        // valt daarom terug op de app-shell.
        if (req.mode === 'navigate') {
          const shell = await c.match('index.html');
          if (shell) return shell;
        }
        throw fout;
      }
    }));
  }
});
