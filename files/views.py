from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from .models import Folder, File, FileShare
from .serializers import (
    FolderSerializer, FolderListSerializer, FolderDetailSerializer,
    FileSerializer, FileListSerializer, FileDetailSerializer,
    FileShareSerializer
)
import os
import mimetypes

class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FolderListSerializer
        elif self.action == 'retrieve':
            return FolderDetailSerializer
        return FolderSerializer
    
    def get_queryset(self):
        queryset = Folder.objects.all()
        
        # Filter by parent folder
        parent_id = self.request.query_params.get('parent', None)
        if parent_id is not None:
            if parent_id == 'root':
                queryset = queryset.filter(parent=None)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        # Filter by project
        project_id = self.request.query_params.get('project', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter project folders only
        project_folders_only = self.request.query_params.get('project_folders_only', None)
        if project_folders_only == 'true':
            queryset = queryset.filter(is_project_folder=True)
        
        # Filter employee folders only
        employee_folders_only = self.request.query_params.get('employee_folders_only', None)
        if employee_folders_only == 'true':
            queryset = queryset.filter(is_employee_folder=True)
        
        # Filter by specific employee
        employee_id = self.request.query_params.get('employee', None)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def contents(self, request, pk=None):
        """Get folder contents (subfolders and files)"""
        folder = self.get_object()
        
        # Get subfolders
        subfolders = folder.subfolders.all()
        subfolder_serializer = FolderListSerializer(subfolders, many=True)
        
        # Get files
        files = folder.files.all()
        file_serializer = FileListSerializer(files, many=True)
        
        return Response({
            'folder': FolderDetailSerializer(folder).data,
            'subfolders': subfolder_serializer.data,
            'files': file_serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def create_project_folder(self, request):
        """Create a folder for a project"""
        project_id = request.data.get('project_id')
        project_name = request.data.get('project_name')
        
        if not project_id or not project_name:
            return Response(
                {'error': 'project_id and project_name are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if project folder already exists
        existing_folder = Folder.objects.filter(
            project_id=project_id,
            is_project_folder=True
        ).first()
        
        if existing_folder:
            return Response(
                FolderDetailSerializer(existing_folder).data,
                status=status.HTTP_200_OK
            )
        
        # Create project folder
        folder = Folder.objects.create(
            name=f"Project_{project_name}",
            project_id=project_id,
            created_by=request.user,
            is_project_folder=True,
            is_system_folder=True,
            color='blue',
            description=f"Project folder for {project_name}"
        )
        
        return Response(
            FolderDetailSerializer(folder).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def create_client_folder(self, request):
        """Create a folder for a client"""
        client_id = request.data.get('client_id')
        client_name = request.data.get('client_name')
        
        if not client_id or not client_name:
            return Response(
                {'error': 'client_id and client_name are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if client folder already exists
        existing_folder = Folder.objects.filter(
            client_id=client_id,
            is_client_folder=True
        ).first()
        
        if existing_folder:
            return Response(
                FolderDetailSerializer(existing_folder).data,
                status=status.HTTP_200_OK
            )
        
        # Create client folder
        folder = Folder.objects.create(
            name=f"Client_{client_name}",
            client_id=client_id,
            created_by=request.user,
            is_client_folder=True,
            is_system_folder=True,
            color='green',
            description=f"Client folder for {client_name}"
        )
        
        return Response(
            FolderDetailSerializer(folder).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def create_employee_folder(self, request):
        """Create a folder for an employee"""
        employee_id = request.data.get('employee_id')
        employee_name = request.data.get('employee_name')
        
        if not employee_id or not employee_name:
            return Response(
                {'error': 'employee_id and employee_name are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if employee folder already exists
        existing_folder = Folder.objects.filter(
            employee_id=employee_id,
            is_employee_folder=True
        ).first()
        
        if existing_folder:
            return Response(
                FolderDetailSerializer(existing_folder).data,
                status=status.HTTP_200_OK
            )
        
        # Create employee folder
        folder = Folder.objects.create(
            name=f"Employee_{employee_name}",
            employee_id=employee_id,
            created_by=request.user,
            is_employee_folder=True,
            is_system_folder=True,
            color='yellow',
            description=f"Employee folder for {employee_name}"
        )
        
        return Response(
            FolderDetailSerializer(folder).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def share_link(self, request, pk=None):
        """Get shareable link for folder"""
        folder = self.get_object()
        return Response({
            'folder_id': folder.id,
            'folder_name': folder.name,
            'share_link': f"/files/shared/folder/{folder.folder_link}",
            'full_url': request.build_absolute_uri(f"/files/shared/folder/{folder.folder_link}")
        })
    
    @action(detail=True, methods=['post'])
    def copy_link(self, request, pk=None):
        """Copy folder link to clipboard (returns link for frontend to copy)"""
        folder = self.get_object()
        full_url = request.build_absolute_uri(f"/files/shared/folder/{folder.folder_link}")
        return Response({
            'link': full_url,
            'message': 'Link ready to copy'
        })
    
    def destroy(self, request, *args, **kwargs):
        """Override delete to prevent deletion of system folders"""
        folder = self.get_object()
        if folder.is_system_folder:
            return Response(
                {'error': 'System folders cannot be deleted. Only admin can delete from Files & Folders section.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FileListSerializer
        elif self.action == 'retrieve':
            return FileDetailSerializer
        return FileSerializer
    
    def get_queryset(self):
        queryset = File.objects.all()
        
        # Filter by folder
        folder_id = self.request.query_params.get('folder', None)
        if folder_id:
            if folder_id == 'root':
                queryset = queryset.filter(folder=None)
            else:
                queryset = queryset.filter(folder_id=folder_id)
        
        # Filter by file type
        file_type = self.request.query_params.get('type', None)
        if file_type:
            queryset = queryset.filter(file_type=file_type)
        
        # Search by name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(original_name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        # Handle folder assignment
        folder_id = self.request.data.get('folder')
        folder = None
        if folder_id and folder_id != 'root':
            try:
                folder = Folder.objects.get(id=folder_id)
            except Folder.DoesNotExist:
                pass
        
        serializer.save(uploaded_by=self.request.user, folder=folder)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download file"""
        file_obj = self.get_object()
        
        try:
            file_path = file_obj.file_path.path
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type=file_obj.mime_type or 'application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{file_obj.original_name}"'
                    return response
            else:
                raise Http404("File not found")
        except Exception as e:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def share_link(self, request, pk=None):
        """Get shareable link for file"""
        file_obj = self.get_object()
        return Response({
            'file_id': file_obj.id,
            'file_name': file_obj.name,
            'share_link': f"/files/shared/file/{file_obj.file_link}",
            'full_url': request.build_absolute_uri(f"/files/shared/file/{file_obj.file_link}")
        })
    
    @action(detail=True, methods=['post'])
    def copy_link(self, request, pk=None):
        """Copy file link to clipboard (returns link for frontend to copy)"""
        file_obj = self.get_object()
        full_url = request.build_absolute_uri(f"/files/shared/file/{file_obj.file_link}")
        return Response({
            'link': full_url,
            'message': 'Link ready to copy'
        })

class FileShareViewSet(viewsets.ModelViewSet):
    queryset = FileShare.objects.all()
    serializer_class = FileShareSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return FileShare.objects.filter(
            Q(shared_with=self.request.user) | 
            Q(shared_by=self.request.user)
        )
    
    def perform_create(self, serializer):
        serializer.save(shared_by=self.request.user)


# Shared access views (no authentication required)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def shared_folder_access(request, folder_link):
    """Access shared folder via link"""
    try:
        folder = get_object_or_404(Folder, folder_link=folder_link)
        
        # Get folder contents
        subfolders = folder.subfolders.all()
        files = folder.files.all()
        
        return Response({
            'folder': FolderDetailSerializer(folder).data,
            'subfolders': FolderListSerializer(subfolders, many=True).data,
            'files': FileListSerializer(files, many=True).data
        })
    except Exception as e:
        return Response({'error': 'Folder not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def shared_file_access(request, file_link):
    """Access shared file via link"""
    try:
        file_obj = get_object_or_404(File, file_link=file_link)
        return Response(FileDetailSerializer(file_obj).data)
    except Exception as e:
        return Response({'error': 'File not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def shared_file_download(request, file_link):
    """Download shared file via link"""
    try:
        file_obj = get_object_or_404(File, file_link=file_link)
        file_path = file_obj.file_path.path
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type=file_obj.mime_type or 'application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{file_obj.original_name}"'
                return response
        else:
            raise Http404("File not found")
    except Exception as e:
        return Response({'error': 'File not found or access denied'}, status=status.HTTP_404_NOT_FOUND)