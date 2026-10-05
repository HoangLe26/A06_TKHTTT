# Báo cáo tích hợp ngày 05/10/2026

## Kết quả kiểm tra thực tế

Môi trường: Windows, Python 3.13.2, NumPy 2.5.3, Node 20.19.2. Giao diện dùng HTML/JavaScript hiện có, backend dùng HTTP server thư viện chuẩn Python, không thêm framework Python.

| Nhóm | Lệnh | Kết quả |
| --- | --- | --- |
| API và search pipeline | `python -m unittest discover -s CodePython/tests -v` | 15/15 test methods đạt, nhiều trường hợp con |
| JavaScript DOM + API thật | `npm test` trong `FrontEnd`, server ở cổng 8000 | 33/33 kiểm tra thao tác đạt |
| Cú pháp JavaScript | `node --check` với 5 file assets JS | Đạt |

Các test DOM dùng [jsdom](https://github.com/jsdom/jsdom), mô phỏng DOM và chạy các script local với API Python thật. Tài nguyên ngoài CDN được bỏ qua trong test. Dialog, scroll, object URL preview và print được thay bằng hàm mô phỏng để kiểm tra luồng; chúng không chứng minh việc render/giải mã ảnh/in thực tế của browser.

Những hành vi đã kiểm tra: kết quả default, liên kết điều hướng, lọc danh mục/tồn kho, top-k, nhập và Enter, preset, Clear, chi tiết sản phẩm, lỗi kết nối, no-results, chống chèn HTML qua query summary, voice transcript, grid/list toggle, image vector sai chiều/zero, threshold, upload-preview yêu cầu vector mới, giới hạn file, ba đơn hàng/tổng tiền, unknown order, reset và nút không hỗ trợ bị vô hiệu hóa.

## Ví dụ kết quả từ backend

| Input | Kết quả đứng đầu | Điểm / total |
| --- | --- | --- |
| Text: black shoes | Nike Running Shoes | keyword score 2.0000 |
| Voice: find running shoes | Nike Running Shoes | keyword score 2.0000 |
| Image preset: [0.95, 0.10, 0.15] | Nike Running Shoes | similarity 1.0000 |
| Image preset: [0.12, 0.20, 0.93] | Black Leather Bag | similarity 1.0000 |
| Order O001 | Shipped | 175.00 USD |
| Order O002 | Delivered | 135.00 USD |
| Order O003 | Processing | 75.00 USD |

## Phạm vi kiểm tra còn thiếu

Công cụ điều khiển trình duyệt trả danh sách browser rỗng nên không có screenshot hoặc kiểm tra responsive bằng browser thật. Cần mở URL local để rà lại bố cục desktop/mobile, font/icon CDN, preview JPEG/PNG và hộp thoại in. File `screen.png` trong từng folder là bản thiết kế cũ, được giữ nguyên.

## API

- `GET /api/health`: trạng thái, số sản phẩm/đơn, chiều vector và chế độ mô phỏng.
- `GET /api/catalog`: sản phẩm, danh mục, chiều vector và đường dẫn ảnh minh họa.
- `POST /api/search`: JSON gồm `type`, `query` hoặc `embedding`, `top_k`, `filters` và `min_similarity` tùy chọn.
- `GET /api/products/{id}`: một sản phẩm.
- `GET /api/orders`: các đơn mẫu.
- `GET /api/orders/{id}`: một đơn với sản phẩm và tổng tiền được tính.

Ví dụ request tìm kiếm ảnh:

```json
{"type":"image","embedding":[0.12,0.20,0.93],"top_k":3,"filters":{"category":null,"in_stock":false},"min_similarity":0.85}
```

`filters` hỗ trợ `category`, `in_stock`, `max_price`; `min_similarity` chỉ áp dụng image. Bộ lọc chạy sau retrieval và trước ranking/top-k. API trả candidate_count trước lọc, filtered_count trước top-k, returned_count sau top-k và duration_ms của xử lý server.

Ảnh preview không được POST lên API. Static routes chỉ phục vụ bốn trang, assets JS/CSS và ảnh minh họa; không công khai JSON, mã Python, file báo cáo hay thư mục `.git`.
