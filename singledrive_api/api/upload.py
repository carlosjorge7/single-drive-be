import os
import uuid
import mimetypes
from django.conf import settings
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from singledrive_api.models import DriveFile, Folder
from singledrive_api.serializers.file import DriveFileDetailSerializer
from singledrive_api.utils import detect_file_type


class FileUploadView(APIView):
    """
    Simple streaming upload — file goes directly to disk via TemporaryFileUploadHandler.
    No chunking needed for local/VPN network usage.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'detail': 'No se recibió ningún archivo.'}, status=400)

        # Size check
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 20 * 1024 * 1024 * 1024)
        if uploaded.size > max_size:
            return Response(
                {'detail': f'El archivo supera el límite de {max_size // (1024**3)} GB.'},
                status=413,
            )

        # Extension check
        ext = os.path.splitext(uploaded.name)[1].lower()
        blocked = getattr(settings, 'BLOCKED_EXTENSIONS', set())
        if ext in blocked:
            return Response(
                {'detail': f'Tipo de archivo no permitido ({ext}).'},
                status=415,
            )

        folder = None
        folder_id = request.data.get('folder_id')
        if folder_id:
            try:
                folder = Folder.objects.get(
                    Q(owner=request.user) | Q(is_shared=True),
                    id=folder_id,
                    is_deleted=False,
                )
            except Folder.DoesNotExist:
                return Response({'detail': 'Carpeta no encontrada.'}, status=404)

        original_name = uploaded.name
        mime_type = uploaded.content_type or mimetypes.guess_type(original_name)[0] or 'application/octet-stream'
        file_type = detect_file_type(mime_type)
        needs_processing = file_type in (DriveFile.FileType.IMAGE, DriveFile.FileType.VIDEO)

        ext = os.path.splitext(original_name)[1]
        relative_path = f"files/{request.user.id}/{uuid.uuid4()}{ext}"
        final_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        # Write to disk in chunks — never loads full file in RAM
        with open(final_path, 'wb') as dest:
            for chunk in uploaded.chunks(chunk_size=256 * 1024):
                dest.write(chunk)

        drive_file = DriveFile.objects.create(
            owner=request.user,
            folder=folder,
            name=original_name,
            original_name=original_name,
            file=relative_path,
            size=uploaded.size,
            mime_type=mime_type,
            file_type=file_type,
            processing_status=(
                DriveFile.ProcessingStatus.PENDING
                if needs_processing
                else DriveFile.ProcessingStatus.DONE
            ),
        )

        # Trigger background tasks
        from singledrive_api.tasks.hashing import compute_file_hash
        compute_file_hash(str(drive_file.id))

        if file_type == DriveFile.FileType.IMAGE:
            from singledrive_api.tasks.thumbnails import generate_image_thumbnails
            generate_image_thumbnails(str(drive_file.id))
        elif file_type == DriveFile.FileType.VIDEO:
            from singledrive_api.tasks.thumbnails import generate_video_thumbnail
            generate_video_thumbnail(str(drive_file.id))

        return Response(
            DriveFileDetailSerializer(drive_file, context={'request': request}).data,
            status=201,
        )
