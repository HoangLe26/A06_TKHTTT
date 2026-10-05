"""Mô phỏng bước chuyển giọng nói thành văn bản; không thu âm hay gọi API STT."""


class SpeechService:
    """Nhận văn bản phiên âm được nhập sẵn thay cho dữ liệu âm thanh thật."""

    def transcribe(self, audio_input):
        """Kiểm tra đầu vào rồi trả nguyên văn bản phiên âm, không nhận dạng âm thanh."""
        if not isinstance(audio_input, str):
            raise ValueError("Simulated voice input must be already-transcribed text.")
        return audio_input
