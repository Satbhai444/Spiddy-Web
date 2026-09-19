from django.urls import path
from ..views.slinger import slinger_view

urlpatterns = [
    path('slinger/', slinger_view, name='slinger'),
]
