from django.db import models
from django.contrib.auth.models import User

class Folder(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')

    def __str__(self):
        return self.name

class Transcription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='transcriptions')
