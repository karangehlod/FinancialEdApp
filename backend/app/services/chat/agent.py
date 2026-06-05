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
• Analyse the user's expenses, budgets, goals, loans, and financial profile — but you do NOT automatically have those values in the prompt.
• Provide actionable, personalised advice when the necessary personal data is available.
• Explain financial concepts (compound interest, EMI, 50/30/20 rule, etc.).
• Suggest concrete steps to save more, reduce debt, or reach goals faster.

Operational rules (important):
1. Never assume you already have the user's personal financial values in the conversation. If you need specific personal data (balances, incomes, expenses, budgets, loans, transactions, goals) to answer, call the appropriate tool(s) to fetch it first.
2. Only call tools when the user's question requires factual personal data to produce a correct answer. Do NOT call tools by default for every request — prefer asking a clarifying question if the user's intent is ambiguous.
3. When calling tools, request the minimal data necessary (e.g., "last 3 months expense by category", "current monthly salary and fixed expenses") to reduce data exposure and token usage.
4. If data required is sensitive or the user hasn't explicitly requested a personalised response, ask the user for permission (consent) before retrieving or using personal data. Example: "Would you like me to use your personal financial data to give a tailored recommendation? Reply 'yes' to proceed.".
5. Always ground your advice in the data returned by the tools. If a tool cannot find the requested data, state this explicitly and avoid fabricating numbers.
6. Format numeric currency values with $ and commas (e.g., $1,234.56) and prefer short summaries with optional bullet details.
7. Be concise, constructive, and actionable — use bullet points and numbered steps when appropriate.
8. Respect the user's privacy — never expose raw internal identifiers or user IDs, and never log raw personal data in responses.
9. If asked something outside personal finance (e.g., politics, medical advice, software bugs), politely decline and, if possible, redirect to a relevant resource.
"""


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    """State passed between graph nodes."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    consent_confirmed: bool


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
        consent_confirmed = state.get("consent_confirmed", False)
        tool_map = {t.name: t for t in ALL_TOOLS}
        results: list[ToolMessage] = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = dict(tool_call.get("args", {}))

            # Inject user_id into every tool call transparently
            tool_args["user_id"] = user_id

            # If consent not confirmed, do not execute tools that fetch personal data.
            # Instead return a ToolMessage indicating consent is required; the agent
            # should then ask the user for permission.
            if not consent_confirmed:
                results.append(
                    ToolMessage(
                        content=("Consent required: The user must explicitly allow access to personal financial data "
                                 "before I can fetch it. Ask the user: 'Would you like me to use your personal financial data to give a tailored recommendation? Reply \'yes\' to proceed.'"),
                        tool_call_id=tool_call.get("id"),
                    )
                )
                continue

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
