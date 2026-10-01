"""Convert each modality into the common query representation."""

from .image_service import normalize_embedding


class QueryService:
    @staticmethod
    def _normalize_text(text):
        if not isinstance(text, str):
            raise ValueError("Text and voice queries must be strings.")
        return text.strip()

    def text_query(self, text):
        return {"type": "text", "query": self._normalize_text(text)}

    def voice_query(self, text):
        return {"type": "voice", "query": self._normalize_text(text)}

    def image_query(self, embedding):
        return {"type": "image", "embedding": normalize_embedding(embedding)}
