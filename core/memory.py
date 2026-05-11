class MemoryManager:
    """Manages conversation memory and automatic context compression."""
    def __init__(self, llm, max_recent_turns=4):
        self.llm = llm
        self.max_recent_turns = max_recent_turns  # Max original dialogue turns (1 Q&A = 2 turns)
        self.summary = ""                         # Compressed summary of past history
        self.recent_history = []                  # Recent history records

    def add_turn(self, role: str, content: str):
        """Add a new turn to the conversation history."""
        self.recent_history.append({"role": role, "content": content})

    async def get_context_and_compress(self) -> str:
        """Retrieve current context and automatically compress if history limit is reached."""
        
        # 1. Check for compression (exceeds max turns)
        if len(self.recent_history) > self.max_recent_turns:
            # Extract oldest turns (1 Q&A) for compression
            turns_to_compress = self.recent_history[:2]
            self.recent_history = self.recent_history[2:]
            
            text_to_compress = "\n".join([f"{t['role']}: {t['content']}" for t in turns_to_compress])
            
            print("[Memory] History limit reached, performing context compression...")
            prompt = f"""You are a memory compression assistant.
            Merge key points of the "New Conversation" into the "Existing Summary" (under 100 words).
            Retain user intent and task status. Output the summary in Traditional Chinese.

            [Existing Summary]: {self.summary if self.summary else "None"}
            [New Conversation]:\n{text_to_compress}
            """
            try:
                resp = await self.llm.acomplete(prompt)
                self.summary = str(resp).strip()
            except Exception as e:
                print(f"[Memory] Compression failed: {e}")

        # 2. Assemble final context string
        context_str = ""
        if self.summary:
            context_str += f"[Past Conversation Summary]: {self.summary}\n"
        if self.recent_history:
            context_str += "[Recent Conversation History]:\n"
            context_str += "\n".join([f"{t['role']}: {t['content']}" for t in self.recent_history])
            
        return context_str