"""
SEO views — robots.txt and sitemap.xml.
"""

from django.http import HttpResponse
from django.utils import timezone


def robots_txt_view(request):
    """SEO Robots.txt handler with crawl-budget optimization"""
    content = """User-agent: *
Allow: /
Disallow: /hq/
Disallow: /room/
Disallow: /get/
Disallow: /file/

Sitemap: https://spiddy-web.vercel.app/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")


def sitemap_xml_view(request):
    """SEO Dynamic Sitemap.xml handler with fresh lastmod timestamps"""
    today = timezone.now().strftime('%Y-%m-%d')
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://spiddy-web.vercel.app/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/upload/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/receive/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/docs/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/privacy/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/terms/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/contact/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>
"""
    return HttpResponse(content, content_type="application/xml")
