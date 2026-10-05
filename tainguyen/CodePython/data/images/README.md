# Ảnh sản phẩm thật

`CodePython/data/images/catalog/` ở gốc dự án chứa 20 ảnh sản phẩm từ website/CDN chính hãng Apple, ASUS và Logitech, không dùng ảnh sinh bởi AI. Mỗi sản phẩm trong `CodePython/data/products.json` có đường dẫn `image`, trang `source_url` và link gốc `image_source_url`. Folder tài nguyên này chỉ giữ hướng dẫn và các SVG cũ không dùng khi chạy web.

Xem [PRODUCT_SOURCES.md](../PRODUCT_SOURCES.md) để kiểm tra nguồn từng ảnh. Ảnh được lưu cục bộ để giao diện không phụ thuộc vào hotlink. Các tên/model/màu được đối chiếu với nguồn; giá và tồn kho vẫn là demo.

Ảnh thật **không có nghĩa là tìm kiếm đã dùng mô hình thị giác**. Vector 3 chiều được gán thủ công, preset lấy vector từ chính bản ghi sản phẩm. Ảnh riêng tải lên chỉ dùng preview và cần nhập vector tay.

Các file SVG cũ được giữ lại cho lịch sử demo, không còn được dùng cho ảnh sản phẩm hoặc fallback của giao diện hiện tại.

Ảnh/nhãn hiệu thuộc nhà sản xuất; việc lưu nguồn không cấp phép sử dụng thương mại. Cần kiểm tra quyền sử dụng trước khi công khai hoặc kinh doanh.
