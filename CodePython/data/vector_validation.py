"""Shared numeric-vector validation; no dependency on application services."""

from collections.abc import Mapping
import math
from numbers import Real


def validate_embedding(embedding):
    """Return a finite, nonempty, flat list of floats or raise ValueError."""
    if isinstance(embedding, (str, bytes, Mapping)):
        raise ValueError("Image embedding must be a nonempty one-dimensional vector.")
    try:
        values = list(embedding)
    except TypeError as exc:
        raise ValueError("Image embedding must be a numeric vector.") from exc
    if not values:
        raise ValueError("Image embedding cannot be empty.")
    normalized = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (Real, str)):
            raise ValueError("Image embedding must contain only numeric scalar values.")
        try:
            numeric = float(value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError("Image embedding must contain only numeric values.") from exc
        if not math.isfinite(numeric):
            raise ValueError("Image embedding values must be finite.")
        normalized.append(numeric)
    return normalized
