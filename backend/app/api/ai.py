from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.database import get_db
from app.core.exceptions import FileUploadError
from app.core.rate_limit import limiter
from app.middleware.auth import require_citizen
from app.models.user import User
from app.schemas.ai import AIAnalysisResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["ai"])

_ALLOWED_PREVIEW_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_PREVIEW_BYTES = 10 * 1024 * 1024


@router.post("/analyze-image", response_model=AIAnalysisResponse)
@limiter.limit("30/minute")
async def analyze_image(
    request: Request,
    image: UploadFile = File(...),
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    if image.content_type not in _ALLOWED_PREVIEW_TYPES:
        raise FileUploadError(
            f"Unsupported image type '{image.content_type}'.", error_code="UNSUPPORTED_FILE_TYPE"
        )

    content = await image.read()
    if len(content) == 0:
        raise FileUploadError("Uploaded file is empty.", error_code="EMPTY_FILE")
    if len(content) > _MAX_PREVIEW_BYTES:
        raise FileUploadError("File exceeds the 10MB size limit.", error_code="FILE_TOO_LARGE")

    return await AIService(db).analyze(content, image.content_type)
