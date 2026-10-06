"""Đọc và kiểm tra catalog JSON, không phụ thuộc folder hiện hành của terminal."""

from copy import deepcopy
import json
import math
from pathlib import Path

from .image_vector_repository import load_image_vectors, DIMENSION, MODEL_ID


class ProductRepository:
    """Nạp sản phẩm một lần vào bộ nhớ và cung cấp thao tác tra cứu theo ID."""

    def __init__(self, data_path=None):
        """Đọc products.json mặc định hoặc file được chỉ định và kiểm tra dữ liệu."""
        # Lấy đường dẫn theo vị trí file Python để chạy từ folder nào cũng được.
        self.data_path = (
            Path(data_path) if data_path is not None
            else Path(__file__).resolve().with_name("products.json")
        )
        try:
            with self.data_path.open(encoding="utf-8") as source:
                products = json.load(source)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Product data file not found: {self.data_path}"
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"Invalid product JSON: {self.data_path}: {exc}") from exc
        if not isinstance(products, list):
            raise ValueError("Product data must be a JSON list.")
        # Kiểm tra từng bản ghi và cấm ID trùng trước khi lập bảng tra cứu.
        seen = set()
        for position, product in enumerate(products, start=1):
            self._validate_product(product, position)
            product_id = product["id"]
            if product_id in seen:
                raise ValueError(f"Duplicate product id: {product_id}")
            seen.add(product_id)
        self.image_index_error = None
        # Catalog mặc định dùng vector thật từ cache riêng, không còn vector giả lập.
        # File dữ liệu tùy chọn vẫn được giữ nguyên để test thuật toán độc lập.
        if data_path is None:
            try:
                vectors = load_image_vectors(products)
                for product in products:
                    product.update(embedding=vectors[product['id']], embedding_is_artificial=False,
                                   embedding_dimension=DIMENSION, embedding_model=MODEL_ID)
            except ValueError as exc:
                self.image_index_error = str(exc)
                for product in products:
                    product.pop('embedding', None)
                    product.pop('embedding_is_artificial', None)
        self._products = products
        # Dictionary giúp tra theo ID mà không phải duyệt toàn bộ danh sách.
        self._by_id = {product["id"]: product for product in products}

    @staticmethod
    def _validate_product(product, position):
        """Kiểm tra ID, tên/danh mục/màu, giá, tồn kho và từ khóa bổ sung."""
        prefix = f"Product record {position}"
        if not isinstance(product, dict):
            raise ValueError(f"{prefix} must be an object.")
        product_id = product.get("id")
        if not isinstance(product_id, int) or isinstance(product_id, bool):
            raise ValueError(f"{prefix} must have an integer id.")
        for field in ("name", "category", "color"):
            value = product.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{prefix}: {field} must be a nonempty string.")
        # Giá phải hữu hạn và không âm; bool không được coi là số giá hợp lệ.
        price = product.get("price")
        try:
            valid_price = (
                isinstance(price, (int, float)) and not isinstance(price, bool)
                and math.isfinite(price) and price >= 0
            )
        except OverflowError:
            valid_price = False
        if not valid_price:
            raise ValueError(f"{prefix}: price must be a finite nonnegative number.")
        stock = product.get("stock")
        if not isinstance(stock, int) or isinstance(stock, bool) or stock < 0:
            raise ValueError(f"{prefix}: stock must be a nonnegative integer.")
        terms = product.get('search_terms', [])
        if not isinstance(terms, list) or any(not isinstance(term, str) for term in terms):
            raise ValueError(f"{prefix}: search_terms must be a list of strings.")

    def all_products(self):
        """Trả bản sao sâu để nơi gọi không sửa nhầm dữ liệu gốc trong kho."""
        return deepcopy(self._products)

    def find_by_id(self, product_id):
        """Trả bản sao sản phẩm theo ID hoặc None khi ID không có trong kho."""
        product = self._by_id.get(product_id)
        return deepcopy(product) if product is not None else None
