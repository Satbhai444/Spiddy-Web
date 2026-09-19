"""
URL routing package for the drop app.

This acts as the main `urls.py` by grouping the smaller URL modules
and re-exporting them as `urlpatterns`.
"""

from django.urls import include, path

from ..views import pages as views

# The root-level pages aren't grouped under a prefix, so we include them directly here
urlpatterns = [
    path('', views.home_view, name='home'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('dmca/', views.dmca_view, name='dmca'),
    path('contact/', views.contact_view, name='contact'),
    path('hq/', views.hq_view, name='hq'),
    path('docs/', views.docs_view, name='docs'),

    # Include specific feature routes
    path('', include('drop.urls.filedrop')),
    path('room/', include('drop.urls.rooms')),
    path('', include('drop.urls.seo')),
    path('', include('drop.urls.pwa')),
    path('', include('drop.urls.slinger')),
]
