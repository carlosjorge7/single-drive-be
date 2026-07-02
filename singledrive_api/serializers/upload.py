from rest_framework import serializers
from singledrive_api.models import ChunkedUpload


class InitUploadSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=500)
    total_size = serializers.IntegerField(min_value=1)
    folder_id = serializers.UUIDField(required=False, allow_null=True)


class ChunkedUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChunkedUpload
        fields = ['upload_id', 'filename', 'total_size', 'offset', 'status', 'created_at']
        read_only_fields = ['upload_id', 'offset', 'status', 'created_at']
