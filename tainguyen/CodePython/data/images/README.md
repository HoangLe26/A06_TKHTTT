# Ảnh sản phẩm thật

`CodePython/data/images/catalog/` ở gốc dự án chứa 20 ảnh sản phẩm từ website/CDN chính hãng Apple, ASUS và Logitech, không dùng ảnh sinh bởi AI. Mỗi sản phẩm trong `CodePython/data/products.json` có đường dẫn `image`, trang `source_url` và link gốc `image_source_url`. Folder tài nguyên này chỉ giữ hướng dẫn và các SVG cũ không dùng khi chạy web.

Xem [PRODUCT_SOURCES.md](../PRODUCT_SOURCES.md) để kiểm tra nguồn từng ảnh. Ảnh được lưu cục bộ để giao diện không phụ thuộc vào hotlink. Các tên/model/màu được đối chiếu với nguồn; giá và tồn kho vẫn là demo.

Image Search dùng CLIP local tạo vector thật 512 chiều từ ảnh catalog và ảnh tải lên. Không còn yêu cầu nhập vector giả lập. Sau khi đổi ảnh, chạy `tainguyen/CodePython/setup_clip.py --reindex` và khởi động lại server. Xem `tainguyen/IMAGE_SEARCH_SETUP.md`.

Các file SVG cũ được giữ lại cho lịch sử demo, không còn được dùng cho ảnh sản phẩm hoặc fallback của giao diện hiện tại.

Ảnh/nhãn hiệu thuộc nhà sản xuất; việc lưu nguồn không cấp phép sử dụng thương mại. Cần kiểm tra quyền sử dụng trước khi công khai hoặc kinh doanh.
