import os
import re
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from singledrive_api.models import DriveFile


CHUNK_SIZE = 8 * 1024  # 8 KB


def _file_iterator(file_path, start, end):
    with open(file_path, 'rb') as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


class FileStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def initialize_request(self, request, *args, **kwargs):
        # Inject ?token= into Authorization header before DRF auth runs
        # so <video src>, <iframe src>, <img src> work without custom headers
        token = request.GET.get('token')
        if token and 'HTTP_AUTHORIZATION' not in request.META:
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        return super().initialize_request(request, *args, **kwargs)

    def get(self, request, pk):
        try:
            drive_file = DriveFile.objects.get(pk=pk, is_deleted=False)
        except DriveFile.DoesNotExist:
            return HttpResponse(status=404)

        if drive_file.owner != request.user and not (
            drive_file.folder and drive_file.folder.is_shared
        ):
            return HttpResponse(status=403)

        file_path = drive_file.file.path
        if not os.path.exists(file_path):
            return HttpResponse(status=404)

        file_size = os.path.getsize(file_path)
        content_type = drive_file.mime_type or 'application/octet-stream'

        range_header = request.META.get('HTTP_RANGE', '').strip()
        if range_header:
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else file_size - 1
                end = min(end, file_size - 1)

                response = StreamingHttpResponse(
                    _file_iterator(file_path, start, end),
                    status=206,
                    content_type=content_type,
                )
                response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                response['Content-Length'] = end - start + 1
                response['Accept-Ranges'] = 'bytes'
                return response

        response = StreamingHttpResponse(
            _file_iterator(file_path, 0, file_size - 1),
            content_type=content_type,
        )
        response['Content-Length'] = file_size
        response['Accept-Ranges'] = 'bytes'
        response['Content-Disposition'] = f'inline; filename="{drive_file.original_name}"'
        return response
