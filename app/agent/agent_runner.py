import json
import uuid
from typing import Annotated

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import ChatOllama

from app.tools.openapi_tool import openapi_tool
from app.tools.ssh_tool import ssh_tool
from app.tools.scp_tool import scp_tool
from app.tools.utils import ToolResponse
from app.common.logger import logger

# Load environment variables
load_dotenv()

thread_id = str(uuid.uuid4())

# ==== SYSTEM PROMPT ====
ROUTER_PROMPT = """
You are a router agent. Your only job is to decide which specialized agent should handle the user request.

Options:
- "remote" → if request involves SSH commands or SCP file operations.
- "openapi" → if request involves APIs, endpoints, tokens, specifications, deployment.
- "chat" → if request doesnt match for "remote" or "openapi" and it is normal conversation

Return ONLY one of: remote, openapi, chat
"""

# ==== LLM ====
llm = ChatGroq(temperature=0, model="llama3-70b-8192")


# ==== SUB-AGENTS ====
remote_agent = create_react_agent(llm, [ssh_tool, scp_tool])
openapi_agent = create_react_agent(llm, [openapi_tool])

# ==== STATE ====
class AgentState(BaseModel):
    messages: Annotated[list, add_messages]
    route: str | None = None   # <-- store router decision here

# ==== MEMORY ====
memory = MemorySaver()

# ==== ROUTER NODE ====
def router_node(state: AgentState, config: RunnableConfig):
    """LLM-based router that picks remote, openapi, or chat"""

    # Get only the raw user text
    user_msg = next((m.content for m in reversed(state.messages) if isinstance(m, HumanMessage)), "")

    router_messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=user_msg)   # <-- only raw text
    ]

    decision = llm.invoke(router_messages).content.strip().lower()
    logger.info(f"🤖 Router decision (raw): {decision}")

    # Normalize routing
    if "remote" in decision or "ssh" in decision or "scp" in decision:
        route = "remote"
    elif "api" in decision or "openapi" in decision or "endpoint" in decision:
        route = "openapi"
    else:
        route = "chat"

    return AgentState(messages=state.messages, route=route)


# ==== CHAT NODE ====
def chat_node(state: AgentState, config: RunnableConfig):
    """Fallback normal chat with LLM"""
    user_msg = next((m.content for m in reversed(state.messages) if isinstance(m, HumanMessage)), "")
    response = llm.invoke([HumanMessage(content=user_msg)])
    logger.info(f"💬 Chat response: {response.content}")
    return AgentState(messages=state.messages + [AIMessage(content=response.content)], route="chat")


# ==== GRAPH ====
graph = StateGraph(AgentState)

graph.add_node("router", router_node)
graph.add_node("remote", remote_agent)
graph.add_node("openapi", openapi_agent)
graph.add_node("chat", chat_node)

# now use state.route instead of .get
graph.add_conditional_edges(
    "router",
    lambda state: state.route,
    {"remote": "remote", "openapi": "openapi", "chat": "chat"}   # added chat
)

graph.set_entry_point("router")
graph.set_finish_point("remote")
graph.set_finish_point("openapi")
graph.set_finish_point("chat")

app_flow = graph.compile(checkpointer=memory)

# ==== RUNNER ====
def run_agent(user_input: str | dict, base_url: str = None) -> dict:
    prompt_text = user_input.get("prompt", "")
    base_url_to_use = user_input.get("base_url", base_url or "")
    fields = user_input.get("fields", {})

    prompt = (
       "The user wants to perform a task using these details:\n"
       f"{json.dumps({'prompt': prompt_text, 'base_url': base_url_to_use, 'fields': fields}, indent=2)}"
    )

    logger.info("🟢 User Input: %s", prompt)

    messages = [HumanMessage(content=prompt)]

    result = app_flow.invoke(
        input=AgentState(messages=messages),
        config=RunnableConfig(configurable={
            "thread_id": thread_id,
            "base_url": base_url_to_use,
            "fields": fields  # downstream agents can use these
        })
    )

    logger.info("🧠 Agent Response Trace:")
    for msg in result.get("messages", []):
        logger.info("  🔹 %s: %s", type(msg).__name__, getattr(msg, "content", str(msg)))

    tool_response = "[No tool response]"
    file_name = None
    api_request = None
    api_response = None
    missing_fields = {"url_fields": [], "payload_fields": []}

    for m in reversed(result.get("messages", [])):
        if isinstance(m, ToolMessage):
            try:
                parsed = ToolResponse.parse_raw(m.content)
                tool_response = parsed.return_message or tool_response
                file_name = parsed.filename
                api_request = parsed.api_request
                api_response = parsed.api_response
                if parsed.missing_fields and isinstance(parsed.missing_fields, dict):
                    missing_fields = parsed.missing_fields
                break
            except Exception as e:
                tool_response = f"[Tool Output Parsing Error] {e}\nRaw: {m.content}"
                logger.error("❌ Failed to parse tool output: %s", e)
                break

    final_ai_message = next(
        (m.content for m in reversed(result.get("messages", [])) if isinstance(m, AIMessage)),
        "[No response]"
    )

    return {
        "llm_response": str(final_ai_message),
        "tool_response": tool_response,
        "file_name": file_name,
        "api_request": api_request,
        "api_response": api_response,
        "missing_fields": missing_fields
    }
