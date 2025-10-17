from django.utils import timezone
from django.db import models
from django.contrib.auth import authenticate
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Organization, Role, Permission, Module, ProfileUpdateRequest
from .serializers import (
    UserListSerializer, UserDetailSerializer, OrganizationSerializer, 
    RoleSerializer, PermissionSerializer, ModuleSerializer,
    ProfileUpdateRequestSerializer, ProfileUpdateRequestCreateSerializer
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
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to include plain_password for admin users."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        # Include plain_password only for admin users
        if request.user.is_staff or request.user.is_superuser:
            data['plain_password'] = instance.plain_password
        
        return Response(data)

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


class ProfileUpdateRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProfileUpdateRequestCreateSerializer
        return ProfileUpdateRequestSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # If user is admin/staff, show all requests
        if user.is_superuser or user.is_staff:
            return ProfileUpdateRequest.objects.all()
        
        # Regular employees can only see their own requests
        return ProfileUpdateRequest.objects.filter(user=user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve a profile update request (admin only)"""
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({'error': 'Permission denied'}, status=403)
        
        try:
            update_request = self.get_object()
            
            if update_request.status != 'pending':
                return Response({'error': 'Request is not pending'}, status=400)
            
            # Apply the update to the user profile
            user = update_request.user
            field_name = update_request.field_name
            new_value = update_request.new_value
            
            # Handle multiple fields update (consolidated request)
            if field_name == 'multiple_fields':
                # Parse the new_value to extract individual field changes
                # Format: "field name: old → new, field2: old → new"
                import re
                changes = new_value.split(', ')
                
                for change in changes:
                    # Extract field name and new value - allow spaces in field names
                    match = re.match(r'([^:]+):\s*"([^"]*?)"\s*→\s*"([^"]*?)"', change)
                    if match:
                        field = match.group(1).strip()
                        new_val = match.group(3)
                        
                        # Convert field name with spaces to underscore format
                        field = field.replace(' ', '_')
                        
                        # Apply the change
                        if field in ['current_address', 'permanent_address']:
                            from common.models import Address
                            # Update existing address or create new one
                            existing_address = getattr(user, field, None)
                            if existing_address:
                                existing_address.line1 = new_val
                                existing_address.save()
                            else:
                                address = Address.objects.create(
                                    line1=new_val,
                                    city='N/A',
                                    pincode='000000',
                                    type='current' if field == 'current_address' else 'permanent'
                                )
                                setattr(user, field, address)
                        else:
                            # Handle regular fields
                            setattr(user, field, new_val)
                
                user.save()
            else:
                # Handle single field update (backward compatibility)
                if field_name in ['current_address', 'permanent_address']:
                    # Handle address fields - create or update Address object
                    from common.models import Address
                    existing_address = getattr(user, field_name, None)
                    if existing_address:
                        existing_address.line1 = new_value
                        existing_address.save()
                    else:
                        address = Address.objects.create(
                            line1=new_value,
                            city='N/A',  # Default value
                            pincode='000000',  # Default value
                            type='current' if field_name == 'current_address' else 'permanent'
                        )
                        setattr(user, field_name, address)
                else:
                    # Handle regular fields
                    setattr(user, field_name, new_value)
                
                user.save()
            
            # Update request status
            update_request.status = 'approved'
            update_request.approved_by = request.user
            update_request.processed_at = timezone.now()
            update_request.admin_comment = request.data.get('admin_comment', '')
            update_request.save()
            
            return Response({
                'message': 'Profile update approved and applied',
                'request_id': update_request.id
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject a profile update request (admin only)"""
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({'error': 'Permission denied'}, status=403)
        
        try:
            update_request = self.get_object()
            
            if update_request.status != 'pending':
                return Response({'error': 'Request is not pending'}, status=400)
            
            # Update request status
            update_request.status = 'rejected'
            update_request.approved_by = request.user
            update_request.processed_at = timezone.now()
            update_request.admin_comment = request.data.get('admin_comment', 'Request rejected')
            update_request.save()
            
            return Response({
                'message': 'Profile update rejected',
                'request_id': update_request.id
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pending(self, request):
        """Get all pending requests (admin only)"""
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({'error': 'Permission denied'}, status=403)
        
        pending_requests = ProfileUpdateRequest.objects.filter(status='pending')
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_requests(self, request):
        """Get current user's profile update requests"""
        user_requests = ProfileUpdateRequest.objects.filter(user=request.user)
        serializer = self.get_serializer(user_requests, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def custom_logout(request):
    """
    Custom logout view that logs the logout event for session management.
    """
    user = request.user
    
    # Log the logout event (with backward compatibility)
    try:
        from attendance.models import SessionLog
        SessionLog.log_event(
            user=user,
            event_type='logout',
            request=request,
            notes='User initiated logout'
        )
    except Exception as e:
        # SessionLog table might not exist yet - continue without session logging
        print(f"Session logging not available: {e}")
    
    return Response({
        'message': 'Logout successful.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_login(request):
    """
    Custom login view that provides specific error messages
    for different authentication failure scenarios.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    # Check if username and password are provided
    if not username or not password:
        return Response({
            'error': 'Username and password are required.',
            'details': 'Please provide both username and password to login.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user exists
    try:
        user = User.objects.get(username=username, deleted_at__isnull=True)
    except User.DoesNotExist:
        return Response({
            'error': 'Invalid username or password.',
            'details': 'The username or password you entered is incorrect. Please check your credentials and try again.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user is active
    if not user.is_active:
        return Response({
            'error': 'Account is inactive.',
            'details': 'Your account has been deactivated. Please contact your administrator for assistance.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Authenticate user
    authenticated_user = authenticate(username=username, password=password)
    
    if authenticated_user is None:
        return Response({
            'error': 'Invalid username or password.',
            'details': 'The username or password you entered is incorrect. Please check your credentials and try again.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user has been soft deleted
    if authenticated_user.deleted_at is not None:
        return Response({
            'error': 'Account not found.',
            'details': 'Your account is no longer available. Please contact your administrator for assistance.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check organization status if applicable
    if authenticated_user.organization and not authenticated_user.organization.is_active:
        return Response({
            'error': 'Organization is inactive.',
            'details': 'Your organization account has been suspended. Please contact your administrator.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Create JWT tokens
    refresh = RefreshToken.for_user(authenticated_user)
    access_token = refresh.access_token
    
    # CRITICAL: Log the login event for session management and security (with backward compatibility)
    try:
        from attendance.models import SessionLog
        SessionLog.log_event(
            user=authenticated_user,
            event_type='login',
            request=request,
            notes=f'Successful login from {request.META.get("HTTP_USER_AGENT", "Unknown")[:100]}'
        )
    except Exception as e:
        # SessionLog table might not exist yet - continue without session logging
        print(f"Session logging not available: {e}")
    
    # Prepare user data
    user_data = {
        'id': authenticated_user.id,
        'username': authenticated_user.username,
        'email': authenticated_user.email,
        'first_name': authenticated_user.first_name,
        'last_name': authenticated_user.last_name,
        'is_staff': authenticated_user.is_staff,
        'is_superuser': authenticated_user.is_superuser,
        'phone': authenticated_user.phone,
        'employee_type': authenticated_user.employee_type.name if authenticated_user.employee_type else None,
        'organization': {
            'id': authenticated_user.organization.id if authenticated_user.organization else None,
            'name': authenticated_user.organization.name if authenticated_user.organization else None,
        } if authenticated_user.organization else None,
        'role': {
            'id': authenticated_user.role.id if authenticated_user.role else None,
            'name': authenticated_user.role.display_name if authenticated_user.role else None,
        } if authenticated_user.role else None,
        'joining_date': authenticated_user.joining_date,
        'profile_picture': authenticated_user.profile_picture.url if authenticated_user.profile_picture else None,
    }
    
    return Response({
        'access': str(access_token),
        'refresh': str(refresh),
        'message': 'Login successful.',
        'user': user_data
    }, status=status.HTTP_200_OK)

