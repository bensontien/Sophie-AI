import inspect
from typing import Callable, Awaitable, Any, Union
from pydantic import BaseModel
from core.state import AgentState

# Define the standard execution interface (supports both sync and async functions)
ActionExecutor = Callable[[AgentState], Union[AgentState, Awaitable[AgentState]]]

class ToolNode(BaseModel):
    name: str
    description: str
    executor: Any  # The actual execution function or object method

class NodeRegistry:
    def __init__(self):
        self._nodes: dict[str, ToolNode] = {}

    def register(self, name: str, description: str, executor: ActionExecutor):
        """Register a new Agent or Tool"""
        self._nodes[name] = ToolNode(name=name, description=description, executor=executor)

    def get_all_descriptions(self) -> str:
        """Dynamically generate the tool list for the LLM (Orchestrator brain) to read"""
        return "\n".join([f"- {name}: {node.description}" for name, node in self._nodes.items()])

    def get_node(self, name: str) -> ToolNode | None:
        """Retrieve the corresponding node by its name"""
        return self._nodes.get(name)