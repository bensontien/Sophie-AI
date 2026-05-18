from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step
from core.state import AgentState
from core.prompt_loader import PromptLoader

class ChatAgent(Workflow):
    def __init__(self, llm, tool_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        self.tool_manager = tool_manager

    @step
    async def chat(self, ev: StartEvent) -> StopEvent:
        state: AgentState = ev.get("state")
        
        print("[ChatAgent] Thinking and generating response...")
        
        prompt_template = PromptLoader.load_agent_prompt("chat_agent")
        
        # Use capability info from state (populated by Orchestrator)
        available_agents = state.available_agents if state.available_agents else "None"
        available_tools = state.available_tools if state.available_tools else "None"

        prompt = prompt_template.format(
            memory_context=state.memory_context if state.memory_context else "None",
            user_topic=state.user_topic,
            available_agents=available_agents,
            available_tools=available_tools
        )
        
        try:
            # Use Ray Proxy to get dynamic tool list if needed (fallback)
            # available_tools = self.tool_manager.get_all_tool_descriptions()
            
            response = await self.llm.acomplete(prompt)
            state.chat_reply = str(response).strip()
        except Exception as e:
            print(f"[ChatAgent] Failed to generate response: {e}")
            state.chat_reply = "ERROR"

        return StopEvent(result=state)
