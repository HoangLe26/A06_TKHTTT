"""Cosine similarity over artificial, validated image feature vectors."""

import numpy as np

if __package__ and '.' in __package__:
    from ..data.vector_validation import validate_embedding
else:
    from data.vector_validation import validate_embedding


def normalize_embedding(embedding):
    """Validate an embedding and return an independent list of finite floats."""
    return validate_embedding(embedding)


class ImageService:
    def cosine_similarity(self, a, b):
        left = np.asarray(normalize_embedding(a), dtype=np.float64)
        right = np.asarray(normalize_embedding(b), dtype=np.float64)
        if left.size != right.size:
            raise ValueError(
                f"Embedding dimension mismatch: {left.size} and {right.size}."
            )
        # Scale first so large or tiny finite values do not overflow or
        # underflow during the dot product and norm calculations.
        left_scale = float(np.max(np.abs(left)))
        right_scale = float(np.max(np.abs(right)))
        if left_scale == 0.0 or right_scale == 0.0:
            return 0.0
        left /= left_scale
        right /= right_scale
        left /= np.linalg.norm(left)
        right /= np.linalg.norm(right)
        return float(np.clip(np.dot(left, right), -1.0, 1.0))
