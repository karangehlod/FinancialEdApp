"""
Chat service package — Azure OpenAI financial advisor with LangGraph agentic flow.

Modules:
  llm_factory   — Build LLM instances (Azure OpenAI / OpenAI) with easy model switching.
  tools         — LangChain tools that query the user's financial data.
  agent         — LangGraph state-machine orchestrating the agentic conversation.
  chat_service  — High-level ChatService consumed by the API layer.
"""
