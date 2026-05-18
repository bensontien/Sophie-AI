from opencc import OpenCC

class ChineseConverter:
    """Utility class to convert Simplified Chinese to Traditional Chinese."""
    
    def __init__(self, config='s2t'):
        # s2t: Simplified Chinese to Traditional Chinese
        self.cc = OpenCC(config)

    def to_traditional(self, text: str) -> str:
        """Converts the given text to Traditional Chinese if it contains Simplified Chinese."""
        if not text:
            return text
        try:
            return self.cc.convert(text)
        except Exception as e:
            print(f"[ChineseConverter] Conversion error: {e}")
            return text

# Global instance for easy access
converter = ChineseConverter()
