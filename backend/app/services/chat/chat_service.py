"""
ChatService — high-level service consumed by the API layer.

Responsibilities:
  • Manage per-user conversation history (Redis-backed, in-memory fallback).
  • Build the LangGraph agent with the configured LLM.
  • Expose a simple `send_message(user_id, message, conversation_id)` API.
  • Handle graceful degradation when the LLM is not configured.

Thread-safe: one singleton instance created at startup and shared across
all request handlers.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import settings
from app.services.chat.conversation_store import ConversationStore

logger = logging.getLogger(__name__)


class ChatService:
    """Stateful chat service backed by LangGraph agent."""

    def __init__(self, redis_client=None):
        self._store = ConversationStore(redis_client)
        self._agent = None
        self._available = False
        self._init_agent()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def _init_agent(self) -> None:
        """Try to build the LLM + agent graph. Fail gracefully."""
        try:
            from app.services.chat.llm_factory import build_llm
            from app.services.chat.agent import build_agent_graph

            llm = build_llm()
            self._agent = build_agent_graph(llm)
            self._available = True
            logger.info("ChatService initialised — agent ready")
        except Exception as exc:
            logger.warning("ChatService unavailable (LLM not configured): %s", exc)
            self._available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def is_available(self) -> bool:
        return self._available

    async def send_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict:
        """
        Send a user message and return the agent's reply.

        Args:
            user_id:          Authenticated user's ID.
            message:          The user's input text.
            conversation_id:  Optional conversation ID for history continuity.
            model:            Optional model override for this request.

        Returns:
            {
                "reply": str,
                "conversation_id": str,
                "model": str,
            }
        """
        conv_id = conversation_id or str(uuid.uuid4())

        if not self._available:
            return self._fallback_response(message, conv_id)

        # Optionally rebuild agent with a different model
        agent = self._agent
        if model and model != settings.AZURE_OPENAI_DEPLOYMENT:
            try:
                from app.services.chat.llm_factory import build_llm
                from app.services.chat.agent import build_agent_graph
                agent = build_agent_graph(build_llm(model=model))
            except Exception as exc:
                logger.warning("Failed to build agent with model=%s: %s", model, exc)
                agent = self._agent

        # Verify ownership when a conversation_id was provided
        if conversation_id is not None:
            try:
                user_convs = await self._store.list_user_conversations(user_id)
                if conv_id not in user_convs:
                    raise PermissionError("Conversation does not belong to user")
            except PermissionError:
                raise
            except Exception:
                # If we cannot verify membership due to store error, proceed but log
                logger.warning("Could not verify conversation ownership for user %s", user_id)

        # Load message history from Redis / memory
        history = await self._store.get_history(conv_id)
        history.append(HumanMessage(content=message))

        # Check for consent confirmation: if the last stored meta contains a pending_consent flag
        try:
            meta = await self._store.get_conversation_meta(conv_id)
        except Exception:
            meta = {}

        consent_confirmed = False
        if isinstance(message, str) and message.strip().lower() in ('yes', 'y', 'confirm'):
            if meta.get('pending_consent'):
                consent_confirmed = True
                # clear the pending flag
                try:
                    meta.pop('pending_consent', None)
                    await self._store._redis.set(f"chat:conv:{conv_id}:meta", json.dumps(meta), ex=86400)
                except Exception:
                    # best-effort; ignore if redis not available
                    pass

        # Trim to max history
        max_msgs = settings.CHAT_MAX_HISTORY * 2  # each turn = 2 messages
        if len(history) > max_msgs:
            history = history[-max_msgs:]

        try:
            result = await agent.ainvoke({
                "messages": history,
                "user_id": user_id,
                "consent_confirmed": consent_confirmed,
            })

            # Extract the final AI message
            ai_messages = [
                m for m in result["messages"]
                if isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None)
            ]
            reply = ai_messages[-1].content if ai_messages else "I'm sorry, I couldn't process that."

            # Update conversation history and persist
            history.append(AIMessage(content=reply))
            await self._store.save_history(conv_id, history)

            model_used = model or settings.AZURE_OPENAI_DEPLOYMENT or settings.AZURE_OPENAI_MODEL

            return {
                "reply": reply,
                "conversation_id": conv_id,
                "model": model_used,
            }

        except Exception as exc:
            logger.error("Agent invocation failed: %s", exc, exc_info=True)
            return self._fallback_response(message, conv_id)

    async def create_conversation(self) -> dict:
        """Create a new conversation and return its ID."""
        # Deprecated: use create_conversation_for_user where possible
        conv_id = str(uuid.uuid4())
        await self._store.save_history(conv_id, [])
        return {"id": conv_id}

    async def create_conversation_for_user(self, user_id: str) -> dict:
        """Create a new conversation, persist empty history, and record ownership for a user."""
        conv_id = str(uuid.uuid4())
        await self._store.save_history(conv_id, [])
        try:
            await self._store.add_user_conversation(user_id, conv_id)
        except Exception:
            logger.warning("Failed to associate conv %s with user %s", conv_id, user_id)
        return {"id": conv_id}

    async def get_conversations(self, user_id: str) -> dict:
        """List conversation IDs belonging to a specific user, including meta (title, last message, timestamp)."""
        conv_ids = await self._store.list_user_conversations(user_id)
        conversations = []
        for cid in conv_ids:
            try:
                meta = await self._store.get_conversation_meta(cid)
            except Exception:
                logger.warning("Failed to load meta for conv %s", cid)
                meta = {}
            conversations.append({
                "id": cid,
                "title": meta.get("title"),
                "last": meta.get("last"),
                "ts": meta.get("ts"),
            })
        return {"conversations": conversations}

    async def get_history(self, conversation_id: str, user_id: Optional[str] = None) -> dict:
        """Return messages in a conversation.

        If user_id is provided, verify the conversation belongs to the user.
        """
        if user_id is not None:
            try:
                user_convs = await self._store.list_user_conversations(user_id)
                if conversation_id not in user_convs:
                    raise PermissionError("Conversation does not belong to user")
            except PermissionError:
                raise
            except Exception:
                logger.warning("Could not verify conversation ownership for user %s", user_id)

        history = await self._store.get_history(conversation_id)
        messages = []
        for m in history:
            ts = None
            # preserve stored timestamp if present (could be ISO string)
            try:
                ts = getattr(m, 'timestamp', None)
            except Exception:
                ts = None
            if isinstance(m, HumanMessage):
                messages.append({"role": "user", "content": m.content, "timestamp": ts})
            elif isinstance(m, AIMessage):
                messages.append({"role": "assistant", "content": m.content, "timestamp": ts})
        return {"messages": messages, "conversation_id": conversation_id}

    async def delete_conversation(self, conversation_id: str, user_id: Optional[str] = None) -> None:
        """Delete a conversation and remove association with a user.

        If user_id is provided, enforce ownership.
        """
        if user_id is not None:
            user_convs = await self._store.list_user_conversations(user_id)
            if conversation_id not in user_convs:
                raise PermissionError("Conversation does not belong to user")

        # Remove conversation data and associations (best-effort)
        await self._store.delete_conversation(conversation_id)
        if user_id is not None:
            try:
                await self._store.remove_user_conversation(user_id, conversation_id)
            except Exception:
                logger.warning("Failed to remove conversation %s from user %s set", conversation_id, user_id)

    # ------------------------------------------------------------------
    # Fallback when LLM is not configured
    # ------------------------------------------------------------------
    @staticmethod
    def _fallback_response(message: str, conv_id: str) -> dict:
        """Return a helpful fallback when the AI agent is unavailable."""
        import random
        tips = [
            "💡 Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings.",
            "💡 Building an emergency fund of 3-6 months' expenses is a great start.",
            "💡 Track every expense — awareness is the first step to better finances.",
            "💡 Pay off high-interest debt first (avalanche method) to save more long-term.",
            "💡 Automate your savings: set up auto-transfers on payday.",
            "💡 Review your subscriptions regularly — cancel what you don't use.",
            "💡 Set specific, measurable financial goals with deadlines.",
            "💡 Use the app's budget feature to set spending limits per category.",
        ]
        return {
            "reply": (
                "I'm currently running in offline mode (AI model not configured). "
                f"Here's a financial tip: {random.choice(tips)} "
                "Ask your administrator to configure AI-features for full AI-powered advice based on your expertise."
            ),
            "conversation_id": conv_id,
            "model": "fallback",
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Return the singleton ChatService instance (lazy init)."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def init_chat_service(redis_client=None) -> ChatService:
    """Initialise the singleton with an explicit Redis client (called from lifespan)."""
    global _chat_service
    _chat_service = ChatService(redis_client=redis_client)
    return _chat_service
