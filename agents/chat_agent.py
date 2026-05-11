from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step
from core.state import AgentState
from core.prompt_loader import PromptLoader

class ChatAgent(Workflow):
    def __init__(self, llm, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm

    @step
    async def chat(self, ev: StartEvent) -> StopEvent:
        state: AgentState = ev.get("state")
        
        print("[ChatAgent] Thinking and generating response...")
        
        prompt_template = PromptLoader.load_agent_prompt("chat_agent")
        
        prompt = prompt_template.format(
            memory_context=state.memory_context if state.memory_context else "None",
            user_topic=state.user_topic
        )
        
        try:
            response = await self.llm.acomplete(prompt)
            state.chat_reply = str(response).strip()
        except Exception as e:
            print(f"[ChatAgent] Failed to generate response: {e}")
            state.chat_reply = "ERROR"

        return StopEvent(result=state)
