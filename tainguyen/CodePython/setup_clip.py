"""Tải model CLIP chính thức một lần và tạo cache vector ảnh thật cho catalog."""

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CodePython.application.image_embedding_service import MODEL_PATH, MODEL_FILES, embed_image, read_image
from CodePython.data.image_vector_repository import (MODEL_ID, MODEL_REVISION, DIMENSION,
    PREPROCESSING, INDEX_PATH, image_path, image_sha256)
from CodePython.data.product_repository import ProductRepository


def download_model():
    """Ghim revision, kiểm tra hash theo metadata chính thức và ghi file tạm an toàn."""
    import requests
    MODEL_PATH.mkdir(parents=True, exist_ok=True)
    metadata = requests.get(f'https://huggingface.co/api/models/{MODEL_ID}/revision/{MODEL_REVISION}?blobs=true', timeout=60)
    metadata.raise_for_status()
    files = {entry['rfilename']: entry for entry in metadata.json()['siblings']}
    for name in MODEL_FILES:
        target = MODEL_PATH / name
        info = files[name]
        expected_size = info['size']
        if expected_size > 700 * 1024 * 1024:
            raise ValueError('Unexpected model file size.')
        expected_hash = info.get('lfs', {}).get('sha256')
        if target.is_file() and target.stat().st_size == expected_size:
            with target.open('rb') as existing:
                valid_hash = not expected_hash or hashlib.file_digest(existing, 'sha256').hexdigest() == expected_hash
            if valid_hash:
                print(f'Already installed: {name}', flush=True)
                continue
        print(f'Downloading {name} ({expected_size / 1024 / 1024:.1f} MB)...', flush=True)
        part = target.with_suffix(target.suffix + '.part')
        digest = hashlib.sha256()
        size = 0
        with requests.get(f'https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{name}', stream=True, timeout=(30, 90)) as response:
            response.raise_for_status()
            with part.open('wb') as output:
                for chunk in response.iter_content(1024 * 1024):
                    size += len(chunk)
                    if size > expected_size:
                        raise ValueError('Downloaded model file exceeds expected size.')
                    digest.update(chunk)
                    output.write(chunk)
        if size != expected_size or (expected_hash and digest.hexdigest() != expected_hash):
            raise ValueError('Model download size/checksum mismatch.')
        # os.replace chỉ thay file model sinh bởi bộ cài, không sửa tài liệu người dùng.
        os.replace(part, target)
        print(f'Installed: {name}', flush=True)


def build_index():
    """Tính lại toàn bộ 20 ảnh, chỉ thay cache khi mọi vector đã tạo thành công."""
    products = ProductRepository().all_products()
    entries = []
    for position, product in enumerate(products, 1):
        path = image_path(product)
        recognition = embed_image(read_image(path.read_bytes()))
        entries.append({'id': product['id'], 'image': product['image'],
                        'sha256': image_sha256(path), 'embedding': recognition['embedding']})
        print(f'Indexed {position}/{len(products)}: {product["name"]} ({recognition["detected_object"]})', flush=True)
    cache = {'format_version': 1, 'model': MODEL_ID, 'revision': MODEL_REVISION,
             'dimension': DIMENSION, 'preprocessing': PREPROCESSING, 'products': entries}
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=INDEX_PATH.parent,
                                      prefix='clip_embeddings-', suffix='.tmp', delete=False) as output:
        json.dump(cache, output, ensure_ascii=False, allow_nan=False, indent=2)
        temporary = output.name
    os.replace(temporary, INDEX_PATH)
    print(f'Image index ready: {len(entries)} products, {DIMENSION} dimensions.', flush=True)


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    try:
        # --reindex dùng hoàn toàn offline sau khi model đã cài.
        if '--reindex' not in sys.argv:
            download_model()
        build_index()
    except Exception as exc:
        print(f'CLIP setup failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
