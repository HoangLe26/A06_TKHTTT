"""Đưa đầu vào văn bản, giọng nói và vector ảnh về cấu trúc truy vấn thống nhất."""

from .image_service import normalize_embedding


class QueryService:
    """Tạo dictionary truy vấn để các chế độ dùng chung SearchService."""

    @staticmethod
    def _normalize_text(text):
        """Kiểm tra kiểu chuỗi và bỏ khoảng trắng thừa ở hai đầu."""
        if not isinstance(text, str):
            raise ValueError("Text and voice queries must be strings.")
        return text.strip()

    def text_query(self, text):
        """Gắn loại text cho nội dung tìm kiếm đã được kiểm tra."""
        return {"type": "text", "query": self._normalize_text(text)}

    def voice_query(self, text):
        """Gắn loại voice cho văn bản phiên âm do SpeechService trả về."""
        return {"type": "voice", "query": self._normalize_text(text)}

    def image_query(self, embedding):
        """Kiểm tra vector số trước khi tạo truy vấn loại image."""
        return {"type": "image", "embedding": normalize_embedding(embedding)}
