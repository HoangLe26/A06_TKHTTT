/* Kiểm thử trình điều khiển micro bằng thiết bị/API mock; không gọi dịch vụ có phí. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const root = path.resolve(__dirname, '../../..');
const html = fs.readFileSync(path.join(root, 'FrontEnd/voice_search_vintage_editorial/code.html'), 'utf8');
const apiJS = fs.readFileSync(path.join(root, 'FrontEnd/assets/api.js'), 'utf8');
const voiceJS = fs.readFileSync(path.join(root, 'FrontEnd/assets/voice.js'), 'utf8');
let checks = 0;

const sleep = () => new Promise(resolve => setTimeout(resolve, 10));
async function waitFor(predicate) {
  for (let attempt = 0; attempt < 150; attempt++) {
    if (predicate()) return;
    await sleep();
  }
  throw new Error('Timed out waiting for voice state');
}
function check(label, callback) {
  callback(); checks++;
  console.log(`PASS ${label}`);
}
function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

async function page(settings = {}) {
  const dom = new JSDOM(html, { url: 'http://127.0.0.1:8000/voice-search', runScripts: 'outside-only' });
  const w = dom.window;
  const requests = [];
  const intervals = new Map();
  let intervalID = 0;
  let now = 0;
  let stopped = 0;
  let mediaCalls = 0;
  const track = { stop() { stopped++; } };
  const stream = { getTracks: () => [track] };
  w.Date.now = () => now;
  w.setInterval = callback => { intervals.set(++intervalID, callback); return intervalID; };
  w.clearInterval = id => intervals.delete(id);
  w.AbortController = globalThis.AbortController;
  const p = { dom, w, requests, stream,
    get stopped() { return stopped; }, get mediaCalls() { return mediaCalls; },
    $: id => w.document.getElementById(id),
    audioRequests: () => requests.filter(request => request.path === '/api/voice-search'),
    advance(seconds) { now += seconds * 1000; for (const callback of [...intervals.values()]) callback(); },
    close() { w.dispatchEvent(new w.Event('beforeunload')); dom.window.close(); }
  };
  const result = { transcribed_text: 'find laptop', candidate_count: 5, filtered_count: 5,
    returned_count: 1, duration_ms: 123, results: [{ rank: 1, score: 1,
      product: { id: 11, name: 'Apple MacBook Air', price: 1049, stock: 8, category: 'laptop' } }] };
  w.fetch = async (url, options = {}) => {
    requests.push({ path: String(url), options });
    if (url === '/api/health') return { ok: true, json: async () => ({ voice_api: { configured: settings.configured !== false } }) };
    if (url === '/api/voice-search' && settings.responseGate) await settings.responseGate.promise;
    if (url === '/api/voice-search' && settings.apiError) return { ok: false, status: 503, json: async () => ({ error: 'Local Vosk model unavailable.' }) };
    return { ok: true, json: async () => result };
  };
  if (!settings.unsupported) {
    Object.defineProperty(w.navigator, 'mediaDevices', { value: {
      getUserMedia: async () => {
        mediaCalls++;
        if (settings.permissionGate) await settings.permissionGate.promise;
        if (settings.permissionError) throw new w.DOMException('Denied', 'NotAllowedError');
        return stream;
      }
    } });
    w.MediaRecorder = class extends w.EventTarget {
      static isTypeSupported(type) { return type === 'audio/webm;codecs=opus'; }
      constructor(stream, options) { super(); this.state = 'inactive'; this.mimeType = options.mimeType; }
      start() { this.state = 'recording'; }
      stop() {
        this.state = 'inactive';
        w.setTimeout(() => {
          const event = new w.Event('dataavailable');
          const data = settings.emptyAudio ? new Uint8Array(0)
            : settings.largeAudio ? new Uint8Array(2 * 1024 * 1024 + 1)
            : new Uint8Array([0x1a, 0x45, 0xdf, 0xa3, ...new Array(32).fill(0)]);
          event.data = new w.Blob([data], { type: this.mimeType });
          this.dispatchEvent(event);
          this.dispatchEvent(new w.Event('stop'));
        }, 0);
      }
    };
  }
  w.eval(apiJS);
  w.eval(voiceJS);
  await waitFor(() => p.$('voice-api-status').textContent !== 'Checking local voice model...');
  return p;
}

async function begin(p) {
  p.$('voice-record-btn').click();
  await waitFor(() => !p.$('voice-stop-btn').disabled);
}

(async () => {
  let p = await page();
  try {
    check('No automatic audio request or microphone capture on page load', () => {
      assert.equal(p.mediaCalls, 0); assert.equal(p.audioRequests().length, 0);
      assert.equal(p.$('voice-input').value, '');
    });
    p.$('voice-category').value = 'laptop';
    p.$('voice-top-k').value = '3';
    await begin(p);
    check('Record enables Stop, locks transcript and does not upload before stopping', () => {
      assert.equal(p.audioRequests().length, 0); assert.ok(p.$('voice-input').disabled);
      assert.ok(p.$('voice-record-btn').disabled);
    });
    p.$('voice-stop-btn').click();
    await waitFor(() => p.$('voice-input').value === 'find laptop' && !p.$('simulateVoiceBtn').disabled);
    check('Stop sends one base64 recording and selected filters then displays ranked products', () => {
      assert.equal(p.audioRequests().length, 1);
      const request = p.audioRequests()[0];
      const payload = JSON.parse(request.options.body);
      assert.equal(request.options.method, 'POST');
      assert.equal(payload.mime_type, 'audio/webm;codecs=opus');
      assert.ok(Buffer.from(payload.audio_base64, 'base64').length > 16);
      assert.equal(payload.filters.category, 'laptop'); assert.equal(payload.top_k, 3);
      assert.match(p.$('voice-results').textContent, /Apple MacBook Air/);
      assert.match(p.$('voice-pipeline-status').textContent, /Vosk Offline STT/);
      assert.ok(p.stopped > 0);
    });
    p.$('simulateVoiceBtn').click();
    await waitFor(() => !p.$('simulateVoiceBtn').disabled);
    check('Searching the editable transcript again does not re-run audio recognition', () => {
      assert.equal(p.audioRequests().length, 1);
      assert.equal(p.requests.at(-1).path, '/api/search');
    });
    await begin(p);
    p.$('voice-clear-btn').click();
    await sleep();
    check('Cancel recording stops microphone and never submits the cancelled audio', () => {
      assert.equal(p.audioRequests().length, 1); assert.ok(p.$('voice-stop-btn').disabled);
      assert.equal(p.$('voice-input').value, '');
    });
  } finally { p.close(); }

  p = await page();
  try {
    await begin(p); p.advance(30);
    await waitFor(() => p.audioRequests().length === 1 && !p.$('simulateVoiceBtn').disabled);
    check('30-second limit automatically stops and searches once', () => {
      assert.equal(p.audioRequests().length, 1); assert.ok(p.stopped > 0);
      assert.equal(p.$('voice-record-time').textContent, '30 / 30 seconds');
    });
  } finally { p.close(); }

  for (const settings of [{ permissionError: true }, { apiError: true }, { emptyAudio: true }, { largeAudio: true }]) {
    p = await page(settings);
    try {
      p.$('voice-record-btn').click();
      if (!settings.permissionError) { await waitFor(() => !p.$('voice-stop-btn').disabled); p.$('voice-stop-btn').click(); }
      await waitFor(() => p.$('voice-status').getAttribute('role') === 'alert');
      check(`Error handling ${Object.keys(settings)[0]} restores controls without fake results`, () => {
        assert.equal(p.$('voice-results').children.length, 0);
        assert.ok(!p.$('voice-record-btn').disabled); assert.ok(!p.$('voice-input').disabled);
        assert.equal(p.audioRequests().length, settings.apiError ? 1 : 0);
        if (!settings.permissionError) assert.ok(p.stopped > 0);
      });
    } finally { p.close(); }
  }

  const permissionGate = deferred();
  p = await page({ permissionGate });
  try {
    p.$('voice-record-btn').click(); p.$('voice-clear-btn').click(); permissionGate.resolve();
    await waitFor(() => p.stopped > 0);
    check('Cancelling during permission prompt releases late microphone stream without upload', () => {
      assert.equal(p.audioRequests().length, 0); assert.ok(p.$('voice-stop-btn').disabled);
    });
  } finally { p.close(); }

  const responseGate = deferred();
  p = await page({ responseGate });
  try {
    await begin(p); p.$('voice-stop-btn').click();
    await waitFor(() => p.audioRequests().length === 1);
    p.$('voice-clear-btn').click(); responseGate.resolve();
    await waitFor(() => !p.$('simulateVoiceBtn').disabled);
    check('Clear during API request ignores late response instead of repopulating results', () => {
      assert.equal(p.$('voice-input').value, ''); assert.equal(p.$('voice-results').children.length, 0);
      assert.match(p.$('voice-status').textContent, /may still finish/);
    });
  } finally { p.close(); }

  for (const settings of [{ configured: false }, { unsupported: true }]) {
    p = await page(settings);
    try {
      check(`Unavailable recording ${Object.keys(settings)[0]} retains typed fallback`, () => {
        assert.ok(p.$('voice-record-btn').disabled); assert.ok(!p.$('voice-input').disabled);
        assert.equal(p.audioRequests().length, 0);
      });
      p.$('voice-input').value = 'find laptop'; p.$('simulateVoiceBtn').click();
      await waitFor(() => /Apple MacBook Air/.test(p.$('voice-results').textContent));
    } finally { p.close(); }
  }
  console.log(`\n${checks} microphone/API-mock checks passed. No real audio or paid API was used.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
