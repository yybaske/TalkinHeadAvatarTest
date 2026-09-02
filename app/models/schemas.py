from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
)


class HistoryItem(
    BaseModel
):
    role: str
    content: str


class SearchRequest(
    BaseModel
):
    query: str

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    history: list[
        HistoryItem
    ] = Field(
        default_factory=list
    )


class ChatRequest(
    BaseModel
):
    query: str

    conversation_id: (
        UUID
        | None
    ) = None


class FeatureUpdateRequest(
    BaseModel
):
    enabled: bool