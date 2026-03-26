from datetime import datetime, timezone

from fastapi import APIRouter

from app.storage.db import get_pool

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        p = get_pool()
        async with p.acquire() as conn:
            await conn.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
