"""Nạp chỉ mục CLIP đã tạo từ ảnh thật và kiểm tra nguồn gốc từng vector."""

import hashlib
import json
from pathlib import Path

from .vector_validation import validate_embedding

MODEL_ID = 'openai/clip-vit-base-patch32'
MODEL_REVISION = '3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268'
DIMENSION = 512
PREPROCESSING = 'clip-rgb-exif-alpha-white-center-crop-v1'
DATA_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = DATA_ROOT / 'images'
INDEX_PATH = DATA_ROOT / 'clip_embeddings.json'


def image_path(product, root=IMAGE_ROOT):
    """Chỉ đọc ảnh catalog trong folder cho phép, không theo đường dẫn ra ngoài."""
    name = product.get('image')
    if not isinstance(name, str) or not name:
        raise ValueError('Every indexed product must have a catalog image.')
    path = (Path(root) / name).resolve()
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
        raise ValueError('Catalog image is missing or outside the image folder.')
    return path


def image_sha256(path):
    """Băm ảnh để phát hiện ảnh đã thay đổi sau lần tạo chỉ mục."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_image_vectors(products, index_path=INDEX_PATH, image_root=IMAGE_ROOT):
    """Từ chối cache sai model, sai số chiều hoặc khác ảnh/catalog hiện tại."""
    try:
        cache = json.loads(Path(index_path).read_text(encoding='utf-8'))
        expected = {'format_version': 1, 'model': MODEL_ID, 'revision': MODEL_REVISION,
                    'dimension': DIMENSION, 'preprocessing': PREPROCESSING}
        if not isinstance(cache, dict) or any(cache.get(k) != v for k, v in expected.items()):
            raise ValueError('Image index model or preprocessing does not match.')
        entries = cache.get('products')
        if not isinstance(entries, list) or len(entries) != len(products):
            raise ValueError('Image index does not match the current catalog.')
        by_id = {entry['id']: entry for entry in entries}
        if len(by_id) != len(entries) or set(by_id) != {p['id'] for p in products}:
            raise ValueError('Image index product IDs do not match.')
        vectors = {}
        for product in products:
            entry = by_id[product['id']]
            if entry['image'] != product['image'] or entry['sha256'] != image_sha256(image_path(product, image_root)):
                raise ValueError('A catalog image changed; rebuild the CLIP index.')
            vector = validate_embedding(entry['embedding'])
            if len(vector) != DIMENSION or abs(sum(x*x for x in vector) - 1) > 0.001:
                raise ValueError('Image index must contain normalized 512-dimensional vectors.')
            vectors[product['id']] = vector
        return vectors
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError('CLIP image index is missing, invalid or stale. Run tainguyen/CodePython/setup_clip.py and restart the server.') from exc
