import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from factorys.agent_factory import AgentFactory
from core.registry import NodeRegistry
from core.orchestrator import SophieOrchestrator
from core.memory import MemoryManager
from core.mcp_client import SophieMCPClient
from core.tool_manager import ToolManager, CLITool, MCPTool

# ==========================================
# Define API Request and Response data structures
# ==========================================
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: Optional[str] = None
    news_report: Optional[str] = None
    search_report_file: Optional[str] = None
    translated_file: Optional[str] = None
    current_phase: str
    status: str = "success"

# ==========================================
# Prepare global variables
# ==========================================
sophie_orchestrator = None
session_memories = {} 
tool_manager = ToolManager()
mcp_client = SophieMCPClient(server_script_path="tools_server.py")

# ==========================================
# Define the unified Lifespan context manager
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global sophie_orchestrator, mcp_client, tool_manager
    llm_type='external' 
    
    # --- Startup Phase ---
    print("[Server] Initiating startup sequence...")
    
    # 1. Start the MCP Client process 
    await mcp_client.start()
    
    # 2. Register all available tools into the ToolManager
    # A. Register CLI tools
    tool_manager.register_tool(CLITool(
        name="execute_windows_command",
        description="Execute a command in the host Windows PowerShell from WSL. Use this to check system status, open apps, or read files.",
        schema={
            "properties": {"command": {"type": "string", "description": "PowerShell command to execute"}},
            "required": ["command"]
        },
        is_windows=True,
        category="system_ops" # ✨ Added category assignment
    ))
    
    # B. Register MCP tools dynamically
    if mcp_client.session:
        mcp_tools = await mcp_client.session.list_tools() 
        for t in mcp_tools.tools:
            # We assign a default category or derive it if your MCP server provides it
            # For now, we'll assign web-related tools to 'web_scraping'
            cat = "web_scraping" if "fetch" in t.name or "scrape" in t.name else "general"
            
            tool_manager.register_tool(MCPTool(
                name=t.name,
                description=t.description,
                schema=t.inputSchema,
                mcp_client=mcp_client,
                category=cat # ✨ Added category assignment
            ))      
            
    # 3. Initialize Factory and LLMs
    factory = AgentFactory() 
    orchestrator_llm = factory.get_llm(llm_type) 
    
    # 4. Inject dependencies into Agents
    search_agent = factory.get_agent('SearchPaperAgent', llm_type=llm_type)
    translator_agent = factory.get_agent('PDFTranslatorAgent', timeout=3600, llm_type='translator')
    news_agent = factory.get_agent('NewsAgent', llm_type=llm_type, tool_manager=tool_manager) 
    chat_agent = factory.get_agent('ChatAgent', llm_type=llm_type) 
    
    # 5. Create wrapper for standalone tools
    async def download_pdf_wrapper(state):
        url = state.top_paper.url 
        filename = state.top_paper.title
        result = await tool_manager.execute("download_pdf", url=url, filename=filename)
        state.chat_reply = result
        return state

    # 6. Build the Registry
    registry = NodeRegistry()
    registry.register("SearchPaperAgent", "Used for searching academic papers...", search_agent.run)
    registry.register("DownloadTool", "Used to attempt downloading PDF files.", download_pdf_wrapper)
    registry.register("TranslatorAgent", "Translate PDF files...", translator_agent.run)
    registry.register(
        "NewsAgent", 
        "Use ONLY when the user wants to SEARCH for general news, trends, or updates on a broad topic. DO NOT use this agent if the user provides a specific URL to read or scrape.", 
        news_agent.run
    )
    registry.register("ChatAgent", "General daily conversation...", chat_agent.run)
    
    # 7. Initialize the Orchestrator
    sophie_orchestrator = SophieOrchestrator(llm=orchestrator_llm, registry=registry, tool_manager=tool_manager)
    print("[Server] Sophie 2.0 API startup complete!")
    
    # --- Yield control back to FastAPI ---
    yield
    
    # --- Shutdown Phase ---
    print("[Server] Initiating shutdown sequence...")
    await mcp_client.stop()
    print("[Server] Shutdown complete.")

# ==========================================
# Create FastAPI instance
# ==========================================
app = FastAPI(title="Sophie 2.0 API", version="1.0.0", lifespan=lifespan)

# Setup CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# WebSocket Endpoint
# ==========================================
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    global sophie_orchestrator, session_memories
    
    await websocket.accept()
    print("[WebSocket] Frontend connected!")
    
    # Helper function to get memory for a specific conversation
    def get_memory(session_id: str):
        if session_id not in session_memories:
            orchestrator_llm = AgentFactory().get_llm('external')
            session_memories[session_id] = MemoryManager(llm=orchestrator_llm, max_recent_turns=4)
        return session_memories[session_id]
    
    try:
        while True:
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            session_id = request_data.get("session_id", "default")
            user_message = request_data.get("message", "").strip()
            
            if not user_message:
                continue
                
            # Get the exclusive memory for the current chat room
            current_memory = get_memory(session_id)
            
            # Tell the frontend: message received
            await websocket.send_json({
                "type": "status", 
                "content": "Thinking and planning...",
                "session_id": session_id
            })
            
            current_memory.add_turn("User", user_message)
            context_str = await current_memory.get_context_and_compress()
            
            await websocket.send_json({
                "type": "status", 
                "content": "Executing task, please wait...",
                "session_id": session_id
            })
            
            # Execute time-consuming task
            final_state = await sophie_orchestrator.execute_task(user_message, memory_context=context_str)
            
            # Task complete, push final result and session_id to frontend
            response_payload = {
                "type": "result",
                "reply": final_state.chat_reply,
                "news_report": final_state.news_report,
                "search_report_content": getattr(final_state, "search_report_content", None),
                "search_report_file": final_state.search_report_file,
                "translated_file": final_state.final_translated_file,
                "current_phase": final_state.current_phase,
                "session_id": session_id
            }
            await websocket.send_json(response_payload)
            
            # Save the result into the exclusive memory
            assistant_reply_summary = []
            if final_state.chat_reply:
                assistant_reply_summary.append(final_state.chat_reply[:30] + "...")
            if final_state.news_report:
                assistant_reply_summary.append("Provided a news report.")
            if final_state.top_paper:
                assistant_reply_summary.append(f"Targeted paper: {final_state.top_paper.title}")
            current_memory.add_turn("Sophie", " ".join(assistant_reply_summary))

    except WebSocketDisconnect:
        print("[WebSocket] Frontend disconnected.")
    except Exception as e:
        print(f"[WebSocket Error] {e}")