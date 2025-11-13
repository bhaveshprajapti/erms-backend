from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AttendanceViewSet, LeaveRequestViewSet, 
    TimeAdjustmentViewSet, ApprovalViewSet, SessionLogViewSet
)

router = DefaultRouter()
router.register(r'attendances', AttendanceViewSet, basename='attendance')
router.register(r'leave-requests', LeaveRequestViewSet)
router.register(r'time-adjustments', TimeAdjustmentViewSet)
router.register(r'approvals', ApprovalViewSet)
router.register(r'session-logs', SessionLogViewSet, basename='session-log')

urlpatterns = [
    path('', include(router.urls)),
]
