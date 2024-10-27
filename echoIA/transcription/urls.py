# transcription/urls.py
from django.urls import path
from .views import RecordView, StopRecordingView, TranscribeView

urlpatterns = [
    path("start-recording/", RecordView.as_view(), name="start-recording"),
    path("stop-recording/", StopRecordingView.as_view(), name="stop-recording"),
    path("transcribe/", TranscribeView.as_view(), name="transcribe"),
]
