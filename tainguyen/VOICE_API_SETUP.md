# Voice Search bằng Vosk local — không API key, không phí dịch vụ

## Chạy ngay trên máy này

Thư viện và model đã được cài vào môi trường `.venv` của dự án. Từ folder gốc `KiemTra3Tiet`:

```powershell
.\.venv\Scripts\python.exe CodePython/web_server.py
```

Nếu server phiên bản cũ đang chạy, Ctrl+C tại terminal đó rồi chạy lại. Mở `http://127.0.0.1:8000/voice-search` bằng Chrome hoặc Edge và reload trang. Nếu cổng 8000 đang bận, dùng `--port 8001` và mở cùng địa chỉ ở cổng 8001.

1. Bấm **Record**, cho phép trình duyệt dùng microphone.
2. Nói một câu tiếng Anh ngắn: `find laptop`, `phone`, `tablet` hoặc `keyboard`.
3. Bấm **Stop & Search**. Ứng dụng tự dừng/gửi khi đạt 30 giây.
4. Transcript và sản phẩm được xếp hạng sẽ xuất hiện. Có thể sửa transcript và bấm **Search Transcript** để tìm lại mà không nhận dạng audio lần nữa.

**Cancel Recording** hoặc **Clear** khi đang ghi sẽ bỏ bản ghi, tắt micro và không gửi. Clear khi đã gửi chỉ bỏ qua phản hồi của lần xử lý đang chạy. **Presets** chỉ điền câu mẫu để tìm text, không tạo âm thanh hay phiên âm giả.

## Luồng hoạt động

**MediaRecorder → bản ghi WebM/Ogg/MP4 → API local Python → FFmpeg chuyển sang PCM mono 16-bit/16 kHz → Vosk → transcript → QueryService → SearchService → RankingService → kết quả.**

- `CodePython/application/audio_transcription_service.py`: kiểm tra audio, chuyển đổi, nạp model và phiên âm offline.
- `CodePython/application/speech_service.py`: gọi phiên âm thật trên web; giữ transcript nhập tay cho console.
- `CodePython/application/web_search_service.py`: bộ lọc, tìm kiếm và xếp hạng sau phiên âm.
- `POST /api/voice-search`: API **local**, không phải API cloud có tính phí.
- `FrontEnd/assets/voice.js`: Record, Stop, Cancel, hiển thị transcript và kết quả.

## Cài lại hoặc chạy trên máy khác

Tại folder gốc, dùng Python 64-bit và môi trường riêng:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r CodePython/requirements.txt
.\.venv\Scripts\python.exe tainguyen/CodePython/setup_vosk.py
.\.venv\Scripts\python.exe CodePython/web_server.py
```

Model tiếng Anh: **vosk-model-small-en-us-0.15**, archive khoảng 40 MB, giấy phép Apache 2.0 theo [nhà phát hành](https://alphacephei.com/vosk/models). Cần mạng để cài thư viện/tải model lần đầu; phiên âm sau đó không cần mạng.

- Model dùng khi chạy: `CodePython/models/vosk-model-small-en-us-0.15/`.
- ZIP cài đặt: `tainguyen/downloads/vosk-model-small-en-us-0.15.zip`.
- `setup_vosk.py` kiểm tra phạm vi đường dẫn ZIP, dung lượng và các file model bắt buộc; không ghi đè model đã tồn tại. SHA-256 in ra chỉ để đối chiếu bản tải local, không phải checksum chính thức đã xác nhận.
- `imageio-ffmpeg` đi kèm chương trình FFmpeg, không phải cài FFmpeg vào PATH riêng.
- Thư viện/model/ZIP lớn được bỏ qua bởi Git; khi clone repo sang máy khác cần chạy các bước cài trên.
- Folder có dấu tiếng Việt trên Windows được chuyển sang bí danh đường dẫn ngắn NTFS khi nạp model. Model vẫn ở trong dự án, không đổi tên folder. Nếu ổ đĩa không cung cấp bí danh ASCII, giao diện sẽ báo cần đặt dự án trong đường dẫn không dấu.
- `.env` và API key OpenAI **không được đọc hay sử dụng nữa**. File `.env` cũ được giữ nguyên để tránh xóa cấu hình cá nhân; template trước đây được lưu ở `tainguyen/legacy_openai`.

## Giới hạn và quyền riêng tư

- Nhận dạng tiếng Anh bằng model nhỏ, không streaming, không dịch ngôn ngữ, không phân biệt người nói. Tên sản phẩm lạ hoặc phát âm không rõ có thể nhận sai; luôn xem và sửa transcript nếu cần.
- Ghi âm tối đa 30 giây và 2 MiB; JSON base64 tối đa 3 MiB. Backend cũng giới hạn thời lượng PCM sau chuyển đổi (cho phép sai số container 0.5 giây).
- Âm thanh chỉ gửi đến server localhost trên máy này, không gửi OpenAI/Google hoặc dịch vụ bên ngoài. Không lưu audio người dùng xuống ổ đĩa; decoder trao đổi qua pipe trong bộ nhớ.
- Vosk model được nạp một lần và dùng lại; mỗi bản ghi có recognizer riêng. Server chỉ xử lý một phiên âm cùng lúc.
- Tìm kiếm vẫn là keyword matching, không hiểu điều kiện tự nhiên như "under 100 dollars". Điểm xếp hạng không phải confidence của phiên âm.
- Voice hoạt động offline sau cài đặt, nhưng Tailwind, font và icon của giao diện hiện vẫn tham chiếu CDN; khi không có Internet, hình thức có thể khác. Không đồng nghĩa toàn bộ website đã được đóng gói offline.
- Image Search không đổi: vẫn dùng vector nhân tạo. CLI `main.py --mode voice --query ...` vẫn nhận transcript nhập tay.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tainguyen/CodePython/tests -v
node tainguyen/FrontEnd/tests/voice_recording.cjs
```

Test backend kiểm tra FFmpeg/Vosk thật khi model đã cài, không được kết nối ra mạng trong bài test offline. Test micro dùng thiết bị giả để kiểm tra Record/Stop/Cancel và lỗi quyền micro, không chứng minh phần cứng microphone của bạn hoạt động.

Tài liệu: [Vosk](https://alphacephei.com/vosk/), [cài đặt và định dạng âm thanh](https://alphacephei.com/vosk/install), [FFmpeg đi kèm Python](https://github.com/imageio/imageio-ffmpeg).
