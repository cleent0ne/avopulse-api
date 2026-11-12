from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    """Used by the frontend to show connection badge and status."""
    return {
        "status": "healthy",
        "service": "AvoPulse API",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "sqlite",
        "version": "1.0.0-demo"
    }

