from rest_framework import serializers
from .models import (
    Address, StatusChoice, Priority, Tag, ProjectType, 
    EmployeeType, Designation, Technology, Shift, Holiday, AppService
)

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'

class StatusChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusChoice
        fields = '__all__'

class PrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Priority
        fields = '__all__'

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class ProjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectType
        fields = '__all__'

class EmployeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeType
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for partial updates (when instance exists = update operation)
        if self.instance is not None:
            for field_name, field in self.fields.items():
                field.required = False
                if hasattr(field, 'allow_blank'):
                    field.allow_blank = True

class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for partial updates (when instance exists = update operation)
        if self.instance is not None:
            for field_name, field in self.fields.items():
                field.required = False
                if hasattr(field, 'allow_blank'):
                    field.allow_blank = True

class TechnologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Technology
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for partial updates
        if self.instance is not None:
            for field_name, field in self.fields.items():
                field.required = False
                field.allow_blank = True

class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for partial updates
        if self.instance is not None:
            for field_name, field in self.fields.items():
                field.required = False
                field.allow_blank = True

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = '__all__'

class AppServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppService
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for partial updates
        if self.instance is not None:
            for field_name, field in self.fields.items():
                field.required = False
                field.allow_blank = True
