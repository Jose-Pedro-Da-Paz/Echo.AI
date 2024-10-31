from django.conf import settings
from django.conf.urls.static import static
from .views import RecordView, StopRecordingView, TranscribeView, index
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('start-recording/', RecordView.as_view(), name='start-recording'),
    path('stop-recording/', StopRecordingView.as_view(), name='stop-recording'),
    path('transcribe/', TranscribeView.as_view(), name='transcribe'),
    path('accounts/', include('django.contrib.auth.urls')),
]

# Adiciona URLs para arquivos estáticos em modo de desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL)
