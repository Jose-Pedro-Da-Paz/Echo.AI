from django.db import models
from django.contrib.auth.models import User

class Transcription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    audio_file = models.FileField(upload_to='audio_files/', null=True, blank=True)

    def __str__(self):
        return f"Transcription by {self.user.username} on {self.created_at}"
