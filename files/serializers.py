from rest_framework import serializers
from .models import Folder, File, FileShare
from accounts.serializers import UserListSerializer

class FolderListSerializer(serializers.ModelSerializer):
    files_count = serializers.ReadOnlyField()
    subfolders_count = serializers.ReadOnlyField()
    total_size = serializers.ReadOnlyField()
    created_by_detail = UserListSerializer(source='created_by', read_only=True)
    
    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'description', 'created_at', 'updated_at',
            'files_count', 'subfolders_count', 'total_size', 'created_by_detail',
            'is_project_folder', 'is_employee_folder', 'is_client_folder', 
            'full_path', 'color', 'is_system_folder', 'folder_link'
        ]

class FolderDetailSerializer(serializers.ModelSerializer):
    files_count = serializers.ReadOnlyField()
    subfolders_count = serializers.ReadOnlyField()
    total_size = serializers.ReadOnlyField()
    created_by_detail = UserListSerializer(source='created_by', read_only=True)
    parent_detail = FolderListSerializer(source='parent', read_only=True)
    full_path = serializers.ReadOnlyField()
    
    class Meta:
        model = Folder
        fields = '__all__'

class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = '__all__'

class FileListSerializer(serializers.ModelSerializer):
    uploaded_by_detail = UserListSerializer(source='uploaded_by', read_only=True)
    folder_detail = FolderListSerializer(source='folder', read_only=True)
    formatted_size = serializers.ReadOnlyField()
    extension = serializers.ReadOnlyField()
    
    class Meta:
        model = File
        fields = [
            'id', 'name', 'original_name', 'file_type', 'size', 'formatted_size',
            'extension', 'mime_type', 'created_at', 'updated_at', 'description',
            'is_public', 'uploaded_by_detail', 'folder_detail', 'file_path', 'file_link'
        ]

class FileDetailSerializer(serializers.ModelSerializer):
    uploaded_by_detail = UserListSerializer(source='uploaded_by', read_only=True)
    folder_detail = FolderDetailSerializer(source='folder', read_only=True)
    formatted_size = serializers.ReadOnlyField()
    extension = serializers.ReadOnlyField()
    
    class Meta:
        model = File
        fields = '__all__'

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = '__all__'
        extra_kwargs = {
            'size': {'required': False},
            'mime_type': {'required': False},
            'file_type': {'required': False},
        }
        
    def validate(self, data):
        # Ensure file_path is provided
        if not data.get('file_path'):
            raise serializers.ValidationError({'file_path': 'This field is required.'})
        return data
        
    def create(self, validated_data):
        # Handle file upload - the file comes in as 'file_path' from the model field
        file_data = validated_data.get('file_path')
        if file_data:
            validated_data['size'] = file_data.size
            validated_data['mime_type'] = getattr(file_data, 'content_type', '')
            
        # Set original_name if not provided
        if not validated_data.get('original_name') and file_data:
            validated_data['original_name'] = file_data.name
            
        # Set name if not provided
        if not validated_data.get('name') and file_data:
            validated_data['name'] = file_data.name
            
        return super().create(validated_data)

class FileShareSerializer(serializers.ModelSerializer):
    shared_with_detail = UserListSerializer(source='shared_with', read_only=True)
    shared_by_detail = UserListSerializer(source='shared_by', read_only=True)
    file_detail = FileListSerializer(source='file', read_only=True)
    
    class Meta:
        model = FileShare
        fields = '__all__'