"""
Unit tests for ChatService — covers:
  • Initialization with/without Redis
  • send_message fallback when agent is unavailable
  • send_message with a mock agent
  • create_conversation
  • get_conversations
  • get_history
  • History trimming
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from app.services.chat.chat_service import ChatService
from app.services.chat.conversation_store import ConversationStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(redis_client=None, agent_available=False) -> ChatService:
    """
    Build a ChatService with agent init mocked out.
    If agent_available is True, we inject a fake agent.
    """
    with patch.object(ChatService, "_init_agent"):
        svc = ChatService(redis_client=redis_client)
    svc._available = agent_available
    return svc


# ---------------------------------------------------------------------------
# ConversationStore (in-memory fallback)
# ---------------------------------------------------------------------------

class TestConversationStoreInMemory:
    """Test the ConversationStore with no Redis (pure in-memory)."""

    @pytest.mark.asyncio
    async def test_save_and_get_history(self):
        store = ConversationStore(redis_client=None)
        conv_id = "test-conv-1"
        msgs = [HumanMessage(content="hello"), AIMessage(content="hi there")]

        await store.save_history(conv_id, msgs)
        result = await store.get_history(conv_id)

        assert len(result) == 2
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "hello"
        assert isinstance(result[1], AIMessage)
        assert result[1].content == "hi there"

    @pytest.mark.asyncio
    async def test_get_history_empty(self):
        store = ConversationStore(redis_client=None)
        result = await store.get_history("nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_conversations(self):
        store = ConversationStore(redis_client=None)
        await store.save_history("conv-a", [HumanMessage(content="a")])
        await store.save_history("conv-b", [HumanMessage(content="b")])

        convs = await store.list_conversations()
        assert set(convs) == {"conv-a", "conv-b"}

    @pytest.mark.asyncio
    async def test_delete_conversation(self):
        store = ConversationStore(redis_client=None)
        await store.save_history("conv-del", [HumanMessage(content="x")])
        await store.delete_conversation("conv-del")

        result = await store.get_history("conv-del")
        assert result == []


# ---------------------------------------------------------------------------
# ConversationStore (mocked Redis)
# ---------------------------------------------------------------------------

class TestConversationStoreRedis:
    """Test the ConversationStore with a mocked Redis client."""

    def _make_redis_mock(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        redis.delete = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_save_and_get_via_redis(self):
        redis = self._make_redis_mock()
        store = ConversationStore(redis_client=redis)

        msgs = [HumanMessage(content="q"), AIMessage(content="a")]
        await store.save_history("r-conv-1", msgs)

        # Verify redis.set was called
        redis.set.assert_awaited_once()
        call_args = redis.set.call_args
        assert "chat:conv:r-conv-1" in call_args.args or call_args.args[0] == "chat:conv:r-conv-1"

        # Now set up redis.get to return the stored data
        import json
        stored = json.dumps([
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "a"},
        ])
        redis.get = AsyncMock(return_value=stored)
        result = await store.get_history("r-conv-1")

        assert len(result) == 2
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)

    @pytest.mark.asyncio
    async def test_redis_failure_falls_back_to_memory(self):
        redis = self._make_redis_mock()
        redis.get = AsyncMock(side_effect=Exception("Redis down"))
        redis.set = AsyncMock(side_effect=Exception("Redis down"))

        store = ConversationStore(redis_client=redis)
        msgs = [HumanMessage(content="test")]
        # Should not raise — falls back to memory
        await store.save_history("fallback-conv", msgs)
        result = await store.get_history("fallback-conv")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delete_via_redis(self):
        redis = self._make_redis_mock()
        store = ConversationStore(redis_client=redis)
        await store.delete_conversation("del-conv")
        redis.delete.assert_awaited_once()


# ---------------------------------------------------------------------------
# ChatService — fallback mode (no LLM configured)
# ---------------------------------------------------------------------------

class TestChatServiceFallback:
    """Test ChatService in fallback mode (agent unavailable)."""

    @pytest.mark.asyncio
    async def test_send_message_returns_fallback(self):
        svc = _make_service(agent_available=False)
        result = await svc.send_message(user_id="u1", message="hello")

        assert result["model"] == "fallback"
        assert "offline mode" in result["reply"]
        assert "conversation_id" in result

    @pytest.mark.asyncio
    async def test_is_available_false(self):
        svc = _make_service(agent_available=False)
        assert svc.is_available is False


# ---------------------------------------------------------------------------
# ChatService — agent available (mocked)
# ---------------------------------------------------------------------------

class TestChatServiceWithAgent:
    """Test ChatService with a mocked agent."""

    def _make_agent_mock(self, reply_text="I can help with budgeting!"):
        agent = AsyncMock()
        agent.ainvoke = AsyncMock(return_value={
            "messages": [
                HumanMessage(content="test"),
                AIMessage(content=reply_text),
            ]
        })
        return agent

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        svc = _make_service(agent_available=True)
        svc._agent = self._make_agent_mock("Budget tip: save 20%")

        result = await svc.send_message(user_id="u1", message="help with budget")

        assert result["reply"] == "Budget tip: save 20%"
        assert result["conversation_id"] is not None
        assert result["model"] is not None

    @pytest.mark.asyncio
    async def test_send_message_preserves_conversation_id(self):
        svc = _make_service(agent_available=True)
        svc._agent = self._make_agent_mock("reply")

        conv_id = "my-conv-123"
        result = await svc.send_message(
            user_id="u1", message="hi", conversation_id=conv_id
        )
        assert result["conversation_id"] == conv_id

    @pytest.mark.asyncio
    async def test_send_message_agent_error_returns_fallback(self):
        svc = _make_service(agent_available=True)
        agent = AsyncMock()
        agent.ainvoke = AsyncMock(side_effect=RuntimeError("LLM error"))
        svc._agent = agent

        result = await svc.send_message(user_id="u1", message="crash")
        assert result["model"] == "fallback"
        assert "offline mode" in result["reply"]

    @pytest.mark.asyncio
    async def test_history_persists_across_messages(self):
        svc = _make_service(agent_available=True)
        svc._agent = self._make_agent_mock("first reply")

        conv_id = str(uuid.uuid4())
        await svc.send_message(user_id="u1", message="msg1", conversation_id=conv_id)

        svc._agent = self._make_agent_mock("second reply")
        await svc.send_message(user_id="u1", message="msg2", conversation_id=conv_id)

        history_result = await svc.get_history(conv_id)
        # Should have 4 messages: user1, ai1, user2, ai2
        assert len(history_result["messages"]) == 4

    @pytest.mark.asyncio
    @patch("app.services.chat.chat_service.settings")
    async def test_history_trimming(self, mock_settings):
        mock_settings.CHAT_MAX_HISTORY = 2  # max 2 turns → 4 messages
        mock_settings.AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
        mock_settings.AZURE_OPENAI_MODEL = "gpt-4o"

        svc = _make_service(agent_available=True)
        svc._agent = self._make_agent_mock("reply")

        conv_id = str(uuid.uuid4())
        # Send 5 messages — should trim to 4 (2 turns * 2)
        for i in range(5):
            svc._agent = self._make_agent_mock(f"reply-{i}")
            await svc.send_message(
                user_id="u1", message=f"msg-{i}", conversation_id=conv_id
            )

        history = await svc.get_history(conv_id)
        # After trimming: max 4 messages kept per cycle
        assert len(history["messages"]) <= 4 + 2  # ≤ max_msgs + 2 for the last turn


# ---------------------------------------------------------------------------
# ChatService — conversation management
# ---------------------------------------------------------------------------

class TestChatServiceConversations:

    @pytest.mark.asyncio
    async def test_create_conversation(self):
        svc = _make_service()
        result = await svc.create_conversation()
        assert "id" in result
        # Verify it's a valid UUID
        uuid.UUID(result["id"])

    @pytest.mark.asyncio
    async def test_get_conversations(self):
        svc = _make_service()
        await svc.create_conversation()
        await svc.create_conversation()

        result = await svc.get_conversations("u1")
        assert len(result["conversations"]) >= 2

    @pytest.mark.asyncio
    async def test_get_history_empty_conversation(self):
        svc = _make_service()
        result = await svc.get_history("nonexistent-conv")
        assert result["messages"] == []
        assert result["conversation_id"] == "nonexistent-conv"
