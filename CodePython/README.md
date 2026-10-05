# Tìm kiếm đa phương thức cho thương mại điện tử

Prototype Python cho Assignment 06, Task 5: kho sản phẩm, tìm kiếm văn bản, giọng nói mô phỏng, tìm kiếm bằng vector ảnh và xếp hạng kết quả. Chạy mặc định sẽ trình diễn cả ba cách tìm kiếm, phù hợp để demo Task 6.

Đã tích hợp thêm giao diện HTML trong `../FrontEnd`. Từ folder gốc chạy `.\.venv\Scripts\python.exe CodePython/web_server.py`, rồi mở `http://127.0.0.1:8000/`. Khi đang ở `CodePython`, chạy `python web_server.py`. Xem `../FrontEnd/README.md` để biết cách sử dụng và giới hạn tương thích.

## Cài đặt và chạy

Cần Python **3.10 trở lên**, pip và NumPy. Trong terminal tại thư mục `CodePython`:

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
python main.py --mode image --embedding 0.95 0.10 0.05 --top-k 5
python main.py --mode interactive
```

Chế độ tương tác nhận `text`, `voice`, `image`, `exit` (hoặc `1`, `2`, `3`, `0`). Vector có thể nhập `0.95 0.10 0.05` hoặc `0.95, 0.10, 0.05`. EOF hoặc Ctrl+C thoát gọn. `--top-k` phải là số nguyên dương; bỏ tùy chọn này để nhận toàn bộ kết quả.

Mỗi kết quả hiển thị tên, category, color, price, stock và điểm. Các mức giá trong dữ liệu là số minh họa; dùng đơn vị USD để demo, không phải giá bán hiện hành. Tìm kiếm ảnh hiển thị nhãn `similarity`. Không có kết quả sẽ hiện `No products found.`; đầu vào không hợp lệ được báo lỗi kiểm tra dữ liệu, không in traceback trong UI.

## Kiến trúc ba lớp

```text
CodePython/
├── main.py                         # Composition root, CLI và demo
├── evaluate.py                     # Đánh giá truy vấn và ví dụ giới hạn
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
│   ├── products.json                # 20 sản phẩm thật và embeddings nhân tạo
│   ├── orders.json                  # Ba đơn mẫu cho giao diện Order Search
│   └── images/                      # Ảnh chính hãng trong catalog/; không mã hóa ảnh
├── tests/                          # 19 kiểm thử API/pipeline bằng unittest
├── requirements.txt
└── README.md
```

Luồng xử lý: `SearchUI → QueryService → SearchService → RankingService → SearchUI`. Với giọng nói, `SpeechService.transcribe()` chạy trước bước tạo truy vấn. `SearchService` lấy dữ liệu qua `ProductRepository` và `VectorIndex`, dùng `ImageService` để tính điểm ảnh. Presentation không đọc JSON trực tiếp; truy xuất và xếp hạng thuộc hai service riêng.

## Cách tìm kiếm và xếp hạng

- **Văn bản:** chuyển query và chuỗi `name + category + color + search_terms` thành chữ thường, tách query theo khoảng trắng. Mỗi từ xuất hiện trong chuỗi sản phẩm đóng góp 1 điểm. Đây là đối chiếu chuỗi con theo từ khóa, nên có thể trả về sản phẩm chỉ khớp một phần truy vấn. Ví dụ `phone` trả 5 điện thoại. Có thêm từ khóa danh mục tiếng Việt có dấu/không dấu và từ khóa `chuột`, `bàn phím`.
- **Giọng nói mô phỏng:** đầu vào là văn bản đã phiên âm, ví dụ `find laptop`. `transcribe()` trả lại văn bản này rồi dùng cùng cơ chế truy xuất văn bản. Prototype không ghi âm microphone và không gọi API nhận dạng giọng nói.
- **Ảnh:** đầu vào là vector số nhân tạo ba chiều, ví dụ `[0.95, 0.10, 0.05]`; không phải đường dẫn file ảnh. Điểm là `dot(a,b) / (norm(a) * norm(b))`. Vector không có độ lớn trả điểm 0; vector sai chiều, rỗng hoặc không phải số được kiểm tra và báo lỗi.
- **Xếp hạng:** sắp xếp ứng viên theo điểm từ cao xuống thấp. Điểm bằng nhau giữ nguyên thứ tự ứng viên để kết quả ổn định. Giới hạn `top_k` áp dụng sau khi xếp hạng. Điểm keyword và cosine thuộc hai thang đo khác nhau, không dùng để so sánh chéo các chế độ.

Thư mục `data/images/catalog/` lưu 20 ảnh sản phẩm từ Apple, ASUS và Logitech; không dùng ảnh sinh bởi AI. Xem [PRODUCT_SOURCES.md](data/PRODUCT_SOURCES.md) để biết từng tên, model, ảnh và nguồn chính hãng. Giá/tồn kho là dữ liệu demo. Ảnh là thật nhưng vector vẫn được gán thủ công: chương trình **không đọc pixel hay tự mã hóa file ảnh**. Các SVG cũ chỉ được giữ lại, không dùng cho sản phẩm hiện tại.

## Kiểm thử

Từ thư mục `CodePython`:

```powershell
python -m unittest discover -s tests -v
python main.py --mode text --query ""
python main.py --mode text --query "zzzz_no_match"
python main.py --mode image --embedding 0 0 0 --top-k 3
python main.py --mode image --embedding 0.90 0.10
python main.py --mode image --embedding invalid 0.10 0.20
```

Query rỗng được xử lý có kiểm soát; query không khớp trả danh sách rỗng. Vector không không gây chia cho 0. Hai lệnh cuối minh họa lỗi kích thước và lỗi thành phần không phải số.

Báo cáo tích hợp và kiểm thử web ở `../FrontEnd/INTEGRATION_NOTES.md`. Dùng `main.py` và `evaluate.py` để chạy demo và đánh giá console.

Chạy `python evaluate.py` để in bảng đánh giá 11 truy vấn. Dữ liệu hiện tại đạt 10/11 (90,91%): 10 tình huống trong khả năng prototype và 1 tình huống có yêu cầu lọc giá mà thuật toán từ khóa chưa hỗ trợ. Đây là tập ví dụ nhỏ được chọn thủ công, không phải độ chính xác trên dữ liệu thực tế. API web có filter `max_price` rõ ràng; chưa phân tích điều kiện giá trong câu tìm kiếm tự nhiên.

## Thay đổi dữ liệu và giới hạn

Chỉnh `data/products.json` để thêm hoặc sửa sản phẩm; mỗi bản ghi gồm `id`, `name`, `category`, `color`, `price`, `stock`, `embedding`, `image`, `source_url`, `image_source_url`, `price_is_demo` và `search_terms`. `image` là đường dẫn tương đối dưới `data/images/`. Giữ `id` duy nhất, chuỗi mô tả không rỗng, giá/tồn kho hợp lệ và tất cả embeddings có cùng số chiều (mặc định 3). Nếu đổi số chiều, đổi vector của mọi sản phẩm và vector truy vấn tương ứng. Repository và index kiểm tra dữ liệu khi khởi tạo.

Dữ liệu nhỏ và lưu cục bộ. Tìm kiếm văn bản không hiểu ngữ nghĩa hay lỗi chính tả; tiếng Việt chỉ được hỗ trợ bằng các từ khóa bổ sung đã khai báo. Embedding ảnh là số minh họa, chưa trích xuất đặc trưng từ ảnh thật. Giọng nói là mô phỏng. Xếp hạng chỉ dựa vào điểm phù hợp; API web có bộ lọc danh mục, tồn kho, giá và similarity, còn console giữ cách tìm kiếm cơ bản. Đã có giao diện web local và tra đơn mẫu; chưa có database, đăng nhập, giỏ hàng, đặt hàng, thanh toán hay tracking thực tế.

Sau khi sửa JSON, dừng server bằng Ctrl+C rồi chạy lại để nạp dữ liệu mới. Catalog hiện gồm 5 điện thoại, 5 máy tính bảng, 5 laptop và 5 phụ kiện (3 chuột, 2 bàn phím).
