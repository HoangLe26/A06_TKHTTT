"""Serve the existing frontend and a small local JSON API using Python only."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import socket
from urllib.parse import unquote, urlsplit

if __package__:
    from .application.order_service import OrderService
    from .application.web_search_service import WebSearchService
    from .data.order_repository import OrderRepository
    from .main import build_ui
else:
    from application.order_service import OrderService
    from application.web_search_service import WebSearchService
    from data.order_repository import OrderRepository
    from main import build_ui

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / 'FrontEnd'
IMAGE_ROOT = Path(__file__).resolve().parent / 'data' / 'images'
PAGES = {
    '/text-search': 'text_search_vintage_editorial/code.html',
    '/voice-search': 'voice_search_vintage_editorial/code.html',
    '/image-search': 'image_search_vintage_editorial/code.html',
    '/order-search': 'order_search_details_vintage_editorial/code.html',
}
MAX_BODY = 65536


def build_services():
    ui = build_ui()
    search = WebSearchService(ui.query_service, ui.speech_service, ui.search_service, ui.ranking_service)
    orders = OrderService(OrderRepository.from_json(), ui.search_service.repository)
    # Fail at startup with a useful diagnostic if demo data is inconsistent.
    orders.all_orders()
    return search, orders


class SearchHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != 'nt'

    def server_bind(self):
        # On Windows SO_REUSEADDR can let two live servers share a port,
        # causing requests to reach an older application instance.
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, address, search_service, order_service, frontend_root=FRONTEND_ROOT):
        self.search_service = search_service
        self.order_service = order_service
        self.frontend_root = Path(frontend_root)
        super().__init__(address, SearchRequestHandler)


class SearchRequestHandler(BaseHTTPRequestHandler):
    server_version = 'MultimodalSearch/1.0'

    def _send(self, status, content, content_type='application/json; charset=utf-8', head=False):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if not head:
            self.wfile.write(content)

    def _file(self, path, head=False):
        if not path.is_file():
            return self._send(404, {'error': 'File not found.'}, head=head)
        content_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        if content_type.startswith('text/') or content_type == 'application/javascript':
            content_type += '; charset=utf-8'
        return self._send(200, path.read_bytes(), content_type, head=head)

    def _static(self, root, relative_path, extensions, head=False):
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root.resolve()) or path.suffix.lower() not in extensions:
            return self._send(404, {'error': 'File not found.'}, head=head)
        return self._file(path, head=head)

    def do_HEAD(self):
        self.do_GET(head=True)

    def do_GET(self, head=False):
        path = unquote(urlsplit(self.path).path)
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/text-search')
            self.send_header('Content-Length', '0')
            return self.end_headers()
        try:
            if path in PAGES:
                return self._file(self.server.frontend_root / PAGES[path], head=head)
            # Support users who already bookmarked the original HTML paths.
            if path.lstrip('/') in PAGES.values():
                return self._file(self.server.frontend_root / path.lstrip('/'), head=head)
            if path.startswith('/assets/'):
                return self._static(self.server.frontend_root / 'assets', path[8:], {'.js', '.css', '.svg'}, head)
            if path.startswith('/product-images/'):
                return self._static(IMAGE_ROOT, path[16:], {'.svg', '.png', '.jpg', '.jpeg', '.webp'}, head)
            if path == '/api/health':
                catalog = self.server.search_service.catalog()
                return self._send(200, {'status': 'ok', 'product_count': len(catalog['products']),
                    'order_count': len(self.server.order_service.all_orders()),
                    'vector_dimension': catalog['vector_dimension'],
                    'voice_mode': 'simulated', 'image_mode': 'artificial vectors'}, head=head)
            if path == '/api/catalog':
                return self._send(200, self.server.search_service.catalog(), head=head)
            if path == '/api/orders':
                return self._send(200, {'orders': self.server.order_service.all_orders()}, head=head)
            if path.startswith('/api/orders/'):
                result = self.server.order_service.find(path[len('/api/orders/'):])
                return self._send(200, result, head=head) if result else self._send(404, {'error': 'Order not found.'}, head=head)
            if path.startswith('/api/products/'):
                try:
                    product_id = int(path[len('/api/products/'):])
                except ValueError:
                    raise ValueError('Product ID must be an integer.') from None
                result = self.server.search_service.product(product_id)
                return self._send(200, {'product': result}, head=head) if result else self._send(404, {'error': 'Product not found.'}, head=head)
            if path == '/api/search':
                return self._send(405, {'error': 'Use POST for search.'}, head=head)
            return self._send(404, {'error': 'Page or endpoint not found.'}, head=head)
        except ValueError as exc:
            return self._send(400, {'error': str(exc)}, head=head)
        except OSError:
            return self._send(500, {'error': 'Unable to read application files.'}, head=head)

    def do_POST(self):
        if urlsplit(self.path).path != '/api/search':
            return self._send(404, {'error': 'Endpoint not found.'})
        if self.headers.get_content_type() != 'application/json':
            return self._send(415, {'error': 'Content-Type must be application/json.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self._send(400, {'error': 'Invalid Content-Length.'})
        if not 0 < length <= MAX_BODY:
            return self._send(413 if length > MAX_BODY else 400, {'error': 'JSON request must be between 1 byte and 64 KiB.'})
        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._send(400, {'error': 'Invalid JSON request.'})
        try:
            return self._send(200, self.server.search_service.search(payload))
        except (ValueError, TypeError) as exc:
            return self._send(400, {'error': str(exc)})


def main(argv=None):
    parser = argparse.ArgumentParser(description='Serve FrontEnd with the Python search API locally.')
    parser.add_argument('--host', choices=['127.0.0.1', 'localhost'], default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    try:
        services = build_services()
        server = SearchHTTPServer((args.host, args.port), *services)
    except (OSError, ValueError, TypeError) as exc:
        print(f'Unable to start web application: {exc}')
        return 1
    print(f'Web application: http://{args.host}:{args.port}/', flush=True)
    print('Voice is simulated; image search uses artificial vectors. Press Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
