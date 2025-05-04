from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Root"])

class HealthResponse(BaseModel):
    status: str

@router.get("/health", response_model=HealthResponse)
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}
