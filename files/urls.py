from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FolderViewSet, FileViewSet, FileShareViewSet,
    shared_folder_access, shared_file_access, shared_file_download
)

router = DefaultRouter()
router.register(r'folders', FolderViewSet)
router.register(r'files', FileViewSet)
router.register(r'shares', FileShareViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('shared/folder/<str:folder_link>/', shared_folder_access, name='shared_folder_access'),
    path('shared/file/<str:file_link>/', shared_file_access, name='shared_file_access'),
    path('shared/file/<str:file_link>/download/', shared_file_download, name='shared_file_download'),
]