"""
Free-tier cloud storage helpers for audio files.

Supports:
- Local file storage (dev/small scale)
- Backblaze B2 (10GB free tier, S3-compatible, no payment method required!)
- Cloudflare R2 (10GB free tier, S3-compatible)
- AWS S3 (for later when funded)
"""

import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from typing import Optional
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()
MEDIA_DIR = os.getenv("MEDIA_DIR", "./media")


def get_storage_client():
    """Get S3-compatible storage client (works for R2, B2, and S3)."""
    backend = STORAGE_BACKEND
    
    if backend == "r2":
        # Cloudflare R2 (S3-compatible)
        account_id = os.getenv("R2_ACCOUNT_ID")
        access_key = os.getenv("R2_ACCESS_KEY_ID")
        secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
        
        if not all([account_id, access_key, secret_key]):
            logger.warning("R2 credentials incomplete; falling back to local storage")
            return None
        
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        return boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='auto'  # R2 uses 'auto'
        )
    
    elif backend == "b2":
        # Backblaze B2 (S3-compatible, 10GB free!)
        key_id = os.getenv("B2_KEY_ID")
        app_key = os.getenv("B2_APPLICATION_KEY")
        endpoint = os.getenv("B2_ENDPOINT")  # e.g., s3.us-west-004.backblazeb2.com
        
        if not all([key_id, app_key, endpoint]):
            logger.warning("B2 credentials incomplete; falling back to local storage")
            return None
        
        return boto3.client(
            's3',
            endpoint_url=f"https://{endpoint}",
            aws_access_key_id=key_id,
            aws_secret_access_key=app_key,
            region_name='us-west-004'  # B2 region
        )
    
    elif backend == "s3":
        # AWS S3
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION", "us-east-1")
        
        if not all([access_key, secret_key]):
            logger.warning("S3 credentials incomplete; falling back to local storage")
            return None
        
        return boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    
    # Local storage (default)
    return None


def upload_audio(key: str, content: bytes, content_type: str = 'audio/mpeg') -> tuple[bool, Optional[str]]:
    """
    Upload audio file to configured storage backend.
    
    Returns:
        (success: bool, url: Optional[str])
        - For cloud storage: returns public URL or key
        - For local storage: returns relative path
    """
    backend = STORAGE_BACKEND
    
    if backend in ["r2", "b2", "s3"]:
        client = get_storage_client()
        if not client:
            logger.warning(f"{backend.upper()} client unavailable; falling back to local")
            backend = "local"
        else:
            # Get bucket name
            bucket = (
                os.getenv("R2_BUCKET_NAME") if backend == "r2" 
                else os.getenv("B2_BUCKET_NAME") if backend == "b2"
                else os.getenv("S3_BUCKET_NAME")
            )
            
            if not bucket:
                logger.warning(f"No bucket configured for {backend}; falling back to local")
                backend = "local"
            else:
                try:
                    client.put_object(
                        Bucket=bucket,
                        Key=key,
                        Body=content,
                        ContentType=content_type
                    )
                    
                    # For R2, construct public URL if bucket is public
                    if backend == "r2":
                        # Option 1: R2 custom domain (if configured)
                        custom_domain = os.getenv("R2_PUBLIC_DOMAIN")
                        if custom_domain:
                            return True, f"https://{custom_domain}/{key}"
                        # Option 2: Return key (app will serve via presigned URL)
                        return True, key
                    
                    # For B2, construct public URL (bucket must be public)
                    elif backend == "b2":
                        endpoint = os.getenv("B2_ENDPOINT", "s3.us-west-004.backblazeb2.com")
                        bucket_name = os.getenv("B2_BUCKET_NAME")
                        # B2 public URL format
                        return True, f"https://{endpoint}/file/{bucket_name}/{key}"
                    
                    # For S3, return key (will generate presigned URL later)
                    return True, key
                    
                except (BotoCoreError, ClientError) as e:
                    logger.error(f"Failed to upload to {backend}: {e}")
                    backend = "local"
    
    # Local storage fallback
    try:
        # Ensure media directory exists
        os.makedirs(MEDIA_DIR, exist_ok=True)
        
        # Write file
        filepath = os.path.join(MEDIA_DIR, key.replace('/', '_'))
        with open(filepath, 'wb') as f:
            f.write(content)
        
        # Return relative URL path
        return True, f"/media/{key.replace('/', '_')}"
        
    except Exception as e:
        logger.error(f"Failed to save locally: {e}")
        return False, None


def generate_presigned_url(key: str, expires: int = 3600) -> Optional[str]:
    """Generate presigned URL for cloud storage (R2/B2/S3)."""
    backend = STORAGE_BACKEND
    
    if backend not in ["r2", "b2", "s3"]:
        # For local storage, return direct path
        return f"/media/{key.replace('/', '_')}"
    
    client = get_storage_client()
    if not client:
        return None
    
    bucket = (
        os.getenv("R2_BUCKET_NAME") if backend == "r2" 
        else os.getenv("B2_BUCKET_NAME") if backend == "b2"
        else os.getenv("S3_BUCKET_NAME")
    )
    
    if not bucket:
        return None
    
    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expires
        )
        return url
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None


# Backward compatibility with existing S3 helpers
def upload_tts_to_s3(key: str, content: bytes, content_type: str = 'audio/wav') -> bool:
    """Legacy S3 upload helper (now supports R2 too)."""
    success, _ = upload_audio(key, content, content_type)
    return success


def _s3_client():
    """Legacy S3 client getter."""
    return get_storage_client()
