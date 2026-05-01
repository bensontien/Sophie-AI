# Sophie AI Assistant (Sophie 智能助理)

Sophie 是一個基於 **微服務與多代理人架構 (Microservices & Multi-Agent Architecture)** 的高彈性、企業級 AI 助理系統。它具備自主任務規劃、動態代理人生成、漸進式工具揭露 (Progressive Tool Disclosure) 等核心特性，並將 AI 邏輯 (Python Brain) 與工具執行 (MCP Muscle) 進行嚴格分離。

本系統採用高度解耦的架構：由 **FastAPI** 驅動的 Python 大腦、基於 **Model Context Protocol (MCP)** 的工具伺服器，以及 **Prompts-as-Code** 的設計哲學，允許透過 Markdown 檔案即時熱更新 LLM 的行為。

## 🌟 核心特性

*   **雙軌任務編排 (Dual-Track Orchestration)**：利用主 LLM (透過 OpenRouter 或本地 vLLM) 對複雜需求進行任務分解。它能將標準工作流路由至「專化代理人 (Specialized Agents)」，或針對自定義長尾需求動態生成「通用代理人 (GenericAgents)」。
*   **統一工具管理與 MCP 支持**：採用 **Model Context Protocol (MCP)** 實現工具的動態註冊與調用。`ToolManager` 支援階層式路由，代理人先選擇「技能類別」(如 `web_scraping`, `system_ops`)，再動態加載相關工具，有效節省 Context Window 並減少幻覺。
*   **指令即代碼 (Prompts-as-Code)**：所有系統指令、代理人人格 (Personas) 與技能規則均抽離至 `.sophie/` 目錄下的 Markdown 檔案。支援熱加載、版本控制，並確保代碼邏輯的純潔。
*   **腦肌分離架構 (Brain-Muscle Architecture)**：
    *   **大腦 (Python Brain)**：處理 LLM 編排、任務規劃、狀態管理與 Websocket 串流。
    *   **肌肉 (MCP Server)**：基於 `FastMCP` 實現的高效工具伺服器，處理網頁爬取、系統操作 (Windows PowerShell) 與文件下載等 I/O 密集型任務。
*   **混合 LLM 支援**：完美支援本地 **vLLM** 推理框架與 **OpenRouter** 雲端 API，可根據任務複雜度與成本考量靈活切換。

## 🏗 架構與目錄結構

```text
Agents/
├── .sophie/                # 🧠 Prompts-as-Code (Markdown 設定)
│   ├── agents/             # 編排器與各類代理人的 Persona
│   └── skills/             # 技能清單與使用規範
│
├── agents/                 # 🤖 代理人實現 (LlamaIndex Workflows)
│   ├── searchpaper_agent.py# 論文搜索代理人
│   ├── translator_agent.py # PDF 翻譯代理人
│   ├── news_agent.py       # 新聞分析代理人
│   └── generic_agent.py    # 通用型任務代理人
│
├── core/                   # ⚙️ 核心邏輯
│   ├── orchestrator.py     # 任務分解與調度
│   ├── tool_manager.py     # 工具適配器 (CLI, MCP)
│   └── mcp_client.py       # MCP 伺服器客戶端
│
├── factorys/               # 🏭 工廠模式實現
│   ├── agent_factory.py    # 代理人生成工廠
│   └── model_factory.py    # LLM 模型實例工廠
│
├── sophie-ui/              # 💻 前端界面 (React + Vite)
│
├── server.py               # 🚀 FastAPI 主程式入口
├── tools_server.py         # 🛠 MCP 工具伺服器
└── config.py               # ⚙️ 系統配置管理
```

## 🚀 快速開始

### 1. 配置環境變數
在根目錄創建 `.env` 檔案，填入您的 API 金鑰與模型配置：

```env
# OpenRouter 配置
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL_NAME=google/gemma-2-9b-it

# 本地 vLLM 配置 (選填)
DEFAULT_LOCAL_MODEL_PATH=/path/to/model
VLLM_API_BASE=http://localhost:8000/v1
```

### 2. 安裝依賴
```bash
pip install -r requirements.txt
```

### 3. 啟動服務

**步驟 A：啟動主後端服務**
這會同時啟動 FastAPI 伺服器並自動掛載 `tools_server.py` 作為 MCP 背景進程。
```bash
python server.py
# 或使用 uvicorn
# uvicorn server:app --host 0.0.0.0 --port 8080
```

**步驟 B：啟動前端介面**
```bash
cd sophie-ui
npm install
npm run dev
```

## 🛠 開發與擴展

### 如何新增一個工具 (Tool)
1.  在 `tools_server.py` 中使用 `@mcp.tool()` 裝飾器定義新功能。
2.  在 `.sophie/skills/catalog.md` 中更新工具描述。
3.  如果需要特定的安全規則，在 `.sophie/skills/` 下建立對應的 Markdown 檔案。

### 如何新增一個專化代理人 (Agent)
1.  在 `agents/` 目錄下參考現有代理人 (如 `news_agent.py`) 建立新的 Workflow 類別。
2.  在 `.sophie/agents/` 下定義該代理人的 `persona.md`。
3.  在 `factorys/agent_factory.py` 中註冊該代理人，以便編排器調用。

---

## 📄 授權
本專案採用 MIT 授權條款。
