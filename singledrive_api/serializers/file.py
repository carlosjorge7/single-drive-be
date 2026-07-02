from rest_framework import serializers
from singledrive_api.models import DriveFile


class DriveFileListSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    stream_url = serializers.SerializerMethodField()
    thumbnail_small_url = serializers.SerializerMethodField()
    thumbnail_medium_url = serializers.SerializerMethodField()

    class Meta:
        model = DriveFile
        fields = [
            'id', 'name', 'original_name', 'stream_url', 'size', 'mime_type',
            'file_type', 'thumbnail_small_url', 'thumbnail_medium_url',
            'processing_status', 'is_deleted', 'created_at', 'updated_at',
            'owner_username', 'folder',
        ]
        read_only_fields = ['id', 'stream_url', 'created_at', 'updated_at', 'owner_username', 'processing_status']

    def get_stream_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/v1/files/{obj.id}/stream/')
        return None

    def get_thumbnail_small_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail_small and request:
            return request.build_absolute_uri(obj.thumbnail_small.url)
        return None

    def get_thumbnail_medium_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail_medium and request:
            return request.build_absolute_uri(obj.thumbnail_medium.url)
        return None


class DriveFileDetailSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    stream_url = serializers.SerializerMethodField()
    thumbnail_small_url = serializers.SerializerMethodField()
    thumbnail_medium_url = serializers.SerializerMethodField()

    class Meta:
        model = DriveFile
        fields = [
            'id', 'name', 'original_name', 'stream_url', 'size',
            'mime_type', 'file_type', 'thumbnail_small_url', 'thumbnail_medium_url',
            'exif_data', 'duration', 'file_hash', 'processing_status',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at',
            'owner_username', 'folder',
        ]
        read_only_fields = [
            'id', 'stream_url', 'size', 'mime_type', 'file_type',
            'thumbnail_small_url', 'thumbnail_medium_url', 'exif_data', 'duration',
            'file_hash', 'processing_status', 'created_at', 'updated_at', 'owner_username',
        ]

    def get_stream_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/v1/files/{obj.id}/stream/')
        return None

    def get_thumbnail_small_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail_small and request:
            return request.build_absolute_uri(obj.thumbnail_small.url)
        return None

    def get_thumbnail_medium_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail_medium and request:
            return request.build_absolute_uri(obj.thumbnail_medium.url)
        return None
