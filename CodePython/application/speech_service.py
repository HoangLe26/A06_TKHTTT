"""Simulated speech recognition for the assignment's console prototype."""


class SpeechService:
    def transcribe(self, audio_input):
        """Input represents already-transcribed speech text, returned unchanged."""
        if not isinstance(audio_input, str):
            raise ValueError("Simulated voice input must be already-transcribed text.")
        return audio_input
