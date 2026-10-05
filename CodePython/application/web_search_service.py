"""Chuyển yêu cầu JSON của giao diện web vào luồng tìm kiếm Python dùng chung."""

from collections.abc import Mapping
import math
from time import perf_counter


def product_for_web(product):
    """Tạo bản sao sản phẩm và thêm URL phục vụ ảnh chính hãng lưu trên máy."""
    result = dict(product)
    result['image_url'] = '/product-images/' + product['image'] if product.get('image') else None
    result['image_is_illustration'] = False
    return result


def optional_number(value, name, minimum=0, maximum=None):
    """Cho phép None; nếu có giá trị thì phải là số hữu hạn trong khoảng hợp lệ."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number.')
    try:
        valid = math.isfinite(value) and value >= minimum
        if maximum is not None:
            valid = valid and value <= maximum
    except OverflowError:
        valid = False
    if not valid:
        bounds = f'{minimum} or greater' if maximum is None else f'between {minimum} and {maximum}'
        raise ValueError(f'{name} must be finite and {bounds}.')
    return float(value)


class WebSearchService:
    """Cung cấp catalog, chi tiết sản phẩm, tìm kiếm và bộ lọc cho API web."""

    def __init__(self, query_service, speech_service, search_service, ranking_service):
        """Dùng lại các service của console để tránh viết hai thuật toán riêng."""
        self.query_service = query_service
        self.speech_service = speech_service
        self.search_service = search_service
        self.ranking_service = ranking_service

    def catalog(self):
        """Trả toàn bộ sản phẩm, nhãn danh mục tiếng Anh và số chiều vector."""
        products = self.search_service.repository.all_products()
        return {
            'products': [product_for_web(product) for product in products],
            'categories': sorted({product['category'] for product in products}),
            'category_labels': {'phone': 'Phones', 'tablet': 'Tablets',
                                'laptop': 'Laptops', 'accessory': 'Accessories'},
            'vector_dimension': self.search_service.vector_index.dimension,
        }

    def product(self, product_id):
        """Trả thông tin một sản phẩm theo ID, hoặc None nếu không tìm thấy."""
        product = self.search_service.repository.find_by_id(product_id)
        return product_for_web(product) if product is not None else None

    def search(self, payload):
        """Kiểm tra đầu vào, tìm ứng viên, lọc rồi xếp hạng và tạo JSON kết quả."""
        started = perf_counter()
        if not isinstance(payload, Mapping):
            raise ValueError('Request body must be a JSON object.')
        mode = payload.get('type')
        transcript = None
        # Chuẩn hóa ba kiểu đầu vào; voice chỉ mô phỏng bằng văn bản phiên âm.
        if mode == 'text':
            query = self.query_service.text_query(payload.get('query'))
        elif mode == 'voice':
            transcript = self.speech_service.transcribe(payload.get('query'))
            query = self.query_service.voice_query(transcript)
        elif mode == 'image':
            query = self.query_service.image_query(payload.get('embedding'))
        else:
            raise ValueError('Search type must be text, voice, or image.')
        # Duyệt catalog chỉ áp dụng cho text với ô nhập trống, không phải tìm từ khóa.
        browse_catalog = payload.get('browse_catalog', False)
        if not isinstance(browse_catalog, bool):
            raise ValueError('browse_catalog must be true or false.')
        if browse_catalog and (mode != 'text' or query['query'].strip()):
            raise ValueError('Catalog browsing requires text mode with an empty query.')
        top_k = payload.get('top_k')
        if top_k is not None and (
            not isinstance(top_k, int) or isinstance(top_k, bool) or not 0 <= top_k <= 100
        ):
            raise ValueError('top_k must be an integer between 0 and 100, or null.')
        # Kiểm tra bộ lọc rõ ràng từ giao diện, không suy diễn từ câu tìm kiếm.
        filters = payload.get('filters', {})
        if not isinstance(filters, Mapping):
            raise ValueError('filters must be a JSON object.')
        unknown = set(filters) - {'category', 'in_stock', 'max_price'}
        if unknown:
            raise ValueError('Unsupported filters: ' + ', '.join(sorted(unknown)))
        category = filters.get('category')
        if category is not None and not isinstance(category, str):
            raise ValueError('category must be a string or null.')
        category = category.strip().lower() if category else None
        in_stock = filters.get('in_stock', False)
        if not isinstance(in_stock, bool):
            raise ValueError('in_stock must be true or false.')
        max_price = optional_number(filters.get('max_price'), 'max_price')
        threshold = optional_number(payload.get('min_similarity'), 'min_similarity', -1, 1)
        if threshold is not None and mode != 'image':
            raise ValueError('min_similarity is only supported for image search.')
        # Duyệt catalog lấy tất cả sản phẩm với điểm nội bộ 0; giao diện không
        # hiển thị điểm này như điểm liên quan của một truy vấn từ khóa.
        candidates = (
            [(product, 0.0) for product in self.search_service.repository.all_products()]
            if browse_catalog else self.search_service.search(query)
        )
        # Lọc trước top-k để sản phẩm bị loại không chiếm chỗ của kết quả hợp lệ.
        filtered = [
            (product, score) for product, score in candidates
            if (category is None or product['category'].lower() == category)
            and (not in_stock or product['stock'] > 0)
            and (max_price is None or product['price'] <= max_price)
            and (threshold is None or score >= threshold)
        ]
        ranked = self.ranking_service.rank(filtered, top_k=top_k)
        # Trả cả dữ liệu kết quả và số lượng ở từng bước để giao diện mô tả xử lý.
        return {
            'query': query,
            'transcribed_text': transcript,
            'results': [
                {'product': product_for_web(product), 'score': float(score), 'rank': rank}
                for rank, (product, score) in enumerate(ranked, start=1)
            ],
            'candidate_count': len(candidates),
            'filtered_count': len(filtered),
            'returned_count': len(ranked),
            'duration_ms': round((perf_counter() - started) * 1000, 3),
            'method': ('Catalog browsing' if browse_catalog else
                       'Cosine similarity (artificial vectors)' if mode == 'image' else 'Keyword matching'),
            'browse_catalog': browse_catalog,
            'vector_dimension': self.search_service.vector_index.dimension,
            'filters': {'category': category, 'in_stock': in_stock, 'max_price': max_price},
            'min_similarity': threshold,
        }
