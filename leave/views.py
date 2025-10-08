from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# Import the existing models and serializers from the original apps
from attendance.models import LeaveRequest
from attendance.serializers import LeaveRequestSerializer
from attendance.views import LeaveRequestViewSet as AttendanceLeaveRequestViewSet

from policies.models import LeaveBalance
from policies.serializers import LeaveBalanceSerializer
from policies.views import LeaveBalanceViewSet as PoliciesLeaveBalanceViewSet


class LeaveRequestViewSet(AttendanceLeaveRequestViewSet):
    """
    Proxy ViewSet that delegates to the existing LeaveRequestViewSet in attendance app.
    This maintains all existing functionality while providing the expected /api/v1/leave/ endpoint.
    """
    pass


class LeaveBalanceViewSet(PoliciesLeaveBalanceViewSet):
    """
    Proxy ViewSet that delegates to the existing LeaveBalanceViewSet in policies app.
    This maintains all existing functionality while providing the expected /api/v1/leave/ endpoint.
    """
    pass