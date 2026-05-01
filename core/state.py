from typing import Optional, List
from pydantic import BaseModel, Field

class Task(BaseModel):
    task_id: int
    description: str       
    assigned_node: str     
    status: str = "pending" # pending, in_progress, completed, failed
    
    # 用於階層式工具路由，由 Orchestrator 填入大分類 (例如 "WebScraping")
    required_category: Optional[str] = None 
    
    # 作為內部狀態記錄，GenericAgent 解析完分類後，可將實際調用的工具名稱寫入此處
    required_tools: List[str] = Field(default_factory=list) 
    
    role_prompt: str = ""

class Plan(BaseModel):
    tasks: List[Task] = Field(default_factory=list)

class PaperData(BaseModel):
    title: str
    url: str
    pdf_path: Optional[str] = None

class AgentState(BaseModel):
    user_topic: str
    search_source: str = "openalex"
    search_keywords_used: List[str] = Field(default_factory=list)
    
    memory_context: str = ""
    
    plan: Optional[Plan] = None
    search_report_content: Optional[str] = None
    search_report_file: Optional[str] = None
    top_paper: Optional[PaperData] = None
    final_translated_file: Optional[str] = None
    news_report: Optional[str] = None 
    
    chat_reply: Optional[str] = None
    
    current_phase: str = "init"
    is_aborted: bool = False

    # 用於多 Agent 協作時，儲存各個 Step 的執行結果（Scratchpad 機制）
    step_results: dict[int, str] = Field(default_factory=dict)