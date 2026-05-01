from typing import Any, Optional
from config import LLM_LOCAL_CONFIG, LLM_OPENROUTER_CONFIG, LLM_TRANSLATOR_CONFIG
from factorys.model_factory import ModelFactory
from agents.searchpaper_agent import SearchPaperAgent
from agents.translator_agent import PDFTranslatorAgent
from agents.news_agent import NewsAgent
from agents.chat_agent import ChatAgent

class AgentFactory:
    """
    Universal Agent Factory Class
    Responsible for unified management of creation, dependency injection, and instance caching for all Agents
    """
    
    def __init__(self):
        # Initialize all available LLMs
        self.local_llm = ModelFactory.create_llm(LLM_LOCAL_CONFIG)
        self.translator_llm = ModelFactory.create_llm(LLM_TRANSLATOR_CONFIG)
        self.external_llm = ModelFactory.create_llm(LLM_OPENROUTER_CONFIG)
        
        # Read global default timeout
        self.default_timeout = LLM_LOCAL_CONFIG.get("timeout", 1200)

    def get_llm(self, llm_type: str = 'local') -> Any:
        """Get the LLM instance of the specified type"""
        if llm_type == 'local':
            return self.local_llm
        elif llm_type == 'translator':
            return self.translator_llm
        elif llm_type == 'external':
            return self.external_llm
        else:
            raise ValueError(f"Unknown LLM type: {llm_type}")

    def create_agent(self, agent_type: str, llm_type: str = 'local', **kwargs) -> Any:
        
        # 1. Dynamically retrieve the corresponding LLM instance based on the passed llm_type
        target_llm = self.get_llm(llm_type)
        
        # 2. Calculate the final timeout
        timeout = kwargs.pop('timeout', self.default_timeout)

        # 3. Instantiate the Agent
        if agent_type == 'SearchPaperAgent':
            return SearchPaperAgent(
                llm=target_llm, 
                timeout=timeout,
                verbose=True, 
                **kwargs
            )
            
        elif agent_type == 'PDFTranslatorAgent':
            trans_timeout = timeout if timeout > 1200 else 3600
            actual_llm = target_llm if llm_type != 'local' else self.get_llm('translator')
            
            return PDFTranslatorAgent(
                llm=actual_llm, 
                timeout=trans_timeout,
                verbose=True, 
                **kwargs
            )
            
        elif agent_type == 'NewsAgent':
            # Explicitly extract the tool_manager from kwargs if it exists
            # This ensures we don't accidentally pass legacy mcp_client references
            tool_mgr = kwargs.pop('tool_manager', None)
            
            return NewsAgent(
                llm=target_llm,
                tool_manager=tool_mgr,
                timeout=timeout,
                verbose=True, 
                **kwargs
            )
        
        elif agent_type == 'ChatAgent':
            return ChatAgent(
                llm=target_llm, 
                timeout=timeout, 
                verbose=True, 
                **kwargs
            )
            
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    def get_agent(self, agent_type: str, llm_type: str = 'local', **kwargs) -> Any:
        return self.create_agent(agent_type, llm_type=llm_type, **kwargs)