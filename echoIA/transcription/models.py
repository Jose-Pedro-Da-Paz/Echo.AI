from django.db import models
from django.contrib.auth.models import User

class Transcription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transcriptions')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcrição por {self.user.username} em {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
