from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)

from app.core.config import settings
from app.routes.auth_route import (
    router as auth_router,
)
from app.services.auth_service import (
    decode_session_token
)
from fastapi.staticfiles import (
    StaticFiles,
)
from fastapi.templating import (
    Jinja2Templates,
)

from app.models.schemas import (
    ChatRequest,
    FeatureUpdateRequest,
)
from app.routes.conversation_feature_routes import (
    router as conversation_feature_router,
)
from app.services.conversation_service import (
    get_conversation,
    get_conversation_list,
    prepare_conversation,
    remove_conversation,
    save_chat_result,
)
from app.services.document_service import (
    delete_document,
    list_documents,
    register_document,
)
from app.services.feature_service import (
    get_feature_status,
    get_features,
    set_feature_status,
)
from app.services.rag_service import (
    chat,
    search,
)


# =========================================================
# Path
# =========================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


STATIC_DIR = (
    BASE_DIR
    / "static"
)


TEMPLATE_DIR = (
    BASE_DIR
    / "templates"
)


# =========================================================
# FastAPI
# =========================================================

app = FastAPI(
    title="LipThink RAG API",
    version="1.0.0",
)


# =========================================================
# Router
# =========================================================

app.include_router(
    conversation_feature_router
)

app.include_router(
    auth_router
)

PUBLIC_PATHS = {
    "/login",
    "/logout",
    "/docs",
    "/openapi.json",
    "/redoc",
}

@app.middleware(
    "http"
)
async def authentication_middleware(
    request: Request,
    call_next,
):
    path = request.url.path

    if path.startswith(
        "/static/"
    ):
        return await call_next(
            request
        )

    if path in PUBLIC_PATHS:
        return await call_next(
            request
        )

    token = request.cookies.get(
        settings.AUTH_COOKIE_NAME
    )

    user = None

    if token:
        user = decode_session_token(
            token
        )

    if user is None:
        if path.startswith(
            "/api/"
        ) or request.method != "GET":
            return JSONResponse(
                status_code=401,
                content={
                    "detail":
                        "認証が必要です。"
                },
            )

        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    request.state.user = user

    return await call_next(
        request
    )


# =========================================================
# Static
# =========================================================

app.mount(
    "/static",
    StaticFiles(
        directory=str(
            STATIC_DIR
        )
    ),
    name="static",
)


templates = (
    Jinja2Templates(
        directory=str(
            TEMPLATE_DIR
        )
    )
)


# =========================================================
# Health
# =========================================================

@app.get(
    "/health"
)
def health():
    return {
        "status": "ok",
    }


# =========================================================
# Frontend
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
def index(
    request: Request,
):
    token = request.cookies.get(
        settings.AUTH_COOKIE_NAME
    )

    if not token:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    user = decode_session_token(
        token
    )

    if not user:
        response = RedirectResponse(
            url="/login",
            status_code=303,
        )

        response.delete_cookie(
            key=settings.AUTH_COOKIE_NAME,
            path="/",
        )

        return response

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_user": user,
        },
    )


# =========================================================
# login
# =========================================================
@app.get(
    "/login",
    response_class=HTMLResponse,
)
def login_page(
    request: Request,
):
    token = request.cookies.get(
        settings.AUTH_COOKIE_NAME
    )

    if token:
        user = decode_session_token(
            token
        )

        if user:
            return RedirectResponse(
                url="/",
                status_code=303,
            )

    error = (
        request.query_params.get(
            "error"
        )
        == "1"
    )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": error,
        },
    )


# =========================================================
# Search
# =========================================================

@app.get(
    "/search"
)
def search_documents(
    query: str,
    limit: int = 5,
):
    try:
        return search(
            query=query,
            limit=limit,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Chat
# =========================================================

@app.post(
    "/chat"
)
def chat_endpoint(
    request: ChatRequest,
):
    try:
        # -----------------------------------------
        # 会話準備
        #
        # 新規の場合:
        #   conversation作成
        #   conversation_features初期化
        #
        # 既存の場合:
        #   履歴取得
        # -----------------------------------------

        conversation_id, history = (
            prepare_conversation(
                request.conversation_id
            )
        )

        # -----------------------------------------
        # RAG / 通常会話
        #
        # conversation_idを渡すことで
        # conversation_features.local_rag
        # が実際の検索処理に反映される。
        # -----------------------------------------

        result = chat(
            query=request.query,
            history=history,
            conversation_id=(
                conversation_id
            ),
        )

        # -----------------------------------------
        # 会話保存
        # -----------------------------------------

        save_chat_result(
            conversation_id=(
                conversation_id
            ),
            query=request.query,
            result=result,
        )

        # -----------------------------------------
        # Frontendへ会話ID返却
        # -----------------------------------------

        result[
            "conversation_id"
        ] = conversation_id

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Conversations
# =========================================================

@app.get(
    "/conversations"
)
def get_conversations():
    try:
        return (
            get_conversation_list()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get(
    "/conversations/{conversation_id}"
)
def get_conversation_detail(
    conversation_id: str,
):
    try:
        return get_conversation(
            conversation_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.delete(
    "/conversations/{conversation_id}"
)
def delete_conversation_endpoint(
    conversation_id: str,
):
    try:
        return remove_conversation(
            conversation_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Documents
# =========================================================

@app.get(
    "/documents"
)
def get_document_list():
    try:
        return list_documents()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post(
    "/documents"
)
async def upload_document(
    file: UploadFile = File(...),
):
    try:
        return await register_document(
            file
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.delete(
    "/documents/{document_id}"
)
def delete_document_endpoint(
    document_id: int,
):
    try:
        return delete_document(
            document_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Feature Flags
#
# 管理者側のグローバル設定
# =========================================================

@app.get(
    "/features"
)
def get_feature_list():
    try:
        return get_features()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get(
    "/features/{feature_key}"
)
def get_feature_detail(
    feature_key: str,
):
    try:
        return get_feature_status(
            feature_key
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.put(
    "/features/{feature_key}"
)
def update_feature_setting(
    feature_key: str,
    request: FeatureUpdateRequest,
):
    try:
        return set_feature_status(
            feature_key=(
                feature_key
            ),
            enabled=(
                request.enabled
            ),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )