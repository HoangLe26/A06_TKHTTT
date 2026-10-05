"""Small in-memory order repository for the optional architecture component."""

from copy import deepcopy
import json
from pathlib import Path


class OrderRepository:
    """Store order records independently; orders are outside search Task 5."""

    def __init__(self, orders=()):
        self._orders = {}
        for order in orders:
            self.add(order)

    def add(self, order):
        if not isinstance(order, dict) or "id" not in order:
            raise ValueError("An order must be a dictionary with an id.")
        order_id = order["id"]
        try:
            if order_id in self._orders:
                raise ValueError(f"Duplicate order id: {order_id}")
            self._orders[order_id] = deepcopy(order)
        except TypeError as exc:
            raise ValueError("Order id must be hashable.") from exc

    def all_orders(self):
        return deepcopy(list(self._orders.values()))

    @classmethod
    def from_json(cls, data_path=None):
        """Load demo orders without changing the original in-memory interface."""
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
        return deepcopy(self._orders.get(order_id))
