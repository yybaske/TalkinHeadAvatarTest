from fastapi import (
    APIRouter,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import (
    JSONResponse,
    RedirectResponse,
)

from app.core.config import settings
from app.services.auth_service import (
    authenticate_user,
    create_session_token,
    decode_session_token,
    public_user,
)


router = APIRouter()


@router.post(
    "/login",
)
def login(
    username: str = Form(...),
    password: str = Form(...),
):
    user = authenticate_user(
        username=username,
        password=password,
    )

    if user is None:
        return RedirectResponse(
            url="/login?error=1",
            status_code=303,
        )

    token = create_session_token(
        user
    )

    response = RedirectResponse(
        url="/",
        status_code=303,
    )

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=(
            settings.AUTH_EXPIRE_MINUTES
            * 60
        ),
        path="/",
    )

    return response


@router.post(
    "/logout",
)
def logout():
    response = RedirectResponse(
        url="/login",
        status_code=303,
    )

    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
    )

    return response


@router.get(
    "/api/auth/me",
)
def get_current_user_api(
    request: Request,
):
    token = request.cookies.get(
        settings.AUTH_COOKIE_NAME
    )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="認証が必要です。",
        )

    user = decode_session_token(
        token
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="セッションが無効です。",
        )

    return {
        "status": "ok",
        "user": public_user(
            user
        ),
    }