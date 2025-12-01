from django.utils import timezone
from django.db import models
from django.contrib.auth import authenticate
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Organization, Role, Permission, Module, ProfileUpdateRequest, EmployeePayment
from .serializers import (
    UserListSerializer, UserDetailSerializer, OrganizationSerializer, 
    RoleSerializer, PermissionSerializer, ModuleSerializer,
    ProfileUpdateRequestSerializer, ProfileUpdateRequestCreateSerializer,
    EmployeePaymentSerializer
)
from datetime import date
import random

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(deleted_at__isnull=True).order_by('-created_at')
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

    @action(detail=False, methods=['get'])
    def today_birthday(self, request):
        """Return all employees whose birthday is today with their photos and messages"""
        # Use IST timezone for birthday check
        from common.timezone_utils import get_current_ist_date
        today = get_current_ist_date()

        birthday_users = User.objects.filter(
            birth_date__isnull=False,
            birth_date__month=today.month,
            birth_date__day=today.day,
            is_active=True,
            deleted_at__isnull=True
        )

        BIRTHDAY_MESSAGES = [
            "🎉 Wishing you a fantastic birthday!",
            "🎂 Have an amazing birthday! Enjoy your day!",
            "✨ May your birthday bring happiness and joy!",
            "🥳 Happy Birthday! Stay blessed!",
            "🎉 Cheers to your special day!",
            "🌟 May your year be filled with success & smiles!",
            "🎂 Warm wishes on your birthday!",
            "🥳 Have a wonderful birthday celebration!",
            "🎊 Another year of amazing you! Happy Birthday!",
            "🌈 May all your dreams come true! Happy Birthday!",
            "🎁 Wishing you a day filled with love and laughter!",
            "🎈 Here's to a year of great achievements! Happy Birthday!"
        ]

        birthday_data = []
        for user in birthday_users:
            # Get profile picture URL
            profile_picture_url = None
            if user.profile_picture:
                profile_picture_url = request.build_absolute_uri(user.profile_picture.url)
            
            birthday_data.append({
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": f"{user.first_name} {user.last_name}",
                "message": random.choice(BIRTHDAY_MESSAGES),
                "profile_picture": profile_picture_url,
                "employee_id": user.employee_id,
                "gender": user.gender  # Include gender for color theming
            })

        return Response({
            "count": birthday_users.count(),
            "birthdays": birthday_data
        })
    
    @action(detail=False, methods=['get'])
    def my_birthday_message(self, request):
        """Return birthday message for the current user if today is their birthday"""
        # Use IST timezone for birthday check
        from common.timezone_utils import get_current_ist_date
        today = get_current_ist_date()
        user = request.user
        
        # Check if today is the user's birthday (using IST date)
        if user.birth_date and user.birth_date.month == today.month and user.birth_date.day == today.day:
            BIRTHDAY_MESSAGES = [
                "🎉 Wishing you a fantastic birthday!",
                "🎂 Have an amazing birthday! Enjoy your day!",
                "✨ May your birthday bring happiness and joy!",
                "🥳 Happy Birthday! Stay blessed!",
                "🎉 Cheers to your special day!",
                "🌟 May your year be filled with success & smiles!",
                "🎂 Warm wishes on your birthday!",
                "🥳 Have a wonderful birthday celebration!",
                "🎊 Another year of amazing you! Happy Birthday!",
                "🌈 May all your dreams come true! Happy Birthday!",
                "🎁 Wishing you a day filled with love and laughter!",
                "🎈 Here's to a year of great achievements! Happy Birthday!"
            ]
            
            message = f"{random.choice(BIRTHDAY_MESSAGES)} {user.first_name}! 🎈"
            
            return Response({
                "is_birthday": True,
                "message": message,
                "first_name": user.first_name,
                "last_name": user.last_name
            })
        
        return Response({
            "is_birthday": False,
            "message": None
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_profile_picture(self, request, pk=None):
        """
        Upload or remove profile picture for a user.
        - Users can upload/remove their own profile picture (no approval needed)
        - Admins can upload/remove profile pictures for any user
        """
        user = self.get_object()
        
        # Check permissions: user can update own profile, or admin can update any
        if user.id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response({
                'error': 'Permission denied',
                'detail': 'You can only update your own profile picture'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if this is a removal request (empty file or no file)
        if 'profile_picture' not in request.FILES or not request.FILES['profile_picture']:
            # Remove profile picture
            if user.profile_picture:
                try:
                    user.profile_picture.delete(save=False)
                except Exception as e:
                    print(f"Error deleting profile picture: {e}")
                
                user.profile_picture = None
                user.save()
                
                return Response({
                    'message': 'Profile picture removed successfully',
                    'profile_picture_url': None
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'No profile picture to remove',
                    'detail': 'User does not have a profile picture'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        profile_picture = request.FILES['profile_picture']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if profile_picture.content_type not in allowed_types:
            return Response({
                'error': 'Invalid file type',
                'detail': 'Please upload a valid image file (JPEG, PNG, GIF, or WebP)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        if profile_picture.size > max_size:
            return Response({
                'error': 'File too large',
                'detail': 'Profile picture must be less than 5MB'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete old profile picture if exists
        if user.profile_picture:
            try:
                user.profile_picture.delete(save=False)
            except Exception as e:
                # Log error but continue with upload
                print(f"Error deleting old profile picture: {e}")
        
        # Save new profile picture
        user.profile_picture = profile_picture
        user.save()
        
        return Response({
            'message': 'Profile picture updated successfully',
            'profile_picture_url': request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None
        }, status=status.HTTP_200_OK)

    
class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all().order_by('-created_at')
    serializer_class = OrganizationSerializer

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().order_by('-created_at')
    serializer_class = RoleSerializer

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all().order_by('-created_at')
    serializer_class = PermissionSerializer

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all().order_by('-created_at')
    serializer_class = ModuleSerializer


class EmployeePaymentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeePaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = EmployeePayment.objects.all().order_by('-date', '-created_at')
        
        # Filter by employee if provided
        employee_id = self.request.query_params.get('employee')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        # Filter by payment type if provided
        payment_type = self.request.query_params.get('payment_type')
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)
        
        return queryset
    
    def perform_create(self, serializer):
        # Ensure the employee exists
        employee_id = self.request.data.get('employee_id')
        if not employee_id:
            raise serializers.ValidationError({'employee_id': 'Employee ID is required'})
        
        try:
            employee = User.objects.get(id=employee_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({'employee_id': 'Employee not found'})
        
        serializer.save(employee=employee)


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
            return ProfileUpdateRequest.objects.all().order_by('-requested_at')
        
        # Regular employees can only see their own requests
        return ProfileUpdateRequest.objects.filter(user=user).order_by('-requested_at')
    
    def perform_create(self, serializer):
        """Create profile update request and notify admins"""
        profile_request = serializer.save(user=self.request.user)
        
        # Send notification to admins
        try:
            from notifications.services import NotificationService
            NotificationService.notify_profile_update_submitted(profile_request)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send profile update notification: {e}")
    
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
            
            # Send notification to employee
            try:
                from notifications.services import NotificationService
                NotificationService.notify_profile_update_approved(update_request)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to send profile approval notification: {e}")
            
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
            admin_comment = request.data.get('admin_comment', 'Request rejected')
            update_request.admin_comment = admin_comment
            update_request.save()
            
            # Send notification to employee
            try:
                from notifications.services import NotificationService
                NotificationService.notify_profile_update_rejected(update_request, admin_comment)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to send profile rejection notification: {e}")
            
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
        
        pending_requests = ProfileUpdateRequest.objects.filter(status='pending').order_by('-requested_at')
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_requests(self, request):
        """Get current user's profile update requests"""
        user_requests = ProfileUpdateRequest.objects.filter(user=request.user).order_by('-requested_at')
        serializer = self.get_serializer(user_requests, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def custom_logout(request):
    """
    Custom logout view that blacklists tokens and logs the logout event.
    """
    user = request.user
    
    try:
        # Blacklist the refresh token if provided
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        # Log the logout event (with backward compatibility)
        try:
            from attendance.models import SessionLog
            SessionLog.log_event(
                user=user,
                event_type='logout',
                request=request,
                notes='User initiated logout - token blacklisted'
            )
        except Exception as e:
            # SessionLog table might not exist yet - continue without session logging
            print(f"Session logging not available: {e}")
        
        return Response({
            'message': 'Logout successful. Please clear your browser cache if you experience any issues.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Even if blacklisting fails, allow logout to proceed
        print(f"Token blacklisting failed: {e}")
        
        return Response({
            'message': 'Logout completed.'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    Custom token refresh endpoint with enhanced error handling
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
    
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response({
            'error': 'Refresh token is required.',
            'details': 'Please provide a valid refresh token.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Validate and refresh the token
        refresh = RefreshToken(refresh_token)
        
        # Get the user from the token
        user_id = refresh.payload.get('user_id')
        if not user_id:
            return Response({
                'error': 'Invalid token.',
                'details': 'Token does not contain valid user information.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Validate user exists and is active
        try:
            user_obj = User.objects.get(
                id=user_id, 
                deleted_at__isnull=True, 
                is_active=True
            )
        except User.DoesNotExist:
            return Response({
                'error': 'User not found.',
                'details': 'The user associated with this token no longer exists or is inactive.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user's organization is still active
        if user_obj.organization and not user_obj.organization.is_active:
            return Response({
                'error': 'Organization is inactive.',
                'details': 'Your organization account has been suspended.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate new access token
        access_token = refresh.access_token
        
        # Always rotate refresh token for enhanced security
        new_refresh = RefreshToken.for_user(user_obj)
        
        # Update user's last login time
        user_obj.last_login = timezone.now()
        user_obj.save(update_fields=['last_login'])
        
        return Response({
            'access': str(access_token),
            'refresh': str(new_refresh),
            'expires_in': 28800,  # 8 hours in seconds
            'token_type': 'Bearer'
        }, status=status.HTTP_200_OK)
        
    except TokenError as e:
        return Response({
            'error': 'Invalid or expired refresh token.',
            'details': 'Your session has expired. Please login again.'
        }, status=status.HTTP_401_UNAUTHORIZED)
    except User.DoesNotExist:
        return Response({
            'error': 'User not found.',
            'details': 'The user associated with this token no longer exists.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Token refresh failed.',
            'details': 'An error occurred while refreshing your session. Please login again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        'profile_picture': request.build_absolute_uri(authenticated_user.profile_picture.url) if authenticated_user.profile_picture else None,
    }
    
    # Update user's last login time
    authenticated_user.last_login = timezone.now()
    authenticated_user.save(update_fields=['last_login'])
    
    return Response({
        'access': str(access_token),
        'refresh': str(refresh),
        'message': 'Login successful.',
        'user': user_data,
        'expires_in': 28800,  # 8 hours in seconds
        'token_type': 'Bearer'
    }, status=status.HTTP_200_OK)

