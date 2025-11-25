from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, TaskViewSet, TimeLogViewSet, TaskCommentViewSet
)

# indrajit start
from .views import ProjectDetailViewSet,AmountPayableViewSet,AmountReceivedViewSet
# indrajit end

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'time-logs', TimeLogViewSet)
router.register(r'task-comments', TaskCommentViewSet)

# indrajit start

router.register(r'project-details',ProjectDetailViewSet)
router.register(r'amounts-payable', AmountPayableViewSet)
router.register(r'amounts-received', AmountReceivedViewSet)

# indrajit end

urlpatterns = [
    path('', include(router.urls)),
]
