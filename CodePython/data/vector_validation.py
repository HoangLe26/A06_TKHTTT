"""Kiểm tra vector dùng chung, không phụ thuộc vào dịch vụ tầng nghiệp vụ."""

from collections.abc import Mapping
import math
from numbers import Real


def validate_embedding(embedding):
    """Đổi vector một chiều, không rỗng sang danh sách số thực hữu hạn."""
    # Không nhận cả chuỗi làm vector; chuỗi số chỉ hợp lệ khi là từng phần tử.
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
        # Loại bool và phần tử lồng nhau; cho phép số hoặc chuỗi số từ console.
        if isinstance(value, bool) or not isinstance(value, (Real, str)):
            raise ValueError("Image embedding must contain only numeric scalar values.")
        try:
            numeric = float(value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError("Image embedding must contain only numeric values.") from exc
        # NaN và vô cực sẽ làm điểm cosine không hợp lệ nên phải loại từ đầu.
        if not math.isfinite(numeric):
            raise ValueError("Image embedding values must be finite.")
        normalized.append(numeric)
    return normalized
