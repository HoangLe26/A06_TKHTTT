"""In-memory product embeddings; retrieval and ranking live above this layer."""

from .vector_validation import validate_embedding


class VectorIndex:
    def __init__(self, products):
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
            if embedding is None:
                continue
            try:
                vector = validate_embedding(embedding)
            except ValueError as exc:
                raise ValueError(f"Invalid embedding for product {product_id}: {exc}") from exc
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
        """Vector length, or None when no product has an embedding."""
        return self._dimension

    def all_embeddings(self):
        return {product_id: list(vector) for product_id, vector in self._embeddings.items()}

    def get_embedding(self, product_id):
        vector = self._embeddings.get(product_id)
        return list(vector) if vector is not None else None
