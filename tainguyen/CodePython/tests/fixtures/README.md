# English speech fixture

`find-laptop.wav` says **find laptop**. It was generated locally with the Windows
Microsoft David Desktop speech synthesizer for a deterministic integration test;
it is not a user microphone recording.

The test converts this WAV to WebM/Opus, submits it to the real local HTTP endpoint,
and verifies Vosk transcription and ranked laptop results with external network
connections blocked. This validates the pipeline, not real-world microphone or
accent accuracy.
