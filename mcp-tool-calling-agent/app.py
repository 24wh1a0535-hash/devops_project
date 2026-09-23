"""
app.py
------
Main entry point for the MCP Tool-Calling AI Agent.

Run:
    python app.py

This starts an interactive command-line session where you can ask questions
about ACME Technologies employees, departments, projects, and policies.

The flow is:
    User question → LangGraph agent → MCP client → Tool functions → Data → Answer
"""

import logging
import os
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

# ---- Logging ----------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_agent():
    """
    Initialize the MCP client, build the LangGraph, and return the compiled graph.
    """
    from mcp_client import MCPClient
    from agent.graph import build_graph, get_llm

    # 1. Initialize MCP client (discovers and wraps tools)
    mcp_client = MCPClient()
    tools = mcp_client.get_tools()
    logger.info("MCP tools loaded: %s", [t.name for t in tools])

    # 2. Initialize LLM and bind tools
    llm_with_tools = get_llm(tools)
    logger.info("LLM initialized with %d tools", len(tools))

    # 3. Build LangGraph
    graph = build_graph(llm_with_tools, mcp_client)
    logger.info("LangGraph compiled successfully")

    return graph


def run_query(graph, question: str, user_role: str = "employee") -> str:
    """
    Run a single question through the agent graph.

    Args:
        graph: Compiled LangGraph runnable.
        question: The user's question.
        user_role: The user's access role (employee/manager/admin).

    Returns:
        The agent's final answer as a string.
    """
    initial_state = {
        "messages": [HumanMessage(content=question)],
        "user_role": user_role,
        "tool_results": [],
        "final_answer": None,
        "error": None,
    }

    result = graph.invoke(initial_state)

    if result.get("error"):
        return f"Error: {result['error']}"

    if result.get("final_answer"):
        return result["final_answer"]

    # Fallback: get last AI message content
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_call_id"):
            return str(msg.content)

    return "No answer was generated."


def main():
    """Interactive CLI for the MCP agent."""
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    print("=" * 60)
    print("  ACME Technologies AI Assistant")
    print("  MCP Tool-Calling Agent (Half 1 - Local Demo)")
    print("=" * 60)
    print(f"  DEMO_MODE: {'ON (using local CSV files)' if demo_mode else 'OFF (Databricks)'}")
    print()

    # Initialize agent
    print("Initializing agent...")
    try:
        graph = create_agent()
    except ValueError as e:
        print(f"\nConfiguration error: {e}")
        print("\nSetup steps:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your OPENAI_API_KEY (or ANTHROPIC_API_KEY) to .env")
        print("  3. Run: python app.py")
        sys.exit(1)

    print("Agent ready!\n")
    print("Example questions:")
    print("  - Who works in the AI department?")
    print("  - What projects are currently active?")
    print("  - Who works in the AI department and what projects are they on?")
    print("  - How many days of annual leave do I get?")
    print("  - What are the password requirements?")
    print()
    print("Type 'quit' or 'exit' to stop.")
    print("-" * 60)

    # Default role for CLI demo
    user_role = os.getenv("USER_ROLE", "employee")
    print(f"Current user role: {user_role}")
    print()

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue

        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if question.lower().startswith("/role "):
            user_role = question.split(" ", 1)[1].strip().lower()
            print(f"Role changed to: {user_role}\n")
            continue

        print("Agent: ", end="", flush=True)
        answer = run_query(graph, question, user_role)
        print(answer)
        print()


if __name__ == "__main__":
    main()
