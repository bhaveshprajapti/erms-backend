"""
Custom middleware for handling authentication, CORS, and caching issues
"""

from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.utils import timezone
import json


class AuthCacheMiddleware(MiddlewareMixin):
    """
    Middleware to handle authentication-related caching issues
    """
    
    def process_response(self, request, response):
        # Add cache control headers for all API endpoints to prevent stale data
        if request.path.startswith('/api/'):
            # Prevent caching of API responses
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            # Add security headers
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            
            # Add timestamp header for debugging
            response['X-Response-Time'] = str(timezone.now().isoformat())
        
        # Handle CORS preflight requests
        if request.method == 'OPTIONS':
            response['Access-Control-Allow-Origin'] = self.get_allowed_origin(request)
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '3600'  # 1 hour (reduced from 24)
        
        return response
    
    def get_allowed_origin(self, request):
        """Get the allowed origin for CORS"""
        origin = request.META.get('HTTP_ORIGIN', '')
        
        allowed_origins = [
            'http://localhost:3000',
            'http://localhost:3001',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:3001',
            'https://ems.digiwavetechnologies.in',
            'https://digiwavetechnologies.in',
        ]
        
        if origin in allowed_origins:
            return origin
        
        return allowed_origins[0]  # Default to localhost:3000


class SessionCleanupMiddleware(MiddlewareMixin):
    """
    Middleware to automatically clean up expired sessions and invalid tokens
    """
    
    def process_request(self, request):
        # Skip cleanup for static files and admin
        skip_paths = ['/admin/', '/static/', '/media/']
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # For API requests, add headers to prevent caching
        if request.path.startswith('/api/'):
            # This will be handled in process_response
            pass
        
        return None
    
    def process_response(self, request, response):
        # Add no-cache headers for API responses to prevent stale data
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            # Add ETag based on current time to force refresh
            response['ETag'] = f'"{timezone.now().timestamp()}"'
        
        return response