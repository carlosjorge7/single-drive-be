from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from singledrive_api.api.auth import LoginView, LogoutView, MeView, RegisterView
from singledrive_api.api.files import DriveFileViewSet
from singledrive_api.api.folders import FolderViewSet
from singledrive_api.api.upload import FileUploadView
from singledrive_api.api.stream import FileStreamView
from singledrive_api.api.trash import TrashViewSet

router = DefaultRouter()
router.register(r'files', DriveFileViewSet, basename='drivefile')
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'trash', TrashViewSet, basename='trash')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('api/v1/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/v1/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('api/v1/auth/me/', MeView.as_view(), name='auth-me'),

    # File upload (streaming, no chunking needed on local/VPN)
    path('api/v1/upload/', FileUploadView.as_view(), name='file-upload'),

    # File streaming (dev) — in production nginx handles /media/ directly
    path('api/v1/files/<uuid:pk>/stream/', FileStreamView.as_view(), name='file-stream'),

    # REST API
    path('api/v1/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
