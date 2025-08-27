# 🔐 Agentic AI - NativeEdge Assistant

**NativeEdge Assistant** is an intelligent assistant that automates NativeEdge operations, powered by **Groq LLaMA3** and **LangGraph agents**. It understands natural language commands and dynamically selects the appropriate tool to execute operation securely.

![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-blueviolet)
![Groq LLaMA3](https://img.shields.io/badge/LLM-Groq%20LLaMA3-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)

---

## ✨ Features

- ⚙️ **Tool-Augmented Execution**: Supports SSH (command execution) and SCP (file downloads)
- 🧠 **Persistent Memory**: Remembers IPs, usernames, etc. using `MemorySaver` (SQLite-based)
- 🗣️ **Natural Language Commands**: Run commands like:
  > "Connect to ECE with IP, username , password and run `ls -ltr`"
- 🪄 **Automatic Tool Routing**: Automatically detects which tool to use
- 📥 **File Download Support**: Streamlit UI enables downloading SCP’d files
- 🔁 **Batch Mode**: Upload a file to process multiple requests in one go
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
│   └── utils.py
├── ui/
│   └── chat_ui.py
.env
README.md
requirements.txt
```

---

## 🤝 Contributions

Got a new tool to add or a feature idea? PRs welcome!

