from typing import Dict
from llama_index.llms.openai_like import OpenAILike
from llama_index.llms.openai import OpenAI

class ModelFactory:
    @staticmethod
    def create_llm(config: Dict):
        """
        Return the corresponding LlamaIndex LLM instance based on the provided configuration dictionary
        """
        provider = config.get("provider", "vllm")
        
        if provider == "vllm" or provider == "local":
            return OpenAILike(
                model=config["model_name"],
                api_base=config["api_base"],
                api_key=config["api_key"],
                is_chat_model=True,
                timeout=config.get("timeout", 600)
            )
            
        elif provider == "openai":
            return OpenAI(
                model=config["model_name"],
                api_key=config["api_key"],
                api_base=config.get("api_base"),
                timeout=config.get("timeout", 60)
            )
            
        elif provider == "openrouter":
            return OpenAILike(
                model=config["model_name"],
                api_base=config.get("api_base", "https://openrouter.ai/api/v1"),
                api_key=config["api_key"],
                is_chat_model=True,
                timeout=config.get("timeout", 120),
                default_headers={
                    "HTTP-Referer": "https://your-website.com", # 替換成你的網站或專案名稱
                    "X-Title": "My LlamaIndex App",            # 替換成你的 App 名稱
                }
            )
        
        else:
            raise ValueError(f"Unsupported model provider: {provider}")