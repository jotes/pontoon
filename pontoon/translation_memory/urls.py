from django.conf.urls import patterns, url

from pontoon.translation_memory import views


urlpatterns = patterns(
    '',
    url(r'^translation-memory2/$', views.translation_memory,
        name='pontoon.translation_memory2')
)
