"""Phiên âm tiếng Anh offline bằng Vosk; chỉ xử lý audio trong bộ nhớ."""

import base64
import binascii
import ctypes
from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess

MODEL = 'vosk-model-small-en-us-0.15'
LANGUAGE = 'en'
MODEL_PATH = Path(__file__).resolve().parents[1] / 'models' / MODEL
MAX_AUDIO_BYTES = 2 * 1024 * 1024
MAX_SECONDS = 30
SAMPLE_RATE = 16000
AUDIO_FORMATS = {'audio/webm': ('matroska', b'\x1a\x45\xdf\xa3'),
                 'audio/ogg': ('ogg', b'OggS'),
                 'audio/mp4': ('mov', b'ftyp'),
                 'audio/wav': ('wav', b'RIFF')}
MODEL_FILES = ('am/final.mdl', 'conf/mfcc.conf', 'graph/HCLr.fst', 'graph/Gr.fst')


class TranscriptionError(Exception):
    """Lỗi phiên âm an toàn để giao diện hiển thị thay vì traceback hay transcript giả."""

    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def _dependencies():
    """Import khi cần để các chức năng text/image vẫn chạy nếu chưa cài voice."""
    try:
        import vosk
        from imageio_ffmpeg import get_ffmpeg_exe
        executable = get_ffmpeg_exe()
    except (ImportError, OSError, RuntimeError):
        raise TranscriptionError('Install voice dependencies: python -m pip install -r CodePython/requirements.txt.') from None
    return vosk, executable


def _native_model_path():
    """Dùng tên ngắn NTFS để thư viện C++ của Vosk đọc được folder có dấu trên Windows."""
    path = str(MODEL_PATH.resolve())
    if os.name != 'nt' or path.isascii():
        return path
    # Chỉ lấy bí danh của cùng folder, không sao chép model ra ngoài dự án.
    get_short_path = ctypes.windll.kernel32.GetShortPathNameW
    get_short_path.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
    get_short_path.restype = ctypes.c_uint
    buffer = ctypes.create_unicode_buffer(32768)
    length = get_short_path(path, buffer, len(buffer))
    if not 0 < length < len(buffer) or not buffer.value.isascii():
        raise TranscriptionError('Vosk cannot read this Windows path. Use a project folder without accented characters.')
    return buffer.value


def audio_configuration():
    """Kiểm tra thư viện và model local; không đọc key, gọi mạng hay tự tải model."""
    error = None
    try:
        _dependencies()
        if not all((MODEL_PATH / name).is_file() for name in MODEL_FILES):
            error = 'English Vosk model is missing. Run python tainguyen/CodePython/setup_vosk.py.'
        else:
            _native_model_path()
    except TranscriptionError as exc:
        error = str(exc)
    return {'configured': error is None, 'engine': 'vosk', 'model': MODEL,
            'language': LANGUAGE, 'offline': True, 'requires_api_key': False,
            'max_seconds': MAX_SECONDS, 'max_audio_bytes': MAX_AUDIO_BYTES, 'error': error}


@lru_cache(maxsize=1)
def _model():
    """Nạp model từ đường dẫn cố định một lần, không dùng Model(lang=...) tự download."""
    vosk, _ = _dependencies()
    if not all((MODEL_PATH / name).is_file() for name in MODEL_FILES):
        raise TranscriptionError('English Vosk model is missing. Run python tainguyen/CodePython/setup_vosk.py.')
    try:
        vosk.SetLogLevel(-1)
        return vosk.Model(_native_model_path())
    except TranscriptionError:
        raise
    except Exception:
        raise TranscriptionError('Unable to load the local Vosk model. Check or reinstall the model files.') from None


def decode_audio(payload):
    """Giải mã base64 và kiểm tra dung lượng, MIME, chữ ký container trước phiên âm."""
    encoded = payload.get('audio_base64')
    mime = payload.get('mime_type')
    if not isinstance(encoded, str) or not encoded:
        raise ValueError('A non-empty audio_base64 string is required.')
    if not isinstance(mime, str):
        raise ValueError('mime_type must describe the recorded audio.')
    mime = mime.split(';', 1)[0].strip().lower()
    if mime not in AUDIO_FORMATS:
        raise ValueError('Record WebM, Ogg, MP4 or WAV audio.')
    if len(encoded) > 4 * ((MAX_AUDIO_BYTES + 2) // 3):
        raise ValueError('Audio must not exceed 2 MiB.')
    try:
        audio = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError('Audio must be valid base64.') from None
    if not 16 <= len(audio) <= MAX_AUDIO_BYTES:
        raise ValueError('Audio is empty, incomplete or exceeds 2 MiB.')
    signature = AUDIO_FORMATS[mime][1]
    # MP4 đặt loại container ở byte 4; WAV phải có cả RIFF và WAVE.
    valid = audio[4:8] == signature if mime == 'audio/mp4' else audio.startswith(signature)
    if mime == 'audio/wav':
        valid = valid and audio[8:12] == b'WAVE'
    if not valid:
        raise ValueError('The audio container does not match its MIME type.')
    return audio, mime


def _decode_pcm(audio, mime):
    """Chuyển bản ghi thành PCM mono 16-bit/16 kHz bằng FFmpeg đi kèm thư viện."""
    _, executable = _dependencies()
    command = [executable, '-nostdin', '-hide_banner', '-loglevel', 'error',
               '-protocol_whitelist', 'pipe', '-f', AUDIO_FORMATS[mime][0], '-i', 'pipe:0',
               '-vn', '-ac', '1', '-ar', str(SAMPLE_RATE), '-t', str(MAX_SECONDS + 1),
               '-f', 's16le', 'pipe:1']
    # Không mở cửa sổ console phụ trên Windows, không chạy qua shell.
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        result = subprocess.run(command, input=audio, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=15, creationflags=flags, check=False)
    except subprocess.TimeoutExpired:
        raise TranscriptionError('Audio decoding timed out. Try a shorter recording.', 422) from None
    except OSError:
        raise TranscriptionError('Unable to start the local audio decoder. Reinstall imageio-ffmpeg.') from None
    if result.returncode or not result.stdout or len(result.stdout) % 2:
        raise TranscriptionError('Unable to decode the recording. Record a clear English sentence again.', 422)
    # Cho phép 0.5 giây sai số container; vẫn chặn file dài được gửi trực tiếp tới API.
    if len(result.stdout) > (MAX_SECONDS + 0.5) * SAMPLE_RATE * 2:
        raise TranscriptionError('Recording exceeds the 30-second limit.', 422)
    return result.stdout


def transcribe_audio(audio, mime):
    """Phiên âm hoàn toàn local, tạo recognizer riêng cho từng bản ghi để không lẫn câu."""
    if mime not in AUDIO_FORMATS or not isinstance(audio, bytes) or not 16 <= len(audio) <= MAX_AUDIO_BYTES:
        raise ValueError('Invalid recorded audio.')
    pcm = _decode_pcm(audio, mime)
    vosk, _ = _dependencies()
    model = _model()
    try:
        recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)
        parts = []
        for offset in range(0, len(pcm), 4000):
            if recognizer.AcceptWaveform(pcm[offset:offset + 4000]):
                parts.append(json.loads(recognizer.Result()).get('text', ''))
        parts.append(json.loads(recognizer.FinalResult()).get('text', ''))
        text = ' '.join(part.strip() for part in parts if isinstance(part, str) and part.strip())
    except Exception:
        raise TranscriptionError('Local speech recognition failed. Please record again.', 422) from None
    if not text:
        raise TranscriptionError('No speech was recognized. Speak a short English sentence near the microphone.', 422)
    return text
