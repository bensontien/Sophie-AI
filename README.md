# Sophie AI Assistant

Sophie is a highly flexible, enterprise-grade AI assistant system based on a Microservices & Multi-Agent Architecture. It features autonomous task planning, dynamic agent generation, and Progressive Tool Disclosure, while strictly separating AI logic (Python Brain) from tool execution (MCP Muscle).

The system adopts a highly decoupled architecture: a Python brain driven by FastAPI, a tool server based on the Model Context Protocol (MCP), and a Prompts-as-Code design philosophy, allowing for real-time hot updates of LLM behavior via Markdown files.

## Core Features

*   **Dual-Track Orchestration**: Utilizes a main LLM (via OpenRouter or local vLLM) to decompose complex requirements. It can route standard workflows to "Specialized Agents" or dynamically generate "Generic Agents" for custom long-tail requirements.
*   **Unified Tool Management and MCP Support**: Uses the Model Context Protocol (MCP) for dynamic registration and invocation of tools. The ToolManager supports hierarchical routing, where agents first select a "Skill Category" (e.g., web_scraping, system_ops) and then dynamically load relevant tools, effectively saving context window and reducing hallucinations.
*   **Prompts-as-Code**: All system instructions, agent personas, and skill rules are extracted into Markdown files under the .sophie/ directory. This supports hot loading, version control, and ensures the purity of code logic.
*   **Brain-Muscle Architecture**:
    *   **Brain (Python Brain)**: Handles LLM orchestration, task planning, state management, and WebSocket streaming.
    *   **Muscle (MCP Server)**: A high-performance tool server implemented based on FastMCP, handling I/O intensive tasks such as web scraping, system operations (Windows PowerShell), and file downloads.
*   **Hybrid LLM Support**: Perfectly supports both local vLLM inference frameworks and OpenRouter cloud APIs, allowing for flexible switching based on task complexity and cost considerations.

## Architecture and Directory Structure

```text
Agents/
├── .sophie/                # Prompts-as-Code (Markdown configurations)
│   ├── agents/             # Personas for orchestrator and various agents
│   └── skills/             # Skill lists and usage specifications
│
├── agents/                 # Agent implementations (LlamaIndex Workflows)
│   ├── searchpaper_agent.py# Academic paper search agent
│   ├── translator_agent.py # PDF translation agent
│   ├── news_agent.py       # News analysis agent
│   └── generic_agent.py    # Generic task agent
│
├── core/                   # Core logic
│   ├── orchestrator.py     # Task decomposition and scheduling
│   ├── tool_manager.py     # Tool adapters (CLI, MCP)
│   └── mcp_client.py       # MCP server client
│
├── factorys/               # Factory pattern implementations
│   ├── agent_factory.py    # Agent generation factory
│   └── model_factory.py    # LLM model instance factory
│
├── sophie-ui/              # Frontend interface (React + Vite)
│
├── server.py               # Main FastAPI backend entry point
├── tools_server.py         # MCP tool server
└── config.py               # System configuration management
```

## Quick Start

### 1. Configure Environment Variables
Create a .env file in the root directory and fill in your API keys and model configurations:

```env
# OpenRouter Configuration
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL_NAME=google/gemma-2-9b-it

# Local vLLM Configuration (Optional)
DEFAULT_LOCAL_MODEL_PATH=/path/to/model
VLLM_API_BASE=http://localhost:8000/v1
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Services

**Step A: Start the Main Backend Service**
This starts the FastAPI server and automatically mounts tools_server.py as a background MCP process.
```bash
uvicorn server:app --host 0.0.0.0 --port 8080
```

**Step B: Start the Frontend Interface**
```bash
cd sophie-ui
npm install
npm run dev
```

## Development and Extension

### How to Add a New Tool
1.  Define the new functionality using the @mcp.tool() decorator in tools_server.py.
2.  Update the tool description in .sophie/skills/catalog.md.
3.  If specific safety rules are required, create a corresponding Markdown file under .sophie/skills/.

### How to Add a Specialized Agent
1.  Create a new Workflow class in the agents/ directory, referencing existing agents (like news_agent.py).
2.  Define the agent's persona.md under .sophie/agents/.
3.  Register the agent in factorys/agent_factory.py so the orchestrator can call it.

---

## License
This project is licensed under the MIT License.
