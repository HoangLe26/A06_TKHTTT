# Image Search — local CLIP

## Cách dùng trên máy hiện tại

Đã cài bản CPU, tải model chính thức và tạo vector thật cho 20 ảnh sản phẩm.
Không cần API key, không có phí gọi API. Ảnh chỉ gửi tới Python trên máy.

1. Dừng server cũ bằng `Ctrl + C`, rồi chạy lại tại folder `KiemTra3Tiet`:

   ```powershell
   .\.venv\Scripts\python.exe CodePython/web_server.py
   ```

2. Mở `http://127.0.0.1:8000/image-search`.
3. Bấm **Browse File** hoặc kéo thả ảnh JPEG/PNG, rồi **Search Similar Products**.
4. Xem **Predicted object**, danh sách sản phẩm xếp hạng và **View / Export Generated Vector**.
   Có thể tải vector đầy đủ bằng **Download Vector JSON**.

Các nút reference dùng ảnh catalog thật, không còn dùng vector gán thủ công.
Không tự chạy model khi mở trang; bấm Search hoặc chọn reference để tìm.

## Luồng hoạt động

Ảnh → kiểm tra JPEG/PNG và kích thước → sửa hướng EXIF, ghép nền trắng nếu trong suốt
→ CLIP resize/center crop → vector chuẩn hóa L2 512 chiều → cosine với 20 vector sản phẩm
→ áp dụng bộ lọc → xếp hạng điểm giảm dần → kết quả.

Model: `openai/clip-vit-base-patch32`, revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`.
Ảnh truy vấn và ảnh sản phẩm dùng cùng model và tiền xử lý. Nhãn được dự đoán bằng cách
so ảnh với các mô tả tiếng Anh: phone, tablet, laptop, mouse, keyboard.
Nhãn không tự lọc cứng kết quả; người dùng vẫn quyết định bộ lọc Category.

## Cài lại / clone sang máy khác

Python 3.10+; máy hiện tại đã chạy thử với Python 3.13 trên Windows.
Tải model lần đầu cần mạng; phiên âm/nhận dạng sau khi cài không cần API bên ngoài.
CLIP nặng hơn Vosk: file weights khoảng 605 MB, thư viện PyTorch và RAM còn cần thêm.

```powershell
.\.venv\Scripts\python.exe -m pip install 'torch>=2.6,<3' --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r CodePython/requirements.txt
.\.venv\Scripts\python.exe tainguyen/CodePython/setup_clip.py
```

Bộ cài ghim revision và kiểm tra SHA-256 file weights theo metadata chính thức.
Runtime dùng `local_files_only=True`, `weights_only=True`, CPU và chế độ inference.
Không đọc API key và không tự tải model trong request.

## File quan trọng

- `CodePython/application/image_embedding_service.py`: đọc ảnh, CLIP vector và nhãn dự đoán.
- `CodePython/data/image_vector_repository.py`: xác thực cache, model, số chiều và hash ảnh.
- `CodePython/data/clip_embeddings.json`: vector thật + hash của 20 ảnh, có thể đưa vào Git.
- `CodePython/models/clip-vit-base-patch32/`: model runtime; bỏ qua trong Git vì lớn.
- `tainguyen/CodePython/setup_clip.py`: tải model và tạo lại cache; không cần chạy mỗi lần tìm.
- `POST /api/image-search`: nhận `image_base64` hoặc `product_id` của ảnh reference.
- `FrontEnd/assets/image.js`: tải/preview ảnh, gọi Python, hiển thị và xuất vector.

`products.json` chỉ giữ thông tin catalog; vector giả lập 3 chiều đã được bỏ.
ProductRepository ghép vector thật từ cache vào sản phẩm khi khởi tạo.
Text, Vosk voice và order search vẫn hoạt động nếu model/index ảnh chưa cài.
Image Search báo lỗi rõ ràng, không dùng lại vector giả lập làm phương án dự phòng.

## Khi thay ảnh hoặc thêm sản phẩm

Chạy lệnh này để tính lại vector offline, sau đó khởi động lại server:

```powershell
.\.venv\Scripts\python.exe tainguyen/CodePython/setup_clip.py --reindex
```

Nếu hash ảnh/catalog khác cache, hệ thống yêu cầu tạo lại index.
Không cần huấn luyện lại model khi chỉ thêm sản phẩm; cần tính vector ảnh mới.

Console cũng nhận ảnh thật:

```powershell
.\.venv\Scripts\python.exe CodePython/main.py --mode image --image-file 'C:\path\mouse.jpg' --top-k 3
```

## Giới hạn / lưu ý

- JPEG/PNG tối đa 12 MiB và 20 megapixel; không nhận GIF, SVG hoặc ảnh động.
- Python xử lý ảnh trong bộ nhớ, không lưu ảnh người dùng lên ổ đĩa.
- Mỗi lần chỉ xử lý một request ảnh; request trùng nhận HTTP 429.
- Lần tìm đầu tiên cần nạp model nên chậm hơn các lần sau.
- CLIP tạo embedding cho cả ảnh, không phải bộ phát hiện vật thể vẽ bounding box.
  Dùng một vật thể rõ, ít nền; nhiều vật thể có thể làm sai vector. Không thêm YOLO ở phiên bản này.
- Nhãn là dự đoán giữa năm nhóm, không phải xác nhận vật thể thuộc một trong năm nhóm.
  Ảnh ngoài nhóm có thể bị gán nhãn gần nhất. Chưa có bộ phát hiện out-of-domain đáng tin cậy.
- Cosine là điểm tương đồng [-1, 1], không phải phần trăm đúng. Không bảo đảm phân biệt
  chính xác hãng, dung lượng hoặc các phiên bản có thiết kế gần giống nhau.
- Ảnh catalog có một số ảnh lineup nhiều màu/kích thước và một số sản phẩm dùng cùng ảnh.
  Các sản phẩm đó có thể đồng điểm; không thể phân biệt kích thước chỉ bằng ảnh trùng nhau.
- Trong kiểm thử, iPad Pro M4 ảnh lineup được dự đoán thành phone; nhãn chỉ tham khảo.
  Không sửa/gán cứng nhãn theo tên sản phẩm để giả vờ nhận dạng đúng.
- Backend nhận dạng offline; các font và Tailwind CDN của giao diện vẫn có thể cần mạng.

Nguồn: [CLIP chính thức](https://github.com/openai/CLIP),
[model chính thức](https://huggingface.co/openai/clip-vit-base-patch32).

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tainguyen/CodePython/tests -v
node tainguyen/FrontEnd/tests/integration.cjs http://127.0.0.1:8000
node tainguyen/FrontEnd/tests/image_upload.cjs
```

Tests backend dùng ảnh catalog thật, thử đổi kích thước, ảnh lỗi, vector và bộ lọc,
đồng thời chặn kết nối ngoài localhost khi gọi endpoint nhận dạng.
Tests DOM/mocks không thay thế kiểm thử bố cục trình duyệt thực.
