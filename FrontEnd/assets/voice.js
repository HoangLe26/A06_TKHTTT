/* Ghi âm một câu ngắn, gửi khi dừng và giữ tìm kiếm transcript làm dự phòng. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const input = $('voice-input');
  const button = $('simulateVoiceBtn');
  const recordButton = $('voice-record-btn');
  const stopButton = $('voice-stop-btn');
  const results = $('voice-results');
  const status = $('voice-status');
  const category = $('voice-category');
  const inStock = $('voice-in-stock');
  const limit = $('voice-top-k');
  const controls = [input, button, category, inStock, limit, $('voice-preset-btn')];
  const maxSeconds = 30;
  const maxBytes = 2 * 1024 * 1024;
  let requestNumber = 0;
  let audioConfigured = false;
  let starting = false;
  let pending = false;
  let session = null;
  let recordingVersion = 0;
  let disposed = false;
  document.title = 'Voice Search · Multimodal Catalog';

  function supportedMime() {
    if (!window.MediaRecorder) return null;
    return ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
      .find(type => MediaRecorder.isTypeSupported(type)) || null;
  }

  function updateControls() {
    if (disposed) return;
    const busy = starting || pending || !!session;
    controls.forEach(control => { control.disabled = busy; });
    recordButton.disabled = busy || !audioConfigured || !supportedMime() || !navigator.mediaDevices?.getUserMedia;
    stopButton.disabled = !session || session.recorder.state !== 'recording';
    $('voice-clear-btn').textContent = session || starting ? 'Cancel Recording' : 'Clear';
  }

  function resetMetrics(message = 'No search yet') {
    $('voice-transcribed').textContent = '—';
    $('voice-candidates').textContent = '—';
    $('voice-flow-count').textContent = message;
    $('voice-count').textContent = message;
    $('voice-pipeline-status').textContent = message;
    $('voice-latency').textContent = 'Latency: —';
    $('voice-banner-latency').textContent = 'Timing appears after search';
    $('voice-input-mode').textContent = 'Microphone / typed transcript';
  }

  function invalidate(message = 'Ready to search') {
    ++requestNumber;
    results.replaceChildren();
    results.setAttribute('aria-busy', 'false');
    resetMetrics(message);
  }

  function options() {
    return { top_k: limit.value ? Number(limit.value) : null,
      filters: { category: category.value || null, in_stock: inStock.checked } };
  }

  function display(response, fromAudio) {
    Catalog.renderProducts(results, response.results, {
      scoreLabel: 'Keyword score', onDetails: (product, score) => Catalog.showProduct(product, score)
    });
    if (fromAudio) input.value = response.transcribed_text;
    $('voice-transcribed').textContent = response.transcribed_text || '(empty transcript)';
    $('voice-candidates').textContent = `${response.candidate_count} retrieved · ${response.filtered_count} after filters`;
    $('voice-flow-count').textContent = `${response.returned_count} Results`;
    $('voice-count').textContent = `${response.returned_count} Ranked Results`;
    $('voice-input-mode').textContent = fromAudio ? 'Recorded audio · English' : 'Typed transcript';
    $('voice-pipeline-status').textContent = fromAudio
      ? 'Vosk Offline STT → Keyword Search → Ranking' : 'Typed Text → Keyword Search → Ranking';
    const timing = `Latency: ${Number(response.duration_ms).toFixed(2)} ms`;
    $('voice-latency').textContent = timing;
    $('voice-banner-latency').textContent = timing;
    Catalog.setStatus(status, response.results.length
      ? (fromAudio ? 'Recording transcribed and searched. You can edit the transcript and search again.'
        : 'Transcript searched. Products are ranked by matching keywords.')
      : 'No matching products. Edit the transcript or broaden your category filter.');
  }

  async function search(audioPayload = null) {
    if (pending || starting || session) return;
    if (!audioPayload && !input.value.trim()) {
      invalidate();
      Catalog.setStatus(status, 'Record a query, or type a transcript before searching.', true);
      return;
    }
    const currentRequest = ++requestNumber;
    pending = true;
    results.replaceChildren();
    results.setAttribute('aria-busy', 'true');
    resetMetrics(audioPayload ? 'Transcribing...' : 'Searching...');
    updateControls();
    Catalog.setStatus(status, audioPayload ? 'Transcribing English audio locally with Vosk...'
      : 'Searching with your transcript...');
    try {
      const response = audioPayload
        ? await Catalog.searchAudio({ ...audioPayload, ...options() })
        : await Catalog.search({ type: 'voice', query: input.value, ...options() });
      if (currentRequest !== requestNumber) return;
      display(response, !!audioPayload);
    } catch (error) {
      if (currentRequest !== requestNumber) return;
      resetMetrics('Search failed');
      Catalog.setStatus(status, error.message || 'Unable to process this voice query.', true);
    } finally {
      pending = false;
      results.setAttribute('aria-busy', 'false');
      updateControls();
    }
  }

  function release(current) {
    clearInterval(current.timer);
    current.stream.getTracks().forEach(track => track.stop());
    if (session === current) {
      session = null;
      if (!disposed) $('voice-record-state').textContent = 'Microphone off';
    }
  }

  function audioBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(',', 2)[1]);
      reader.onerror = () => reject(new Error('Unable to read the recording. Please try again.'));
      reader.readAsDataURL(blob);
    });
  }

  function stopRecording() {
    if (!session || session.recorder.state !== 'recording') return;
    session.recorder.stop();
    stopButton.disabled = true;
    Catalog.setStatus(status, 'Finishing recording...');
  }

  async function startRecording() {
    if (recordButton.disabled) return;
    const version = ++recordingVersion;
    starting = true;
    invalidate();
    updateControls();
    Catalog.setStatus(status, 'Allow microphone access to record your English query.');
    let stream;
    let current;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Nếu hủy trong lúc chờ quyền micro, đóng stream vừa được cấp.
      if (version !== recordingVersion) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      const recorder = new MediaRecorder(stream, { mimeType: supportedMime(), audioBitsPerSecond: 64000 });
      current = { recorder, stream, chunks: [], cancelled: false, timer: null, version, bytes: 0 };
      session = current;
      recorder.addEventListener('dataavailable', event => {
        if (event.data.size) {
          current.chunks.push(event.data);
          current.bytes += event.data.size;
          if (current.bytes > maxBytes && recorder.state === 'recording') {
            current.cancelled = true;
            recorder.stop();
            Catalog.setStatus(status, 'Recording exceeds 2 MiB. Try a shorter sentence.', true);
          }
        }
      });
      recorder.addEventListener('error', () => {
        current.cancelled = true;
        if (recorder.state !== 'inactive') recorder.stop();
        release(current);
        updateControls();
        Catalog.setStatus(status, 'Recording failed. Check your microphone and try again.', true);
      });
      recorder.addEventListener('stop', async () => {
        release(current);
        if (current.cancelled || current.version !== recordingVersion) { updateControls(); return; }
        // Khóa nút trong lúc đọc Blob để không gửi bản ghi cũ sau khi đã bắt đầu bản mới.
        starting = true;
        updateControls();
        try {
          const blob = new Blob(current.chunks, { type: recorder.mimeType });
          if (!blob.size || blob.size > maxBytes) throw new Error('Recording is empty or too large. Please try again.');
          const audio = await audioBase64(blob);
          if (current.version !== recordingVersion) return;
          starting = false;
          await search({ audio_base64: audio, mime_type: blob.type });
        } catch (error) {
          if (current.version === recordingVersion) Catalog.setStatus(status, error.message, true);
        } finally {
          if (current.version === recordingVersion) starting = false;
          updateControls();
        }
      });
      input.value = '';
      $('voice-record-time').textContent = `0 / ${maxSeconds} seconds`;
      $('voice-record-state').textContent = 'Recording...';
      recorder.start(1000);
      const began = Date.now();
      current.timer = setInterval(() => {
        const elapsed = Math.min(maxSeconds, Math.floor((Date.now() - began) / 1000));
        $('voice-record-time').textContent = `${elapsed} / ${maxSeconds} seconds`;
        if (elapsed >= maxSeconds) stopRecording();
      }, 250);
      Catalog.setStatus(status, 'Recording. Say one short English sentence, then select Stop & Search.');
    } catch (error) {
      if (stream) stream.getTracks().forEach(track => track.stop());
      if (current) release(current);
      if (version === recordingVersion) {
        const message = error.name === 'NotAllowedError' ? 'Microphone permission denied. Allow access in your browser, or type a transcript.'
          : error.name === 'NotFoundError' ? 'No microphone found. Connect one, or type a transcript.'
          : 'Unable to start recording. Check your microphone and browser permissions.';
        Catalog.setStatus(status, message, true);
      }
    } finally {
      if (version === recordingVersion) starting = false;
      updateControls();
    }
  }

  function cancelRecording() {
    ++recordingVersion;
    starting = false;
    if (session) {
      const current = session;
      current.cancelled = true;
      if (current.recorder.state !== 'inactive') current.recorder.stop();
      release(current);
    }
    if (!disposed) $('voice-record-time').textContent = `0 / ${maxSeconds} seconds`;
  }

  button.addEventListener('click', () => search());
  recordButton.addEventListener('click', startRecording);
  stopButton.addEventListener('click', stopRecording);
  $('voice-preset-btn').addEventListener('click', () => {
    input.value = 'find laptop';
    category.value = '';
    inStock.checked = false;
    limit.value = '';
    search();
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); search(); }
  });
  input.addEventListener('input', () => {
    invalidate();
    Catalog.setStatus(status, 'Transcript edited. Select Search Transcript or press Enter to refresh.');
  });
  [category, inStock, limit].forEach(control => control.addEventListener('change', () => search()));
  $('voice-clear-btn').addEventListener('click', () => {
    cancelRecording();
    invalidate('Search cleared');
    input.value = '';
    Catalog.setStatus(status, pending ? 'Results cleared. Local transcription may still finish; no cloud request is made.'
      : 'Record an English query, or type a transcript to begin.');
    updateControls();
    input.focus();
  });
  window.addEventListener('beforeunload', () => {
    disposed = true;
    ++requestNumber;
    cancelRecording();
  });
  const gridButton = $('voice-grid-btn');
  const listButton = $('voice-list-btn');
  function setView(list) {
    results.classList.toggle('md:grid-cols-2', !list);
    results.classList.toggle('lg:grid-cols-3', !list);
    results.classList.toggle('catalog-list', list);
    gridButton.setAttribute('aria-pressed', String(!list));
    listButton.setAttribute('aria-pressed', String(list));
  }
  gridButton.addEventListener('click', () => setView(false));
  listButton.addEventListener('click', () => setView(true));
  resetMetrics();
  updateControls();
  (async () => {
    try {
      const health = await Catalog.getHealth();
      if (disposed) return;
      audioConfigured = !!health.voice_api?.configured;
      const browserSupported = !!navigator.mediaDevices?.getUserMedia && !!supportedMime();
      Catalog.setStatus('voice-api-status', !browserSupported
        ? 'Recording is unavailable in this browser. Use Chrome or Edge on localhost, or type a transcript.'
        : !audioConfigured ? (health.voice_api?.error || 'Install Vosk and the English model, then reload.')
        : 'Offline English transcription ready · Vosk small · no API key · maximum 30 seconds.', !browserSupported || !audioConfigured);
    } catch (error) {
      if (disposed) return;
      Catalog.setStatus('voice-api-status', error.message || 'Unable to check the local voice model.', true);
    }
    updateControls();
  })();
})();
