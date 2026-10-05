"""Kho đơn hàng trong bộ nhớ, có thể nạp dữ liệu đơn mẫu từ orders.json."""

from copy import deepcopy
import json
from pathlib import Path


class OrderRepository:
    """Lưu đơn hàng tách biệt với kho sản phẩm; tra đơn là chức năng mở rộng."""

    def __init__(self, orders=()):
        """Tạo kho và thêm các đơn đầu vào qua cùng bước kiểm tra dữ liệu."""
        self._orders = {}
        for order in orders:
            self.add(order)

    def add(self, order):
        """Thêm bản sao của đơn; không cho phép thiếu ID hoặc trùng ID."""
        if not isinstance(order, dict) or "id" not in order:
            raise ValueError("An order must be a dictionary with an id.")
        order_id = order["id"]
        try:
            if order_id in self._orders:
                raise ValueError(f"Duplicate order id: {order_id}")
            self._orders[order_id] = deepcopy(order)
        # ID phải dùng được làm khóa dictionary, không thể là list/dictionary.
        except TypeError as exc:
            raise ValueError("Order id must be hashable.") from exc

    def all_orders(self):
        """Trả bản sao sâu của danh sách đơn để bảo vệ dữ liệu trong kho."""
        return deepcopy(list(self._orders.values()))

    @classmethod
    def from_json(cls, data_path=None):
        """Đọc danh sách đơn mẫu từ JSON rồi tạo OrderRepository tương ứng."""
        path = Path(data_path) if data_path is not None else Path(__file__).with_name('orders.json')
        try:
            with path.open(encoding='utf-8') as source:
                records = json.load(source)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f'Order data file not found: {path}') from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f'Invalid order JSON: {path}') from exc
        if not isinstance(records, list):
            raise ValueError('Order data must be a JSON list.')
        return cls(records)

    def find_by_id(self, order_id):
        """Tra ID chính xác và trả bản sao đơn, hoặc None nếu không tồn tại."""
        return deepcopy(self._orders.get(order_id))
