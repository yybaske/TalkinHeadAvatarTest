from fastapi import (
    APIRouter,
    HTTPException,
)
from pydantic import BaseModel

from app.services.conversation_feature_service import (
    get_conversation_features,
    update_conversation_feature,
)
from app.services.tool_router_service import (
    get_tool_context,
)


router = APIRouter(
    prefix="/conversations",
    tags=[
        "conversation-features"
    ],
)


class ConversationFeatureUpdateRequest(
    BaseModel
):
    enabled: bool


# =========================================================
# Conversation Features
# =========================================================

@router.get(
    "/{conversation_id}/features"
)
def get_features_for_conversation(
    conversation_id: str,
):
    try:
        return (
            get_conversation_features(
                conversation_id
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.put(
    "/{conversation_id}/features/{feature_key}"
)
def update_feature_for_conversation(
    conversation_id: str,
    feature_key: str,
    request: ConversationFeatureUpdateRequest,
):
    try:
        return (
            update_conversation_feature(
                conversation_id=(
                    conversation_id
                ),
                feature_key=(
                    feature_key
                ),
                enabled=(
                    request.enabled
                ),
            )
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
# Tool Router
# =========================================================

@router.get(
    "/{conversation_id}/tools"
)
async def get_tools_for_conversation(
    conversation_id: str,
):
    """
    この会話で利用可能なToolを返す。
    """

    try:
        return await get_tool_context(
            conversation_id
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