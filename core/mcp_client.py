import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class SophieMCPClient:
    def __init__(self, server_script_path: str = "tools_server.py"):
        self.server_script_path = server_script_path
        self.exit_stack = AsyncExitStack()
        self.session = None

    async def start(self):
        """Establish standard I/O connection with the MCP server and initialize the session"""
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path]
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        print("[MCP Client] Successfully connected to tools_server")

    async def execute_tool(self, tool_name: str, **kwargs) -> str:
        """直接呼叫遠端工具"""
        if not self.session:
            raise RuntimeError("MCP Client is not initialized. Call start() first.")
        
        # 過濾掉值為 None 的 kwargs，讓 MCP Server 使用預設值
        clean_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        result = await self.session.call_tool(tool_name, arguments=clean_kwargs)
        return result.content[0].text

    async def stop(self):
        """Close the MCP connection"""
        await self.exit_stack.aclose()