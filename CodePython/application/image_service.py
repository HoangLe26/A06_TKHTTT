"""Tính độ tương đồng cosine giữa các vector ảnh CLIP đã được kiểm tra."""

import numpy as np

# Hỗ trợ cả import qua gói CodePython và chạy từ file main.py trực tiếp.
if __package__ and '.' in __package__:
    from ..data.vector_validation import validate_embedding
else:
    from data.vector_validation import validate_embedding


def normalize_embedding(embedding):
    """Trả bản sao vector dạng số thực hữu hạn; không chuẩn hóa độ dài về 1."""
    return validate_embedding(embedding)


class ImageService:
    """So sánh vector; ImageEmbeddingService phụ trách trích xuất đặc trưng ảnh."""

    def cosine_similarity(self, a, b):
        """Tính cosine trong khoảng [-1, 1]; vector toàn số 0 trả điểm 0."""
        left = np.asarray(normalize_embedding(a), dtype=np.float64)
        right = np.asarray(normalize_embedding(b), dtype=np.float64)
        if left.size != right.size:
            raise ValueError(
                f"Embedding dimension mismatch: {left.size} and {right.size}."
            )
        # Chia theo phần tử lớn nhất trước để tránh tràn hoặc hụt số
        # khi tính tích vô hướng và độ dài với các giá trị quá lớn/nhỏ.
        left_scale = float(np.max(np.abs(left)))
        right_scale = float(np.max(np.abs(right)))
        if left_scale == 0.0 or right_scale == 0.0:
            return 0.0
        left /= left_scale
        right /= right_scale
        # Đưa mỗi vector về độ dài 1, sau đó lấy tích vô hướng làm điểm cosine.
        left /= np.linalg.norm(left)
        right /= np.linalg.norm(right)
        # Giới hạn kết quả để sai số số thực không vượt ra ngoài [-1, 1].
        return float(np.clip(np.dot(left, right), -1.0, 1.0))
