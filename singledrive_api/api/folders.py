from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from singledrive_api.models import Folder
from singledrive_api.permissions import IsOwner
from singledrive_api.serializers.folder import FolderSerializer


class FolderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = FolderSerializer

    def get_queryset(self):
        user = self.request.user
        return Folder.objects.filter(
            Q(owner=user) | Q(is_shared=True),
            is_deleted=False
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        folders = Folder.objects.filter(
            Q(owner=request.user) | Q(is_shared=True),
            parent__isnull=True,
            is_deleted=False
        ).prefetch_related('children')
        serializer = self.get_serializer(folders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def trash(self, request, pk=None):
        folder = self.get_object()
        folder.is_deleted = True
        folder.deleted_at = timezone.now()
        folder.save(update_fields=['is_deleted', 'deleted_at'])
        return Response({'detail': 'Carpeta movida a la papelera.'})
