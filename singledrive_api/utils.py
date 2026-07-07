import os

from singledrive_api.models import DriveFile


def delete_file_from_disk(file):
    for field in (file.file, file.thumbnail_small, file.thumbnail_medium):
        if field and field.name:
            try:
                path = field.path
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


def detect_file_type(mime_type):
    if not mime_type:
        return DriveFile.FileType.OTHER
    if mime_type.startswith('image/'):
        return DriveFile.FileType.IMAGE
    if mime_type.startswith('video/'):
        return DriveFile.FileType.VIDEO
    if mime_type.startswith('audio/'):
        return DriveFile.FileType.AUDIO
    if mime_type in (
        'application/pdf', 'application/msword', 'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ):
        return DriveFile.FileType.DOCUMENT
    return DriveFile.FileType.OTHER
