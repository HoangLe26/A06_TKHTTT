"""Exercise the actual HTTP adapter and the existing multimodal pipeline."""

import http.client
import json
from pathlib import Path
import sys
import threading
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web_server import SearchHTTPServer, SearchRequestHandler, build_services


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
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
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

    def test_health_and_catalog(self):
        status, health, _ = self.request('GET', '/api/health')
        self.assertEqual(status, 200)
        self.assertEqual(health['product_count'], 10)
        self.assertEqual(health['order_count'], 3)
        self.assertEqual(health['vector_dimension'], 3)
        _, catalog, _ = self.request('GET', '/api/catalog')
        self.assertEqual(set(catalog['categories']), {'shoes', 'bag', 'clothing', 'accessory'})
        self.assertTrue(all(p['image_url'].startswith('/product-images/') for p in catalog['products']))

    def test_text_retrieval_ranking_and_metadata(self):
        result = self.search({'type': 'text', 'query': 'black shoes'})
        self.assertEqual(result['results'][0]['product']['id'], 1)
        self.assertEqual(result['results'][0]['score'], 2.0)
        self.assertEqual(result['candidate_count'], 8)
        self.assertEqual(result['returned_count'], len(result['results']))
        scores = [item['score'] for item in result['results']]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertGreaterEqual(result['duration_ms'], 0)
        self.assertEqual([item['rank'] for item in result['results']], list(range(1, 9)))

    def test_filters_apply_before_top_k(self):
        result = self.search({'type': 'text', 'query': 'black shoes', 'top_k': 2,
                             'filters': {'category': 'shoes', 'in_stock': True}})
        self.assertEqual(result['candidate_count'], 8)
        self.assertEqual(result['filtered_count'], 5)
        self.assertEqual(result['returned_count'], 2)
        self.assertTrue(all(item['product']['category'] == 'shoes' for item in result['results']))

    def test_explicit_price_filter(self):
        result = self.search({'type': 'text', 'query': 'Nike shoes',
                             'filters': {'category': 'shoes', 'max_price': 99.99}})
        self.assertEqual(result['results'][0]['product']['id'], 5)
        self.assertTrue(all(item['product']['price'] < 100 for item in result['results']))

    def test_simulated_voice_reuses_text_retrieval(self):
        query = 'find running shoes'
        voice = self.search({'type': 'voice', 'query': query})
        text = self.search({'type': 'text', 'query': query})
        self.assertEqual(voice['transcribed_text'], query)
        self.assertEqual(voice['results'], text['results'])

    def test_image_similarity_and_threshold(self):
        result = self.search({'type': 'image', 'embedding': [.12, .2, .93],
                             'min_similarity': .99, 'top_k': 3})
        self.assertEqual(result['results'][0]['product']['id'], 3)
        self.assertAlmostEqual(result['results'][0]['score'], 1.0)
        self.assertTrue(all(item['score'] >= .99 for item in result['results']))

    def test_empty_queries_and_zero_vector(self):
        for query in ['', 'zzznomatchingproductzzz']:
            self.assertEqual(self.search({'type': 'text', 'query': query})['results'], [])
        result = self.search({'type': 'image', 'embedding': [0, 0, 0]})
        self.assertEqual(len(result['results']), 10)
        self.assertTrue(all(item['score'] == 0.0 for item in result['results']))

    def test_invalid_search_data_reports_json_errors(self):
        for payload in [None, [], {}, {'type': 'audio', 'query': 'shoes'},
                        {'type': 'text', 'query': None},
                        {'type': 'image', 'embedding': [1, 2]},
                        {'type': 'image', 'embedding': [1, 'bad', 3]},
                        {'type': 'image', 'embedding': [float('nan'), 0, 1]},
                        {'type': 'text', 'query': 'shoes', 'top_k': -1},
                        {'type': 'text', 'query': 'shoes', 'filters': {'in_stock': 'true'}},
                        {'type': 'image', 'embedding': [1, 0, 0], 'min_similarity': 2}]:
            with self.subTest(payload=payload):
                encoded = json.dumps(payload).encode('utf-8')
                status, result, _ = self.request('POST', '/api/search', encoded)
                self.assertEqual(status, 400)
                self.assertIn('error', result)

    def test_order_details_and_totals(self):
        for order_id, total, status_text in [('O001', 175, 'Shipped'), ('O002', 135, 'Delivered'), ('O003', 75, 'Processing')]:
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

    def test_static_assets_and_illustrations(self):
        for filename in ['api.js', 'site.css', 'text.js', 'voice.js', 'image.js', 'orders.js']:
            with self.subTest(filename=filename):
                self.assertEqual(self.request('GET', '/assets/' + filename)[0], 200)
        for image in ['shoe.svg', 'bag.svg', 'shirt.svg', 'accessory.svg']:
            self.assertEqual(self.request('GET', '/product-images/' + image)[0], 200)

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
