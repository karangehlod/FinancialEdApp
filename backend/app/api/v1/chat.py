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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat / AI Advisor"])

# Try to import Chat service — fail gracefully if optional deps missing
try:
    from app.services.chat.chat_service import get_chat_service, ChatService
    _CHAT_AVAILABLE = True
except Exception as exc:  # ModuleNotFoundError, ImportError, or runtime error
    _CHAT_AVAILABLE = False
    get_chat_service = None  # type: ignore
    ChatService = None  # type: ignore
    logger.warning("ChatService unavailable at import time: %s", exc)


# Provide a dependency wrapper that raises 503 when chat is not available
def _get_chat_service() -> ChatService:
    if not _CHAT_AVAILABLE or get_chat_service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chat feature is not available in this environment")
    return get_chat_service()


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
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
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
    # create conversation associated with the current user
    result = await chat_service.create_conversation_for_user(str(current_user.id))
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
    try:
        result = await chat_service.get_history(conversation_id, user_id=str(current_user.id))
        return ChatHistoryResponse(**result)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch chat history: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve chat history")


@router.delete(
    "/conversation/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation and its history",
)
async def delete_conversation(
    conversation_id: str,
    current_user=Depends(get_current_user),
    chat_service: ChatService = Depends(_get_chat_service),
):
    """Delete conversation history and remove its association with the user."""
    try:
        await chat_service.delete_conversation(conversation_id, user_id=str(current_user.id))
        return
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete conversation %s: %s", conversation_id, exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete conversation")


@router.get(
    "/prefs",
    summary="Get chat UI preferences for current user",
)
async def get_prefs(
    current_user=Depends(get_current_user),
    chat_service: ChatService = Depends(_get_chat_service),
):
    """Return chat-related UI preferences for the authenticated user."""
    try:
        prefs = await chat_service._store.get_user_prefs(str(current_user.id))
        return prefs
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to read prefs for user %s: %s", current_user.id, exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to read preferences")


@router.put(
    "/prefs",
    summary="Set chat UI preferences for current user",
)
async def set_prefs(
    body: dict,
    current_user=Depends(get_current_user),
    chat_service: ChatService = Depends(_get_chat_service),
):
    """Update chat-related UI preferences for the authenticated user."""
    try:
        for k, v in body.items():
            await chat_service._store.set_user_pref(str(current_user.id), k, v)
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to save prefs for user %s: %s", current_user.id, exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save preferences")


from pydantic import BaseModel


class MigrateConversationRequest(BaseModel):
    messages: list[ChatHistoryMessage]


@router.post(
    "/migrate",
    response_model=ConversationResponse,
    summary="Migrate local client conversation into a server-side conversation for the user",
)
async def migrate_conversation(
    body: MigrateConversationRequest,
    current_user=Depends(get_current_user),
    chat_service: ChatService = Depends(_get_chat_service),
):
    """Create a new conversation for the user and import the supplied message history.

    The request should include messages with `role` and `content` and optional `timestamp`.
    """
    try:
        # Create conv for user
        result = await chat_service.create_conversation_for_user(str(current_user.id))
        conv_id = result["id"]

        # Convert incoming messages into LangChain message objects
        try:
            from langchain_core.messages import HumanMessage, AIMessage
        except Exception:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chat feature unavailable")

        msgs = []
        for m in body.messages:
            ts = getattr(m, 'timestamp', None)
            if m.role == 'user' or m.role == 'human':
                msg = HumanMessage(content=m.content)
            else:
                msg = AIMessage(content=m.content)
            # preserve timestamp if supplied
            if ts:
                try:
                    setattr(msg, 'timestamp', ts)
                except Exception:
                    pass
            msgs.append(msg)

        # Persist history
        await chat_service._store.save_history(conv_id, msgs)
        return ConversationResponse(id=conv_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to migrate conversation: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to migrate conversation")
