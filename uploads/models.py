import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


def default_expiry():
    return timezone.now() + timedelta(hours=24)


class UploadedFile(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    file = models.FileField(
        upload_to='uploads/%Y/%m/%d/'
    )

    original_name = models.CharField(max_length=255)

    file_size = models.BigIntegerField()

    content_type = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(default=default_expiry)

    def __str__(self):
        return self.original_name