# Giao diện nối với dự án Python

Bốn trang HTML trong folder này đã được nối với API trong `CodePython`. Giữ phong cách vintage của giao diện gốc; kết quả sản phẩm, thứ hạng, số lượng ứng viên và thời gian xử lý hiện lấy từ backend. Các file `screen.png` là ảnh tham khảo thiết kế gốc, không phải ảnh chụp phiên bản đã tích hợp.

## Chạy ứng dụng

Từ thư mục gốc `KiemTra3Tiet`, dùng PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r CodePython/requirements.txt
.\.venv\Scripts\python.exe CodePython/web_server.py
```

Mở `http://127.0.0.1:8000/`. Giữ terminal đang chạy; Ctrl+C để dừng. Nếu dùng môi trường Python khác đã cài NumPy, có thể dùng `python CodePython/web_server.py`. Chạy dạng package bằng `python -m CodePython.web_server` cũng được.

Nếu cổng 8000 đã được dùng, chạy `python CodePython/web_server.py --port 8001`, rồi mở `http://127.0.0.1:8001/`.

Không cần Node/npm để chạy ứng dụng. Không mở `code.html` bằng cách nhấp đúp hoặc dùng một Live Server riêng: các đường dẫn tài nguyên và API được phục vụ cùng origin bởi server Python.

| Trang | URL | Chức năng đã nối |
| --- | --- | --- |
| Text Search | `/text-search` | Search/Enter, Clear, preset, danh mục, top-k, chi tiết sản phẩm |
| Voice Search | `/voice-search` | Văn bản phiên âm chỉnh được, mô phỏng SpeechService, bộ lọc, top-k, xem dạng lưới/danh sách |
| Image Search | `/image-search` | 4 preset điện thoại/máy tính bảng/laptop/phụ kiện, vector nhập tay, cosine, ngưỡng similarity, bộ lọc, preview ảnh cục bộ |
| Order Search | `/order-search` | Tra ID, preset, tra gần đây trong phiên, chi tiết/tổng tiền/tracking mẫu, in hoặc lưu PDF bằng trình duyệt |

## Những điểm đã điều chỉnh để tương thích

- Toàn bộ giao diện hiển thị tiếng Anh, gồm nhãn danh mục Phones / Tablets / Laptops / Accessories, bộ lọc, preset, dialog, thông báo và thuộc tính hỗ trợ truy cập. Từ khóa tìm kiếm tiếng Việt vẫn được hỗ trợ nội bộ; không được dùng làm nhãn giao diện.
- **Filter Facets:** bấm danh mục sẽ xóa từ khóa cũ và giới hạn top-k để duyệt sản phẩm của nhóm; All Categories hiển thị toàn catalog. Nút In Stock Only và biểu tượng check_circle đã được bỏ khỏi Text Search; trang này không lọc tồn kho. Nhập từ khóa rồi Search/Enter để tìm trong nhóm đang chọn; tìm kiếm với ô trống sẽ duyệt nhóm.
- Kết quả sản phẩm mẫu cố định trong HTML được thay bằng 20 sản phẩm có tên thật trong `CodePython/data/products.json`; tên, giá và điểm của các sản phẩm trang mẫu cũ không còn được dùng làm kết quả.
- Nhãn BM25/inverted index được đổi thành keyword matching đúng thuật toán hiện tại.
- Trang voice bỏ nhãn Whisper, dữ liệu âm thanh PCM và confidence giả. Đầu vào là văn bản đã phiên âm; waveform chỉ minh họa.
- Trang image bỏ nhãn ViT/TensorRT, vector 512 chiều và ROI giả. Vector hiện có 3 chiều, được gán thủ công; similarity không phải xác suất nhận dạng đúng.
- Bổ sung `orders.json` với ba đơn mẫu và `OrderService` để trang Order Search lấy dữ liệu thực. `OrderRepository` giữ giao diện dùng trong bộ nhớ cũ và thêm cách tải JSON.
- Hình sản phẩm là 20 ảnh chính hãng lưu cục bộ trong `CodePython/data/images/catalog/`, không sinh bằng AI. Mỗi sản phẩm có link nguồn chính hãng trong View Details; danh sách nguồn nằm ở `CodePython/data/PRODUCT_SOURCES.md`. Mức giá USD dùng để trình diễn, không phải bảng giá bán thật.

