"""Kiểm thử Vosk/FFmpeg local và luồng HTTP; không cần key hay dịch vụ bên ngoài."""

import base64
import http.client
from io import BytesIO
import json
import socket
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import wave

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKSPACE_ROOT))
from CodePython.application import audio_transcription_service as audio_api
import test_web_integration as web_tests

AUDIO = b'\x1a\x45\xdf\xa3' + b'\x00' * 32


def recording(**overrides):
    payload = {'audio_base64': base64.b64encode(AUDIO).decode(), 'mime_type': 'audio/webm;codecs=opus'}
    payload.update(overrides)
    return payload


def silent_wav(seconds=1):
    """Tạo WAV PCM thật để thử decoder và xử lý bản ghi không có lời nói."""
    output = BytesIO()
    with wave.open(output, 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(bytes(int(seconds * 16000) * 2))
    return output.getvalue()


class LocalAudioTests(unittest.TestCase):
    def test_missing_dependencies_are_reported_without_breaking_other_features(self):
        with patch.object(audio_api, '_dependencies', side_effect=audio_api.TranscriptionError('Missing dependencies')):
            config = audio_api.audio_configuration()
            self.assertFalse(config['configured'])
            self.assertEqual(config['error'], 'Missing dependencies')
            self.assertFalse(config['requires_api_key'])

    def test_missing_model_is_reported(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(audio_api, 'MODEL_PATH', Path(directory)), patch.object(audio_api, '_dependencies'):
            config = audio_api.audio_configuration()
            self.assertFalse(config['configured'])
            self.assertIn('setup_vosk.py', config['error'])

    def test_configuration_is_local_and_requires_no_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            for filename in audio_api.MODEL_FILES:
                file = model / filename
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
            with patch.object(audio_api, 'MODEL_PATH', model), patch.object(audio_api, '_dependencies'), patch.object(audio_api, '_native_model_path', return_value=str(model)):
                config = audio_api.audio_configuration()
                self.assertTrue(config['configured'])
                self.assertTrue(config['offline'])
                self.assertEqual(config['engine'], 'vosk')
                self.assertEqual(config['model'], 'vosk-model-small-en-us-0.15')
                self.assertFalse(config['requires_api_key'])

    def test_valid_recorded_container_types(self):
        for mime, data in [('audio/webm', AUDIO), ('audio/ogg', b'OggS' + bytes(32)),
                           ('audio/mp4', bytes(4) + b'ftyp' + bytes(32)), ('audio/wav', silent_wav())]:
            with self.subTest(mime=mime):
                self.assertEqual(audio_api.decode_audio(recording(
                    audio_base64=base64.b64encode(data).decode(), mime_type=mime)), (data, mime))

    def test_invalid_audio_is_rejected(self):
        for data in [recording(audio_base64='!bad'), recording(audio_base64=''), recording(audio_base64=34),
                     recording(mime_type=None), recording(mime_type='text/html'), recording(mime_type='audio/wav'),
                     recording(audio_base64=base64.b64encode(b'too short').decode()),
                     recording(audio_base64='A' * (4 * ((audio_api.MAX_AUDIO_BYTES + 2) // 3) + 4))]:
            with self.subTest(data=str(data)[:80]), self.assertRaises(ValueError):
                audio_api.decode_audio(data)

    def test_pcm_conversion_uses_bounded_local_pipe_not_shell(self):
        result = subprocess.CompletedProcess([], 0, bytes(16000), b'')
        with patch.object(audio_api, '_dependencies', return_value=(MagicMock(), 'ffmpeg.exe')), patch.object(audio_api.subprocess, 'run', return_value=result) as run:
            self.assertEqual(audio_api._decode_pcm(AUDIO, 'audio/webm'), bytes(16000))
            args = run.call_args.args[0]
            self.assertIn('16000', args)
            self.assertIn('s16le', args)
            self.assertIn('pipe:0', args)
            self.assertIn('pipe:1', args)
            self.assertIn('31', args)
            self.assertEqual(run.call_args.kwargs['input'], AUDIO)
            self.assertEqual(run.call_args.kwargs['timeout'], 15)
            self.assertNotIn('shell', run.call_args.kwargs)

    def test_decoder_failure_empty_audio_and_duration_limit(self):
        for result in [subprocess.CompletedProcess([], 1, b'', b'private decoder details'),
                       subprocess.CompletedProcess([], 0, b'', b''),
                       subprocess.CompletedProcess([], 0, b'x', b''),
                       subprocess.CompletedProcess([], 0, bytes(31 * 16000 * 2), b'')]:
            with patch.object(audio_api, '_dependencies', return_value=(MagicMock(), 'ffmpeg.exe')), patch.object(audio_api.subprocess, 'run', return_value=result):
                with self.assertRaises(audio_api.TranscriptionError) as raised:
                    audio_api._decode_pcm(AUDIO, 'audio/webm')
                self.assertEqual(raised.exception.status, 422)
                self.assertNotIn('private', str(raised.exception))

    def test_decoder_timeout_is_safe(self):
        with patch.object(audio_api, '_dependencies', return_value=(MagicMock(), 'ffmpeg.exe')), patch.object(audio_api.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ffmpeg', 15)):
            with self.assertRaises(audio_api.TranscriptionError) as raised:
                audio_api._decode_pcm(AUDIO, 'audio/webm')
            self.assertEqual(raised.exception.status, 422)

    def test_vosk_combines_segments_and_final_result(self):
        vosk = MagicMock()
        recognizer = vosk.KaldiRecognizer.return_value
        recognizer.AcceptWaveform.side_effect = [True, False]
        recognizer.Result.return_value = '{"text": "find"}'
        recognizer.FinalResult.return_value = '{"text": "laptop"}'
        model = object()
        with patch.object(audio_api, '_decode_pcm', return_value=bytes(5000)), patch.object(audio_api, '_dependencies', return_value=(vosk, 'ffmpeg')), patch.object(audio_api, '_model', return_value=model):
            self.assertEqual(audio_api.transcribe_audio(AUDIO, 'audio/webm'), 'find laptop')
            vosk.KaldiRecognizer.assert_called_once_with(model, 16000)
            self.assertEqual(recognizer.AcceptWaveform.call_count, 2)

    def test_empty_or_invalid_recognition_never_returns_sample_text(self):
        for final in ['{"text": ""}', '{bad']:
            vosk = MagicMock()
            vosk.KaldiRecognizer.return_value.AcceptWaveform.return_value = False
            vosk.KaldiRecognizer.return_value.FinalResult.return_value = final
            with patch.object(audio_api, '_decode_pcm', return_value=bytes(4000)), patch.object(audio_api, '_dependencies', return_value=(vosk, 'ffmpeg')), patch.object(audio_api, '_model'):
                with self.assertRaises(audio_api.TranscriptionError) as raised:
                    audio_api.transcribe_audio(AUDIO, 'audio/webm')
                self.assertEqual(raised.exception.status, 422)

    def test_real_decoder_and_vosk_silence_without_network(self):
        if not audio_api.audio_configuration()['configured']:
            self.skipTest('Install the local English model to run this real-engine check.')
        # Model(path) và decoder không được kết nối mạng ngay cả khi thư viện có hỗ trợ download.
        with patch('socket.socket.connect', side_effect=AssertionError('Network is forbidden')):
            pcm = audio_api._decode_pcm(silent_wav(), 'audio/wav')
            self.assertEqual(len(pcm), 16000 * 2)
            with self.assertRaises(audio_api.TranscriptionError) as raised:
                audio_api.transcribe_audio(silent_wav(), 'audio/wav')
            self.assertEqual(raised.exception.status, 422)
            self.assertIn('No speech', str(raised.exception))

    def test_real_long_recording_is_rejected(self):
        if not audio_api.audio_configuration()['configured']:
            self.skipTest('Install voice dependencies and model first.')
        with self.assertRaises(audio_api.TranscriptionError) as raised:
            audio_api._decode_pcm(silent_wav(31), 'audio/wav')
        self.assertEqual(raised.exception.status, 422)
        self.assertIn('30-second', str(raised.exception))


class RecordedVoiceHTTPTests(unittest.TestCase):
    setUpClass = classmethod(web_tests.WebIntegrationTests.setUpClass.__func__)
    tearDownClass = classmethod(web_tests.WebIntegrationTests.tearDownClass.__func__)
    request = web_tests.WebIntegrationTests.request
    search = web_tests.WebIntegrationTests.search

    def test_recording_transcription_search_ranking_and_filters(self):
        with patch.object(self.server.search_service.speech_service, 'transcribe_audio', return_value='find laptop') as transcribe:
            status, result, _ = self.request('POST', '/api/voice-search', recording(top_k=3, filters={'category': 'laptop'}))
            self.assertEqual(status, 200, result)
            self.assertEqual(result['transcribed_text'], 'find laptop')
            self.assertEqual(result['voice_source'], 'microphone')
            self.assertEqual(result['transcription_model'], 'vosk-model-small-en-us-0.15')
            self.assertEqual(result['transcription_language'], 'en')
            self.assertTrue(result['transcription_offline'])
            self.assertEqual(result['results'], self.search({'type': 'voice', 'query': 'find laptop', 'top_k': 3,
                                                          'filters': {'category': 'laptop'}})['results'])
            transcribe.assert_called_once_with(AUDIO, 'audio/webm')

    def test_invalid_options_never_invoke_recognition(self):
        for payload in [None, [], recording(top_k=-1), recording(filters={'in_stock': 'yes'}),
                        recording(filters={'unknown': 2}), recording(query='pretend'), recording(mime_type='text/plain')]:
            with self.subTest(payload=str(payload)[:100]), patch.object(self.server.search_service.speech_service, 'transcribe_audio') as call:
                self.assertEqual(self.request('POST', '/api/voice-search', json.dumps(payload).encode())[0], 400)
                call.assert_not_called()

    def test_transcribed_punctuation_preserves_results_and_displayed_text(self):
        with patch.object(self.server.search_service.speech_service, 'transcribe_audio', return_value='Find laptop.'):
            status, result, _ = self.request('POST', '/api/voice-search', recording())
            self.assertEqual(status, 200)
            self.assertEqual(result['transcribed_text'], 'Find laptop.')
            self.assertEqual(result['returned_count'], 5)
            self.assertTrue(all(item['product']['category'] == 'laptop' for item in result['results']))

    def test_missing_model_is_json_and_releases_slot(self):
        with patch.object(self.server.search_service.speech_service, 'transcribe_audio', side_effect=audio_api.TranscriptionError('English Vosk model is missing.')):
            status, body, _ = self.request('POST', '/api/voice-search', recording())
            self.assertEqual(status, 503)
            self.assertIn('model', body['error'])
        self.assertTrue(self.server.audio_slot.acquire(blocking=False))
        self.server.audio_slot.release()

    def test_busy_audio_request_does_not_invoke_recognition(self):
        self.server.audio_slot.acquire()
        try:
            with patch.object(self.server.search_service.speech_service, 'transcribe_audio') as call:
                self.assertEqual(self.request('POST', '/api/voice-search', recording())[0], 429)
                call.assert_not_called()
        finally:
            self.server.audio_slot.release()

    def test_audio_http_limits_and_methods(self):
        self.assertEqual(self.request('POST', '/api/voice-search', b'{}', 'text/plain')[0], 415)
        self.assertEqual(self.request('POST', '/api/voice-search', b'{bad')[0], 400)
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.putrequest('POST', '/api/voice-search')
            connection.putheader('Content-Type', 'application/json')
            connection.putheader('Content-Length', str(3 * 1024 * 1024 + 1))
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 413)
            response.read()
        finally:
            connection.close()
        self.assertEqual(self.request('GET', '/api/voice-search')[0], 405)

    def test_origin_protection_and_matching_local_origin(self):
        for origin, expected in [('https://untrusted.example', 403), ('null', 403),
                                 (f'http://127.0.0.1:{self.server.server_port}', 200)]:
            connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
            try:
                with patch.object(self.server.search_service.speech_service, 'transcribe_audio', return_value='phone') as call:
                    connection.request('POST', '/api/voice-search', body=json.dumps(recording()),
                                       headers={'Content-Type': 'application/json', 'Origin': origin})
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected)
                    response.read()
                    if expected == 403:
                        call.assert_not_called()
            finally:
                connection.close()

    def test_health_reports_offline_engine_and_keeps_files_private(self):
        status, health, _ = self.request('GET', '/api/health')
        self.assertEqual(status, 200)
        self.assertEqual(health['voice_api']['engine'], 'vosk')
        self.assertTrue(health['voice_api']['offline'])
        self.assertFalse(health['voice_api']['requires_api_key'])
        for path in ['/.env', '/CodePython/models/vosk-model-small-en-us-0.15/am/final.mdl']:
            self.assertEqual(self.request('GET', path)[0], 404)

    def test_real_webm_transcription_through_http_returns_laptops_offline(self):
        if not audio_api.audio_configuration()['configured']:
            self.skipTest('Install the local model to run real transcription.')
        fixture = Path(__file__).parent / 'fixtures' / 'find-laptop.wav'
        if not fixture.is_file():
            self.skipTest('English speech fixture is not available.')
        _, ffmpeg = audio_api._dependencies()
        converted = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-f', 'wav',
                                    '-i', 'pipe:0', '-c:a', 'libopus', '-f', 'webm', 'pipe:1'],
                                   input=fixture.read_bytes(), capture_output=True, timeout=15,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
        original_connect = socket.socket.connect

        def local_only(sock, address):
            if address[0] not in {'127.0.0.1', 'localhost', '::1'}:
                raise AssertionError('External network is forbidden during transcription.')
            return original_connect(sock, address)

        with patch('socket.socket.connect', local_only):
            status, result, _ = self.request('POST', '/api/voice-search', recording(
                audio_base64=base64.b64encode(converted.stdout).decode(), top_k=3))
        self.assertEqual(status, 200, result)
        self.assertEqual(result['transcribed_text'], 'find laptop')
        self.assertEqual(result['returned_count'], 3)
        self.assertTrue(result['transcription_offline'])
        self.assertTrue(all(item['product']['category'] == 'laptop' for item in result['results']))

    def test_real_corrupt_recording_is_json_not_fake_results(self):
        if not audio_api.audio_configuration()['configured']:
            self.skipTest('Install voice dependencies and model first.')
        status, body, _ = self.request('POST', '/api/voice-search', recording())
        self.assertEqual(status, 422, body)
        self.assertIn('decode', body['error'].lower())


if __name__ == '__main__':
    unittest.main()
