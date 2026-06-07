"""
Chat API endpoints — AI-powered financial advisor.

Routes:
  POST /chat/message          → send a message, get AI reply
  POST /chat/conversation     → create a new conversation
  GET  /chat/conversations    → list user's conversations
  GET  /chat/history/{id}     → get messages in a conversation

All endpoints require authentication.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.services.chat.chat_service import get_chat_service, ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat / AI Advisor"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatMessageRequest(BaseModel):
    """User sends a message to the AI advisor."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message text")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for history continuity")
    model: Optional[str] = Field(None, description="Optional model override (e.g., gpt-4o, gpt-35-turbo)")


class ChatMessageResponse(BaseModel):
    """AI advisor reply."""
    reply: str
    conversation_id: str
    model: str


class ConversationResponse(BaseModel):
    id: str


class ConversationsListResponse(BaseModel):
    conversations: list[str]


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryMessage]
    conversation_id: str


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def _get_chat_service() -> ChatService:
    return get_chat_service()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/message",
    response_model=ChatMessageResponse,
    summary="Send a message to the financial advisor",
)
async def send_message(
    body: ChatMessageRequest,
    current_user=Depends(get_current_user),
    chat_service: ChatService = Depends(_get_chat_service),
):
    """
    Send a message to the AI financial advisor and receive a reply.

    The agent has access to the user's expenses, budgets, goals, loans, and
    financial profile.  It will fetch the relevant data automatically based
    on the question.

    Pass `model` to switch the underlying LLM for this request
    (e.g., "gpt-35-turbo" for cheaper/faster responses).
    """
    try:
        result = await chat_service.send_message(
            user_id=str(current_user.id),
            message=body.message,
            conversation_id=body.conversation_id,
            model=body.model,
        )
        return ChatMessageResponse(**result)
    except Exception as exc:
        logger.error("Chat message failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message. Please try again.",
        )


@router.post(
    "/conversation",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_conversation(
    current_user=Depends(get_current_user),
    chat_service: ChatService = Depends(_get_chat_service),
):
    """Create a new empty conversation and return its ID."""
    result = await chat_service.create_conversation()
    return ConversationResponse(id=result["id"])


@router.get(
    "/conversations",
    response_model=ConversationsListResponse,
    summary="List conversations",
)
async def list_conversations(
    current_user=Depends(get_current_user),
    chat_service: ChatService = Depends(_get_chat_service),
):
    """List all conversation IDs for the current user."""
    result = await chat_service.get_conversations(str(current_user.id))
    return ConversationsListResponse(**result)


@router.get(
    "/history/{conversation_id}",
    response_model=ChatHistoryResponse,
    summary="Get conversation history",
)
async def get_history(
    conversation_id: str,
    current_user=Depends(get_current_user),
    chat_service: ChatService = Depends(_get_chat_service),
):
    """Return the message history for a specific conversation."""
    result = await chat_service.get_history(conversation_id)
    return ChatHistoryResponse(**result)
