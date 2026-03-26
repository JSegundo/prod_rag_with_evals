import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.storage.db import get_pool

COOKIE_NAME = "docchat_session"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session_id = request.cookies.get(COOKIE_NAME)
        needs_cookie = False

        if session_id:
            # Verify session exists in DB
            pool = get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id FROM sessions WHERE id = $1", uuid.UUID(session_id)
                )
                if not row:
                    session_id = None

        if not session_id:
            # Create new session
            pool = get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "INSERT INTO sessions DEFAULT VALUES RETURNING id"
                )
                session_id = str(row["id"])
            needs_cookie = True

        request.state.session_id = session_id

        response: Response = await call_next(request)

        if needs_cookie:
            response.set_cookie(
                key=COOKIE_NAME,
                value=session_id,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
            )

        return response
