
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
    )


def upload_to_s3(
    content: bytes,
    key: str,
    content_type: str,
) -> str:
    client = get_s3_client()

    client.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type,
    )

    return key


def get_file_url(key: str) -> str:
    client = get_s3_client()

    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": key,
        },
        ExpiresIn=settings.AWS_PRESIGNED_URL_EXPIRE,
    )


def delete_from_s3(key: str) -> None:
    client = get_s3_client()

    client.delete_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
    )

import boto3

from app.core.config import settings


def get_s3_client():
    """Create an S3 client using the configured AWS credentials."""
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
    )


def upload_to_s3(
    content: bytes,
    key: str,
    content_type: str,
) -> str:
    """Upload a file to the private S3 bucket."""
    client = get_s3_client()

    client.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type,
    )

    return key


def get_file_url(key: str) -> str:
    """Generate a temporary secure URL for a private S3 object."""
    client = get_s3_client()

    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": key,
        },
        ExpiresIn=settings.AWS_PRESIGNED_URL_EXPIRE,
    )


def delete_from_s3(key: str) -> None:
    """Delete an object from S3."""
    client = get_s3_client()

    client.delete_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
    )
