"""Read sample orders and assemble their product and total information."""

import re
from time import perf_counter

from .web_search_service import optional_number, product_for_web


class OrderService:
    def __init__(self, order_repository, product_repository):
        self.order_repository = order_repository
        self.product_repository = product_repository

    def all_orders(self):
        return [self._assemble(order) for order in self.order_repository.all_orders()]

    def find(self, order_id):
        started = perf_counter()
        if not isinstance(order_id, str):
            raise ValueError('Order ID must be text.')
        normalized = order_id.strip().upper()
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{0,63}', normalized):
            raise ValueError('Enter a valid order ID, such as O001.')
        order = self.order_repository.find_by_id(normalized)
        if order is None:
            return None
        return {'order': self._assemble(order), 'duration_ms': round((perf_counter() - started) * 1000, 3)}

    def _assemble(self, order):
        result = dict(order)
        items = []
        for item in order.get('items', []):
            quantity = item.get('quantity')
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                raise ValueError(f"Order {order['id']}: quantity must be a positive integer.")
            product = self.product_repository.find_by_id(item.get('product_id'))
            if product is None:
                raise ValueError(f"Order {order['id']}: product not found.")
            unit_price = optional_number(item.get('unit_price', product['price']), 'unit_price')
            if unit_price is None:
                raise ValueError('unit_price is required.')
            items.append({**item, 'unit_price': unit_price, 'product': product_for_web(product),
                          'line_total': round(unit_price * quantity, 2)})
        subtotal = round(sum(item['line_total'] for item in items), 2)
        shipping = optional_number(order.get('shipping', 0), 'shipping')
        tax = optional_number(order.get('tax', 0), 'tax')
        if shipping is None or tax is None:
            raise ValueError('shipping and tax must be numbers.')
        result.update(items=items, subtotal=subtotal, shipping=shipping, tax=tax,
                      total=round(subtotal + shipping + tax, 2), is_sample=True)
        return result
