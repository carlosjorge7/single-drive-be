from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsOwnerOrSharedReadOnly(permissions.BasePermission):
    """Read access to shared resources; write access only to the owner."""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.owner == request.user or getattr(obj, 'is_shared', False)
        return obj.owner == request.user
