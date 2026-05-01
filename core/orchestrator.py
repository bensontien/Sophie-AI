import os
import json
import inspect
from core.state import AgentState, Plan, Task
from agents.generic_agent import GenericAgent
from core.prompt_loader import PromptLoader 

class SophieOrchestrator:
    def __init__(self, llm, registry, tool_manager=None):
        self.llm = llm
        self.registry = registry
        self.tool_manager = tool_manager

    async def _generate_plan(self, user_prompt: str, memory_context: str = "") -> Plan:
        specialized_agents_desc = self.registry.get_all_descriptions()
        
        # Fetch the skill catalog instead of all tool schemas
        available_skills_desc = "None currently available."
        if self.tool_manager:
            available_skills_desc = PromptLoader.load_skill_catalog()

        # Load the base orchestrator prompt from the Markdown file
        base_prompt_template = PromptLoader.load_agent_prompt("orchestrator")
        
        # Inject the dynamic context into the prompt
        prompt = base_prompt_template.format(
            specialized_agents_desc=specialized_agents_desc,
            available_skills_desc=available_skills_desc,
            memory_context=memory_context if memory_context else "None",
            user_prompt=user_prompt
        )
        
        print("[Orchestrator] Thinking and planning tasks...")
        try:
            response = await self.llm.acomplete(prompt)
            raw_text = str(response).strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3].strip()
                
            plan = Plan(**json.loads(raw_text))
            return plan
        except Exception as e:
            print(f"Planning failed: {e}")
            return Plan(tasks=[])

    async def execute_task(self, user_prompt: str, search_source: str = "openalex", memory_context: str = "") -> AgentState:
        state = AgentState(user_topic=user_prompt, search_source=search_source)
        state.memory_context = memory_context
        os.makedirs("Papers", exist_ok=True)
        
        state.plan = await self._generate_plan(user_prompt, memory_context)
        
        print("\n=== Current Task Execution Plan ===")
        for t in state.plan.tasks:
            # Notice we now print the requested category, not the specific tools
            category_info = f"(Category: {getattr(t, 'required_category', 'None')})" if hasattr(t, 'required_category') and getattr(t, 'required_category') else ""
            print(f"  [{t.task_id}] {t.assigned_node} {category_info} -> {t.description}")
        print("===========================\n")

        for task in state.plan.tasks:
            if state.is_aborted:
                break
                
            print(f"\nExecuting step {task.task_id}: {task.assigned_node}")
            state.current_phase = task.assigned_node
            
            if task.assigned_node == "GenericAgent":
                if not self.tool_manager:
                    print("Tool Manager is not initialized, skipping GenericAgent task.")
                    continue
                    
                # The orchestrator now passes the requested skill category to the GenericAgent
                req_category = getattr(task, 'required_category', None)
                print(f"[Orchestrator] Spawning custom GenericAgent with requested skill category: {req_category}")
                
                try:
                    temp_agent = GenericAgent(
                        llm=self.llm,
                        tool_manager=self.tool_manager,
                        required_category=req_category, # Pass the category instead of required_tools
                        system_prompt=task.role_prompt if task.role_prompt else "Use available tools or context to fulfill the user's request.",
                        task_id=task.task_id
                    )
                    
                    result = await temp_agent.run(state=state)
                    state = result
                except Exception as e:
                    print(f"Fatal error in GenericAgent: {e}")
                    state.is_aborted = True
                    
            else:
                node = self.registry.get_node(task.assigned_node)
                if not node:
                    print(f"Cannot find registered tool: {task.assigned_node}, skipping.")
                    continue

                executor = node.executor
                try:
                    result = executor(state=state)
                    if inspect.isawaitable(result):
                        state = await result
                    else:
                        state = result
                except Exception as e:
                    print(f"Fatal error occurred while executing node {task.assigned_node}: {e}")
                    state.is_aborted = True

        state.current_phase = "finished"
        print("\n[Orchestrator] Plan execution completed!")
        return state