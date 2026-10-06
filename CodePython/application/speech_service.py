"""Nhận text nhập tay cho console và phiên âm âm thanh thật cho web."""

from . import audio_transcription_service


class SpeechService:
    """Giữ tương thích với console và nhận dạng bản ghi tiếng Anh bằng Vosk offline."""

    def audio_configuration(self):
        """Trả trạng thái thư viện/model local, không cần cấu hình tài khoản hay API key."""
        return audio_transcription_service.audio_configuration()

    def transcribe_audio(self, audio, mime):
        """Gọi Vosk local; không trả dữ liệu mẫu nếu model hoặc âm thanh có lỗi."""
        return audio_transcription_service.transcribe_audio(audio, mime)

    def transcribe(self, audio_input):
        """Kiểm tra đầu vào rồi trả nguyên văn bản phiên âm, không nhận dạng âm thanh."""
        if not isinstance(audio_input, str):
            raise ValueError("Simulated voice input must be already-transcribed text.")
        return audio_input
