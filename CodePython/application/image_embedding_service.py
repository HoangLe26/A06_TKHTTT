"""Đọc ảnh thật và trích xuất vector CLIP offline trên CPU; không gọi API ngoài."""

import base64
import binascii
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import threading
import warnings

if __package__ and '.' in __package__:
    from ..data.image_vector_repository import MODEL_ID, MODEL_REVISION, DIMENSION
else:
    from data.image_vector_repository import MODEL_ID, MODEL_REVISION, DIMENSION

MODEL_PATH = Path(__file__).resolve().parents[1] / 'models' / 'clip-vit-base-patch32'
MODEL_FILES = ('config.json', 'preprocessor_config.json', 'pytorch_model.bin',
               'tokenizer_config.json', 'special_tokens_map.json', 'vocab.json', 'merges.txt')
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 20_000_000
LABELS = ('phone', 'tablet', 'laptop', 'mouse', 'keyboard')
PROMPTS = ('a photo of a smartphone', 'a photo of a tablet computer',
           'a photo of a laptop computer', 'a photo of a computer mouse',
           'a photo of a computer keyboard')
MODEL_LOCK = threading.Lock()


class ImageRecognitionError(RuntimeError):
    """Lỗi có nội dung an toàn để gửi cho giao diện và mã HTTP rõ ràng."""
    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def model_installed():
    return all((MODEL_PATH / name).is_file() for name in MODEL_FILES)


def image_configuration(index_ready=True, index_error=None):
    """Kiểm tra file/thư viện nhẹ, không tải model hoặc kết nối mạng trong health."""
    import importlib.util
    error = index_error
    if any(importlib.util.find_spec(name) is None for name in ('torch', 'transformers', 'PIL')):
        error = 'Install CodePython/requirements.txt to enable local image recognition.'
    elif not model_installed():
        error = 'CLIP model is not installed. Run tainguyen/CodePython/setup_clip.py.'
    elif not index_ready:
        error = error or 'Rebuild the CLIP image index and restart the server.'
    return {'configured': error is None, 'engine': 'clip', 'model': MODEL_ID,
            'revision': MODEL_REVISION, 'offline': True, 'requires_api_key': False,
            'dimension': DIMENSION, 'device': 'cpu', 'max_image_bytes': MAX_IMAGE_BYTES,
            'max_pixels': MAX_PIXELS, 'labels': list(LABELS), 'error': error}


def read_image(data):
    """Xác thực JPEG/PNG thật, giới hạn pixel, sửa EXIF và ghép nền trắng cho PNG."""
    if not isinstance(data, bytes) or not data:
        raise ValueError('Image data must not be empty.')
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageRecognitionError('Image exceeds the 12 MB limit.', 413)
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise ImageRecognitionError('Install Pillow to read uploaded images.') from exc
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as original:
                if original.format not in ('JPEG', 'PNG'):
                    raise ValueError('Choose a JPEG or PNG image.')
                if original.width * original.height > MAX_PIXELS:
                    raise ImageRecognitionError('Image exceeds the 20 megapixel limit.', 413)
                if getattr(original, 'n_frames', 1) != 1:
                    raise ValueError('Animated images are not supported.')
                original.load()
                image = ImageOps.exif_transpose(original)
                # PNG trong catalog có nền trong suốt: ghép trắng trước khi đổi RGB.
                if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
                    rgba = image.convert('RGBA')
                    background = Image.new('RGBA', rgba.size, 'white')
                    image = Image.alpha_composite(background, rgba)
                return image.convert('RGB')
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageRecognitionError('Image is too large to decode safely.', 413) from exc
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError('Image is corrupt or is not a valid JPEG/PNG.') from exc


def decode_image(payload):
    """Giới hạn chuỗi base64 trước khi giải mã; tin định dạng thực thay vì MIME client."""
    encoded = payload.get('image_base64')
    if not isinstance(encoded, str) or not encoded:
        raise ValueError('image_base64 must be a nonempty base64 string.')
    if len(encoded) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
        raise ImageRecognitionError('Image exceeds the 12 MB limit.', 413)
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('image_base64 is not valid base64.') from exc
    # Kiểm tra ảnh tại server dù trình duyệt đã kiểm tra loại và kích thước file.
    return read_image(data)


@lru_cache(maxsize=1)
def _model():
    """Nạp duy nhất một model local; weights_only không thực thi pickle tùy ý."""
    if not model_installed():
        raise ImageRecognitionError('CLIP model is missing. Run tainguyen/CodePython/setup_clip.py.')
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor
        torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
        processor = CLIPProcessor.from_pretrained(str(MODEL_PATH), local_files_only=True, use_fast=False)
        model = CLIPModel.from_pretrained(str(MODEL_PATH), local_files_only=True,
                                          use_safetensors=False, weights_only=True).to('cpu').eval()
        with torch.inference_mode():
            text = processor(text=list(PROMPTS), return_tensors='pt', padding=True)
            features = model.get_text_features(**text)
            features = features / features.norm(dim=-1, keepdim=True)
        return torch, model, processor, features
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise ImageRecognitionError('Unable to load local CLIP. Reinstall requirements/model and restart the server.') from exc


def embed_image(image):
    """Vector truy vấn và sản phẩm cùng model/tiền xử lý; dự đoán nhãn không lọc cứng."""
    # Dùng khóa vì server nhiều luồng nhưng model CPU là tài nguyên dùng chung.
    with MODEL_LOCK:
        torch, model, processor, text_features = _model()
        try:
            with torch.inference_mode():
                inputs = processor(images=image, return_tensors='pt')
                features = model.get_image_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
                vector = features[0].tolist()
                similarities = (features @ text_features.T)[0].tolist()
        except (RuntimeError, ValueError, TypeError) as exc:
            raise ImageRecognitionError('Unable to encode this image locally. Try a different JPEG/PNG.', 422) from exc
    if len(vector) != DIMENSION:
        raise ImageRecognitionError('CLIP returned an unexpected vector dimension.')
    predictions = sorted(({'label': label, 'similarity': float(score)}
                          for label, score in zip(LABELS, similarities)),
                         key=lambda item: item['similarity'], reverse=True)
    return {'embedding': vector, 'detected_object': predictions[0]['label'],
            'object_predictions': predictions}
