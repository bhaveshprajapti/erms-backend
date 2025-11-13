from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AddressViewSet, StatusChoiceViewSet, PriorityViewSet, TagViewSet,
    ProjectTypeViewSet, EmployeeTypeViewSet, DesignationViewSet,
    TechnologyViewSet, ShiftViewSet, HolidayViewSet, AppServiceViewSet
)

router = DefaultRouter()
router.register(r'addresses', AddressViewSet)
router.register(r'status-choices', StatusChoiceViewSet)
router.register(r'priorities', PriorityViewSet)
router.register(r'tags', TagViewSet)
router.register(r'project-types', ProjectTypeViewSet)
router.register(r'employee-types', EmployeeTypeViewSet)
router.register(r'designations', DesignationViewSet)
router.register(r'technologies', TechnologyViewSet)
router.register(r'shifts', ShiftViewSet)
router.register(r'holidays', HolidayViewSet)
router.register(r'app-services', AppServiceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
