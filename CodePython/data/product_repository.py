"""Read and validate the local product catalogue independently of the CWD."""

from copy import deepcopy
import json
import math
from pathlib import Path


class ProductRepository:
    def __init__(self, data_path=None):
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
        seen = set()
        for position, product in enumerate(products, start=1):
            self._validate_product(product, position)
            product_id = product["id"]
            if product_id in seen:
                raise ValueError(f"Duplicate product id: {product_id}")
            seen.add(product_id)
        self._products = products
        self._by_id = {product["id"]: product for product in products}

    @staticmethod
    def _validate_product(product, position):
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

    def all_products(self):
        """Return independent records so callers cannot alter the catalogue."""
        return deepcopy(self._products)

    def find_by_id(self, product_id):
        product = self._by_id.get(product_id)
        return deepcopy(product) if product is not None else None
