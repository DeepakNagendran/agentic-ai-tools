# 🔐 Agentic AI - Assistant

This project provides an **Agentic AI assistant** built with **LangGraph** and **LangChain**.  
The assistant integrates multiple tools into a single agent, allowing it to execute:

- **SSH commands** on remote systems
- **SCP file transfers**
- **OpenAPI-based API requests** (automatically parsing OpenAPI specifications, constructing payloads, and making authenticated requests)

![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-blueviolet)
![Groq LLaMA3](https://img.shields.io/badge/LLM-Groq%20LLaMA3-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)

---

## ✨ Features

- ⚙️ **Tool-Augmented Execution**: Supports SSH (command execution) and SCP (file downloads)
- 🧠 **Persistent Memory**: Remembers IPs, usernames, etc. using `MemorySaver` (SQLite-based)
- 🗣️ **Natural Language Commands**: Run commands like:
  > "ssh to Device with IP, and run `ls -ltr`"
  > "scp to Device with IP, and download the file `abs filepath`"
- 🪄 **Automatic Tool Routing**: Automatically detects which tool to use
- 📥 **File Download Support**: Streamlit UI enables downloading SCP’d files
- 🔁 **OpenAPI spec parsing**: from local files (`app/openapi/`)
- ✅ **Automatic API request construction** with placeholder replacement
- 💬 **Interactive Chat UI**: Built with Streamlit, includes avatars, message history, and downloads
- 🧾 **Structured Tool Response**: JSON format with `return_message`, `filename`, and `base64` encoded data
- 📜 **Detailed Logging**: Tracks user input, tool calls, responses, and errors

---

## 🧠 Architecture

```
User ⇨ Streamlit Chat UI
         ⇩
   Natural Language Input
         ⇩
     LangGraph Agent (LLaMA3 + Tools)
        ↙        ↘
 Tool 1  ... Tool N
        ↘        ↙
     Tool Response (Structured JSON)
         ⇩
   MemorySaver (SQLite thread memory)
         ⇩
   Response + Optional Download
```

---

## 🚀 Getting Started

### 📦 Prerequisites

- Python 3.10+
- SSH/SCP accessible systems
- Groq API key (sign up at [groq.com](https://groq.com/))
- Streamlit
- Dependencies from `requirements.txt`

### 🔧 Installation

```bash
# Clone this repo
git clone https://github.com/your-username/agentic-ai-ne-assistant.git
cd agentic-ai-ne-assistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
touch .env
```

Update `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
```

---

## ▶️ Running the App

```bash
export PYTHONPATH=$(pwd)
streamlit run app/ui/chat_ui.py
```

---

## 📁 Directory Structure

```
app/
├── agent/
│   ├── agent_runner.py
│   └── alias.py
├── tools/
│   ├── ssh_tool.py
│   ├── scp_tool.py
│   ├── openapi_tool.py
│   └── utils.py
├── common/
│   ├──logger.py
│   └── parser.py
├── ui/
│   └── chat_ui.py
├── openapi/
│   └── OpenAPI spec yaml files
├── configs/
│   ├── server_client_secret.json
│   └── device_credential.json
.env
README.md
requirements.txt
```

---

## 🤝 Contributions

Got a new tool to add or a feature idea? PRs welcome!