# Báo cáo tích hợp ngày 05/10/2026

Sau khi sắp xếp tài nguyên: backend test nằm ở `tainguyen/CodePython/tests`; DOM test và package npm nằm ở `tainguyen/FrontEnd`; script tải ảnh nằm ở `tainguyen/CodePython/data/download_product_images.py`. Code chạy vẫn giữ trong `CodePython` và `FrontEnd` ở gốc.

## Kết quả kiểm tra thực tế

Môi trường: Windows, Python 3.13.2, NumPy 2.5.3, Node 20.19.2. Giao diện dùng HTML/JavaScript hiện có, backend dùng HTTP server thư viện chuẩn Python, không thêm framework Python.

| Nhóm | Lệnh | Kết quả |
| --- | --- | --- |
| API và search pipeline | `python -m unittest discover -s tainguyen/CodePython/tests -v` | 19/19 test methods đạt, nhiều trường hợp con |
| JavaScript DOM + API thật | `npm test` trong `tainguyen/FrontEnd`, server ở cổng 8000 | 73/73 kiểm tra thao tác đạt |
| Cú pháp JavaScript | `node --check` với 5 file assets JS | Đạt |

Các test DOM dùng [jsdom](https://github.com/jsdom/jsdom), mô phỏng DOM và chạy các script local với API Python thật. Tài nguyên ngoài CDN được bỏ qua trong test. Dialog, scroll, object URL preview và print được thay bằng hàm mô phỏng để kiểm tra luồng; chúng không chứng minh việc render/giải mã ảnh/in thực tế của browser.

Những hành vi đã kiểm tra: kết quả default, liên kết điều hướng, lọc danh mục/tồn kho, top-k, nhập và Enter, preset, Clear, chi tiết sản phẩm, lỗi kết nối, no-results, chống chèn HTML qua query summary, voice transcript, grid/list toggle, image vector sai chiều/zero, threshold, upload-preview yêu cầu vector mới, giới hạn file, ba đơn hàng/tổng tiền, unknown order, reset và nút không hỗ trợ bị vô hiệu hóa.

## Ví dụ kết quả từ backend

| Input | Kết quả đứng đầu | Điểm / total |
| --- | --- | --- |
| Text: phone | Apple iPhone 16 | keyword score 1.0000 |
| Voice: find laptop | Apple MacBook Air 13-inch M4 (2025) | keyword score 1.0000 |
| Image preset: [0.95, 0.10, 0.05] | Apple iPhone 16 | similarity 1.0000 |
| Image preset: [0.65, 0.70, 0.10] | Apple iPad (A16) | similarity 1.0000 |
| Order O001 | Shipped | 994.00 USD |
| Order O002 | Delivered | 464.00 USD |
| Order O003 | Processing | 1109.00 USD |

## Phạm vi kiểm tra còn thiếu

Công cụ điều khiển trình duyệt trả danh sách browser rỗng nên không có screenshot hoặc kiểm tra responsive bằng browser thật. Cần mở URL local để rà lại bố cục desktop/mobile, font/icon CDN, preview JPEG/PNG và hộp thoại in. File `screen.png` trong từng folder là bản thiết kế cũ, được giữ nguyên.

## API

- `GET /api/health`: trạng thái, số sản phẩm/đơn, chiều vector và chế độ mô phỏng.
- `GET /api/catalog`: sản phẩm, danh mục, chiều vector và đường dẫn ảnh sản phẩm chính hãng và category_labels.
- `POST /api/search`: JSON gồm `type`, `query` hoặc `embedding`, `top_k`, `filters` và `min_similarity` tùy chọn.
- `GET /api/products/{id}`: một sản phẩm.
- `GET /api/orders`: các đơn mẫu.
- `GET /api/orders/{id}`: một đơn với sản phẩm và tổng tiền được tính.

Ví dụ request tìm kiếm ảnh:

```json
{"type":"image","embedding":[0.65,0.70,0.10],"top_k":3,"filters":{"category":null,"in_stock":false},"min_similarity":0.85}
```

`filters` hỗ trợ `category`, `in_stock`, `max_price`; `min_similarity` chỉ áp dụng image. Bộ lọc chạy sau retrieval và trước ranking/top-k. API trả candidate_count trước lọc, filtered_count trước top-k, returned_count sau top-k và duration_ms của xử lý server.

Ảnh preview không được POST lên API. Static routes chỉ phục vụ bốn trang, assets JS/CSS và ảnh sản phẩm; không công khai JSON, mã Python, file báo cáo hay thư mục `.git`.


## Thay bộ dữ liệu sản phẩm

Đã thay toàn bộ catalog cũ bằng 20 sản phẩm: 5 điện thoại, 5 máy tính bảng, 5 laptop, 3 chuột và 2 bàn phím. 20 file JPG/PNG đã tải từ nguồn chính hãng, kiểm tra MIME/đọc file qua HTTP và xem ảnh trực tiếp. Không sử dụng ảnh sinh bởi AI; không dùng SVG cũ làm fallback. Một số iPad và hai MacBook Air dùng ảnh lineup nhiều màu của nhà sản xuất, được ghi rõ trong chi tiết và [nguồn sản phẩm](../CodePython/data/PRODUCT_SOURCES.md).

Giá USD/tồn kho/đơn hàng vẫn là demo; các vector không được trích xuất từ ảnh. Các preset lấy tên, ảnh và vector trực tiếp từ API/catalog, không hardcode dữ liệu sản phẩm cũ. Đơn O001/O002/O003 tham chiếu sản phẩm mới và dùng đơn giá demo tương ứng.

Demo dùng truy vấn tiếng Anh. Đã bỏ dictionary alias, vòng lặp chuyển đổi cụm từ tiếng Việt và các từ khóa tiếng Việt trong catalog; giữ các từ khóa tiếng Anh. Kiểm thử danh mục/phụ kiện dùng `phone`, `smartphone`, `tablet`, `laptop`, `notebook`, `accessories`, `mouse`, `keyboard`, gồm trường hợp chữ hoa và dấu câu. Đã thử bộ lọc tồn kho loại bỏ ID15/20 có stock 0. Console demo chạy đủ ba chế độ; evaluate.py đạt 10/11, giữ ví dụ thất bại về phân tích điều kiện giá tự nhiên.

## Sửa Filter Facets

Toàn bộ chữ Demo trong nội dung hiển thị/tooltip đã được bỏ hoặc thay bằng cách diễn đạt phù hợp. Giá/tồn kho vẫn được mô tả là sample data, không biến thành giá bán thực. Khách hàng/địa chỉ đơn giả lập đổi nhãn sang Sample thay vì Demo; ID, sản phẩm, số lượng và giá trị đơn giữ nguyên. Dòng nhãn danh mục/màu trên thẻ kết quả Text/Voice/Image và dòng sản phẩm trong đơn hàng đã được bỏ; bộ lọc và thông tin Category/Color trong dialog vẫn giữ. Bốn kiểm tra DOM bổ sung xác minh không còn chữ Demo hay nhãn ghép danh mục/màu trên thẻ sản phẩm.

Đã bỏ các nhãn/mô tả intro được yêu cầu ở đầu Text/Voice/Image và thanh Connected trên cả bốn trang. Text bỏ nút demo nhanh cùng icon auto_fix_high; nút Presets trên header vẫn giữ chức năng autofill cũ. Các thông tin còn lại trong thanh đầu trang, điều hướng, tìm kiếm, bộ lọc và dữ liệu không thay đổi. Bốn kiểm tra DOM bổ sung xác minh các intro đã biến mất và phần còn lại vẫn tồn tại; kiểm tra shell không còn phụ thuộc vào banner Connected. API health vẫn được giữ nguyên.

Giao diện của cả bốn trang đã thống nhất tiếng Anh. Nhãn danh mục trả từ API và hiển thị trên filter, card, dialog, dropdown và preset là Phones / Tablets / Laptops / Accessories. Kiểm thử bổ sung kiểm tra `lang="en"`, nội dung và thuộc tính aria-label/placeholder/title/alt không còn nhãn tiếng Việt ở trạng thái mặc định; từ khóa tìm kiếm tiếng Việt vẫn được giữ nội bộ để không làm mất chức năng cũ.

Bấm danh mục trên Text Search xóa từ khóa và giới hạn top-k cũ để duyệt nhóm: 5 sản phẩm mỗi nhóm hoặc 20 ở All Categories. Nút In Stock Only/check_circle cùng state và event handler liên quan đã được bỏ khỏi Text Search; request không gửi bộ lọc tồn kho. Voice/Image và API vẫn giữ chức năng lọc tồn kho riêng. Nhập từ khóa sau đó sẽ tìm trong nhóm đang chọn. API nhận `browse_catalog: true` chỉ với `type: text` và query trống; dùng toàn catalog làm ứng viên trước bộ lọc/top-k. Query trống không có cờ này vẫn giữ hành vi cũ (không có kết quả). Duyệt catalog không hiển thị điểm keyword giả trên card hoặc dialog.

Đã thêm kiểm tra DOM bấm đủ năm nút khi ô tìm kiếm còn `phone` và giới hạn Top 3; kiểm tra kết quả đúng danh mục, reset đầu vào, All Categories và tìm từ khóa sau khi duyệt. Trên Windows, server sử dụng cổng độc quyền để ngăn nhiều instance cùng cổng khiến request tới backend cũ. Test xác minh không thể mở server thứ hai trên cổng đang được phục vụ. Các instance cũ của đúng dự án đã được dừng sau khi cấp quyền; server mới đã chạy và kiểm tra tại cổng 8000.

Quá trình tải ảnh đã xử lý ACL riêng của thư mục tạm trên Windows: copy dữ liệu vào thư mục ảnh trước khi thay file để giữ quyền đọc bình thường. Có script tải lại `tainguyen/CodePython/data/download_product_images.py` (cần internet/curl); không cần chạy lại khi sử dụng giao diện.
