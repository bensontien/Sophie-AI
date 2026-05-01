class MemoryManager:
    def __init__(self, llm, max_recent_turns=4):
        self.llm = llm
        self.max_recent_turns = max_recent_turns  # Maximum number of original dialogue turns to keep (1 Q & A counts as 2 turns)
        self.summary = ""                         # Compressed summary of past conversations
        self.recent_history = []                  # Recent conversation history [{role: ..., content: ...}]

    def add_turn(self, role: str, content: str):
        """Add a new conversation record"""
        self.recent_history.append({"role": role, "content": content})

    async def get_context_and_compress(self) -> str:
        """Get the current context, and automatically compress if the history is too long"""
        
        # 1. Check if compression is needed (exceeds maximum turns)
        if len(self.recent_history) > self.max_recent_turns:
            # Extract the oldest two sentences (1 Q & A) for compression
            turns_to_compress = self.recent_history[:2]
            # Keep the rest in the recent conversation history
            self.recent_history = self.recent_history[2:]
            
            text_to_compress = "\n".join([f"{t['role']}: {t['content']}" for t in turns_to_compress])
            
            print("[Memory] Conversation length limit reached, performing context compression...")
            prompt = f"""You are a memory compression assistant.
            Please merge the key points of the following "New Conversation" into the "Existing Summary" to create a short, coherent background context (under 100 words).
            Only retain the user's core intent and the task execution status.
            (Please output the summary in Traditional Chinese)

            [Existing Summary]: {self.summary if self.summary else "None"}
            [New Conversation]:\n{text_to_compress}
            
            Please output ONLY the new summary content without any additional explanations.
            """
            try:
                resp = await self.llm.acomplete(prompt)
                self.summary = str(resp).strip()
            except Exception as e:
                print(f"[Memory] Compression failed: {e}")

        # 2. Assemble the final Context string for the Orchestrator
        context_str = ""
        if self.summary:
            context_str += f"[Past Conversation Summary]: {self.summary}\n"
        if self.recent_history:
            context_str += "[Recent Conversation History]:\n"
            context_str += "\n".join([f"{t['role']}: {t['content']}" for t in self.recent_history])
            
        return context_str