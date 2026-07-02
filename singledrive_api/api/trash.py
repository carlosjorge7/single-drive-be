import os
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination

from singledrive_api.models import DriveFile
from singledrive_api.serializers.file import DriveFileListSerializer


class TrashCursorPagination(CursorPagination):
    page_size = 50
    ordering = '-deleted_at'


class TrashViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DriveFileListSerializer
    pagination_class = TrashCursorPagination

    def get_queryset(self):
        return DriveFile.objects.filter(owner=self.request.user, is_deleted=True)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

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
    def permanent(self, request, pk=None):
        try:
            file = DriveFile.objects.get(pk=pk, owner=request.user, is_deleted=True)
        except DriveFile.DoesNotExist:
            return Response({'detail': 'No encontrado.'}, status=404)
        for field in [file.file, file.thumbnail_small, file.thumbnail_medium]:
            if field:
                try:
                    os.remove(field.path)
                except FileNotFoundError:
                    pass
        file.delete()
        return Response(status=204)

    @action(detail=False, methods=['delete'])
    def empty(self, request):
        files = DriveFile.objects.filter(owner=request.user, is_deleted=True)
        for file in files:
            for field in [file.file, file.thumbnail_small, file.thumbnail_medium]:
                if field:
                    try:
                        os.remove(field.path)
                    except FileNotFoundError:
                        pass
        files.delete()
        return Response(status=204)
