# Tìm kiếm đa phương thức cho thương mại điện tử

Prototype Python cho Assignment 06, Task 5: kho sản phẩm, tìm kiếm văn bản, giọng nói mô phỏng, tìm kiếm bằng vector ảnh và xếp hạng kết quả. Chạy mặc định sẽ trình diễn cả ba cách tìm kiếm, phù hợp để demo Task 6.

**Cập nhật voice trên web:** Record / Stop & Search dùng Vosk tiếng Anh offline, không cần API key hay phí dịch vụ. Xem [VOICE_API_SETUP.md](../VOICE_API_SETUP.md) để cài model. Cần thêm `vosk` và `imageio-ffmpeg` trong requirements; console vẫn nhận transcript nhập tay. Image Search dùng CLIP local và ảnh thật; xem [IMAGE_SEARCH_SETUP.md](../IMAGE_SEARCH_SETUP.md).

Tài liệu này đã chuyển vào `tainguyen/CodePython`. Các đường dẫn code và lệnh chạy bên dưới vẫn tính từ folder chạy `CodePython` ở gốc dự án, không phải folder chứa README. Test và `evaluate.py` đã chuyển vào `tainguyen`; xem [hướng dẫn tài nguyên](../README.md).

Đã tích hợp thêm giao diện HTML trong `FrontEnd` ở gốc dự án. Từ folder gốc chạy `.\.venv\Scripts\python.exe CodePython/web_server.py`, rồi mở `http://127.0.0.1:8000/`. Khi đang ở `CodePython`, chạy `python web_server.py`. Xem [hướng dẫn giao diện](../FrontEnd/README.md) để biết cách sử dụng và giới hạn tương thích.

## Cài đặt và chạy

Cần Python **3.10 trở lên**, pip và NumPy; phần voice thật dùng thêm Vosk và imageio-ffmpeg. Trong terminal tại thư mục `CodePython`:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Có thể tạo môi trường riêng trước khi cài thư viện:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Nếu đang ở thư mục cha, chạy `python CodePython/main.py`. Đường dẫn dữ liệu được xác định theo vị trí file Python, nên không phụ thuộc thư mục hiện hành. Import `main.py` không tự chạy demo; hàm `build_ui()` tạo hệ thống đã được nối các dependency.

Môi trường `.venv` ở thư mục cha đã có NumPy. Từ thư mục cha hiện tại có thể chạy ngay trong PowerShell bằng `.\.venv\Scripts\python.exe CodePython/main.py`. Cũng hỗ trợ chạy dạng package: `python -m CodePython.main`.

## Các lệnh demo

```powershell
python main.py
python main.py --mode demo --top-k 3
python main.py --mode text --query "phone"
python main.py --mode voice --query "find laptop" --top-k 3
python main.py --mode image --image-file data/images/catalog/apple-iphone-16-ultramarine.jpg --top-k 5
python main.py --mode interactive
```

Chế độ tương tác nhận `text`, `voice`, `image`, `exit` (hoặc `1`, `2`, `3`, `0`). Vector có thể nhập `0.95 0.10 0.05` hoặc `0.95, 0.10, 0.05`. EOF hoặc Ctrl+C thoát gọn. `--top-k` phải là số nguyên dương; bỏ tùy chọn này để nhận toàn bộ kết quả.

Mỗi kết quả hiển thị tên, category, color, price, stock và điểm. Các mức giá trong dữ liệu là số minh họa; dùng đơn vị USD để demo, không phải giá bán hiện hành. Tìm kiếm ảnh hiển thị nhãn `similarity`. Không có kết quả sẽ hiện `No products found.`; đầu vào không hợp lệ được báo lỗi kiểm tra dữ liệu, không in traceback trong UI.

## Kiến trúc ba lớp

