from rest_framework import serializers
from singledrive_api.models import Folder


class FolderSerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'parent', 'is_shared',
            'children_count', 'files_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'children_count', 'files_count']

    def get_children_count(self, obj):
        return obj.children.filter(is_deleted=False).count()

    def get_files_count(self, obj):
        return obj.files.filter(is_deleted=False).count()
