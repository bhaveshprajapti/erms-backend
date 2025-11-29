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
    path('', include(router.urls)),
    path('calendar/', views.leave_calendar, name='leave-calendar'),
    path('statistics/', views.leave_statistics, name='leave-statistics'),
    path('test/', views.test_view, name='leave-test'),
]