```text
CodePython/
├── main.py                         # Composition root, CLI và demo
├── web_server.py                   # Server local phục vụ frontend và API JSON
├── presentation/
│   ├── __init__.py
│   └── search_ui.py                 # Nhận đầu vào, gọi service, hiển thị
├── application/
│   ├── __init__.py
│   ├── query_service.py             # Biểu diễn truy vấn chung
│   ├── web_search_service.py        # Chuyển request web sang pipeline + bộ lọc
│   ├── order_service.py             # Lắp dữ liệu chi tiết/tổng tiền đơn mẫu
│   ├── speech_service.py            # Speech-to-text mô phỏng
│   ├── image_service.py             # Cosine similarity
│   ├── search_service.py            # Truy xuất ứng viên
│   └── ranking_service.py           # Sắp xếp điểm giảm dần
├── data/
│   ├── __init__.py
│   ├── product_repository.py        # Đọc và kiểm tra dữ liệu JSON
│   ├── order_repository.py          # Kho đơn hàng nhỏ để mở rộng sau này
│   ├── vector_index.py              # Vector ảnh theo ID sản phẩm
│   ├── vector_validation.py         # Kiểm tra vector dùng chung
│   ├── products.json                # 20 sản phẩm thật; không chứa vector giả lập
│   ├── orders.json                  # Ba đơn mẫu cho giao diện Order Search
│   └── images/                      # Ảnh chính hãng trong catalog/; không mã hóa ảnh
└── requirements.txt
```

Luồng xử lý: `SearchUI → QueryService → SearchService → RankingService → SearchUI`. Với giọng nói, `SpeechService.transcribe()` chạy trước bước tạo truy vấn. `SearchService` lấy dữ liệu qua `ProductRepository` và `VectorIndex`, dùng `ImageService` để tính điểm ảnh. Presentation không đọc JSON trực tiếp; truy xuất và xếp hạng thuộc hai service riêng.

## Cách tìm kiếm và xếp hạng

- **Văn bản:** chuyển query và chuỗi `name + category + color + search_terms` thành chữ thường, tách các từ bằng regex để bỏ dấu câu do API phiên âm thêm vào. Mỗi từ xuất hiện trong chuỗi sản phẩm đóng góp 1 điểm. Đây là đối chiếu chuỗi con theo từ khóa, nên có thể trả về sản phẩm chỉ khớp một phần truy vấn. Demo dùng truy vấn và từ khóa tiếng Anh, ví dụ `phone`, `tablet`, `laptop`, `mouse`, `keyboard`; không có bước chuyển đổi alias ngôn ngữ.
- **Giọng nói:** web nhận bản ghi micro, FFmpeg chuyển sang PCM và Vosk tiếng Anh phiên âm local trước khi tìm kiếm. Console/ô nhập tay vẫn nhận transcript, ví dụ `find laptop`, để dùng chung cơ chế truy xuất. Không gọi dịch vụ cloud hay dùng API key.
- **Ảnh:** JPEG/PNG → CLIP ViT-B/32 local CPU → vector chuẩn hóa 512 chiều → cosine similarity với ảnh sản phẩm → xếp hạng. Có thể chạy console với `--image-file` hoặc nhập vector CLIP đủ 512 số bằng `--embedding`. Web hiển thị nhãn dự đoán và cho xuất JSON vector.
- **Xếp hạng:** sắp xếp ứng viên theo điểm từ cao xuống thấp. Điểm bằng nhau giữ nguyên thứ tự ứng viên để kết quả ổn định. Giới hạn `top_k` áp dụng sau khi xếp hạng. Điểm keyword và cosine thuộc hai thang đo khác nhau, không dùng để so sánh chéo các chế độ.

