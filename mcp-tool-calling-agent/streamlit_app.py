"""
streamlit_app.py
----------------
Streamlit web UI for the ACME Technologies MCP Tool-Calling Agent.

Run:
    streamlit run streamlit_app.py

Features:
    - Chat interface with conversation history
    - User role selector (employee / manager / admin)
    - Shows which tool was called and which data source was used
    - Shows demo/Databricks mode indicator
    - Shows permission status
"""

import json
import os

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ACME Technologies AI Assistant",
    page_icon="🤖",
    layout="wide",
)

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []      # list of {"role", "content", "metadata"}
if "graph" not in st.session_state:
    st.session_state.graph = None
if "agent_ready" not in st.session_state:
    st.session_state.agent_ready = False
if "agent_error" not in st.session_state:
    st.session_state.agent_error = None


# ── Helper: initialise agent ──────────────────────────────────────────────────
@st.cache_resource(show_spinner="Initialising AI agent...")
def load_agent():
    from mcp_client import MCPClient
    from agent.graph import build_graph, get_llm
    client = MCPClient()
    tools  = client.get_tools()
    llm    = get_llm(tools)
    graph  = build_graph(llm, client)
    return graph, client


def run_agent(question: str, user_role: str):
    """Run one question through the LangGraph agent and return result dict."""
    graph, _ = load_agent()
    result = graph.invoke({
        "messages":          [HumanMessage(content=question)],
        "user_role":         user_role,
        "tool_results":      [],
        "final_answer":      None,
        "error":             None,
        "permission_denied": False,
    })
    return result


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    mode_label = "🟢 DEMO MODE (Local CSV)" if demo_mode else "🔵 Databricks Mode"
    st.info(mode_label)

    st.markdown("---")
    user_role = st.selectbox(
        "Your Role",
        options=["employee", "manager", "admin"],
        index=0,
        help=(
            "employee: general info only\n"
            "manager: + team details\n"
            "admin: full access"
        ),
    )

    st.markdown("---")
    st.markdown("**Example Questions**")
    examples = [
        "Who works in the AI department?",
        "What projects are currently active?",
        "Who works in AI and what projects are they on?",
        "Who works in Security and what are the security policies?",
        "What is the company leave policy?",
        "What are the password requirements?",
        "Show restricted salary information.",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["prefill"] = ex

    st.markdown("---")
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption("Half 2 — MCP + LangGraph + Vector Search")


# ── Main panel ────────────────────────────────────────────────────────────────
st.title("🤖 ACME Technologies AI Assistant")
st.caption(
    "Ask questions about employees, departments, projects, and company policies. "
    "The agent uses MCP tools and LangGraph to retrieve real data."
)

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        meta = msg.get("metadata")
        if meta:
            with st.expander("ℹ️ Details", expanded=False):
                cols = st.columns(3)
                cols[0].metric("Tool Used", meta.get("tool", "—"))
                cols[1].metric("Data Source", meta.get("source", "—"))
                cols[2].metric("Permission", "✅ Granted" if meta.get("permission_ok") else "❌ Denied")


# Chat input — honour example button prefill
prefill = st.session_state.pop("prefill", "")
user_input = st.chat_input("Ask a question...", key="chat_input")
question = prefill or user_input

if question:
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": question, "metadata": None})
    with st.chat_message("user"):
        st.markdown(question)

    # Run agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = run_agent(question, user_role)
            except ValueError as e:
                st.error(str(e))
                st.info("Add your API key to the `.env` file and restart.")
                st.stop()
            except Exception as e:
                st.error(f"Agent error: {e}")
                st.stop()

        # Extract answer
        answer = result.get("final_answer") or ""
        if not answer:
            for m in reversed(result.get("messages", [])):
                if hasattr(m, "content") and m.content and not hasattr(m, "tool_call_id"):
                    answer = str(m.content)
                    break
        if not answer:
            answer = "I was unable to generate an answer. Please try rephrasing your question."

        st.markdown(answer)

        # Extract tool metadata for display
        tool_records = result.get("tool_results", [])
        meta = None
        if tool_records:
            last = tool_records[-1]
            meta = {
                "tool":          last.get("tool", "—"),
                "source":        last.get("source", "—"),
                "permission_ok": last.get("permission_ok", True),
            }
            all_tools  = list({r.get("tool", "") for r in tool_records})
            all_sources = list({r.get("source", "") for r in tool_records})

            with st.expander("ℹ️ Details", expanded=True):
                cols = st.columns(3)
                cols[0].metric("Tools Used", ", ".join(all_tools) if all_tools else "—")
                cols[1].metric("Data Source", ", ".join(all_sources) if all_sources else "—")
                perm_status = "✅ Granted" if all(r.get("permission_ok", True) for r in tool_records) else "❌ Denied"
                cols[2].metric("Permission", perm_status)
        elif result.get("permission_denied"):
            meta = {"tool": "—", "source": "permission_denied", "permission_ok": False}
            with st.expander("ℹ️ Details", expanded=True):
                st.warning("Permission denied for this role.")

    # Save to history
    st.session_state.messages.append({
        "role":     "assistant",
        "content":  answer,
        "metadata": meta,
    })
