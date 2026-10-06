"""Khởi tạo các thành phần ba lớp và cung cấp điểm chạy chương trình console."""

import argparse

# Hỗ trợ cả `python -m CodePython.main` và `python CodePython/main.py`.
if __package__:
    from .application.image_service import ImageService
    from .application.query_service import QueryService
    from .application.ranking_service import RankingService
    from .application.search_service import SearchService
    from .application.speech_service import SpeechService
    from .data.product_repository import ProductRepository
    from .data.vector_index import VectorIndex
    from .presentation.search_ui import SearchUI
else:
    from application.image_service import ImageService
    from application.query_service import QueryService
    from application.ranking_service import RankingService
    from application.search_service import SearchService
    from application.speech_service import SpeechService
    from data.product_repository import ProductRepository
    from data.vector_index import VectorIndex
    from presentation.search_ui import SearchUI


def build_ui():
    """Tạo kho dữ liệu và các service, sau đó truyền chúng vào SearchUI."""
    repository = ProductRepository()
    vector_index = VectorIndex(repository.all_products())
    # Console và web dùng chung các thành phần này để thống nhất cách tìm kiếm.
    return SearchUI(
        QueryService(),
        SpeechService(),
        SearchService(repository, vector_index, ImageService()),
        RankingService(),
    )


def positive_integer(value):
    """Kiểm tra tham số top-k của console phải là số nguyên lớn hơn 0."""
    try:
        number = int(value)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("top-k must be a positive integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("top-k must be a positive integer")
    return number


def run_interactive(ui, top_k=None):
    """Cho phép tìm nhiều lần trong terminal, không cần microphone hay ảnh thật."""
    print("\nInteractive search: text / voice / image / exit")
    try:
        while True:
            mode = input("Mode: ").strip().lower()
            if mode in {"exit", "quit", "q", "0"}:
                print("Goodbye.")
                return
            if mode in {"text", "1"}:
                ui.search_text(input("Text query: "), top_k=top_k)
            elif mode in {"voice", "2"}:
                ui.search_voice(input("Simulated voice text: "), top_k=top_k)
            elif mode in {"image", "3"}:
                # Chấp nhận cả dấu phẩy lẫn khoảng trắng ngăn cách các số vector.
                raw_embedding = input("CLIP image vector (512 numbers; or use --image-file): ")
                ui.search_image(raw_embedding.replace(",", " ").split(), top_k=top_k)
            else:
                print("Choose text, voice, image, or exit.")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")


def main(argv=None):
    """Đọc tham số dòng lệnh, khởi tạo hệ thống và chạy chế độ được chọn."""
    parser = argparse.ArgumentParser(
        description="Multimodal product search: keywords, typed voice transcripts, local CLIP images."
    )
    parser.add_argument(
        "--mode", choices=("demo", "text", "voice", "image", "interactive"), default="demo"
    )
    parser.add_argument("--query", help="Text query or already-transcribed voice text")
    parser.add_argument(
        "--embedding", nargs="+", help="512-dimensional numeric CLIP vector"
    )
    parser.add_argument('--image-file', help='JPEG/PNG file to recognize locally with CLIP')
    parser.add_argument("--top-k", type=positive_integer, help="Maximum number of results")
    # Kiểm tra tham số bắt buộc theo chế độ trước khi nạp dữ liệu sản phẩm.
    args = parser.parse_args(argv)
    if args.mode in {"text", "voice"} and args.query is None:
        parser.error("--query is required for text and voice modes")
    if args.mode == "image" and (args.embedding is None) == (args.image_file is None):
        parser.error("Provide exactly one of --image-file or --embedding for image mode")

    try:
        ui = build_ui()
    except (OSError, ValueError, TypeError) as exc:
        print(f"Unable to initialize search: {exc}")
        return 1

    # Chế độ mặc định minh họa đủ text, voice mô phỏng và vector ảnh nhân tạo.
    if args.mode == "demo":
        print("=== E-Commerce Search Demo ===")
        ui.search_text("phone", top_k=args.top_k)
        ui.search_voice("find laptop", top_k=args.top_k)
        vector = ui.search_service.vector_index.get_embedding(1)
        if vector is not None:
            ui.search_image(vector, top_k=args.top_k)
        else:
            print('Image search requires local CLIP setup: tainguyen/CodePython/setup_clip.py')
    elif args.mode == "text":
        ui.search_text(args.query, top_k=args.top_k)
    elif args.mode == "voice":
        ui.search_voice(args.query, top_k=args.top_k)
    elif args.mode == "image":
        if args.image_file is not None:
            from pathlib import Path
            if __package__:
                from .application.image_embedding_service import read_image, embed_image, ImageRecognitionError, MAX_IMAGE_BYTES
            else:
                from application.image_embedding_service import read_image, embed_image, ImageRecognitionError, MAX_IMAGE_BYTES
            try:
                path = Path(args.image_file)
                if path.stat().st_size > MAX_IMAGE_BYTES:
                    raise ValueError('Image exceeds the 12 MB limit.')
                recognition = embed_image(read_image(path.read_bytes()))
                print('Predicted object:', recognition['detected_object'])
                ui.search_image(recognition['embedding'], top_k=args.top_k)
            except (OSError, ValueError, ImageRecognitionError) as exc:
                print(f'Image search failed: {exc}')
                return 1
        else:
            ui.search_image(args.embedding, top_k=args.top_k)
    else:
        run_interactive(ui, top_k=args.top_k)
    return 0


# Chỉ tự chạy khi mở file trực tiếp; import build_ui không kích hoạt chương trình.
if __name__ == "__main__":
    raise SystemExit(main())
