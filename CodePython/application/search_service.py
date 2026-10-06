"""Tìm sản phẩm ứng viên và tính điểm; việc sắp xếp thuộc về RankingService."""

from collections.abc import Mapping
import re

from .image_service import normalize_embedding


class SearchService:
    """Tìm theo từ khóa hoặc vector, sử dụng các kho dữ liệu được truyền vào."""

    def __init__(self, product_repository, vector_index, image_service):
        """Nhận kho sản phẩm, chỉ mục vector và dịch vụ tính độ tương đồng."""
        self.repository = product_repository
        self.vector_index = vector_index
        self.image_service = image_service

    def search(self, query):
        """Chọn cách tìm kiếm theo trường type trong dictionary truy vấn."""
        if not isinstance(query, Mapping):
            raise ValueError("Search query must be a query object.")
        mode = query.get("type")
        # Giọng nói đã được phiên âm nên dùng cùng thuật toán với tìm kiếm văn bản.
        if mode in ("text", "voice"):
            return self.search_text(query.get("query"))
        if mode == "image":
            return self.search_image(query.get("embedding"))
        raise ValueError(f"Unsupported query type: {mode!r}")

    def search_text(self, query_text):
        """Mỗi từ truy vấn khớp chuỗi thông tin sản phẩm đóng góp một điểm."""
        if not isinstance(query_text, str):
            raise ValueError("Text search query must be a string.")
        normalized = query_text.lower()
        # API phiên âm thường thêm dấu câu: "Find laptop." vẫn phải khớp "laptop".
        words = re.findall(r'\w+', normalized)
        if not words:
            return []
        candidates = []
        # Tìm trong tên, danh mục, màu và từ khóa bổ sung; đây là khớp chuỗi con,
        # chưa phải tìm kiếm ngữ nghĩa hay phân tích điều kiện giá trong câu.
        for product in self.repository.all_products():
            searchable = " ".join(
                product[field] for field in ("name", "category", "color")
            ).lower() + " " + " ".join(product.get("search_terms", [])).lower()
            score = sum(word in searchable for word in words)
            # Chỉ trả sản phẩm khớp ít nhất một từ; chưa sắp xếp ở bước này.
            if score > 0:
                candidates.append((product, float(score)))
        return candidates

    def search_image(self, query_embedding):
        """So sánh vector truy vấn với các vector sản phẩm có cùng số chiều."""
        vector = normalize_embedding(query_embedding)
        dimension = self.vector_index.dimension
        if dimension is None:
            raise ValueError('Image index is not ready. Run tainguyen/CodePython/setup_clip.py and restart the server.')
        if dimension is not None and len(vector) != dimension:
            raise ValueError(
                f"Image query dimension {len(vector)} does not match "
                f"product embedding dimension {dimension}."
            )
        candidates = []
        # Chỉ mục lưu ID và vector; lấy thông tin sản phẩm tương ứng từ repository.
        for product_id, embedding in self.vector_index.all_embeddings().items():
            product = self.repository.find_by_id(product_id)
            if product is None:
                continue
            score = self.image_service.cosine_similarity(vector, embedding)
            candidates.append((product, float(score)))
        return candidates
