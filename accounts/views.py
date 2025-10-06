from django.utils import timezone
from django.db import models
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import User, Organization, Role, Permission, Module
from .serializers import (
    UserListSerializer, UserDetailSerializer, OrganizationSerializer, 
    RoleSerializer, PermissionSerializer, ModuleSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(deleted_at__isnull=True)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by organization if provided
        organization_id = self.request.query_params.get('organization')
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        # Filter by status if provided
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by employee type if provided
        employee_type = self.request.query_params.get('employee_type')
        if employee_type:
            queryset = queryset.filter(employee_type_id=employee_type)
        
        # Search by name, email, or employee_id
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(employee_id__icontains=search)
            )
        
        return queryset

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Return the authenticated user's data."""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        """Soft delete the user instead of hard delete"""
        # Prevent deletion of superusers
        if instance.is_superuser:
            raise serializers.ValidationError(
                {"detail": "Superuser accounts cannot be deleted."}
            )
        
        # Prevent users from deleting themselves
        if instance == self.request.user:
            raise serializers.ValidationError(
                {"detail": "You cannot delete your own account."}
            )
            
        instance.deleted_at = timezone.now()
        instance.is_active = False
        instance.save()

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