## Các phần còn giới hạn

1. **Voice chưa nhận microphone hay file audio.** Muốn nói trực tiếp cần triển khai nhận dạng giọng nói thật.
2. **Image chưa trích xuất embedding từ ảnh tải lên.** Chọn/kéo thả JPEG/PNG chỉ tạo preview trong trình duyệt, không gửi ảnh lên server. Khi chọn ảnh riêng, vector cũ bị xóa; phải nhập vector thủ công trước khi tìm kiếm. Giới hạn preview 12 MB.
3. **Order là dữ liệu demo, chỉ đọc.** Customer History, Return Log, Saved Invoices, Contact Support, Reorder và Update Status chưa có backend nên được vô hiệu hóa kèm giải thích. Tracking là sự kiện ghi trong JSON, không kết nối hãng vận chuyển. Dữ liệu khách hàng/địa chỉ đều là ví dụ giả lập.
4. **Chưa có đăng nhập, giỏ hàng, thanh toán hoặc quản lý profile.** Đây là giao diện tìm kiếm local.
5. **Tìm kiếm text chưa hiểu điều kiện ngôn ngữ tự nhiên** như `under 100 dollars`. API có filter `max_price` rõ ràng cho mở rộng; chưa có ô lọc giá trên giao diện. Keyword/voice nhận tên thật cùng từ khóa danh mục tiếng Anh hoặc tiếng Việt có dấu/không dấu, `chuột` và `bàn phím`; chưa hiểu ngữ nghĩa.
6. **Thiết kế đầy đủ cần truy cập CDN** Tailwind và Google Fonts/Material Symbols. CSS cục bộ có các style cơ bản cho kết quả/dialog; khi offline, hình thức/bố cục có thể không giống thiết kế đầy đủ.
7. **Chưa xác minh bố cục bằng trình duyệt thật trong phiên tích hợp này:** công cụ không có browser kết nối. Đã kiểm tra HTML/JavaScript qua DOM với API thật, không đánh giá layout responsive hay chất lượng render ảnh. Xem `INTEGRATION_NOTES.md`.

Server mặc định chỉ lắng nghe trên máy local `127.0.0.1`; đây là server demo, không phải cấu hình deploy production.

## Kiểm thử

Kiểm thử backend từ folder gốc:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s CodePython/tests -v
```

Kiểm thử JavaScript/DOM là tùy chọn, cần Node 18 trở lên và npm. Giữ server Python đang chạy ở cổng 8000, rồi:

```powershell
cd FrontEnd
npm ci --ignore-scripts
npm test
```

Khi chạy server ở cổng khác, đặt `$env:SEARCH_BASE_URL='http://127.0.0.1:8001'` trước `npm test`.

`package.json`, `package-lock.json`, `tests/integration.cjs` và `node_modules` chỉ phục vụ kiểm thử DOM; không cần chúng để chạy giao diện. `node_modules` đã được bỏ qua bằng `.gitignore`.

Các file `assets/api.js` và `assets/{text,voice,image,orders}.js` gọi API, hiển thị loading/lỗi/no-results, xóa kết quả cũ khi đổi đầu vào và bỏ qua phản hồi từ yêu cầu cũ.

## Bộ sản phẩm mới

Mỗi nhóm `phone`, `tablet`, `laptop`, `accessory` có đúng 5 sản phẩm. Phụ kiện gồm 3 chuột và 2 bàn phím. Giá, tồn kho, đơn hàng và vector vẫn là demo. Hai sản phẩm có tồn kho 0 để thử bộ lọc In Stock Only. Sau khi thay JSON phải khởi động lại server và tải lại trang.
