from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from singledrive_api.models import Folder
from singledrive_api.permissions import IsOwner
from singledrive_api.serializers.folder import FolderSerializer, FolderTreeSerializer


class FolderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = FolderSerializer
    pagination_class = None  # folders are few; cursor pagination's ordering field doesn't match
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        user = self.request.user
        qs = Folder.objects.select_related('parent').filter(
            Q(owner=user) | Q(is_shared=True),
            is_deleted=False,
        ).annotate(
            _children_count=Count('children', filter=Q(children__is_deleted=False), distinct=True),
            _files_count=Count('files', filter=Q(files__is_deleted=False), distinct=True),
        )
        parent = self.request.query_params.get('parent')
        if parent == 'root':
            qs = qs.filter(parent__isnull=True)
        elif parent:
            qs = qs.filter(parent_id=parent)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Returns root folders with immediate children for sidebar tree."""
        roots = Folder.objects.select_related('parent').filter(
            Q(owner=request.user) | Q(is_shared=True),
            parent__isnull=True,
            is_deleted=False,
        ).prefetch_related('children')
        serializer = FolderTreeSerializer(roots, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def trash(self, request, pk=None):
        folder = self.get_object()
        now = timezone.now()
        folder.is_deleted = True
        folder.deleted_at = now
        folder.save(update_fields=['is_deleted', 'deleted_at'])
        # Cascade: mark all direct and nested files as deleted too
        folder.files.filter(is_deleted=False).update(is_deleted=True, deleted_at=now)
        return Response({'detail': 'Carpeta movida a la papelera.'})
