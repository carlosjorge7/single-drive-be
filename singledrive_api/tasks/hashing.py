import hashlib
from huey.contrib.djhuey import task


@task()
def compute_file_hash(file_id):
    """SHA-256 hash via 4KB streaming reads — never loads full file in RAM."""
    from singledrive_api.models import DriveFile

    try:
        f = DriveFile.objects.get(id=file_id)
        sha256 = hashlib.sha256()

        with open(f.file.path, 'rb') as fp:
            while chunk := fp.read(4 * 1024):
                sha256.update(chunk)

        file_hash = sha256.hexdigest()
        DriveFile.objects.filter(id=file_id).update(file_hash=file_hash)

    except DriveFile.DoesNotExist:
        pass
    except Exception:
        raise
