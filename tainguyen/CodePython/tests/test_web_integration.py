"""Exercise the actual HTTP adapter and the existing multimodal pipeline."""

import http.client
from collections import Counter
import json
from pathlib import Path
import sys
import threading
import unittest

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = WORKSPACE_ROOT / 'CodePython'
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from CodePython.web_server import SearchHTTPServer, SearchRequestHandler, build_services


class QuietHandler(SearchRequestHandler):
    def log_message(self, format, *args):
        pass


class WebIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = SearchHTTPServer(('127.0.0.1', 0), *build_services())
        cls.server.RequestHandlerClass = QuietHandler
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, body=None, content_type='application/json'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=30)
        headers = {}
        if body is not None:
            headers['Content-Type'] = content_type
            body = body if isinstance(body, bytes) else json.dumps(body).encode('utf-8')
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            content = response.read()
            content_type = response.getheader('Content-Type', '')
            parsed = json.loads(content) if content and 'application/json' in content_type else content
            return response.status, parsed, dict(response.getheaders())
        finally:
            connection.close()

    def search(self, payload):
        status, result, _ = self.request('POST', '/api/search', payload)
        self.assertEqual(status, 200, result)
        return result

    def test_all_four_pages_are_served_with_connected_scripts(self):
        for mode in ['text', 'voice', 'image', 'order']:
            with self.subTest(mode=mode):
                status, body, headers = self.request('GET', f'/{mode}-search')
                self.assertEqual(status, 200)
                self.assertIn(b'/assets/api.js', body)
                self.assertIn(b'/assets/site.css', body)
                self.assertIn('text/html', headers['Content-Type'])

    def test_running_server_port_cannot_be_shared(self):
        with self.assertRaises(OSError):
            SearchHTTPServer(('127.0.0.1', self.server.server_port), *build_services())

    def test_health_and_catalog(self):
        status, health, _ = self.request('GET', '/api/health')
        self.assertEqual(status, 200)
        self.assertEqual(health['product_count'], 20)
        self.assertEqual(health['order_count'], 3)
        self.assertEqual(health['vector_dimension'], 512)
        self.assertTrue(health['image_api']['configured'])
        _, catalog, _ = self.request('GET', '/api/catalog')
        self.assertEqual(set(catalog['categories']), {'phone', 'tablet', 'laptop', 'accessory'})
        self.assertEqual(catalog['category_labels'],
                         {'phone': 'Phones', 'tablet': 'Tablets',
                          'laptop': 'Laptops', 'accessory': 'Accessories'})
        self.assertEqual(Counter(p['category'] for p in catalog['products']),
                         {'phone': 5, 'tablet': 5, 'laptop': 5, 'accessory': 5})
        self.assertEqual(len({p['name'] for p in catalog['products']}), 20)
        self.assertTrue(all(p['source_url'].startswith('https://') for p in catalog['products']))
        self.assertTrue(all(p['price_is_demo'] and not p['image_is_illustration'] for p in catalog['products']))
        self.assertTrue(all(p['image_url'].startswith('/product-images/') for p in catalog['products']))

    def test_text_retrieval_ranking_and_metadata(self):
        result = self.search({'type': 'text', 'query': 'phone'})
        self.assertEqual(result['results'][0]['product']['id'], 1)
        self.assertEqual(result['results'][0]['score'], 1.0)
        self.assertEqual(result['candidate_count'], 5)
        self.assertEqual(result['returned_count'], len(result['results']))
        scores = [item['score'] for item in result['results']]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertGreaterEqual(result['duration_ms'], 0)
        self.assertEqual([item['rank'] for item in result['results']], list(range(1, 6)))

    def test_filters_apply_before_top_k(self):
        result = self.search({'type': 'text', 'query': 'phone', 'top_k': 2,
                             'filters': {'category': 'phone', 'in_stock': True}})
        self.assertEqual(result['candidate_count'], 5)
        self.assertEqual(result['filtered_count'], 5)
        self.assertEqual(result['returned_count'], 2)
        self.assertTrue(all(item['product']['category'] == 'phone' for item in result['results']))

    def test_explicit_price_filter(self):
        _, catalog, _ = self.request('GET', '/api/catalog')
        phones = [p for p in catalog['products'] if p['category'] == 'phone']
        limit = min(p['price'] for p in phones)
        result = self.search({'type': 'text', 'query': 'phone',
                             'filters': {'category': 'phone', 'max_price': limit}})
        self.assertEqual({item['product']['id'] for item in result['results']},
                         {p['id'] for p in phones if p['price'] <= limit})

    def test_simulated_voice_reuses_text_retrieval(self):
        query = 'find laptop'
        voice = self.search({'type': 'voice', 'query': query})
        text = self.search({'type': 'text', 'query': query})
        self.assertEqual(voice['transcribed_text'], query)
        self.assertEqual(voice['results'], text['results'])

    def test_image_similarity_and_threshold(self):
        _, product, _ = self.request('GET', '/api/products/6')
        result = self.search({'type': 'image', 'embedding': product['product']['embedding'],
                             'min_similarity': .99, 'top_k': 3})
        self.assertEqual(result['results'][0]['product']['id'], 6)
        self.assertAlmostEqual(result['results'][0]['score'], 1.0)
        self.assertTrue(all(item['score'] >= .99 for item in result['results']))

    def test_empty_queries_and_zero_vector(self):
        for query in ['', 'zzznomatchingproductzzz']:
            self.assertEqual(self.search({'type': 'text', 'query': query})['results'], [])
        result = self.search({'type': 'image', 'embedding': [0] * 512})
        self.assertEqual(len(result['results']), 20)
        self.assertTrue(all(item['score'] == 0.0 for item in result['results']))

    def test_catalog_browsing_filters_and_limits(self):
        for category in [None, 'phone', 'tablet', 'laptop', 'accessory']:
            with self.subTest(category=category):
                result = self.search({'type': 'text', 'query': '  ', 'browse_catalog': True,
                                      'filters': {'category': category}})
                self.assertEqual(result['candidate_count'], 20)
                self.assertEqual(result['returned_count'], 20 if category is None else 5)
                self.assertTrue(result['browse_catalog'])
                self.assertEqual(result['method'], 'Catalog browsing')
                if category:
                    self.assertTrue(all(i['product']['category'] == category for i in result['results']))
        result = self.search({'type': 'text', 'query': '', 'browse_catalog': True, 'top_k': 2,
                              'filters': {'category': 'laptop', 'in_stock': True}})
        self.assertEqual(result['filtered_count'], 4)
        self.assertEqual(result['returned_count'], 2)
        self.assertTrue(all(i['product']['stock'] > 0 for i in result['results']))

    def test_invalid_search_data_reports_json_errors(self):
        for payload in [None, [], {}, {'type': 'audio', 'query': 'shoes'},
                        {'type': 'text', 'query': None},
                        {'type': 'image', 'embedding': [1, 2]},
                        {'type': 'image', 'embedding': [1, 'bad', 3]},
                        {'type': 'image', 'embedding': [float('nan'), 0, 1]},
                        {'type': 'text', 'query': 'shoes', 'top_k': -1},
                        {'type': 'text', 'query': 'shoes', 'filters': {'in_stock': 'true'}},
                        {'type': 'text', 'query': '', 'browse_catalog': 'true'},
                        {'type': 'text', 'query': 'phone', 'browse_catalog': True},
                        {'type': 'voice', 'query': '', 'browse_catalog': True},
                        {'type': 'image', 'embedding': [1, 0, 0], 'browse_catalog': True},
                        {'type': 'image', 'embedding': [1, 0, 0], 'min_similarity': 2}]:
            with self.subTest(payload=payload):
                encoded = json.dumps(payload).encode('utf-8')
                status, result, _ = self.request('POST', '/api/search', encoded)
                self.assertEqual(status, 400)
                self.assertIn('error', result)

    def test_order_details_and_totals(self):
        orders = json.loads((PROJECT_ROOT / 'data' / 'orders.json').read_text(encoding='utf-8'))
        for record in orders:
            order_id, status_text = record['id'], record['status']
            total = sum(i['quantity'] * i['unit_price'] for i in record['items']) + record['shipping'] + record['tax']
            with self.subTest(order_id=order_id):
                status, result, _ = self.request('GET', '/api/orders/' + order_id.lower())
                self.assertEqual(status, 200)
                order = result['order']
                self.assertEqual(order['id'], order_id)
                self.assertEqual(order['total'], total)
                self.assertEqual(order['status'], status_text)
                self.assertEqual(order['subtotal'] + order['shipping'] + order['tax'], total)
                self.assertTrue(all(item['product']['id'] == item['product_id'] for item in order['items']))

    def test_missing_orders_and_products(self):
        for path in ['/api/orders/UNKNOWN', '/api/products/9999']:
            status, result, _ = self.request('GET', path)
            self.assertEqual(status, 404)
            self.assertIn('not found', result['error'].lower())
        self.assertEqual(self.request('GET', '/api/orders/bad%20id')[0], 400)

    def test_static_assets_and_real_product_images(self):
        for filename in ['api.js', 'site.css', 'text.js', 'voice.js', 'image.js', 'orders.js']:
            with self.subTest(filename=filename):
                self.assertEqual(self.request('GET', '/assets/' + filename)[0], 200)
        _, catalog, _ = self.request('GET', '/api/catalog')
        for product in catalog['products']:
            with self.subTest(product=product['name']):
                status, body, headers = self.request('GET', product['image_url'])
                self.assertEqual(status, 200)
                self.assertIn(headers['Content-Type'].split(';')[0],
                              ['image/jpeg', 'image/png', 'image/webp'])
                self.assertGreater(len(body), 1000)
                self.assertEqual(body, (PROJECT_ROOT / 'data' / 'images' / product['image']).read_bytes())

    def test_vietnamese_category_and_accessory_queries(self):
        for query, category, count in [('điện thoại', 'phone', 5), ('dien thoai', 'phone', 5),
                                       ('máy tính bảng', 'tablet', 5), ('may tinh bang', 'tablet', 5),
                                       ('laptop', 'laptop', 5), ('chuột', 'accessory', 3),
                                       ('chuot', 'accessory', 3), ('bàn phím', 'accessory', 2),
                                       ('ban phim', 'accessory', 2)]:
            with self.subTest(query=query):
                result = self.search({'type': 'text', 'query': query})
                self.assertEqual(result['returned_count'], count)
                self.assertTrue(all(i['product']['category'] == category for i in result['results']))

    def test_out_of_stock_products_are_filtered(self):
        for category, excluded_id in [('laptop', 15), ('accessory', 20)]:
            unfiltered = self.search({'type': 'image', 'embedding': [0] * 512,
                                      'filters': {'category': category}})
            filtered = self.search({'type': 'image', 'embedding': [0] * 512,
                                    'filters': {'category': category, 'in_stock': True}})
            self.assertEqual(unfiltered['returned_count'], 5)
            self.assertEqual(filtered['returned_count'], 4)
            self.assertNotIn(excluded_id, [i['product']['id'] for i in filtered['results']])

    def test_source_files_and_parent_paths_are_not_public(self):
        for path in ['/assets/../../CodePython/main.py', '/product-images/../products.json',
                     '/.git/config', '/CodePython/data/products.json', '/TASK5_AI_AGENT_END_TO_END_GUIDE.md']:
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path)[0], 404)

    def test_invalid_http_payloads(self):
        self.assertEqual(self.request('POST', '/api/search', b'{bad')[0], 400)
        self.assertEqual(self.request('POST', '/api/search', b'{}', 'text/plain')[0], 415)
        self.assertEqual(self.request('POST', '/api/search', b' ' * 65537)[0], 413)
        self.assertEqual(self.request('GET', '/api/search')[0], 405)

    def test_root_redirect_and_head(self):
        status, body, headers = self.request('GET', '/')
        self.assertEqual(status, 302)
        self.assertEqual(headers['Location'], '/text-search')
        status, body, _ = self.request('HEAD', '/text-search')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'')


if __name__ == '__main__':
    unittest.main()
