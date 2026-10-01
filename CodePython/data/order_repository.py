"""Small in-memory order repository for the optional architecture component."""

from copy import deepcopy


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

    def find_by_id(self, order_id):
        return deepcopy(self._orders.get(order_id))
