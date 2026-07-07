from datetime import timedelta

from django.utils import timezone
from huey.contrib.djhuey import periodic_task, crontab


@periodic_task(crontab(minute='0', hour='3'))
def purge_old_trash():
    """Delete files that have been in trash for more than 30 days."""
    from singledrive_api.models import DriveFile
    from singledrive_api.utils import delete_file_from_disk
    cutoff = timezone.now() - timedelta(days=30)
    old_files = DriveFile.objects.filter(is_deleted=True, deleted_at__lt=cutoff)
    count = old_files.count()
    for f in old_files:
        delete_file_from_disk(f)
    old_files.delete()
    return f'Purged {count} old trash file(s)'
