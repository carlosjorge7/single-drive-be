from django.contrib import admin
from singledrive_api.models import DriveFile, Folder, ChunkedUpload


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'parent', 'is_shared', 'is_deleted', 'created_at']
    list_filter = ['is_shared', 'is_deleted', 'created_at']
    search_fields = ['name', 'owner__username']
    raw_id_fields = ['owner', 'parent']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(DriveFile)
class DriveFileAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'owner', 'file_type', 'size_display',
        'processing_status', 'is_deleted', 'created_at',
    ]
    list_filter = ['file_type', 'processing_status', 'is_deleted', 'created_at']
    search_fields = ['name', 'original_name', 'owner__username']
    raw_id_fields = ['owner', 'folder']
    readonly_fields = [
        'id', 'size', 'mime_type', 'file_type', 'file_hash',
        'exif_data', 'duration', 'thumbnail_small', 'thumbnail_medium',
        'processing_status', 'created_at', 'updated_at',
    ]

    def size_display(self, obj):
        if obj.size < 1024:
            return f"{obj.size} B"
        if obj.size < 1024 ** 2:
            return f"{obj.size / 1024:.1f} KB"
        if obj.size < 1024 ** 3:
            return f"{obj.size / 1024 ** 2:.1f} MB"
        return f"{obj.size / 1024 ** 3:.1f} GB"
    size_display.short_description = 'Tamaño'


@admin.register(ChunkedUpload)
class ChunkedUploadAdmin(admin.ModelAdmin):
    list_display = ['filename', 'owner', 'offset', 'total_size', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['filename', 'owner__username']
    readonly_fields = ['upload_id', 'created_at', 'updated_at']
