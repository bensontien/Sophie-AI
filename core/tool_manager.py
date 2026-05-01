import asyncio
import subprocess
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Awaitable, List

# ==========================================
# 1. 抽象基礎類別 (Base Interface)
# ==========================================
class Tool(ABC):
    def __init__(self, name: str, description: str, schema: Dict[str, Any], category: str = "general"):
        self.name = name
        self.description = description
        self.schema = schema
        self.category = category # ✨ Added category property

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """所有工具都必須實作這個非同步執行方法"""
        pass

# ==========================================
# 2. 三大適配器 (Adapters)
# ==========================================

class SkillTool(Tool):
    """處理原生 Python 函數的工具 (例如: 時間計算、本地字串處理)"""
    def __init__(self, name: str, description: str, schema: Dict[str, Any], func: Callable[..., Awaitable[str]], category: str = "general"):
        super().__init__(name, description, schema, category)
        self.func = func

    async def execute(self, **kwargs) -> str:
        try:
            return await self.func(**kwargs)
        except Exception as e:
            return f"❌ Skill '{self.name}' execution failed: {e}"

class CLITool(Tool):
    """處理命令列/終端機指令的工具 (包含 Windows 安全防護機制)"""
    def __init__(self, name: str, description: str, schema: Dict[str, Any], is_windows: bool = False, category: str = "system_ops"):
        super().__init__(name, description, schema, category)
        self.is_windows = is_windows

    async def execute(self, command: str, **kwargs) -> str:
        cmd_lower = command.lower()
        
        # Windows PowerShell 的安全攔截器
        if self.is_windows:
            dangerous_keywords = ['remove-item ', 'del ', 'rmdir ', 'stop-computer', 'restart-computer', 'stop-process', 'kill ']
            if any(k in cmd_lower for k in dangerous_keywords):
                return "System Protection: Execution of potentially destructive commands is blocked."
            if 'format' in cmd_lower:
                safe_formats = ['format-table', 'format-list', 'format-wide', 'format-custom']
                if not any(s in cmd_lower for s in safe_formats):
                    return "System Protection: Disk formatting commands are strictly prohibited."

        print(f"[CLITool] 執行指令: {command}")
        
        def run_subprocess():
            # 依據平台選擇執行方式
            shell_cmd = ["powershell.exe", "-Command", command] if self.is_windows else command
            return subprocess.run(
                shell_cmd, 
                shell=not self.is_windows, 
                capture_output=True, 
                text=True, 
                timeout=15
            )

        try:
            # 使用 asyncio.to_thread 避免阻塞 FastAPI 的主執行緒
            result = await asyncio.to_thread(run_subprocess)
            if result.returncode == 0:
                output = result.stdout.strip()
                if len(output) > 3000:
                    output = output[:3000] + "\n...[Output Truncated]"
                return f"✅ Success:\n{output}"
            else:
                return f"❌ Error:\n{result.stderr.strip()}"
        except Exception as e:
            return f"❌ CLI execution failed: {str(e)}"

class MCPTool(Tool):
    """處理遠端 MCP Server 呼叫的工具"""
    def __init__(self, name: str, description: str, schema: Dict[str, Any], mcp_client, category: str = "general"):
        super().__init__(name, description, schema, category)
        self.mcp_client = mcp_client

    async def execute(self, **kwargs) -> str:
        try:
            # 轉交給 MCP Client 執行
            return await self.mcp_client.execute_tool(self.name, **kwargs)
        except Exception as e:
            return f"❌ MCP Tool '{self.name}' execution failed: {e}"

# ==========================================
# 3. 統一工具註冊表與大管家 (Registry & Manager)
# ==========================================
class ToolManager:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool):
        """註冊一個工具"""
        self._tools[tool.name] = tool
        print(f"[ToolManager] Registered {tool.__class__.__name__}: {tool.name} (Category: {tool.category})")

    def get_skill_catalog(self) -> str:
        """
        ✨ 回傳精簡的目錄給 Orchestrator
        動態收集目前所有註冊工具的分類
        """
        categories = set(t.category for t in self._tools.values())
        if not categories:
            return "No skill categories available."
            
        catalog_items = []
        for cat in categories:
            # You can expand this to load descriptions from MD files if preferred
            catalog_items.append(f"- **{cat}**: Contains tools related to {cat.replace('_', ' ')}.")
            
        return "\n".join(catalog_items)

    def get_schemas_by_category(self, category: str) -> str:
        """
        ✨ 只回傳特定分類的詳細工具說明，供 GenericAgent 使用
        """
        matched_tools = [t for t in self._tools.values() if t.category == category]
        if not matched_tools:
            return "No tools found for this category."
            
        schemas = [
            json.dumps({
                "name": t.name, 
                "description": t.description, 
                "schema": t.schema
            }, ensure_ascii=False) 
            for t in matched_tools
        ]
        return "\n".join(schemas)

    def get_all_schemas(self) -> str:
        """(Legacy/Fallback) 產出統一的工具說明書"""
        schemas = [
            json.dumps({
                "name": t.name, 
                "description": t.description, 
                "schema": t.schema
            }, ensure_ascii=False) 
            for t in self._tools.values()
        ]
        return "\n".join(schemas)

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    async def execute(self, tool_name: str, **kwargs) -> str:
        """大腦統一的執行入口"""
        if tool_name not in self._tools:
            return f"Error: Tool '{tool_name}' not found."
        
        tool_instance = self._tools[tool_name]
        print(f"\n⚙️ [ToolManager] Dispatching to {tool_instance.__class__.__name__}: {tool_name}")
        return await tool_instance.execute(**kwargs)