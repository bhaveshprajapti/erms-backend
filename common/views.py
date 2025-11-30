from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Address, StatusChoice, Priority, Tag, ProjectType, 
    EmployeeType, Designation, Technology, Shift, Holiday, AppService
)
from .serializers import (
    AddressSerializer, StatusChoiceSerializer, PrioritySerializer, TagSerializer,
    ProjectTypeSerializer, EmployeeTypeSerializer, DesignationSerializer,
    TechnologySerializer, ShiftSerializer, HolidaySerializer, AppServiceSerializer
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
    
    def get_queryset(self):
        """
        Filter shifts based on query parameters.
        By default, return only active shifts for non-admin operations.
        Use ?all=true to get all shifts (for admin management).
        """
        queryset = Shift.objects.all()
        
        # Check if 'all' parameter is provided (for admin management)
        show_all = self.request.query_params.get('all', 'false').lower() == 'true'
        
        if not show_all:
            # For general use, only return active shifts
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('name')

class HolidayViewSet(viewsets.ModelViewSet):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    
    def get_queryset(self):
        """Filter holidays by year if provided"""
        queryset = Holiday.objects.all().order_by('date')
        year = self.request.query_params.get('year')
        if year:
            try:
                year = int(year)
                queryset = queryset.filter(date__year=year)
            except (ValueError, TypeError):
                pass
        return queryset
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get holiday statistics"""
        from datetime import datetime
        from rest_framework.response import Response
        
        # Get year and month from query params
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if year:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = datetime.now().year
        else:
            year = datetime.now().year
            
        if month:
            try:
                month = int(month)
            except (ValueError, TypeError):
                month = datetime.now().month
        else:
            month = datetime.now().month
        
        # Calculate stats
        total_holidays_year = Holiday.get_total_holidays_in_year(year)
        working_days_month = Holiday.get_working_days_in_month(year, month)
        
        # Get total holidays in current month
        holidays_in_month = Holiday.objects.filter(
            date__year=year, 
            date__month=month
        ).count()
        
        # Get total days in month
        import calendar
        _, total_days_month = calendar.monthrange(year, month)
        
        # Count Sundays in month
        from datetime import date
        sundays_in_month = 0
        for day in range(1, total_days_month + 1):
            if date(year, month, day).weekday() == 6:  # Sunday is 6
                sundays_in_month += 1
        
        return Response({
            'year': year,
            'month': month,
            'total_holidays_in_year': total_holidays_year,
            'working_days_in_month': working_days_month,
            'holidays_in_month': holidays_in_month,
            'total_days_in_month': total_days_month,
            'sundays_in_month': sundays_in_month,
            'non_working_days_in_month': holidays_in_month + sundays_in_month
        })

class AppServiceViewSet(viewsets.ModelViewSet):
    queryset = AppService.objects.all()
    serializer_class = AppServiceSerializer

