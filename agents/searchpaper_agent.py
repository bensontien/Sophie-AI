import os
import asyncio
import requests
import arxiv
import datetime
import re
from typing import List, Dict, Any
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, Event, step
from core.state import AgentState, PaperData

# OpenAlex Settings
OPENALEX_API_URL = "https://api.openalex.org/works"
TARGET_ISSNS = [
    # --- General CS ---
    "0001-0782", # Communications of the ACM (CACM)
    "0360-0300", # ACM Computing Surveys (CSUR)
    "0018-9340", # IEEE Transactions on Computers (TC)
    
    # --- AI & ML ---
    "0162-8828", # IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI) - AI領域神刊
    "2162-237X", # IEEE Transactions on Neural Networks and Learning Systems (TNNLS)
    "1532-4435", # Journal of Machine Learning Research (JMLR)
    "0004-3702", # Artificial Intelligence (Elsevier)
    "2522-5839", # Nature Machine Intelligence

    # --- AI & Educaion ---
    "1946-6226", # ACM Transactions on Computing Education (TOCE)
    "1939-1382", # IEEE Transactions on Learning Technologies (TLT)
    "0360-1315", # Computers & Education (Elsevier)
    "0747-5632", # Computers in Human Behavior (Elsevier)
    "0007-1013", # British Journal of Educational Technology (BJET)
    "1049-4820", # Interactive Learning Environments
    "0018-9359", # IEEE Transactions on Education (ToE)

    # --- Systems, Architecture & Compilers ---
    "1544-3566", # ACM Transactions on Architecture and Code Optimization (TACO)
    "0734-2071", # ACM Transactions on Computer Systems (TOCS)
    "0164-0925", # ACM Transactions on Programming Languages and Systems (TOPLAS)
    "0278-0070", # IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems (TCAD)
    "0272-1732", # IEEE Micro
    
    # --- Software Engineering & Distributed Systems ---
    "0098-5589", # IEEE Transactions on Software Engineering (TSE)
    "1041-4347", # IEEE Transactions on Knowledge and Data Engineering (TKDE)
    "1045-9219"  # IEEE Transactions on Parallel and Distributed Systems (TPDS)
]
MAILTO = "banson56561ncu@g.ncu.edu.tw"

def reconstruct_openalex_abstract(inverted_index: Dict[str, List[int]]) -> str:
    if not inverted_index:
        return "No Abstract Available."
    word_index_list = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_index_list.append((pos, word))
    return " ".join([word for _, word in sorted(word_index_list, key=lambda x: x[0])])

async def _score_single_paper(paper: Dict, user_topic: str, llm) -> Dict:
    prompt = f"""Please act as a paper reviewer and score the following paper abstract based on its relevance to the user's research topic (0-10 for each dimension).
    
    User's Research Topic: "{user_topic}"
    
    Source: {paper.get('venue', 'Unknown')}
    Title: {paper['title']}
    Abstract: {paper['summary']}

    Evaluation dimensions: Relevance to Topic, Innovation, Technical Depth, Practical Value, Predicted Impact, Rigor.
    
    Please output strictly in the following format (Use Traditional Chinese for the keys):
    主題關聯性: [Score]
    創新性: [Score]
    技術深度: [Score]
    實用價值: [Score]
    影響力預測: [Score]
    嚴謹性: [Score]
    總分: [Total Score]
    """
    try:
        if len(paper['summary']) < 50:
            paper['score'] = 0
            paper['detailed_score'] = "Abstract too short"
            return paper

        response = await llm.acomplete(prompt)
        res_text = str(response)
        
        # Search for the "總分" (Total Score) using regex
        scores = re.findall(r"總分:\s*(\d+)", res_text)
        score = int(scores[0]) if scores else 0
        
        paper['score'] = score
        paper['detailed_score'] = res_text
    except Exception as e:
        paper['score'] = 0
        paper['detailed_score'] = f"Scoring failed: {e}"
    
    return paper

# --- [Define Workflow Events (Passing state)] ---
class FetchEvent(Event):
    state: AgentState
    papers: List[Dict]

class ScoreEvent(Event):
    state: AgentState
    scored_papers: List[Dict]

class SnowballEvent(Event):
    state: AgentState
    scored_papers: List[Dict]

class SummaryEvent(Event):
    state: AgentState
    scored_papers: List[Dict]
    final_report: str

