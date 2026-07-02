import os
from django.utils import timezone
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination

from singledrive_api.models import DriveFile
from singledrive_api.permissions import IsOwner
from singledrive_api.serializers.file import DriveFileListSerializer, DriveFileDetailSerializer


def _delete_file_from_disk(file):
    for field in (file.file, file.thumbnail_small, file.thumbnail_medium):
        if field and field.name:
            try:
                path = field.path
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


class DriveFileCursorPagination(CursorPagination):
    page_size = 50
    ordering = '-created_at'
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

        qs = DriveFile.objects.filter(owner=user, is_deleted=False)

        folder = params.get('folder')
        if folder == 'root':
            qs = qs.filter(folder__isnull=True)
        elif folder:
            qs = qs.filter(folder_id=folder)

        file_type = params.get('type')
        if file_type:
            types = [t.strip() for t in file_type.split(',') if t.strip()]
            qs = qs.filter(file_type__in=types)

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
        _delete_file_from_disk(file)
        file.delete()
        return Response(status=204)

    @action(detail=False, methods=['delete'])
    def empty_trash(self, request):
        files = DriveFile.objects.filter(owner=request.user, is_deleted=True)
        count = files.count()
        for f in files:
            _delete_file_from_disk(f)
        files.delete()
        return Response({'detail': f'{count} archivo(s) eliminado(s) permanentemente.'})

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
            'by_type': {
                'image': by_type.get('image', 0),
                'video': by_type.get('video', 0),
                'audio': by_type.get('audio', 0),
                'document': by_type.get('document', 0),
                'other': by_type.get('other', 0),
            },
        })
