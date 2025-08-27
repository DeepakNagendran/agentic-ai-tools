# chat_ui.py
# Streamlit UI for the Agentic AI LangGraph project
# - Sidebar "Base URL"
# - Chat messages using app.agent.agent_runner.run_agent
# - Dynamic missing-fields inputs if tool returns `missing_fields`
# - Shows API request/response and downloaded file links

import os
import json
from pathlib import Path
import streamlit as st
from app.common.logger import logger

# --- Imports from your repo ---
# Project layout in zip: agentic-ai-tool/app/agent/agent_runner.py
# When this file sits at the repo root, the following import works:
try:
    from app.agent.agent_runner import run_agent  # def run_agent(user_input: str|dict, base_url: str=None) -> dict
except Exception as e:
    st.stop()  # Fail fast so error is visible
    raise

# ---------- Session State ----------
def _init_state():
    st.session_state.setdefault("history", [])           # list[{"role": "user"|"assistant", "content": str}]
    st.session_state.setdefault("pending_fields", None)  # list[str] or None
    st.session_state.setdefault("last_task_prompt", "")  # str (the natural language intent used when fields are requested)
    st.session_state.setdefault("collected_values", {})  # dict for partially filled fields

_init_state()

# ---------- Sidebar ----------
st.sidebar.header("API Configuration")
default_base = os.environ.get("BASE_URL", "https://example.com/")
base_url = st.sidebar.text_input("Base URL", value=st.session_state.get("base_url", default_base), placeholder="https://example.com/")
st.session_state["base_url"] = base_url

with st.sidebar.expander("Session"):
    if st.button("Reset conversation", use_container_width=True):
        for k in ["history", "pending_fields", "last_task_prompt", "collected_values"]:
            st.session_state.pop(k, None)
        _init_state()
        st.rerun()

# ---------- Title ----------
st.title("💬 Agentic AI Assistant")

# ---------- Helpers ----------
def render_agent_result(result: dict):
    """
    Renders one assistant turn using the dict returned by run_agent(...).
    """
    llm_text = (result or {}).get("llm_response") or ""
    tool_text = (result or {}).get("tool_response") or ""
    file_name = (result or {}).get("file_name")
    api_req   = (result or {}).get("api_request")
    api_resp  = (result or {}).get("api_response")
    missing   = (result or {}).get("missing_fields")
    logger.info("Missing fields received to UI: %s", missing)

    with st.chat_message("assistant"):
        if missing:
            st.session_state["pending_fields"] = missing
        else:
            st.session_state["pending_fields"] = None

        if llm_text:
            st.markdown(llm_text)

        if tool_text and tool_text.strip() != "[No tool response]":
            st.markdown("**Tool:**")
            st.code(tool_text)

        if api_req:
            with st.expander("API Request"):
                st.json(api_req)

        if api_resp is not None:
            with st.expander("API Response"):
                if api_resp is not None:
                    st.json(api_resp)

        if file_name and Path(file_name).exists():
            try:
                data = Path(file_name).read_bytes()
                st.download_button(
                    label=f"Download: {Path(file_name).name}",
                    data=data,
                    file_name=Path(file_name).name
                )
            except Exception as e:
                st.warning(f"File produced but not readable: {file_name} ({e})")




def call_agent_with_prompt(prompt: str):
    """
    Calls agent with a plain prompt (no fields).
    """
    payload = {"prompt": prompt, "base_url": st.session_state["base_url"], "fields": {}}
    result = run_agent(payload, base_url=st.session_state["base_url"])
    # ✅ update pending_fields immediately
    if isinstance(result.get("missing_fields"), dict) and any(result["missing_fields"].values()):
        st.session_state["pending_fields"] = result["missing_fields"]
    render_agent_result(result)
    return result


def call_agent_with_fields(prompt: str, fields: dict):
    """
    Calls agent with structured input including missing fields.
    """
    payload = {
        "prompt": prompt,
        "base_url": st.session_state["base_url"],
        "fields": fields or {}
    }
    result = run_agent(payload, base_url=st.session_state["base_url"])
    # ✅ update pending_fields immediately
    if isinstance(result.get("missing_fields"), dict) and any(result["missing_fields"].values()):
        st.session_state["pending_fields"] = result["missing_fields"]
    render_agent_result(result)
    return result

# ---------- Show history so far ----------
for msg in st.session_state["history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])



# ---------- Chat input ----------
user_msg = st.chat_input("Enter your task or API prompt…")
if user_msg:
    # Add the user's message to the transcript first
    st.session_state["history"].append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.markdown(user_msg)

    # If there are pending fields, treat this as normal chat (not field values).
    # The tool will likely continue asking for fields, so we remember this as the last task.
    st.session_state["last_task_prompt"] = user_msg

    # Call agent with plain prompt first
    result = call_agent_with_prompt(user_msg)

    # Record the agent's natural reply text into history for continuity
    st.session_state["history"].append({
        "role": "assistant",
        "content": (result or {}).get("llm_response", "")
    })

# ---------- Dynamic Missing Fields UI ----------
pending = st.session_state.get("pending_fields") or {}
has_missing = any(fields for fields in pending.values() if fields)

if has_missing:
    st.info("The tool needs some values before it can proceed.")
    logger.info("Into the missing display")
    st.caption(f"Last task: {st.session_state.get('last_task_prompt','')}")

    with st.form("missing_fields_form", clear_on_submit=False):
        values = {}
        missing = st.session_state["pending_fields"]

        for category, fields in missing.items():
            if not fields:
                continue
            st.subheader(f"Missing {category.replace('_', ' ').title()}")
            for field in fields:
                key = f"{category}.{field}"
                default_val = st.session_state["collected_values"].get(key, "")
                values[key] = st.text_input(
                    label=f"{field} (required)",
                    value=default_val,
                    key=f"mf_{category}_{field}"
                )

        submitted = st.form_submit_button("Submit required fields")
        if submitted:
            # merge new values into collected_values
            st.session_state["collected_values"].update(values)

            # ✅ build structured dict {url_fields:{}, payload_fields:{}}
            structured = {"url_fields": {}, "payload_fields": {}}
            for k, v in st.session_state["collected_values"].items():
                if "." in k:
                    cat, fld = k.split(".", 1)
                    structured.setdefault(cat, {})[fld] = v

            result = call_agent_with_fields(
                st.session_state["last_task_prompt"],
                structured
            )
            st.session_state["history"].append({
                "role": "assistant",
                "content": (result or {}).get("llm_response", "") or
                           f"Submitted required fields: {list(values.keys())}"
            })
