from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination

from singledrive_api.models import DriveFile
from singledrive_api.permissions import IsOwner
from singledrive_api.serializers.file import DriveFileListSerializer, DriveFileDetailSerializer
from singledrive_api.utils import delete_file_from_disk

import io, zipfile, os
from django.db.models import Sum
from django.http import HttpResponse
from django.conf import settings as django_settings


class DriveFileCursorPagination(CursorPagination):
    page_size = 50
    ordering = '-created_at'
    cursor_query_param = 'cursor'


class RecentFilesCursorPagination(CursorPagination):
    page_size = 50
    ordering = '-updated_at'
    cursor_query_param = 'cursor'


class DriveFileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    pagination_class = DriveFileCursorPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'original_name']
    ordering_fields = ['name', 'size', 'created_at', 'file_type']

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        trash = params.get('trash') == 'true'
        shared = params.get('shared') == 'true'

        if trash:
            return DriveFile.objects.filter(owner=user, is_deleted=True)

        if shared:
            return DriveFile.objects.filter(
                owner=user,
                is_deleted=False,
                folder__is_shared=True,
            )

        qs = DriveFile.objects.select_related('owner', 'folder').filter(owner=user, is_deleted=False)

        folder = params.get('folder')
        if folder == 'root':
            qs = qs.filter(folder__isnull=True)
        elif folder:
            qs = qs.filter(folder_id=folder)

        file_type = params.get('type')
        if file_type:
            types = [t.strip() for t in file_type.split(',') if t.strip()]
            # Exclude files whose parent folder is in the trash
            qs = qs.filter(file_type__in=types).filter(
                Q(folder__isnull=True) | Q(folder__is_deleted=False)
            )

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return DriveFileListSerializer
        return DriveFileDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def trash(self, request, pk=None):
        file = self.get_object()
        file.is_deleted = True
        file.deleted_at = timezone.now()
        file.save(update_fields=['is_deleted', 'deleted_at'])
        return Response({'detail': 'Archivo movido a la papelera.'})

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        from singledrive_api.models import Folder
        file = self.get_object()
        folder_id = request.data.get('folder_id')
        if folder_id is None:
            file.folder = None
        else:
            try:
                folder = Folder.objects.get(pk=folder_id, is_deleted=False)
                if folder.owner != request.user and not folder.is_shared:
                    return Response({'detail': 'No permitido.'}, status=403)
                file.folder = folder
            except Folder.DoesNotExist:
                return Response({'detail': 'Carpeta no encontrada.'}, status=404)
        file.save(update_fields=['folder'])
        return Response({'detail': 'Archivo movido.'})

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        try:
            file = DriveFile.objects.get(pk=pk, owner=request.user, is_deleted=True)
        except DriveFile.DoesNotExist:
            return Response({'detail': 'No encontrado.'}, status=404)
        file.is_deleted = False
        file.deleted_at = None
        file.save(update_fields=['is_deleted', 'deleted_at'])
        return Response({'detail': 'Archivo restaurado.'})

    @action(detail=True, methods=['delete'])
    def delete_permanent(self, request, pk=None):
        try:
            file = DriveFile.objects.get(pk=pk, owner=request.user, is_deleted=True)
        except DriveFile.DoesNotExist:
            return Response({'detail': 'No encontrado.'}, status=404)
        # Remove file and thumbnails from disk
        delete_file_from_disk(file)
        file.delete()
        return Response(status=204)

    @action(detail=False, methods=['delete'])
    def empty_trash(self, request):
        files = DriveFile.objects.filter(owner=request.user, is_deleted=True)
        count = files.count()
        for f in files:
            delete_file_from_disk(f)
        files.delete()
        return Response({'detail': f'{count} archivo(s) eliminado(s) permanentemente.'})

    @action(detail=False, methods=['post'])
    def bulk_trash(self, request):
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return Response({'detail': 'Se requiere lista de ids.'}, status=400)
        now = timezone.now()
        count = DriveFile.objects.filter(
            id__in=ids, owner=request.user, is_deleted=False
        ).update(is_deleted=True, deleted_at=now)
        return Response({'detail': f'{count} archivo(s) movido(s) a la papelera.', 'count': count})

    @action(detail=False, methods=['post'])
    def bulk_move(self, request):
        from singledrive_api.models import Folder
        ids = request.data.get('ids', [])
        folder_id = request.data.get('folder_id')
        if not ids or not isinstance(ids, list):
            return Response({'detail': 'Se requiere lista de ids.'}, status=400)
        if folder_id is not None:
            try:
                folder = Folder.objects.get(pk=folder_id, is_deleted=False)
                if folder.owner != request.user and not folder.is_shared:
                    return Response({'detail': 'No permitido.'}, status=403)
            except Folder.DoesNotExist:
                return Response({'detail': 'Carpeta no encontrada.'}, status=404)
        count = DriveFile.objects.filter(
            id__in=ids, owner=request.user, is_deleted=False
        ).update(folder_id=folder_id)
        return Response({'detail': f'{count} archivo(s) movido(s).', 'count': count})

    @action(detail=False, methods=['get'])
    def bulk_download(self, request):
        ids_param = request.query_params.get('ids', '')
        ids = [i.strip() for i in ids_param.split(',') if i.strip()]
        if not ids:
            return Response({'detail': 'No se especificaron archivos.'}, status=400)
        files = DriveFile.objects.filter(
            id__in=ids, owner=request.user, is_deleted=False
        ).only('id', 'file', 'original_name', 'size')
        if not files.exists():
            return Response({'detail': 'No se encontraron archivos.'}, status=404)
        total_size = files.aggregate(total=Sum('size'))['total'] or 0
        if len(ids) > 50:
            return Response({'detail': 'Máximo 50 archivos por descarga.'}, status=400)
        if total_size > 2 * 1024 ** 3:
            return Response({'detail': 'La selección supera 2 GB. Descarga los archivos individualmente.'}, status=413)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            seen = {}
            for f in files:
                if not f.file:
                    continue
                try:
                    name = f.original_name
                    if name in seen:
                        seen[name] += 1
                        base, ext = os.path.splitext(name)
                        name = f'{base} ({seen[name]}){ext}'
                    else:
                        seen[name] = 0
                    zf.write(f.file.path, name)
                except Exception:
                    pass
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="homedrive-download.zip"'
        return response

    @action(detail=False, methods=['get'])
    def recent(self, request):
        from django.db.models import Q as Qr
        qs = DriveFile.objects.select_related('owner', 'folder').filter(
            owner=request.user, is_deleted=False
        ).filter(Qr(folder__isnull=True) | Qr(folder__is_deleted=False))
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Qr(name__icontains=search) | Qr(original_name__icontains=search))
        paginator = RecentFilesCursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = DriveFileListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        from django.db.models import Count, Sum
        qs = DriveFile.objects.filter(owner=request.user, is_deleted=False)
        totals = qs.aggregate(
            total_files=Count('id'),
            total_size=Sum('size'),
        )
        by_type = dict(qs.values_list('file_type').annotate(count=Count('id')))
        return Response({
            'total_files': totals['total_files'] or 0,
            'total_size': totals['total_size'] or 0,
            'quota_bytes': getattr(django_settings, 'USER_STORAGE_QUOTA_BYTES', 100 * 1024 ** 3),
            'by_type': {
                'image': by_type.get('image', 0),
                'video': by_type.get('video', 0),
                'audio': by_type.get('audio', 0),
                'document': by_type.get('document', 0),
                'other': by_type.get('other', 0),
            },
        })
