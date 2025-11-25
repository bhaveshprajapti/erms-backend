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
        # Make all fields optional for partial updates (when instance exists = update operation)
        if self.instance is not None:
            for field_name, field in self.fields.items():
                field.required = False
                if hasattr(field, 'allow_blank'):
                    field.allow_blank = True

class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for partial updates (when instance exists = update operation)
        if self.instance is not None:
            for field_name, field in self.fields.items():
                field.required = False
                if hasattr(field, 'allow_blank'):
                    field.allow_blank = True
    
    def validate(self, data):
        """
        Validate that the shift time combination is unique
        """
        # Only validate time uniqueness if time fields are being updated
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        # For partial updates, only validate if at least one time field is being changed
        if self.instance and 'start_time' not in data and 'end_time' not in data:
            # Neither time field is being updated, skip time validation
            return data
        
        # If we're updating, get the current values if not provided
        if self.instance:
            start_time = start_time if start_time is not None else self.instance.start_time
            end_time = end_time if end_time is not None else self.instance.end_time
        
        # Check if both times are provided
        if start_time and end_time:
            # Build the query to check for existing shifts with same time
            query = Shift.objects.filter(start_time=start_time, end_time=end_time)
            
            # If updating, exclude the current instance
            if self.instance:
                query = query.exclude(id=self.instance.id)
            
            if query.exists():
                raise serializers.ValidationError({
                    'start_time': 'A shift with this time combination already exists.',
                    'end_time': 'A shift with this time combination already exists.'
                })
        
        return data

class HolidaySerializer(serializers.ModelSerializer):
    day_name = serializers.ReadOnlyField()
    
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
