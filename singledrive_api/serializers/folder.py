from rest_framework import serializers
from singledrive_api.models import Folder


class FolderSerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'parent', 'is_shared',
            'children_count', 'files_count', 'path',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'children_count', 'files_count', 'path']

    def get_children_count(self, obj):
        if hasattr(obj, '_children_count'):
            return obj._children_count
        return obj.children.filter(is_deleted=False).count()

    def get_files_count(self, obj):
        if hasattr(obj, '_files_count'):
            return obj._files_count
        return obj.files.filter(is_deleted=False).count()

    def get_path(self, obj):
        """Returns ancestry chain for breadcrumb navigation."""
        path = []
        current = obj
        while current is not None:
            path.insert(0, {'id': str(current.id), 'name': current.name})
            current = current.parent
        return path


class FolderTreeSerializer(FolderSerializer):
    """Includes immediate children — used by the /tree endpoint."""
    children = serializers.SerializerMethodField()

    class Meta(FolderSerializer.Meta):
        fields = FolderSerializer.Meta.fields + ['children']

    def get_children(self, obj):
        kids = obj.children.filter(is_deleted=False)
        return FolderTreeSerializer(kids, many=True).data
