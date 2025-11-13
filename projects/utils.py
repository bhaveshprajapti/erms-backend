# indrajit start
from rest_framework.response import Response
from rest_framework import status

class StandredResponse:
    def get_success_response(self,data,message,http_status=status.HTTP_200_OK):
        return Response({
            'status':http_status,
            'message':message,
            'data':data
        }, status=http_status)
    
    def get_error_response(self, message, http_status=status.HTTP_400_BAD_REQUEST):
        return Response({
            'status': http_status,
            'message': message,
            'data': None
        }, status=http_status)
    
# indrajit start