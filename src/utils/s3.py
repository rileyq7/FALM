"""
S3 Utilities for Document Storage
"""

import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError

from .config import settings

logger = logging.getLogger(__name__)


class S3Client:
    """AWS S3 client for document storage"""

    def __init__(self):
        self.client = None
        self.bucket = settings.S3_BUCKET

    async def initialize(self):
        """Initialize S3 client"""
        if settings.AWS_ACCESS_KEY_ID:
            self.client = boto3.client(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            logger.info(f"[S3] Initialized (bucket: {self.bucket})")

    async def upload_file(self, file_path: str, s3_key: str) -> Optional[str]:
        """Upload file to S3"""
        if not self.client:
            return None

        try:
            self.client.upload_file(file_path, self.bucket, s3_key)
            url = f"https://{self.bucket}.s3.amazonaws.com/{s3_key}"
            return url
        except ClientError as e:
            logger.error(f"[S3] Upload failed: {e}")
            return None


s3_client = S3Client()
