"""
Cloudflare R2 Storage utility - Shared across all apps.
Handles upload and deletion of files to/from Cloudflare R2 bucket.
"""

import os
import io
import boto3
from django.conf import settings
from botocore.config import Config


def get_cloudflare_client():
    """Initialize and return Cloudflare R2 S3 client."""
    s3_client = boto3.client(
        's3',
        endpoint_url=os.getenv('CLOUDFLARE_R2_BUCKET_ENDPOINT'),
        aws_access_key_id=os.getenv('CLOUDFLARE_R2_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('CLOUDFLARE_R2_SECRET_KEY'),
        region_name='auto',
        config=Config(signature_version='s3v4')
    )
    return s3_client


def upload_to_cloudflare(file_obj, folder_name='files'):
    """
    Upload a file to Cloudflare R2 bucket.
    
    Args:
        file_obj: Django UploadedFile object
        folder_name: Subfolder in R2 bucket (default: 'files')
    
    Returns:
        dict: {
            'success': bool,
            'r2_url': str (public URL if successful),
            'error': str (error message if failed),
            'file_key': str (S3 object key)
        }
    """
    try:
        bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET')
        public_url_base = os.getenv('CLOUDFLARE_R2_PUBLIC_URL')
        
        if not bucket_name or not public_url_base:
            return {
                'success': False,
                'error': 'Cloudflare R2 credentials not configured',
                'r2_url': None,
                'file_key': None
            }
        
        # Generate file key with folder
        original_filename = file_obj.name
        file_key = f"{folder_name}/{original_filename}"
        
        # Initialize S3 client
        s3_client = get_cloudflare_client()
        
        # Read file into BytesIO to preserve original file object
        file_obj.seek(0)
        file_content = io.BytesIO(file_obj.read())
        
        # Upload file to R2
        s3_client.upload_fileobj(
            file_content,
            bucket_name,
            file_key,
            ExtraArgs={'ContentType': file_obj.content_type}
        )
        
        # Reset original file pointer for Django
        file_obj.seek(0)
        
        # Generate public URL
        r2_url = f"{public_url_base}/{file_key}"
        
        return {
            'success': True,
            'r2_url': r2_url,
            'error': None,
            'file_key': file_key
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'r2_url': None,
            'file_key': None
        }


def delete_from_cloudflare(file_key):
    """
    Delete a file from Cloudflare R2 bucket.
    
    Args:
        file_key: S3 object key (path to file in bucket)
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET')
        
        if not bucket_name:
            return {
                'success': False,
                'message': 'Cloudflare R2 bucket not configured'
            }
        
        s3_client = get_cloudflare_client()
        s3_client.delete_object(Bucket=bucket_name, Key=file_key)
        
        return {
            'success': True,
            'message': f'Successfully deleted {file_key}'
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }


def extract_file_key_from_url(r2_url):
    """
    Extract the S3 object key (file path) from a Cloudflare R2 public URL.
    
    Args:
        r2_url: The public URL from Cloudflare R2
        Example: https://cdn.example.com/collection_proofs/document.pdf
    
    Returns:
        str: The S3 object key (e.g., 'collection_proofs/document.pdf')
    """
    try:
        public_url_base = os.getenv('CLOUDFLARE_R2_PUBLIC_URL')
        
        if not public_url_base:
            return None
        
        # Remove trailing slash from public URL base if present
        public_url_base = public_url_base.rstrip('/')
        
        # Check if URL starts with public URL base
        if r2_url.startswith(public_url_base):
            # Extract the file key by removing the public URL base and leading slash
            file_key = r2_url[len(public_url_base):].lstrip('/')
            return file_key
        
        return None
    
    except Exception as e:
        return None