Thư mục `data/images/catalog/` lưu 20 ảnh sản phẩm từ Apple, ASUS và Logitech; không dùng ảnh sinh bởi AI. Xem [PRODUCT_SOURCES.md](data/PRODUCT_SOURCES.md) để biết từng tên, model, ảnh và nguồn chính hãng. Giá/tồn kho là dữ liệu demo. Vector được trích xuất từ pixel ảnh thật bằng CLIP; chỉ mục lưu riêng tại `CodePython/data/clip_embeddings.json` và được ghép vào catalog khi khởi tạo. Các SVG cũ chỉ được giữ lại, không dùng cho sản phẩm hiện tại.

## Kiểm thử

Từ thư mục `CodePython`:

```powershell
python -m unittest discover -s ../tainguyen/CodePython/tests -v
python main.py --mode text --query ""
python main.py --mode text --query "zzzz_no_match"
python main.py --mode image --image-file data/images/catalog/logitech-mx-master-3s-bluetooth-black.png --top-k 3
python main.py --mode image --embedding 0.90 0.10
python main.py --mode image --embedding invalid 0.10 0.20
```

Query rỗng được xử lý có kiểm soát; query không khớp trả danh sách rỗng. Thuật toán cosine vẫn xử lý vector không mà không chia cho 0; vector hợp lệ phải có 512 chiều. Hai lệnh cuối minh họa lỗi kích thước và lỗi thành phần không phải số.

Báo cáo tích hợp và kiểm thử web ở [INTEGRATION_NOTES.md](../FrontEnd/INTEGRATION_NOTES.md). Dùng `main.py` để chạy demo; chạy `python ../tainguyen/CodePython/evaluate.py` từ folder `CodePython` để đánh giá console.

Chạy `python tainguyen/CodePython/evaluate.py` từ folder gốc để in bảng đánh giá 11 truy vấn. Dữ liệu hiện tại đạt 10/11 (90,91%): 10 tình huống trong khả năng prototype và 1 tình huống có yêu cầu lọc giá mà thuật toán từ khóa chưa hỗ trợ. Đây là tập ví dụ nhỏ được chọn thủ công, không phải độ chính xác trên dữ liệu thực tế. API web có filter `max_price` rõ ràng; chưa phân tích điều kiện giá trong câu tìm kiếm tự nhiên.

## Thay đổi dữ liệu và giới hạn

Chỉnh `data/products.json` để thêm/sửa sản phẩm: `id`, `name`, `category`, `color`, `price`, `stock`, `image`, link nguồn và `search_terms`. Ảnh nằm dưới `data/images/`. Giữ ID duy nhất, giá/tồn kho hợp lệ. Không tự nhập embedding trong catalog; chạy `python ../tainguyen/CodePython/setup_clip.py --reindex` từ CodePython để tạo lại vector ảnh rồi khởi động lại server. Cache kiểm tra model, số chiều, ID và hash ảnh.

Dữ liệu nhỏ và lưu cục bộ. Tìm kiếm văn bản không hiểu ngữ nghĩa hay lỗi chính tả; tiếng Việt chỉ được hỗ trợ bằng các từ khóa bổ sung đã khai báo. Embedding ảnh thật do CLIP tạo; nhãn chỉ dự đoán giữa 5 nhóm, không bảo đảm đúng tên/model. Ảnh lineup/trùng ảnh có thể nhầm hoặc đồng điểm. Model cần cài trước, không tự gọi mạng trong request. Voice trên web dùng Vosk tiếng Anh nhỏ, có thể nhận sai và cần sửa transcript; console nhận text nhập tay. Xếp hạng chỉ dựa vào điểm phù hợp; API web có bộ lọc danh mục, tồn kho, giá và similarity, còn console giữ cách tìm kiếm cơ bản. Đã có giao diện web local và tra đơn mẫu; chưa có database, đăng nhập, giỏ hàng, đặt hàng, thanh toán hay tracking thực tế.

Sau khi sửa JSON, dừng server bằng Ctrl+C rồi chạy lại để nạp dữ liệu mới. Catalog hiện gồm 5 điện thoại, 5 máy tính bảng, 5 laptop và 5 phụ kiện (3 chuột, 2 bàn phím).
