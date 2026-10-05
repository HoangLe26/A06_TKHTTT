"""Retrieve unsorted candidates; final ordering belongs to RankingService."""

from collections.abc import Mapping
import re

from .image_service import normalize_embedding


class SearchService:
    def __init__(self, product_repository, vector_index, image_service):
        self.repository = product_repository
        self.vector_index = vector_index
        self.image_service = image_service

    def search(self, query):
        if not isinstance(query, Mapping):
            raise ValueError("Search query must be a query object.")
        mode = query.get("type")
        if mode in ("text", "voice"):
            return self.search_text(query.get("query"))
        if mode == "image":
            return self.search_image(query.get("embedding"))
        raise ValueError(f"Unsupported query type: {mode!r}")

    def search_text(self, query_text):
        if not isinstance(query_text, str):
            raise ValueError("Text search query must be a string.")
        normalized = query_text.lower()
        # Match known category phrases as a whole: "ban" must not match "bang".
        aliases = {'điện thoại': 'phone', 'dien thoai': 'phone',
                   'máy tính bảng': 'tablet', 'may tinh bang': 'tablet',
                   'máy tính xách tay': 'laptop', 'may tinh xach tay': 'laptop',
                   'bàn phím': 'keyboard', 'ban phim': 'keyboard',
                   'chuột': 'mouse', 'chuot': 'mouse',
                   'phụ kiện': 'accessory', 'phu kien': 'accessory'}
        for phrase, category in aliases.items():
            normalized = re.sub(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', category, normalized)
        words = normalized.split()
        if not words:
            return []
        candidates = []
        for product in self.repository.all_products():
            searchable = " ".join(
                product[field] for field in ("name", "category", "color")
            ).lower() + " " + " ".join(product.get("search_terms", [])).lower()
            score = sum(word in searchable for word in words)
            if score > 0:
                candidates.append((product, float(score)))
        return candidates

    def search_image(self, query_embedding):
        vector = normalize_embedding(query_embedding)
        dimension = self.vector_index.dimension
        if dimension is not None and len(vector) != dimension:
            raise ValueError(
                f"Image query dimension {len(vector)} does not match "
                f"product embedding dimension {dimension}."
            )
        candidates = []
        for product_id, embedding in self.vector_index.all_embeddings().items():
            product = self.repository.find_by_id(product_id)
            if product is None:
                continue
            score = self.image_service.cosine_similarity(vector, embedding)
            candidates.append((product, float(score)))
        return candidates
