"""
LangGraph agent — orchestrates the financial advisor conversation.

Graph topology (simplified):

    ┌─────────┐     tool_calls?     ┌───────┐
    │  agent  │ ─── yes ──────────► │ tools │
    │  (LLM)  │ ◄── results ────── │       │
    │         │ ─── no (final) ──► END
    └─────────┘

The agent node invokes the LLM with the system prompt + tools bound.
If the LLM returns tool_calls, the graph routes to the tool-execution node
which runs the requested tools and feeds results back to the agent.
When the LLM produces a plain text answer (no tool_calls), the graph ends.

All tools receive user_id transparently — injected into tool args at runtime
so the LLM never needs (or sees) the raw user ID.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.services.chat.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — the persona and guardrails for the financial advisor
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are FinEd AI — a friendly, knowledgeable personal financial advisor.

Your capabilities:
• Analyse the user's expenses, budgets, goals, loans, and financial profile.
• Provide actionable, personalised advice based on their REAL data.
• Explain financial concepts (compound interest, EMI, 50/30/20 rule, etc.).
• Suggest concrete steps to save more, reduce debt, or reach goals faster.

Rules:
1. Always ground your advice in the user's actual data — call the available tools to fetch it.
2. If you need information you don't have, use the appropriate tool before answering.
3. Be concise but thorough — use bullet points and numbers.
4. Never make up numbers. If data is unavailable, say so.
5. Be encouraging and constructive — this is an educational app.
6. Format currency values with $ and commas (e.g., $1,234.56).
7. If asked something outside personal finance (e.g., politics, code), politely decline.
8. Respect the user's privacy — never reveal raw user IDs or internal details.
"""


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    """State passed between graph nodes."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_agent_graph(llm):
    """
    Construct and compile the LangGraph agent.

    Args:
        llm: A LangChain chat model (Azure OpenAI or OpenAI).

    Returns:
        A compiled LangGraph runnable.
    """
    # Bind tools to the LLM so it can call them
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    # ── Agent node ────────────────────────────────────────────────────────
    async def agent_node(state: AgentState) -> dict:
        """Invoke the LLM with the current conversation."""
        messages = list(state["messages"])

        # Ensure system prompt is at the start
        if not messages or not isinstance(messages[0], SystemMessage):
            messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # ── Tool-execution node ───────────────────────────────────────────────
    async def tool_node(state: AgentState) -> dict:
        """Execute tool calls requested by the LLM."""
        last_message = state["messages"][-1]
        user_id = state["user_id"]
        tool_map = {t.name: t for t in ALL_TOOLS}
        results: list[ToolMessage] = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = dict(tool_call.get("args", {}))

            # Inject user_id into every tool call transparently
            tool_args["user_id"] = user_id

            fn = tool_map.get(tool_name)
            if fn is None:
                results.append(
                    ToolMessage(
                        content=f"Unknown tool: {tool_name}",
                        tool_call_id=tool_call["id"],
                    )
                )
                continue

            try:
                output = await fn.ainvoke(tool_args)
                results.append(
                    ToolMessage(content=str(output), tool_call_id=tool_call["id"])
                )
            except Exception as exc:
                logger.error("Tool %s failed: %s", tool_name, exc, exc_info=True)
                results.append(
                    ToolMessage(
                        content=f"Tool error: {exc}",
                        tool_call_id=tool_call["id"],
                    )
                )

        return {"messages": results}

    # ── Router function ───────────────────────────────────────────────────
    def should_continue(state: AgentState) -> str:
        """Route to tool_node if the LLM requested tools, else END."""
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "tools"
        return END

    # ── Build the graph ───────────────────────────────────────────────────
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")   # After tool execution, go back to agent

    return graph.compile()
