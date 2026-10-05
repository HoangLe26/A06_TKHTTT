# Tài nguyên không bắt buộc khi chạy dự án

Code chạy vẫn nằm trong `CodePython/` và `FrontEnd/` ở gốc dự án. Folder này chỉ giữ tài liệu, công cụ hỗ trợ và các file tham khảo; không có file nào bị xóa.

## Nội dung

- `CodePython/tests/`: kiểm thử backend và API.
- `CodePython/evaluate.py`: đánh giá kết quả của 11 truy vấn mẫu.
- `CodePython/data/download_product_images.py`: tải lại ảnh sản phẩm theo JSON trong folder code gốc.
- `CodePython/README.md`, `CodePython/data/PRODUCT_SOURCES.md`: hướng dẫn và nguồn sản phẩm.
- `CodePython/data/images/`: hướng dẫn ảnh và SVG cũ không được giao diện sử dụng.
- `FrontEnd/tests/`, `package.json`, `package-lock.json`, `node_modules/`: công cụ kiểm thử DOM tùy chọn.
- `FrontEnd/*/screen.png`: ảnh tham khảo thiết kế gốc, không phải tài nguyên hiển thị của web.
- `FrontEnd/README.md`, `FrontEnd/INTEGRATION_NOTES.md`: hướng dẫn giao diện và ghi chú tích hợp.
- `Tài liệu và ânhr/`, các file PDF/DOCX và `TASK5_AI_AGENT_END_TO_END_GUIDE.md`: đề bài, báo cáo, sơ đồ và tài liệu tham khảo.
- `backups/`: các phiên bản sao lưu báo cáo.
- `output/`: tài liệu PDF đã xuất.
- `tmp/`: ảnh kiểm tra bố cục và script tạm khi biên soạn báo cáo.

## Chạy ứng dụng

Từ folder gốc `KiemTra3Tiet`:

```powershell
.\.venv\Scripts\python.exe CodePython/web_server.py
```

Mở `http://127.0.0.1:8000/`. Cách chạy không thay đổi. Giữ `.venv`, dữ liệu JSON và `CodePython/data/images/catalog/` tại vị trí hiện tại. Các file `.gitignore`, `.gitattributes` và folder `.git` phục vụ Git, không nên chuyển vào đây.

## Dùng công cụ hỗ trợ sau khi chuyển

Từ folder gốc:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tainguyen/CodePython/tests -v
.\.venv\Scripts\python.exe tainguyen/CodePython/evaluate.py
.\.venv\Scripts\python.exe tainguyen/CodePython/data/download_product_images.py --missing-only
```

Lệnh tải ảnh cần internet và curl; ảnh được ghi vào `CodePython/data/images/catalog/` ở gốc, không vào `tainguyen`.

Kiểm thử DOM cần server Python đang chạy, Node và npm:

```powershell
cd tainguyen/FrontEnd
npm ci --ignore-scripts
npm test
```

Nếu server dùng cổng khác, đặt `$env:SEARCH_BASE_URL='http://127.0.0.1:8001'` trước khi chạy test. Cache `__pycache__` có thể tự xuất hiện lại khi chạy Python; không phải file nguồn cần sắp xếp thủ công.
