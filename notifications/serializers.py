# notifications/serializers.py
from rest_framework import serializers
from .models import FCMToken, Notification


class FCMTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMToken
        fields = ['id', 'token', 'device_type', 'device_name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Get the user from the request
        user = self.context['request'].user
        token = validated_data.get('token')
        
        # Check if token already exists
        existing_token = FCMToken.objects.filter(token=token).first()
        
        if existing_token:
            # Update existing token
            existing_token.device_type = validated_data.get('device_type', existing_token.device_type)
            existing_token.device_name = validated_data.get('device_name', existing_token.device_name)
            existing_token.is_active = True
            existing_token.user = user
            existing_token.save()
            return existing_token
        
        # Create new token
        validated_data['user'] = user
        return super().create(validated_data)


class FCMTokenAdminSerializer(serializers.ModelSerializer):
    """Admin serializer with user details"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = FCMToken
        fields = [
            'id', 'token', 'device_type', 'device_name', 'is_active', 
            'created_at', 'updated_at', 'user_id', 'username', 
            'user_email', 'user_full_name'
        ]
        read_only_fields = fields
    
    def get_user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'body', 'notification_type', 'data', 'is_read', 'sent_at', 'read_at']
        read_only_fields = ['id', 'sent_at', 'read_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    """Admin serializer for notification logs with user details"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'body', 'notification_type', 'data', 
            'is_read', 'sent_at', 'read_at', 'user_id', 'username',
            'user_email', 'user_full_name'
        ]
        read_only_fields = fields
    
    def get_user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username


class SendNotificationSerializer(serializers.Serializer):
    """Serializer for sending notifications"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of user IDs to send notification to. If empty, sends to all users."
    )
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    notification_type = serializers.ChoiceField(
        choices=['info', 'warning', 'error', 'success'],
        default='info'
    )
    data = serializers.JSONField(required=False, allow_null=True)
