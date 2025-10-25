from rest_framework import serializers
from .models import Project, Task, TimeLog, TaskComment
from accounts.serializers import UserListSerializer
from common.serializers import TechnologySerializer, AppServiceSerializer
from clients.serializers import QuotationListSerializer, ClientListSerializer

class ProjectSerializer(serializers.ModelSerializer):
    technologies_detail = TechnologySerializer(source='technologies', many=True, read_only=True)
    app_mode_detail = AppServiceSerializer(source='app_mode', many=True, read_only=True)
    team_members_detail = UserListSerializer(source='team_members', many=True, read_only=True)
    quotation_detail = QuotationListSerializer(source='quotation', read_only=True)
    client_detail = ClientListSerializer(source='client', read_only=True)
    total_expenses = serializers.ReadOnlyField()
    profit_loss = serializers.ReadOnlyField()
    
    class Meta:
        model = Project
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class TimeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeLog
        fields = '__all__'

class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = '__all__'
