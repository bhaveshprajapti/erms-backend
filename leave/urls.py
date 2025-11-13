from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'types', views.LeaveTypeViewSet)
router.register(r'policies', views.LeaveTypePolicyViewSet)
router.register(r'balances', views.LeaveBalanceViewSet)
router.register(r'applications', views.LeaveApplicationViewSet)
router.register(r'flexible-timing-types', views.FlexibleTimingTypeViewSet, basename='flexibletimingtype')
router.register(r'flexible-timing-requests', views.FlexibleTimingRequestViewSet, basename='flexibletimingrequest')
router.register(r'flexible-timing-balances', views.FlexibleTimingBalanceViewSet, basename='flexibletimingbalance')

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('api/v1/calendar/', views.leave_calendar, name='leave-calendar'),
    path('api/v1/statistics/', views.leave_statistics, name='leave-statistics'),
    path('api/v1/test/', views.test_view, name='leave-test'),
]
