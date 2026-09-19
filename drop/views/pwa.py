"""
Progressive Web App (PWA) views — manifest, service worker, favicon.
"""

import os

from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse


def favicon_view(request):
    """Serve favicon.ico with high compatibility for Googlebot and browsers"""
    ico_path = os.path.join(settings.BASE_DIR, 'drop', 'static', 'drop', 'images', 'favicon.ico')
    if os.path.exists(ico_path):
        return FileResponse(open(ico_path, 'rb'), content_type='image/x-icon')
    return HttpResponse(status=404)


def manifest_view(request):
    manifest_data = {
        "name": "SPIDDY Web Drop - Anonymous File Sharing & Spider-Verse Rooms",
        "short_name": "SpiddyWeb",
        "description": "Fast, temporary, encrypted anonymous file sharing & Spider-Verse chat rooms.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f1117",
        "theme_color": "#dc2626",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/drop/images/android-chrome-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/drop/images/android-chrome-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return JsonResponse(manifest_data, content_type='application/manifest+json')


def service_worker_view(request):
    sw_code = """
const CACHE_NAME = 'spiddy-cache-v1';
const STATIC_ASSETS = [
  '/',
  '/upload/',
  '/receive/',
  'https://cdn.tailwindcss.com',
  'https://raw.githubusercontent.com/Satbhai444/Spiddy-Web/main/drop/static/drop/images/spiderman.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});
"""
    return HttpResponse(sw_code, content_type='application/javascript')
