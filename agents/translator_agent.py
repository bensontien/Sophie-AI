import os
import fitz
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step, Event

from core.state import AgentState

# --- Events ---
class ChunkEvent(Event):
    state: AgentState
    chunks: list
    file_name: str

# --- Translator Agent ---
class PDFTranslatorAgent(Workflow):

    def __init__(self, llm, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm

    @step
    async def load_and_chunk(self, ev: StartEvent) -> ChunkEvent:
        state: AgentState = ev.get("state")
        
        if not state.top_paper or not state.top_paper.pdf_path:
            print("[Translator] Error: PDF path not found in State.")
            state.is_aborted = True
            return StopEvent(result=state)
            
        pdf_path = state.top_paper.pdf_path
        print(f"[Translator] Reading PDF: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            print(f"[Translator] Error: File not found {pdf_path}")
            state.is_aborted = True
            return StopEvent(result=state)

        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text()
        except Exception as e:
            print(f"[Translator] Failed to read PDF: {e}")
            state.is_aborted = True
            return StopEvent(result=state)
        
        chunk_size = 2000
        chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
        
        file_name = os.path.basename(pdf_path).replace(".pdf", "")
        print(f"Segmented into {len(chunks)} chunks, preparing for translation...")
        
        return ChunkEvent(state=state, chunks=chunks, file_name=file_name)

    @step
    async def translate_chunks(self, ev: ChunkEvent) -> StopEvent:
        state = ev.state
        print(f"[Translator] Starting sequential translation (Total {len(ev.chunks)} chunks)...")
        
        # Define output file path
        output_path = f"Papers/Translated_{ev.file_name}.md"
        
        # Write file header
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# {ev.file_name} (Full Traditional Chinese Translation)\n\n")

        # Translate chunk by chunk and write immediately
        for i, chunk in enumerate(ev.chunks):
            print(f"   -> Translating chunk {i+1}/{len(ev.chunks)}...")
            
            prompt = f"""You are a professional computer science academic translator.
            Please translate the following paper excerpt into Traditional Chinese (Taiwan academic terminology).
            
            Requirements:
            1. Preserve mathematical formulas in LaTeX format (e.g., $E=mc^2$).
            2. Keep proper nouns (e.g., LLM, Transformer, zero-shot) in English or provide them in parentheses.
            3. Maintain a rigorous and fluent academic tone.

            Original excerpt:
            {chunk}

            Please output ONLY the translated result without any additional explanations.
            """
            
            try:
                response = await self.llm.acomplete(prompt)
                translated_text = str(response)
                
                # Append to file
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(f"\n\n## Section {i+1}\n\n")
                    f.write(translated_text)
                    
            except Exception as e:
                print(f"Translation failed for chunk {i+1}: {e}")
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(f"\n\n[Error: Translation failed for chunk {i+1}]\n\n")

        print(f"Translation complete! File saved at: {output_path}")
        
        # Update the final result into State, and pass the State back to Orchestrator
        state.final_translated_file = output_path
        return StopEvent(result=state)