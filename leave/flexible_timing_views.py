from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal

from .models import (
    FlexibleTimingType, FlexibleTimingRequest, FlexibleTimingBalance, 
    FlexibleTimingPolicy
)
from .serializers import (
    FlexibleTimingTypeSerializer, FlexibleTimingRequestSerializer,
    FlexibleTimingBalanceSerializer, FlexibleTimingPolicySerializer,
    FlexibleTimingRequestCreateSerializer
)


class FlexibleTimingTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing flexible timing types"""
    queryset = FlexibleTimingType.objects.all()
    serializer_class = FlexibleTimingTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return all timing types (active and inactive) for admin management"""
        return FlexibleTimingType.objects.all().order_by('name')


class FlexibleTimingRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for managing flexible timing requests"""
    serializer_class = FlexibleTimingRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter requests based on user role"""
        user = self.request.user
        if user.is_staff:
            # Admin can see all requests
            return FlexibleTimingRequest.objects.all().order_by('-applied_at')
        else:
            # Regular users can only see their own requests
            return FlexibleTimingRequest.objects.filter(user=user).order_by('-applied_at')

    def get_serializer_class(self):
        """Use different serializer for create/update"""
        if self.action in ['create', 'update', 'partial_update']:
            return FlexibleTimingRequestCreateSerializer
        return FlexibleTimingRequestSerializer

    def perform_create(self, serializer):
        """Set the user when creating a request"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Get current user's flexible timing requests"""
        requests = FlexibleTimingRequest.objects.filter(
            user=request.user
        ).order_by('-applied_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            requests = requests.filter(status=status_filter)
        
        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            requests = requests.filter(requested_date__gte=start_date)
        if end_date:
            requests = requests.filter(requested_date__lte=end_date)
        
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_balance(self, request):
        """Get current user's flexible timing balance for current month"""
        today = date.today()
        year = request.query_params.get('year', today.year)
        month = request.query_params.get('month', today.month)
        
        balances = FlexibleTimingBalance.objects.filter(
            user=request.user,
            year=year,
            month=month
        )
        
        # Create balances if they don't exist
        timing_types = FlexibleTimingType.objects.filter(is_active=True)
        for timing_type in timing_types:
            balance, created = FlexibleTimingBalance.objects.get_or_create(
                user=request.user,
                timing_type=timing_type,
                year=year,
                month=month,
                defaults={'total_allowed': timing_type.max_per_month}
            )
            if created:
                balance.update_usage()
        
        # Refresh balances
        balances = FlexibleTimingBalance.objects.filter(
            user=request.user,
            year=year,
            month=month
        )
        
        serializer = FlexibleTimingBalanceSerializer(balances, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a flexible timing request"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        timing_request = self.get_object()
        
        if timing_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be approved'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if monthly limit would be exceeded
        if not timing_request.validate_monthly_limit():
            return Response(
                {'error': 'Monthly limit would be exceeded'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timing_request.status = 'approved'
        timing_request.approved_by = request.user
        timing_request.approved_at = timezone.now()
        timing_request.admin_comments = request.data.get('comments', '')
        timing_request.save()
        
        # Update balance
        balance, created = FlexibleTimingBalance.objects.get_or_create(
            user=timing_request.user,
            timing_type=timing_request.timing_type,
            year=timing_request.requested_date.year,
            month=timing_request.requested_date.month,
            defaults={'total_allowed': timing_request.timing_type.max_per_month}
        )
        balance.update_usage()
        
        serializer = self.get_serializer(timing_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a flexible timing request"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        timing_request = self.get_object()
        
        if timing_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be rejected'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_reason = request.data.get('reason', '')
        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timing_request.status = 'rejected'
        timing_request.approved_by = request.user
        timing_request.rejection_reason = rejection_reason
        timing_request.admin_comments = request.data.get('comments', '')
        timing_request.save()
        
        # Update balance
        balance, created = FlexibleTimingBalance.objects.get_or_create(
            user=timing_request.user,
            timing_type=timing_request.timing_type,
            year=timing_request.requested_date.year,
            month=timing_request.requested_date.month,
            defaults={'total_allowed': timing_request.timing_type.max_per_month}
        )
        balance.update_usage()
        
        serializer = self.get_serializer(timing_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a flexible timing request"""
        timing_request = self.get_object()
        
        # Check permissions
        if timing_request.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not timing_request.can_be_cancelled():
            return Response(
                {'error': 'Request cannot be cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timing_request.status = 'cancelled'
        timing_request.save()
        
        # Update balance
        balance, created = FlexibleTimingBalance.objects.get_or_create(
            user=timing_request.user,
            timing_type=timing_request.timing_type,
            year=timing_request.requested_date.year,
            month=timing_request.requested_date.month,
            defaults={'total_allowed': timing_request.timing_type.max_per_month}
        )
        balance.update_usage()
        
        serializer = self.get_serializer(timing_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_used(self, request, pk=None):
        """Mark a flexible timing request as used"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        timing_request = self.get_object()
        
        if not timing_request.can_be_used():
            return Response(
                {'error': 'Request cannot be marked as used'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        actual_duration = request.data.get('actual_duration_minutes')
        timing_request.mark_as_used(actual_duration)
        
        # Update balance
        balance, created = FlexibleTimingBalance.objects.get_or_create(
            user=timing_request.user,
            timing_type=timing_request.timing_type,
            year=timing_request.requested_date.year,
            month=timing_request.requested_date.month,
            defaults={'total_allowed': timing_request.timing_type.max_per_month}
        )
        balance.update_usage()
        
        serializer = self.get_serializer(timing_request)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending_requests(self, request):
        """Get all pending requests for admin"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        requests = FlexibleTimingRequest.objects.filter(
            status='pending'
        ).order_by('requested_date', 'applied_at')
        
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today_approved(self, request):
        """Get today's approved flexible timing requests"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        today = date.today()
        requests = FlexibleTimingRequest.objects.filter(
            requested_date=today,
            status='approved'
        ).order_by('user__first_name', 'user__last_name')
        
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)


class FlexibleTimingBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing flexible timing balances"""
    serializer_class = FlexibleTimingBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter balances based on user role"""
        user = self.request.user
        if user.is_staff:
            return FlexibleTimingBalance.objects.all().order_by('user__username', '-year', '-month')
        else:
            return FlexibleTimingBalance.objects.filter(user=user).order_by('-year', '-month')

    @action(detail=False, methods=['post'])
    def refresh_balances(self, request):
        """Refresh all balances for current month"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        today = date.today()
        balances = FlexibleTimingBalance.objects.filter(
            year=today.year,
            month=today.month
        )
        
        for balance in balances:
            balance.update_usage()
        
        return Response({'message': 'Balances refreshed successfully'})


class FlexibleTimingPolicyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing flexible timing policies"""
    queryset = FlexibleTimingPolicy.objects.filter(is_active=True)
    serializer_class = FlexibleTimingPolicySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Only staff can manage policies"""
        if self.request.user.is_staff:
            return FlexibleTimingPolicy.objects.all().order_by('name')
        else:
            # Regular users can only view applicable policies
            return FlexibleTimingPolicy.objects.filter(
                is_active=True
            ).order_by('name')

    def create(self, request, *args, **kwargs):
        """Only staff can create policies"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Only staff can update policies"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Only staff can delete policies"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
