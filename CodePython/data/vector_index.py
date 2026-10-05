"""Lưu vector sản phẩm trong bộ nhớ; tìm kiếm và xếp hạng nằm ở tầng nghiệp vụ."""

from .vector_validation import validate_embedding


class VectorIndex:
    """Ánh xạ ID sản phẩm sang vector số nhân tạo đã được kiểm tra."""

    def __init__(self, products):
        """Tạo chỉ mục và yêu cầu mọi vector được lưu phải có cùng số chiều."""
        self._embeddings = {}
        self._dimension = None
        seen = set()
        for product in products:
            if not isinstance(product, dict) or "id" not in product:
                raise ValueError("Indexed products must be dictionaries with an id.")
            product_id = product["id"]
            try:
                if product_id in seen:
                    raise ValueError(f"Duplicate indexed product id: {product_id}")
                seen.add(product_id)
            except TypeError as exc:
                raise ValueError("Indexed product id must be hashable.") from exc
            embedding = product.get("embedding")
            # Sản phẩm không có vector vẫn có thể tìm bằng text, nhưng không vào chỉ mục ảnh.
            if embedding is None:
                continue
            try:
                vector = validate_embedding(embedding)
            except ValueError as exc:
                raise ValueError(f"Invalid embedding for product {product_id}: {exc}") from exc
            # Vector đầu tiên xác định số chiều chuẩn cho các vector còn lại.
            if self._dimension is None:
                self._dimension = len(vector)
            elif len(vector) != self._dimension:
                raise ValueError(
                    f"Product {product_id}: embedding dimension {len(vector)} "
                    f"does not match index dimension {self._dimension}."
                )
            self._embeddings[product_id] = vector

    @property
    def dimension(self):
        """Số phần tử mỗi vector, hoặc None nếu chỉ mục chưa có vector nào."""
        return self._dimension

    def all_embeddings(self):
        """Trả bản sao các vector theo ID, tránh sửa dữ liệu trong chỉ mục."""
        return {product_id: list(vector) for product_id, vector in self._embeddings.items()}

    def get_embedding(self, product_id):
        """Lấy bản sao vector của một sản phẩm, hoặc None nếu không có."""
        vector = self._embeddings.get(product_id)
        return list(vector) if vector is not None else None
