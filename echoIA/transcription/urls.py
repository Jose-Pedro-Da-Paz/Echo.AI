from django.conf import settings
from django.conf.urls.static import static
from .views import RecordView, StopRecordingView, TranscribeView, index, folder_list, create_folder, TranscriptionListView, SaveTranscriptionView, editor_view, save_updates_view, get_concatenated_transcriptions, save_concatenated_transcriptions
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('start-recording/', RecordView.as_view(), name='start-recording'),
    path('stop-recording/', StopRecordingView.as_view(), name='stop-recording'),
    path('transcribe/', TranscribeView.as_view(), name='transcribe'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('folders/', folder_list, name='folder-list'),
    path('folders/<int:folder_id>/transcriptions/', TranscriptionListView.as_view(), name='transcription-list'),
    path('create-folder/', create_folder, name='create-folder'),
    path('save-transcription/', SaveTranscriptionView.as_view(), name='save_transcription'),
    path('editor/<int:folder_id>/', editor_view, name='editor'),
    path('save-updates/', save_updates_view, name='save_updates'),
    path('editor/<int:folder_id>/concatenated/', get_concatenated_transcriptions, name='get_concatenated_transcriptions'),
    path('save-concatenated/', save_concatenated_transcriptions, name='save_concatenated_transcriptions'),
    
]

# Adiciona URLs para arquivos estáticos em modo de desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL)
