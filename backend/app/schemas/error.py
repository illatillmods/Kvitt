from typing import Optional

from pydantic import BaseModel


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    stage: Optional[str] = None
    retryable: bool = False
    suggestions: list[str] = []
    request_id: Optional[str] = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorDetail