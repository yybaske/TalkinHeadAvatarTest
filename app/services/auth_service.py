from datetime import (
    datetime,
    timedelta,
    timezone,
)

import jwt
from jwt.exceptions import (
    InvalidTokenError,
)
from pwdlib import PasswordHash

from app.core.config import settings
from app.repositories.user_repository import (
    create_user,
    get_user_by_id,
    get_user_by_username,
)


password_hash = (
    PasswordHash.recommended()
)


DUMMY_PASSWORD_HASH = (
    password_hash.hash(
        "dummy-password-for-timing"
    )
)


def hash_password(
    password: str,
) -> str:
    return password_hash.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        return password_hash.verify(
            plain_password,
            hashed_password,
        )
    except Exception:
        return False


def authenticate_user(
    username: str,
    password: str,
) -> dict | None:
    username = (
        username
        .strip()
    )

    if not username:
        return None

    user = get_user_by_username(
        username
    )

    if user is None:
        verify_password(
            password,
            DUMMY_PASSWORD_HASH,
        )
        return None

    if not user["enabled"]:
        return None

    if not verify_password(
        password,
        user["password_hash"],
    ):
        return None

    return user


def create_session_token(
    user: dict,
) -> str:
    now = datetime.now(
        timezone.utc
    )

    expires_at = (
        now
        + timedelta(
            minutes=settings.AUTH_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": str(
            user["id"]
        ),
        "username": user[
            "username"
        ],
        "role": user[
            "role"
        ],
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.AUTH_SECRET_KEY,
        algorithm="HS256",
    )


def decode_session_token(
    token: str,
) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[
                "HS256",
            ],
        )
    except InvalidTokenError:
        return None

    user_id = payload.get(
        "sub"
    )

    if user_id is None:
        return None

    try:
        user_id_int = int(
            user_id
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    user = get_user_by_id(
        user_id_int
    )

    if user is None:
        return None

    if not user["enabled"]:
        return None

    return user


def create_initial_admin(
    username: str,
    password: str,
    display_name: str | None = None,
) -> dict:
    username = (
        username
        .strip()
    )

    if not username:
        raise ValueError(
            "ユーザーIDを入力してください。"
        )

    if len(password) < 8:
        raise ValueError(
            "パスワードは8文字以上にしてください。"
        )

    existing_user = (
        get_user_by_username(
            username
        )
    )

    if existing_user:
        raise ValueError(
            "同じユーザーIDが既に存在します。"
        )

    hashed_password = (
        hash_password(
            password
        )
    )

    return create_user(
        username=username,
        password_hash=hashed_password,
        display_name=display_name,
        role="admin",
    )


def public_user(
    user: dict,
) -> dict:
    return {
        "id": user["id"],
        "username": user[
            "username"
        ],
        "display_name": user[
            "display_name"
        ],
        "role": user[
            "role"
        ],
        "enabled": user[
            "enabled"
        ],
    }