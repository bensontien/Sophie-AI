# config.py
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# --- Helper: Get environment variable, or use default value ---
def get_env(key, default=None):
    return os.getenv(key, default)

# =========================================
# 1. Local vLLM Configuration
# =========================================
LLM_LOCAL_CONFIG = {
    "provider": "vllm",
    "api_base": get_env("VLLM_API_BASE", "http://localhost:8000/v1"),
    "api_key": get_env("VLLM_API_KEY", "empty"),
    "model_name": get_env("DEFAULT_LOCAL_MODEL_PATH"), # Required field
    "timeout": int(get_env("DEFAULT_TIMEOUT", 1200))   # Convert to integer
}

# =========================================
# 2. OpenRouter Configuration
# =========================================
LLM_OPENROUTER_CONFIG = {
    "provider": "openrouter",
    "api_key": get_env("OPENROUTER_API_KEY"),
    "api_base": get_env("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
    "model_name": get_env("OPENROUTER_MODEL_NAME"),
    "timeout": 120 # OpenRouter typically does not require a long timeout
}

# =========================================
# 3. Translator Dedicated Configuration
# =========================================
# Translator Agent uses the same vLLM but with a longer timeout
LLM_TRANSLATOR_CONFIG = LLM_LOCAL_CONFIG.copy() # Copy base settings
LLM_TRANSLATOR_CONFIG.update({
    "timeout": int(get_env("TRANSLATOR_TIMEOUT", 3600)) # Override timeout
})

# Basic check for missing critical settings
if not LLM_LOCAL_CONFIG["model_name"]:
    print("Warning: DEFAULT_LOCAL_MODEL_PATH not set in .env. Agent may fail to start.")

if not LLM_OPENROUTER_CONFIG["api_key"] or not LLM_OPENROUTER_CONFIG["model_name"]:
    print("Note: OpenRouter configuration incomplete. Ignore this message if not using OpenRouter.")
