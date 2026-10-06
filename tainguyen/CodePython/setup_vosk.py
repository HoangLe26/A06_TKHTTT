"""Cài model Vosk tiếng Anh nhỏ từ nguồn chính thức, không ghi đè model đã có."""

import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.request import urlopen
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[2]
MODEL_NAME = 'vosk-model-small-en-us-0.15'
URL = 'https://alphacephei.com/vosk/models/' + MODEL_NAME + '.zip'
MODELS = ROOT / 'CodePython' / 'models'
ARCHIVE = ROOT / 'tainguyen' / 'downloads' / (MODEL_NAME + '.zip')
REQUIRED = ('am/final.mdl', 'conf/mfcc.conf', 'graph/HCLr.fst', 'graph/Gr.fst')


def install():
    """Tải có giới hạn, kiểm tra ZIP trong thư mục tạm rồi chuyển model vào runtime."""
    target = MODELS / MODEL_NAME
    if target.exists():
        if all((target / name).is_file() for name in REQUIRED):
            print('English model is already installed:', target)
            return
        raise ValueError('An incomplete model folder already exists. Move it aside before installing again.')
    MODELS.mkdir(parents=True, exist_ok=True)
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    if not ARCHIVE.is_file():
        # Tệp .part không được coi là ZIP hoàn chỉnh nếu kết nối bị gián đoạn.
        partial = ARCHIVE.with_suffix('.zip.part')
        print('Downloading the official English model (about 40 MB)...', flush=True)
        with urlopen(URL, timeout=60) as response, partial.open('wb') as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 60 * 1024 * 1024:
                    raise ValueError('The model archive exceeds the expected download limit.')
                output.write(chunk)
        partial.replace(ARCHIVE)
    with tempfile.TemporaryDirectory(prefix='vosk-install-', dir=MODELS) as staging_name:
        staging = Path(staging_name).resolve()
        with ZipFile(ARCHIVE) as archive:
            entries = archive.infolist()
            if not entries or sum(entry.file_size for entry in entries) > 200 * 1024 * 1024:
                raise ValueError('Unexpected model archive size.')
            # Kiểm tra toàn bộ tên trước khi extract để chặn đường dẫn ra ngoài staging.
            for entry in entries:
                destination = (staging / entry.filename).resolve()
                if not destination.is_relative_to(staging) or not entry.filename.startswith(MODEL_NAME + '/'):
                    raise ValueError('The model archive contains an unsafe path.')
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('The model archive contains a symbolic link.')
            archive.extractall(staging)
        extracted = staging / MODEL_NAME
        if not all((extracted / name).is_file() for name in REQUIRED):
            raise ValueError('The downloaded model is incomplete.')
        shutil.move(str(extracted), str(target))
    with ARCHIVE.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hashlib.sha256(stream.read()).hexdigest()
    print('Installed:', target)
    print('Archive SHA-256 (for local reference):', checksum)


if __name__ == '__main__':
    # Terminal Windows/đầu ra redirect có thể dùng code page không chứa chữ Việt.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    try:
        install()
    except (OSError, ValueError, RuntimeError, BadZipFile) as exc:
        print('Unable to install the model:', exc, file=sys.stderr)
        raise SystemExit(1)
