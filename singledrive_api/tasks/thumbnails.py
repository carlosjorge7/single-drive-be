import os
import subprocess
from huey.contrib.djhuey import task
from django.conf import settings


def _thumb_dir(file_id):
    path = os.path.join(settings.MEDIA_ROOT, 'thumbs', str(file_id))
    os.makedirs(path, exist_ok=True)
    return path


def _save_pil_thumb(img, file_id, size_name):
    from PIL import Image
    filepath = os.path.join(_thumb_dir(file_id), f'{size_name}.jpg')
    rgb = img.convert('RGB') if img.mode not in ('RGB', 'L') else img
    rgb.save(filepath, 'JPEG', quality=85, optimize=True)
    return f'thumbs/{file_id}/{size_name}.jpg'


@task()
def generate_image_thumbnails(file_id):
    from singledrive_api.models import DriveFile
    from PIL import Image

    try:
        f = DriveFile.objects.get(id=file_id)
        f.processing_status = DriveFile.ProcessingStatus.PROCESSING
        f.save(update_fields=['processing_status'])

        with Image.open(f.file.path) as img:
            img.load()

            small = img.copy()
            small.thumbnail((200, 200), Image.LANCZOS)
            small_rel = _save_pil_thumb(small, file_id, 'small')

            medium = img.copy()
            medium.thumbnail((600, 400), Image.LANCZOS)
            medium_rel = _save_pil_thumb(medium, file_id, 'medium')

            # Extract EXIF
            exif_data = _extract_exif(img)

        f.thumbnail_small = small_rel
        f.thumbnail_medium = medium_rel
        f.exif_data = exif_data
        f.processing_status = DriveFile.ProcessingStatus.DONE
        f.save(update_fields=['thumbnail_small', 'thumbnail_medium', 'exif_data', 'processing_status'])

    except DriveFile.DoesNotExist:
        pass
    except Exception:
        DriveFile.objects.filter(id=file_id).update(
            processing_status=DriveFile.ProcessingStatus.ERROR
        )
        raise


def _extract_exif(img):
    try:
        import piexif
        exif_bytes = img.info.get('exif')
        if not exif_bytes:
            return None
        raw = piexif.load(exif_bytes)
        data = {}

        # Date taken
        dt = raw.get('Exif', {}).get(piexif.ExifIFD.DateTimeOriginal)
        if dt:
            data['date_taken'] = dt.decode('utf-8', errors='ignore')

        # GPS
        gps = raw.get('GPS', {})
        if gps:
            lat = _dms_to_decimal(
                gps.get(piexif.GPSIFD.GPSLatitude),
                gps.get(piexif.GPSIFD.GPSLatitudeRef, b'N'),
            )
            lon = _dms_to_decimal(
                gps.get(piexif.GPSIFD.GPSLongitude),
                gps.get(piexif.GPSIFD.GPSLongitudeRef, b'E'),
            )
            if lat is not None and lon is not None:
                data['gps'] = {'lat': lat, 'lon': lon}

        # Camera
        make = raw.get('0th', {}).get(piexif.ImageIFD.Make)
        model = raw.get('0th', {}).get(piexif.ImageIFD.Model)
        if make:
            data['camera_make'] = make.decode('utf-8', errors='ignore').strip('\x00')
        if model:
            data['camera_model'] = model.decode('utf-8', errors='ignore').strip('\x00')

        return data or None
    except Exception:
        return None


def _dms_to_decimal(dms, ref):
    if not dms or len(dms) < 3:
        return None
    try:
        d = dms[0][0] / dms[0][1]
        m = dms[1][0] / dms[1][1]
        s = dms[2][0] / dms[2][1]
        val = d + m / 60 + s / 3600
        if ref in (b'S', b'W'):
            val = -val
        return round(val, 6)
    except (ZeroDivisionError, IndexError, TypeError):
        return None


@task()
def generate_video_thumbnail(file_id):
    from singledrive_api.models import DriveFile

    try:
        f = DriveFile.objects.get(id=file_id)
        f.processing_status = DriveFile.ProcessingStatus.PROCESSING
        f.save(update_fields=['processing_status'])

        thumb_dir = _thumb_dir(file_id)
        small_path = os.path.join(thumb_dir, 'small.jpg')

        # Low-priority frame extraction at 5s (fallback to 0s if video is shorter)
        result = subprocess.run(
            [
                'ffmpeg', '-y',
                '-ss', '00:00:05',
                '-i', f.file.path,
                '-vframes', '1',
                '-vf', 'scale=200:200:force_original_aspect_ratio=decrease,pad=200:200:(ow-iw)/2:(oh-ih)/2',
                '-q:v', '3',
                small_path,
            ],
            capture_output=True,
            timeout=90,
            preexec_fn=lambda: os.nice(10),  # lower CPU priority on Pi
        )

        if result.returncode != 0 or not os.path.exists(small_path):
            # Fallback: grab first frame
            subprocess.run(
                ['ffmpeg', '-y', '-i', f.file.path, '-vframes', '1', '-q:v', '3', small_path],
                capture_output=True, timeout=90,
                preexec_fn=lambda: os.nice(10),
            )

        # Extract duration
        duration = _get_video_duration(f.file.path)

        updates = {'processing_status': DriveFile.ProcessingStatus.DONE}
        if os.path.exists(small_path):
            f.thumbnail_small = f'thumbs/{file_id}/small.jpg'
            updates['thumbnail_small'] = f.thumbnail_small
        if duration:
            f.duration = duration
            updates['duration'] = duration
        updates['processing_status'] = DriveFile.ProcessingStatus.DONE

        DriveFile.objects.filter(id=file_id).update(**updates)

    except DriveFile.DoesNotExist:
        pass
    except Exception:
        DriveFile.objects.filter(id=file_id).update(
            processing_status=DriveFile.ProcessingStatus.ERROR
        )
        raise


def _get_video_duration(file_path):
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                file_path,
            ],
            capture_output=True, timeout=30, text=True,
        )
        import json
        data = json.loads(result.stdout)
        return float(data['format'].get('duration', 0)) or None
    except Exception:
        return None
