# Ảnh minh họa cho demo

Ba ảnh SVG tự vẽ dùng để minh họa bộ dữ liệu khi trình bày bài. Có thể mở bằng trình duyệt; không cần tải ảnh hay cài mô hình AI.

| Ảnh | ID sản phẩm | Vector nhân tạo trong products.json |
| --- | --- | --- |
| shoe.svg | 1 — Nike Running Shoes | [0.95, 0.10, 0.15] |
| bag.svg | 3 — Black Leather Bag | [0.12, 0.20, 0.93] |
| shirt.svg | 6 — Red T-Shirt | [0.20, 0.90, 0.15] |

Các vector được gán thủ công để mô phỏng đặc trưng ảnh. Chương trình **không đọc pixel hay trích xuất vector từ SVG**; truyền vector bằng `--embedding`. Ví dụ từ thư mục `CodePython`:

```powershell
python main.py --mode image --embedding 0.12 0.20 0.93 --top-k 3
```

Kết quả đầu tiên phải là `Black Leather Bag`, similarity bằng `1.0000`.
