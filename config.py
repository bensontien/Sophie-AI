# config.py
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的變數
load_dotenv()

# --- Helper: 取得環境變數，若無則使用預設值 ---
def get_env(key, default=None):
    return os.getenv(key, default)

# =========================================
# 1. 本地 vLLM 配置
# =========================================
LLM_LOCAL_CONFIG = {
    "provider": "vllm",
    "api_base": get_env("VLLM_API_BASE", "http://localhost:8000/v1"),
    "api_key": get_env("VLLM_API_KEY", "empty"),
    "model_name": get_env("DEFAULT_LOCAL_MODEL_PATH"), # 這裡是必填，沒讀到會是 None
    "timeout": int(get_env("DEFAULT_TIMEOUT", 1200))   # 轉成整數
}

# =========================================
# 2. OpenRouter 配置
# =========================================
LLM_OPENROUTER_CONFIG = {
    "provider": "openrouter",
    "api_key": get_env("OPENROUTER_API_KEY"),
    "api_base": get_env("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
    "model_name": get_env("OPENROUTER_MODEL_NAME"),
    "timeout": 120 # OpenRouter 通常不需要像本地端那麼長的 timeout
}

# =========================================
# 3. 翻譯專用配置
# =========================================
# 翻譯 Agent 可能想用同一個 vLLM，但 Timeout 設長一點
LLM_TRANSLATOR_CONFIG = LLM_LOCAL_CONFIG.copy() # 複製一份基礎設定
LLM_TRANSLATOR_CONFIG.update({
    "timeout": int(get_env("TRANSLATOR_TIMEOUT", 3600)) # 覆寫 Timeout
})

# 檢查是否缺少關鍵設定 (防呆)
if not LLM_LOCAL_CONFIG["model_name"]:
    print("⚠️ 警告: 未在 .env 中設定 DEFAULT_LOCAL_MODEL_PATH，Agent 可能無法啟動。")

if not LLM_OPENROUTER_CONFIG["api_key"] or not LLM_OPENROUTER_CONFIG["model_name"]:
    print("ℹ️ 提示: 未偵測到 OpenRouter 完整設定，若不使用可忽略此訊息。")