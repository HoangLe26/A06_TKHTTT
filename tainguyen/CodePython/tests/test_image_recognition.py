"""Kiểm thử ảnh thật, offline inference, cache và tuyến upload HTTP."""

import base64
import http.client
from io import BytesIO
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from CodePython.application import image_embedding_service as image
from CodePython.data.image_vector_repository import (INDEX_PATH, IMAGE_ROOT,
    load_image_vectors, image_path)
from CodePython.data.product_repository import ProductRepository
from CodePython.web_server import SearchHTTPServer, SearchRequestHandler, build_services


def png_bytes(mode='RGB', color='red'):
    from PIL import Image
    output = BytesIO()
    Image.new(mode, (8, 8), color).save(output, format='PNG')
    return output.getvalue()


class ImageValidationTests(unittest.TestCase):
    def test_rgb_decode(self):
        result = image.decode_image({'image_base64': base64.b64encode(png_bytes()).decode()})
        self.assertEqual(result.mode, 'RGB')
        self.assertEqual(result.size, (8, 8))

    def test_alpha_is_composited_on_white(self):
        result = image.read_image(png_bytes('RGBA', (0, 0, 0, 0)))
        self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))

    def test_exif_orientation(self):
        from PIL import Image
        source = Image.new('RGB', (8, 4), 'red')
        exif = source.getexif(); exif[274] = 6
        output = BytesIO(); source.save(output, 'JPEG', exif=exif)
        self.assertEqual(image.read_image(output.getvalue()).size, (4, 8))

    def test_invalid_base64(self):
        for value in (None, '', False, '!!!!', 'data:image/png;base64,AAAA'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                image.decode_image({'image_base64': value})

    def test_corrupt_image(self):
        with self.assertRaises(ValueError):
            image.read_image(b'\x89PNG\r\n\x1a\nnot a valid image')

    def test_gif_and_svg_rejected(self):
        from PIL import Image
        output = BytesIO(); Image.new('RGB', (8, 8)).save(output, 'GIF')
        for data in (output.getvalue(), b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'):
            with self.assertRaises(ValueError):
                image.read_image(data)

    def test_pixel_limit_before_decode(self):
        with patch.object(image, 'MAX_PIXELS', 1), self.assertRaises(image.ImageRecognitionError) as raised:
            image.read_image(png_bytes())
        self.assertEqual(raised.exception.status, 413)

    def test_byte_limit(self):
        with patch.object(image, 'MAX_IMAGE_BYTES', 1), self.assertRaises(image.ImageRecognitionError):
            image.read_image(png_bytes())
        with patch.object(image, 'MAX_IMAGE_BYTES', 1), self.assertRaises(image.ImageRecognitionError):
            image.decode_image({'image_base64': 'AAAA' * 2})

    def test_animated_png_rejected(self):
        from PIL import Image
        output = BytesIO()
        Image.new('RGB', (8, 8), 'red').save(output, 'PNG', save_all=True,
            append_images=[Image.new('RGB', (8, 8), 'blue')], duration=100, loop=0)
        with self.assertRaises(ValueError):
            image.read_image(output.getvalue())

    def test_health_missing_model(self):
        with patch.object(image, 'model_installed', return_value=False):
            result = image.image_configuration()
        self.assertFalse(result['configured'])
        self.assertFalse(result['requires_api_key'])
        self.assertIn('setup_clip.py', result['error'])

    def test_health_missing_index(self):
        result = image.image_configuration(False, 'stale index')
        self.assertFalse(result['configured'])

    def test_cache_checks_model_dimension_ids_and_hash(self):
        products = ProductRepository().all_products()
        original = json.loads(INDEX_PATH.read_text(encoding='utf-8'))
        self.assertEqual(len(load_image_vectors(products)), 20)
        for field, value in [('model', 'other'), ('dimension', 3), ('revision', 'other')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'index.json'
                path.write_text(json.dumps({**original, field: value}), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_image_vectors(products, path)
        for mutation in ('hash', 'dimension', 'duplicate_id'):
            data = json.loads(json.dumps(original))
            if mutation == 'hash': data['products'][0]['sha256'] = 'changed'
            elif mutation == 'dimension': data['products'][0]['embedding'] = [1, 0, 0]
            else: data['products'][1]['id'] = data['products'][0]['id']
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'index.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError): load_image_vectors(products, path)

    def test_catalog_image_path_cannot_escape(self):
        with self.assertRaises(ValueError): image_path({'image': '../products.json'})

    def test_missing_cache_does_not_break_text(self):
        with patch('CodePython.data.product_repository.load_image_vectors', side_effect=ValueError('missing index')):
            service, orders = build_services()
        self.assertFalse(service.image_configuration()['configured'])
        self.assertEqual(service.search({'type': 'text', 'query': 'phone'})['returned_count'], 5)
        self.assertEqual(len(orders.all_orders()), 3)
        with self.assertRaises(image.ImageRecognitionError):
            service.search_uploaded_image({'product_id': 1})


class QuietHandler(SearchRequestHandler):
    def log_message(self, *args): pass


@unittest.skipUnless(image.model_installed() and INDEX_PATH.is_file(), 'Install local CLIP model/index first')
class ImageHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service, orders = build_services()
        cls.server = SearchHTTPServer(('127.0.0.1', 0), cls.service, orders)
        cls.server.RequestHandlerClass = QuietHandler
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(5)

    def request(self, payload=None, method='POST', headers=None, path='/api/image-search'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=60)
        try:
            body = json.dumps(payload).encode() if payload is not None else None
            connection.request(method, path, body=body,
                headers={'Content-Type': 'application/json', **(headers or {})})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally: connection.close()

    def upload(self, data, **options):
        return self.request({'image_base64': base64.b64encode(data).decode(), **options})

    def test_real_upload_is_offline_and_ranks_product(self):
        # Local HTTP được phép; mọi kết nối model/API ngoài máy đều bị chặn.
        connect = socket.socket.connect
        def local_only(sock, address):
            if not isinstance(address, tuple) or address[0] not in ('127.0.0.1', '::1'):
                raise AssertionError('External network attempted during image search')
            return connect(sock, address)
        product = self.service.search_service.repository.find_by_id(16)
        with patch.object(socket.socket, 'connect', local_only):
            # Bỏ cache để kiểm tra cả nạp weights/processor từ file local, không chỉ model đã nóng.
            image._model.cache_clear()
            status, result = self.upload(image_path(product).read_bytes(), top_k=3)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['detected_object'], 'mouse')
        self.assertTrue(result['image_offline'])
        self.assertEqual(result['image_source'], 'upload')
        self.assertEqual(result['results'][0]['product']['id'], 16)
        self.assertGreater(result['results'][0]['score'], .9999)
        self.assertEqual(len(result['embedding']), 512)
        self.assertAlmostEqual(sum(x*x for x in result['embedding']), 1, places=5)
        scores = [row['score'] for row in result['results']]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_real_reference_images_match_all_twenty(self):
        for product in self.service.search_service.repository.all_products():
            with self.subTest(product=product['id']):
                status, result = self.request({'product_id': product['id']})
                self.assertEqual(status, 200, result)
                own = next(row for row in result['results'] if row['product']['id'] == product['id'])
                self.assertGreater(own['score'], .9999)
                self.assertIn(result['detected_object'], image.LABELS)

    def test_resized_photo_still_matches(self):
        product = self.service.search_service.repository.find_by_id(19)
        source = image.read_image(image_path(product).read_bytes())
        output = BytesIO(); source.resize((500, 300)).save(output, 'JPEG', quality=85)
        status, result = self.upload(output.getvalue(), top_k=3)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['detected_object'], 'keyboard')
        self.assertEqual(result['results'][0]['product']['id'], 19)

    def test_filters_top_k_and_threshold(self):
        status, result = self.request({'product_id': 16, 'filters': {'category': 'laptop', 'in_stock': True}, 'top_k': 2})
        self.assertEqual(status, 200, result)
        self.assertEqual(result['filtered_count'], 4)
        self.assertEqual(result['returned_count'], 2)
        self.assertTrue(all(row['product']['category'] == 'laptop' for row in result['results']))
        status, result = self.request({'product_id': 16, 'min_similarity': .99})
        self.assertEqual(status, 200, result)
        self.assertTrue(all(row['score'] >= .99 for row in result['results']))

    def test_invalid_options_do_not_load_model(self):
        for payload in ({}, [], {'product_id': True}, {'product_id': 999},
                {'product_id': 1, 'image_base64': 'AAAA'}, {'product_id': 1, 'embedding': [1,2,3]},
                {'product_id': 1, 'top_k': -1}, {'product_id': 1, 'min_similarity': 2},
                {'product_id': 1, 'filters': {'category': 123}}):
            with self.subTest(payload=payload), patch('CodePython.application.web_search_service.embed_image') as encoder:
                self.assertEqual(self.request(payload)[0], 400)
                encoder.assert_not_called()

    def test_corrupt_uploaded_image(self):
        with patch('CodePython.application.web_search_service.embed_image') as encoder:
            self.assertEqual(self.upload(b'not an image')[0], 400)
            encoder.assert_not_called()

    def test_local_origin_only(self):
        self.assertEqual(self.request({'product_id':1}, headers={'Origin':'https://other.example'})[0], 403)

    def test_get_and_content_type(self):
        self.assertEqual(self.request(method='GET')[0], 405)
        self.assertEqual(self.request({'product_id':1}, headers={'Content-Type':'text/plain'})[0], 415)

    def test_busy_slot_is_released(self):
        self.server.image_slot.acquire()
        try: self.assertEqual(self.request({'product_id':1})[0], 429)
        finally: self.server.image_slot.release()
        self.assertEqual(self.upload(b'bad')[0], 400)
        self.assertTrue(self.server.image_slot.acquire(blocking=False))
        self.server.image_slot.release()


if __name__ == '__main__': unittest.main()
