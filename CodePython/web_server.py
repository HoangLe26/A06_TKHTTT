"""Chạy web local, phục vụ giao diện HTML và API JSON bằng thư viện chuẩn Python."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import socket
import threading
from urllib.parse import unquote, urlsplit

# Chọn kiểu import phù hợp khi chạy dạng package hoặc mở file trực tiếp.
if __package__:
    from .application.audio_transcription_service import TranscriptionError
    from .application.image_embedding_service import ImageRecognitionError
    from .application.order_service import OrderService
    from .application.web_search_service import WebSearchService
    from .data.order_repository import OrderRepository
    from .main import build_ui
else:
    from application.audio_transcription_service import TranscriptionError
    from application.image_embedding_service import ImageRecognitionError
    from application.order_service import OrderService
    from application.web_search_service import WebSearchService
    from data.order_repository import OrderRepository
    from main import build_ui

# Xác định tài nguyên theo vị trí code, không phụ thuộc folder của terminal.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / 'FrontEnd'
IMAGE_ROOT = Path(__file__).resolve().parent / 'data' / 'images'
# Chỉ bốn trang đã khai báo được phục vụ, không công khai toàn bộ folder dự án.
PAGES = {
    '/text-search': 'text_search_vintage_editorial/code.html',
    '/voice-search': 'voice_search_vintage_editorial/code.html',
    '/image-search': 'image_search_vintage_editorial/code.html',
    '/order-search': 'order_search_details_vintage_editorial/code.html',
}
# Giới hạn phần thân yêu cầu JSON ở 64 KiB để tránh đọc dữ liệu quá lớn.
MAX_BODY = 65536
# Bản ghi mã hóa base64 lớn hơn dữ liệu nhị phân; giới hạn riêng cho tuyến voice.
MAX_AUDIO_BODY = 3 * 1024 * 1024
MAX_IMAGE_BODY = 17 * 1024 * 1024


def build_services():
    """Dùng lại bộ tìm kiếm console và bổ sung dịch vụ tra đơn cho web."""
    ui = build_ui()
    search = WebSearchService(ui.query_service, ui.speech_service, ui.search_service, ui.ranking_service)
    orders = OrderService(OrderRepository.from_json(), ui.search_service.repository)
    # Kiểm tra đơn mẫu ngay lúc khởi động để báo sớm nếu dữ liệu bị sai.
    orders.all_orders()
    return search, orders


class SearchHTTPServer(ThreadingHTTPServer):
    """HTTP server xử lý nhiều yêu cầu bằng luồng riêng và giữ các service dùng chung."""

    daemon_threads = True
    allow_reuse_address = os.name != 'nt'

    def server_bind(self):
        """Gắn server vào địa chỉ/cổng, không cho chia sẻ cổng đang chạy trên Windows."""
        # SO_REUSEADDR trên Windows có thể cho hai server dùng chung cổng,
        # khiến request đi nhầm tới phiên bản ứng dụng cũ.
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, address, search_service, order_service, frontend_root=FRONTEND_ROOT):
        """Lưu dịch vụ và folder giao diện trước khi khởi tạo bộ xử lý HTTP."""
        self.search_service = search_service
        self.order_service = order_service
        self.frontend_root = Path(frontend_root)
        # Chỉ cho một lần phiên âm chạy cùng lúc để hạn chế yêu cầu API trùng lặp.
        self.audio_slot = threading.BoundedSemaphore(1)
        # Mỗi lần chỉ xử lý một ảnh để tránh nhiều inference CPU tranh tài nguyên.
        self.image_slot = threading.BoundedSemaphore(1)
        super().__init__(address, SearchRequestHandler)


class SearchRequestHandler(BaseHTTPRequestHandler):
    """Phân tuyến HTTP, kiểm tra yêu cầu và trả file tĩnh hoặc dữ liệu JSON."""

    server_version = 'MultimodalSearch/1.0'

    def _send(self, status, content, content_type='application/json; charset=utf-8', head=False):
        """Gửi mã trạng thái, header và nội dung; HEAD chỉ gửi header."""
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        # Yêu cầu browser dùng đúng kiểu nội dung và không lưu phản hồi cũ vào cache.
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if not head:
            self.wfile.write(content)

    def _file(self, path, head=False):
        """Đọc file tồn tại và xác định Content-Type theo phần mở rộng."""
        if not path.is_file():
            return self._send(404, {'error': 'File not found.'}, head=head)
        content_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        if content_type.startswith('text/') or content_type == 'application/javascript':
            content_type += '; charset=utf-8'
        return self._send(200, path.read_bytes(), content_type, head=head)

    def _static(self, root, relative_path, extensions, head=False):
        """Chỉ cho đọc file trong folder cho phép và có phần mở rộng hợp lệ."""
        path = (root / relative_path).resolve()
        # resolve và kiểm tra phạm vi chặn đường dẫn ../ truy cập ra ngoài folder.
        if not path.is_relative_to(root.resolve()) or path.suffix.lower() not in extensions:
            return self._send(404, {'error': 'File not found.'}, head=head)
        return self._file(path, head=head)

    def do_HEAD(self):
        """Dùng lại tuyến GET nhưng không gửi phần thân phản hồi."""
        self.do_GET(head=True)

    def do_GET(self, head=False):
        """Phục vụ trang giao diện, tài nguyên, catalog, sản phẩm và đơn hàng."""
        path = unquote(urlsplit(self.path).path)
        # Trang gốc chuyển người dùng đến màn hình Text Search.
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/text-search')
            self.send_header('Content-Length', '0')
            return self.end_headers()
        try:
            if path in PAGES:
                return self._file(self.server.frontend_root / PAGES[path], head=head)
            # Giữ tương thích với bookmark trỏ vào đường dẫn HTML ban đầu.
            if path.lstrip('/') in PAGES.values():
                return self._file(self.server.frontend_root / path.lstrip('/'), head=head)
            # Tài nguyên giao diện và ảnh có folder gốc/phần mở rộng riêng được phép.
            if path.startswith('/assets/'):
                return self._static(self.server.frontend_root / 'assets', path[8:], {'.js', '.css', '.svg'}, head)
            if path.startswith('/product-images/'):
                return self._static(IMAGE_ROOT, path[16:], {'.svg', '.png', '.jpg', '.jpeg', '.webp'}, head)
            # API trạng thái chỉ trả thông tin cấu hình voice, không công khai key.
            if path == '/api/health':
                catalog = self.server.search_service.catalog()
                return self._send(200, {'status': 'ok', 'product_count': len(catalog['products']),
                    'order_count': len(self.server.order_service.all_orders()),
                    'vector_dimension': catalog['vector_dimension'],
                    'voice_mode': 'offline vosk + typed transcript',
                    'voice_api': self.server.search_service.speech_service.audio_configuration(),
                    'image_mode': 'offline CLIP image embeddings',
                    'image_api': self.server.search_service.image_configuration()}, head=head)
            # Các tuyến dữ liệu chỉ đọc: catalog, danh sách/chi tiết đơn và sản phẩm.
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
            # Tìm kiếm cần nhận JSON đầu vào nên không hỗ trợ GET.
            if path in {'/api/search', '/api/voice-search', '/api/image-search'}:
                return self._send(405, {'error': 'Use POST for search.'}, head=head)
            return self._send(404, {'error': 'Page or endpoint not found.'}, head=head)
        except ValueError as exc:
            return self._send(400, {'error': str(exc)}, head=head)
        except OSError:
            return self._send(500, {'error': 'Unable to read application files.'}, head=head)

    def do_POST(self):
        """Nhận truy vấn hoặc bản ghi base64; kiểm tra trước khi tìm kiếm/gọi API."""
        path = urlsplit(self.path).path
        if path not in {'/api/search', '/api/voice-search', '/api/image-search'}:
            return self._send(404, {'error': 'Endpoint not found.'})
        is_audio = path == '/api/voice-search'
        is_image = path == '/api/image-search'
        if is_audio or is_image:
            # Chặn website khác gửi âm thanh để chiếm tài nguyên server local.
            host = self.headers.get('Host', '').lower()
            allowed_hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            origin = self.headers.get('Origin')
            if host not in allowed_hosts or (origin is not None and origin != 'http://' + host):
                return self._send(403, {'error': 'Media must be submitted from the local application.'})
        # Hai tuyến cùng nhận JSON; âm thanh là base64, không dùng bộ phân tích form cgi.
        if self.headers.get_content_type() != 'application/json':
            return self._send(415, {'error': 'Content-Type must be application/json.'})
        if self.headers.get('Transfer-Encoding'):
            return self._send(400, {'error': 'Use a request with Content-Length.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self._send(400, {'error': 'Invalid Content-Length.'})
        # Kiểm tra độ dài trước khi đọc request để tránh nạp quá nhiều dữ liệu.
        maximum = MAX_AUDIO_BODY if is_audio else MAX_IMAGE_BODY if is_image else MAX_BODY
        if not 0 < length <= maximum:
            message = ('Audio JSON must be between 1 byte and 3 MiB.' if is_audio else
                       'Image JSON must be between 1 byte and 17 MiB.' if is_image else
                       'JSON request must be between 1 byte and 64 KiB.')
            return self._send(413 if length > maximum else 400, {'error': message})
        try:
            self.connection.settimeout(90)
            raw = self.rfile.read(length)
            if len(raw) != length:
                return self._send(400, {'error': 'Incomplete request body.'})
            payload = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._send(400, {'error': 'Invalid JSON request.'})
        except TimeoutError:
            return self._send(408, {'error': 'Request upload timed out.'})
        # Lỗi kiểm tra đầu vào trả HTTP 400 dưới dạng JSON cho giao diện hiển thị.
        try:
            if is_image:
                if not self.server.image_slot.acquire(blocking=False):
                    return self._send(429, {'error': 'Another image is being processed. Please wait.'})
                try:
                    result = self.server.search_service.search_uploaded_image(payload)
                finally:
                    self.server.image_slot.release()
                return self._send(200, result)
            if is_audio:
                if not self.server.audio_slot.acquire(blocking=False):
                    return self._send(429, {'error': 'Another voice recording is being processed. Please wait.'})
                try:
                    result = self.server.search_service.search_audio(payload)
                finally:
                    self.server.audio_slot.release()
                return self._send(200, result)
            return self._send(200, self.server.search_service.search(payload))
        except (TranscriptionError, ImageRecognitionError) as exc:
            return self._send(exc.status, {'error': str(exc)})
        except (ValueError, TypeError) as exc:
            return self._send(400, {'error': str(exc)})


def main(argv=None):
    """Đọc host/port, khởi động server local và đóng socket khi dừng."""
    parser = argparse.ArgumentParser(description='Serve FrontEnd with the Python search API locally.')
    # Chỉ cho phép lắng nghe trên máy local, không mở server cho mạng bên ngoài.
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
    print('Voice: offline English Vosk. Image: offline CLIP (512 dimensions). No API key. Press Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
    finally:
        # Luôn giải phóng socket, kể cả khi người dùng dừng bằng Ctrl+C.
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
