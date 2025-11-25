from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, TaskViewSet, TimeLogViewSet, TaskCommentViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'time-logs', TimeLogViewSet)
router.register(r'task-comments', TaskCommentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