# --- [Integrated Workflow] ---
class SearchPaperAgent(Workflow):

    def __init__(self, llm, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
    
    @step
    async def fetch_papers(self, ev: StartEvent) -> FetchEvent:
        state: AgentState = ev.get("state")
        raw_prompt = state.user_topic
        
        # ✨ 不再依賴 state.search_source，改成聯合搜尋
        print(f"Starting Deep SearchPaperAgent | Sources: Arxiv + OpenAlex")
        print(f"Received raw prompt: {raw_prompt}")
        
        # ==========================================
        # Step 1: Extract Core Academic Topic
        # ==========================================
        print("Extracting core research topic...")
        extract_prompt = f"""
        You are an expert in academic keyword extraction.
        Extract the "core academic research topic" from the following user command, and translate it into English.
        Ignore any action-related words (e.g., search, download, translate, find the best).
        
        User Command: "{raw_prompt}"
        
        Rules:
        1. Output ONLY the English core topic, without any additional explanations or quotes.
        2. Keep it concise (e.g., "Generative AI in Compiler Optimization").
        """
        try:
            core_topic_response = await self.llm.acomplete(extract_prompt)
            core_topic = str(core_topic_response).strip().replace('"', '').replace("'", "").replace("\n", "")
            print(f"Locked core topic: {core_topic}")
        except Exception as e:
            print(f"Topic extraction failed ({e}), falling back to raw prompt.")
            core_topic = raw_prompt

        state.search_keywords_used = [core_topic]

        # ==========================================
        # Step 2: SLR Keyword Expansion
        # ==========================================
        search_query = core_topic 
        print("Performing SLR keyword expansion...")
        query_prompt = f"""
        You are an expert in Systematic Literature Reviews.
        Convert the following research topic into a Boolean search string suitable for academic databases.
        
        Topic: "{core_topic}"
        
        Rules:
        1. Use AND to combine different concepts.
        2. Use OR to include synonyms.
        3. Keep it single line.
        4. Output ONLY the query string.
        """
        try:
            expanded_query = await self.llm.acomplete(query_prompt)
            search_query = str(expanded_query).strip().replace('"', '').replace("'", "").replace("\n", "")
            print(f"Optimized SLR search string: {search_query}")
        except:
            print("SLR expansion failed, using core topic.")

        all_papers = []

        # ==========================================
        # Step 3: Concurrent Fetching (Arxiv + OpenAlex)
        # ==========================================
        
        def fetch_arxiv(query):
            print(f" [Arxiv] Searching for latest preprints...")
            papers = []
            try:
                # ✨ 為了提供足夠的名額給 Top 20，我們把各自的搜尋上限拉高到 30
                search = arxiv.Search(
                    query=query, 
                    max_results=30,
                    sort_by=arxiv.SortCriterion.SubmittedDate
                )
                for r in search.results():
                    papers.append({
                        "title": r.title.replace("\n", " "),
                        "summary": r.summary.replace("\n", " "),
                        "url": r.pdf_url,
                        "venue": "Arxiv Preprint",
                        "date": r.published.strftime("%Y-%m-%d"),
                        "id": r.entry_id
                    })
            except Exception as e:
                print(f"Arxiv search failed: {e}")
            return papers

        def fetch_openalex(query):
            print(f" [OpenAlex] Searching target journals (ISSN Filter)...")
            papers = []
            issn_filter = "|".join(TARGET_ISSNS)
            params = {
                "filter": f"primary_location.source.issn:{issn_filter},default.search:{query},from_publication_date:2024-01-01",
                "sort": "publication_date:desc",
                "per_page": 30, # ✨ 拉高到 30 篇
                "mailto": MAILTO
            }
            try:
                resp = requests.get(OPENALEX_API_URL, params=params)
                resp.raise_for_status()
                results = resp.json().get("results", [])
                
                # Fallback Mechanism
                if not results and query != core_topic:
                    print(f"  [OpenAlex] Fallback Mechanism: Retrying with core topic '{core_topic}'...")
                    params["filter"] = f"primary_location.source.issn:{issn_filter},default.search:{core_topic},from_publication_date:2024-01-01"
                    resp = requests.get(OPENALEX_API_URL, params=params)
                    results = resp.json().get("results", [])

                for r in results:
                    abstract = reconstruct_openalex_abstract(r.get("abstract_inverted_index"))
                    papers.append({
                        "title": r.get("title", "No Title"),
                        "summary": abstract,
                        "url": r.get("doi") or r.get("primary_location", {}).get("landing_page_url", "No URL"),
                        "venue": r.get("primary_location", {}).get("source", {}).get("display_name", "Unknown Journal"),
                        "date": r.get("publication_date"),
                        "id": r.get("id"), 
                        "referenced_works": r.get("referenced_works", [])
                    })
            except Exception as e:
                print(f"OpenAlex connection failed: {e}")
            return papers

        # Run both searches in parallel using asyncio threads
        loop = asyncio.get_event_loop()
        arxiv_results, openalex_results = await asyncio.gather(
            loop.run_in_executor(None, fetch_arxiv, core_topic), # Arxiv usually handles direct keywords better
            loop.run_in_executor(None, fetch_openalex, search_query) # OpenAlex handles Boolean SLR well
        )
        
        all_papers.extend(arxiv_results)
        all_papers.extend(openalex_results)
        
        # Deduplicate papers based on title (case-insensitive)
        unique_papers = []
        seen_titles = set()
        for p in all_papers:
            title_lower = p['title'].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_papers.append(p)

        print(f"Successfully fetched {len(unique_papers)} unique papers from combined sources.")
        return FetchEvent(state=state, papers=unique_papers)

    @step
    async def score_papers(self, ev: FetchEvent) -> ScoreEvent:
        if not ev.papers:
            print("No papers to score.")
            return ScoreEvent(state=ev.state, scored_papers=[])

        print(f"Starting scoring for {len(ev.papers)} papers...")
        
        # 由於要一次評分高達 60 篇論文，並發請求可能會被 LLM API 限流 (Rate Limit)
        # 建議分批處理 (Batch Processing)
        batch_size = 10
        scored_results = []
        
        for i in range(0, len(ev.papers), batch_size):
            batch = ev.papers[i:i+batch_size]
            tasks = [_score_single_paper(p, ev.state.user_topic, self.llm) for p in batch]
            batch_results = await asyncio.gather(*tasks)
            scored_results.extend(batch_results)
            print(f"  Scored {min(i+batch_size, len(ev.papers))}/{len(ev.papers)}...")
            await asyncio.sleep(1) # 小歇一秒，避免 API 阻擋
        
        # ✨ 修改為取 Top 20 (或者所有評分大於 0 的，取前 20)
        top_20 = sorted(scored_results, key=lambda x: x['score'], reverse=True)[:20]
        return ScoreEvent(state=ev.state, scored_papers=top_20)

    @step
    async def snowball_expansion(self, ev: ScoreEvent) -> SnowballEvent:
        if not ev.scored_papers:
            return SnowballEvent(state=ev.state, scored_papers=ev.scored_papers)

        # 這裡我們只拿最高分的那篇去滾雪球
        top_paper = ev.scored_papers[0]
        ref_ids = top_paper.get("referenced_works", [])
        
        if not ref_ids:
            print("Top 1 paper has no reference data, skipping snowballing.")
            return SnowballEvent(state=ev.state, scored_papers=ev.scored_papers)

        print(f"Initiating Backward Snowballing...")
        print(f"Target paper: {top_paper['title']}")
        print(f"Total {len(ref_ids)} references found, retrieving top 10...") # ✨ 滾雪球範圍拉大到 10 篇

        target_urls = ref_ids[:10]
        clean_ids = [url.split("/")[-1] for url in target_urls]
            
        ids_filter = "|".join(clean_ids)
        params = {
            "filter": f"openalex_id:{ids_filter}", 
            "per_page": 10,
            "mailto": MAILTO
        }
        
        snowball_papers = []
        try:
            response = requests.get(OPENALEX_API_URL, params=params)
            if response.status_code != 200:
                print(f"OpenAlex API Error: {response.status_code} - {response.text}")
                return SnowballEvent(state=ev.state, scored_papers=ev.scored_papers)

            results = response.json().get("results", [])
            
            for r in results:
                abstract = reconstruct_openalex_abstract(r.get("abstract_inverted_index"))
                location = r.get("primary_location") or {}
                source = location.get("source") or {}
                
                snowball_papers.append({
                    "title": f"[Snowball] {r.get('title', 'No Title')}",
                    "summary": abstract,
                    "url": r.get("doi") or location.get("landing_page_url", "No URL"),
                    "venue": source.get("display_name", "Unknown Journal"),
                    "date": r.get("publication_date"),
                    "id": r.get("id")
                })

            if snowball_papers:
                print(f"   Retrieved {len(snowball_papers)} cited papers, starting scoring...")
                tasks = [_score_single_paper(p, ev.state.user_topic, self.llm) for p in snowball_papers]
                scored_snowballs = await asyncio.gather(*tasks)
                
                combined = ev.scored_papers + scored_snowballs
                # ✨ 再次取合併後的 Top 20
                final_top_20 = sorted(combined, key=lambda x: x['score'], reverse=True)[:20]
                
                print(f"Snowballing complete, recommendation list updated.")
                return SnowballEvent(state=ev.state, scored_papers=final_top_20)
            else:
                return SnowballEvent(state=ev.state, scored_papers=ev.scored_papers)
        
        except Exception as e:
            print(f"Snowball API failed: {e}")
            return SnowballEvent(state=ev.state, scored_papers=ev.scored_papers)

    @step
    async def generate_summary(self, ev: SnowballEvent) -> SummaryEvent:
        if not ev.scored_papers:
             return SummaryEvent(state=ev.state, scored_papers=[], final_report="No data available.")

        print(f"Generating in-depth summary report for Top {len(ev.scored_papers)} papers...")
        
        report = f"## 📅 深度文獻回顧報告 (Arxiv + OpenAlex 聯合搜索)\n"
        report += f"**研究主題**：{ev.state.user_topic}\n"
        report += f"**日期**：{datetime.date.today()}\n"
        report += f"**總計收錄**：{len(ev.scored_papers)} 篇高相關性文獻\n\n"
        report += "---\n\n"

        # 這裡為了避免 20 篇論文的總結把 LLM 塞爆，我們一樣使用分批處理
        async def summarize_paper(i, p):
            prompt = f"""Please summarize the following paper:
            Title: {p['title']}
            Abstract: {p['summary']}
            
            Format requirements (Please output in Traditional Chinese using Markdown formatting):
            - **核心貢獻**: 
            - **技術重點**: 
            - **創新點**: 
            """
            try:
                summary = await self.llm.acomplete(prompt)
                return str(summary)
            except:
                return "摘要生成失敗 (Summary generation failed)"

        tasks = [summarize_paper(i, p) for i, p in enumerate(ev.scored_papers)]
        summaries = await asyncio.gather(*tasks)

        for i, (p, summary) in enumerate(zip(ev.scored_papers, summaries)):
            report += f"### {i+1}. {p['title']}\n"
            report += f"- **🏅 Rank**: {i+1} | **⭐ Score**: {p['score']}/60\n"
            report += f"- **📖 Venue**: {p['venue']}\n"
            report += f"- **📅 Date**: {p['date']}\n\n"
            report += f"{summary}\n\n"
            report += f"🔗 **[點此閱讀原始論文 PDF]({p['url']})**\n\n"
            report += "---\n\n"

        return SummaryEvent(state=ev.state, scored_papers=ev.scored_papers, final_report=report)

    @step
    async def save_report(self, ev: SummaryEvent) -> StopEvent:
        state = ev.state
        
        if not ev.scored_papers:
            state.chat_reply = "很抱歉，沒有找到符合條件的論文。"
            return StopEvent(result=state)

        filename = f"Papers/DeepReview_{datetime.date.today()}.txt"
        print(f"Saving deep review report to {filename}...")
        
        os.makedirs("Papers", exist_ok=True)
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(ev.final_report)
            
            state.search_report_file = filename
            top_paper_dict = ev.scored_papers[0]
            state.top_paper = PaperData(
                title=top_paper_dict['title'],
                url=top_paper_dict['url']
            )
            
            state.search_report_content = ev.final_report 
            state.chat_reply = f"我已經為您完成了深度檢索！從 arXiv 和權威期刊中共篩選出前 {len(ev.scored_papers)} 篇最高分的文獻，並生成了詳盡的分析報告。"
            
            return StopEvent(result=state)
            
        except Exception as e:
            print(f"Save failed: {e}")
            state.chat_reply = "很抱歉，生成報告時發生錯誤。"
            return StopEvent(result=state)