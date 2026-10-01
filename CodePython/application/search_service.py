"""Retrieve unsorted candidates; final ordering belongs to RankingService."""

from collections.abc import Mapping

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
        words = query_text.lower().split()
        if not words:
            return []
        candidates = []
        for product in self.repository.all_products():
            searchable = " ".join(
                product[field] for field in ("name", "category", "color")
            ).lower()
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
