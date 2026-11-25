
import os
import uuid

from dataclasses import dataclass
from io import BytesIO

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.exceptions import FileUploadError
from app.utils.storage import upload_to_s3, get_file_url


_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

_VIDEO_EXTENSION_BY_CONTENT_TYPE = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
}


def get_upload_url(relative_path: str) -> str:
    if settings.STORAGE_BACKEND.lower() == "s3":
        return get_file_url(relative_path)

    return f"/uploads/{relative_path}"


def _save_content(content: bytes, key: str, content_type: str) -> None:
    if settings.STORAGE_BACKEND.lower() == "s3":
        upload_to_s3(content, key, content_type)
        return

    destination_path = os.path.join(settings.UPLOAD_DIRECTORY, key)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    with open(destination_path, "wb") as f:
        f.write(content)


@dataclass
class SavedImage:
    relative_path: str
    content_type: str
    size_bytes: int
    width: int
    height: int

    @property
    def url(self) -> str:
        return get_upload_url(self.relative_path)


@dataclass
class SavedVideo:
    relative_path: str
    content_type: str
    size_bytes: int

    @property
    def url(self) -> str:
        return _get_url(self.relative_path)


async def save_uploaded_video(file: UploadFile, subdirectory: str) -> SavedVideo:
    if file.content_type not in settings.ALLOWED_VIDEO_TYPES:
        raise FileUploadError(
            f"Unsupported video type '{file.content_type}'. Allowed types: "
            f"{', '.join(settings.ALLOWED_VIDEO_TYPES)}.",
            error_code="UNSUPPORTED_FILE_TYPE",
        )

    content = await file.read()

    if len(content) == 0:
        raise FileUploadError("Uploaded file is empty.", error_code="EMPTY_FILE")

    max_video_size = settings.MAX_UPLOAD_SIZE * 5

    if len(content) > max_video_size:
        max_mb = max_video_size / (1024 * 1024)
        raise FileUploadError(
            f"Video exceeds the {max_mb:.0f}MB size limit.",
            error_code="FILE_TOO_LARGE",
        )

    extension = _VIDEO_EXTENSION_BY_CONTENT_TYPE[file.content_type]
    filename = f"{uuid.uuid4()}{extension}"
    relative_path = f"{subdirectory}/{filename}"

    _save_content(content, relative_path, file.content_type)

    return SavedVideo(
        relative_path=relative_path,
        content_type=file.content_type,
        size_bytes=len(content),
    )


async def save_uploaded_image(file: UploadFile, subdirectory: str) -> SavedImage:
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise FileUploadError(
            f"Unsupported image type '{file.content_type}'. Allowed types: "
            f"{', '.join(settings.ALLOWED_IMAGE_TYPES)}.",
            error_code="UNSUPPORTED_FILE_TYPE",
        )

    content = await file.read()

    if len(content) == 0:
        raise FileUploadError("Uploaded file is empty.", error_code="EMPTY_FILE")

    if len(content) > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise FileUploadError(
            f"File exceeds the {max_mb:.0f}MB size limit.",
            error_code="FILE_TOO_LARGE",
        )

    try:
        probe = Image.open(BytesIO(content))
        probe.verify()

        image = Image.open(BytesIO(content))
        width, height = image.size

    except (UnidentifiedImageError, OSError):
        raise FileUploadError(
            "Uploaded file is not a valid image.",
            error_code="INVALID_IMAGE",
        )

    extension = _EXTENSION_BY_CONTENT_TYPE[file.content_type]
    filename = f"{uuid.uuid4()}{extension}"
    relative_path = f"{subdirectory}/{filename}"

    _save_content(content, relative_path, file.content_type)

    return SavedImage(
        relative_path=relative_path,
        content_type=file.content_type,
        size_bytes=len(content),
        width=width,
        height=height,
    )
