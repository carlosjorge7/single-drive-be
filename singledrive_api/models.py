import uuid
import os
from django.db import models
from django.contrib.auth.models import User


def drive_file_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f"files/{instance.owner.id}/{uuid.uuid4()}{ext}"


def thumb_upload_path(instance, filename):
    return f"thumbs/{instance.id}/{filename}"


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.CASCADE, related_name='children'
    )
    name = models.CharField(max_length=500)
    is_shared = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['owner', 'parent', 'is_deleted']),
            models.Index(fields=['is_shared']),
        ]

    def __str__(self):
        return self.name


class DriveFile(models.Model):
    class FileType(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        AUDIO = 'audio', 'Audio'
        DOCUMENT = 'document', 'Document'
        OTHER = 'other', 'Other'

    class ProcessingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        DONE = 'done', 'Done'
        ERROR = 'error', 'Error'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drive_files')
    folder = models.ForeignKey(
        Folder, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='files'
    )
    name = models.CharField(max_length=500)
    original_name = models.CharField(max_length=500)
    file = models.FileField(upload_to=drive_file_upload_path)
    size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=200, blank=True)
    file_type = models.CharField(
        max_length=20, choices=FileType.choices, default=FileType.OTHER
    )
    thumbnail_small = models.ImageField(
        upload_to='thumbs/', null=True, blank=True
    )
    thumbnail_medium = models.ImageField(
        upload_to='thumbs/', null=True, blank=True
    )
    exif_data = models.JSONField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    file_hash = models.CharField(max_length=64, null=True, blank=True)
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'folder', 'is_deleted']),
            models.Index(fields=['owner', 'file_type', 'is_deleted']),
            models.Index(fields=['owner', 'is_deleted', 'created_at']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

    @property
    def extension(self):
        return os.path.splitext(self.original_name)[1].lower()


class ChunkedUpload(models.Model):
    class Status(models.TextChoices):
        UPLOADING = 'uploading', 'Uploading'
        COMPLETE = 'complete', 'Complete'
        EXPIRED = 'expired', 'Expired'

    upload_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chunked_uploads')
    filename = models.CharField(max_length=500)
    total_size = models.BigIntegerField()
    offset = models.BigIntegerField(default=0)
    temp_file_path = models.CharField(max_length=1000, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADING
    )
    folder = models.ForeignKey(
        Folder, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['owner', 'status']),
        ]

    def __str__(self):
        return f"{self.filename} ({self.offset}/{self.total_size})"
