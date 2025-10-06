from rest_framework import viewsets
from .models import (
    Address, StatusChoice, Priority, Tag, ProjectType, 
    EmployeeType, Designation, Technology, Shift
)
from .serializers import (
    AddressSerializer, StatusChoiceSerializer, PrioritySerializer, TagSerializer,
    ProjectTypeSerializer, EmployeeTypeSerializer, DesignationSerializer,
    TechnologySerializer, ShiftSerializer
)

class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer

class StatusChoiceViewSet(viewsets.ModelViewSet):
    queryset = StatusChoice.objects.all()
    serializer_class = StatusChoiceSerializer

class PriorityViewSet(viewsets.ModelViewSet):
    queryset = Priority.objects.all()
    serializer_class = PrioritySerializer

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

class ProjectTypeViewSet(viewsets.ModelViewSet):
    queryset = ProjectType.objects.all()
    serializer_class = ProjectTypeSerializer

class EmployeeTypeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeType.objects.all()
    serializer_class = EmployeeTypeSerializer

class DesignationViewSet(viewsets.ModelViewSet):
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer

class TechnologyViewSet(viewsets.ModelViewSet):
    queryset = Technology.objects.all()
    serializer_class = TechnologySerializer

class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer

