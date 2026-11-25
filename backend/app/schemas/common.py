from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: Optional[T] = None


class MessageResponse(BaseModel):
    success: bool = True
    message: str


class ForgotPasswordResponse(BaseModel):
    success: bool = True
    message: str
    dev_reset_token: Optional[str] = None
