"""
graph.py
--------
Builds and compiles the LangGraph agent graph.

Graph flow:
    START → call_llm → [tool_calls?] → tool_executor → call_llm → ... → END

The agent loops: LLM calls tools → gets results → LLM answers.
When the LLM produces a message with no tool_calls, the graph ends.
"""

import logging
import os
from functools import partial

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage

from agent.state import AgentState
from agent.nodes import call_llm_node, tool_node

load_dotenv()
logger = logging.getLogger(__name__)


def _should_continue(state: AgentState) -> str:
    """
    Edge function: decide what to do after the LLM responds.

    If the last AI message has tool calls → go to 'tools' node.
    If the LLM gave a final answer (no tool calls) → go to END.
    If there was an error → go to END.
    """
    if state.get("error"):
        return END

    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return END


def build_graph(llm_with_tools, mcp_client):
    """
    Build and compile the LangGraph agent.

    Args:
        llm_with_tools: A LangChain chat model already bound with tool schemas.
        mcp_client: An MCPClient instance for calling MCP tools.

    Returns:
        A compiled LangGraph runnable.
    """
    # Create partial functions that close over llm and mcp_client
    llm_node = partial(call_llm_node, llm_with_tools=llm_with_tools)
    mcp_tool_node = partial(tool_node, mcp_client=mcp_client)

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("call_llm", llm_node)
    workflow.add_node("tools", mcp_tool_node)

    # Add edges
    workflow.add_edge(START, "call_llm")

    # Conditional edge: after LLM, either call tools or end
    workflow.add_conditional_edges(
        "call_llm",
        _should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )

    # After tools, always go back to LLM to process results
    workflow.add_edge("tools", "call_llm")

    return workflow.compile()


def get_llm(tools: list):
    """
    Initialize and return the LLM, bound with tool schemas.

    Reads LLM_PROVIDER from environment. Supports:
        - openrouter  (OpenAI-compatible, many models via one API key)
        - openai      (direct OpenAI API)
        - anthropic   (direct Anthropic API)

    Args:
        tools: List of LangChain tool objects to bind to the LLM.

    Returns:
        A LangChain chat model bound with tools.

    Raises:
        ValueError: If the provider is unsupported or API key is missing.
    """
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
    model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key or api_key == "your-openrouter-api-key-here":
            raise ValueError(
                "OPENROUTER_API_KEY is not set.\n"
                "Steps to fix:\n"
                "  1. Open .env\n"
                "  2. Set OPENROUTER_API_KEY=your-actual-key\n"
                "  3. Get a key at https://openrouter.ai/keys"
            )
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=model,
            temperature=0,
            api_key=api_key,
            base_url=base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/acme-mcp-agent",
                "X-Title": "ACME MCP Tool-Calling Agent",
            },
        )

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or api_key == "your-openai-api-key-here":
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Copy .env.example to .env and add your API key."
            )
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model, temperature=0, api_key=api_key)

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key or api_key == "your-anthropic-api-key-here":
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Copy .env.example to .env and add your API key."
            )
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=model, temperature=0, api_key=api_key)

    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. "
            "Use 'openrouter', 'openai', or 'anthropic'."
        )

    return llm.bind_tools(tools)
