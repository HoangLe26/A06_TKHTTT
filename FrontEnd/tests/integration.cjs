/* DOM + real API integration checks. This does not measure browser layout. */
const assert = require('node:assert/strict');
const { JSDOM, ResourceLoader, VirtualConsole } = require('jsdom');
const base = process.env.SEARCH_BASE_URL || 'http://127.0.0.1:8000';
const baseOrigin = new URL(base).origin;
let checks = 0;

class LocalResources extends ResourceLoader {
  fetch(url, options) {
    // Verify local scripts without requiring external CSS/font/CDN services.
    if (new URL(url).origin !== baseOrigin) return null;
    return super.fetch(url, options);
  }
}

async function waitFor(predicate, label) {
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 25));
  }
  throw new Error(`Timed out: ${label}`);
}

function check(label, callback) {
  callback(); checks++;
  console.log(`PASS ${label}`);
}

async function page(route) {
  const errors = [];
  const requests = [];
  const console = new VirtualConsole();
  console.on('jsdomError', error => errors.push(error));
  const dom = await JSDOM.fromURL(base + route, {
    runScripts: 'dangerously', resources: new LocalResources(), virtualConsole: console,
    beforeParse(window) {
      window.AbortController = globalThis.AbortController;
      window.fetch = (path, options = {}) => {
        requests.push({ path: String(path), options });
        return fetch(new URL(path, base).href, options);
      };
      window.URL.createObjectURL = () => 'blob:local-test-image';
      window.URL.revokeObjectURL = () => {};
      window.HTMLElement.prototype.scrollIntoView = () => {};
      window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
      window.HTMLDialogElement.prototype.close = function () { this.open = false; };
      window.printCount = 0;
      window.print = () => { window.printCount++; };
    },
  });
  await waitFor(() => dom.window.Catalog && dom.window.document.querySelector('#catalog-connection')?.textContent.includes('Connected'), 'local connection');
  return { dom, window: dom.window, document: dom.window.document, errors, requests };
}

function edit(p, id, value, eventName = 'input') {
  const control = p.document.getElementById(id);
  assert.ok(control, id);
  control.value = value;
  control.dispatchEvent(new p.window.Event(eventName, { bubbles: true }));
}
const cards = (p, id) => [...p.document.querySelectorAll(`#${id} .catalog-result-card`)];
const text = (p, id) => p.document.getElementById(id).textContent;
const submit = (p, id) => p.document.getElementById(id).dispatchEvent(new p.window.Event('submit', { bubbles: true, cancelable: true }));

async function testText() {
  const p = await page('/text-search');
  try {
    await waitFor(() => cards(p, 'text-results').length === 8, 'default text results');
    check('Text default results come from the 10-product catalogue', () => assert.match(cards(p, 'text-results')[0].textContent, /Nike Running Shoes.*2\.0000|2\.0000.*Nike Running Shoes/s));
    check('Navigation links resolve to the four application routes', () => {
      for (const link of p.document.querySelectorAll('a[data-path]')) assert.equal(link.pathname, '/' + link.dataset.path);
    });
    p.document.querySelector('[data-category="shoes"]').click();
    await waitFor(() => cards(p, 'text-results').length === 5, 'shoe filter');
    check('Text category filter fetches and limits real candidates', () => assert.equal(cards(p, 'text-results').length, 5));
    edit(p, 'text-top-k', '3', 'change');
    await waitFor(() => cards(p, 'text-results').length === 3, 'text top-k');
    check('Text top-k truncates after ranking', () => assert.match(text(p, 'text-count'), /3 shown/));
    p.document.getElementById('in-stock-filter').click();
    await waitFor(() => !p.document.getElementById('search-exec-btn').disabled, 'stock filter');
    check('Stock filter is included in the request', () => {
      const payload = JSON.parse(p.requests.filter(r => r.path === '/api/search').at(-1).options.body);
      assert.equal(payload.filters.in_stock, true);
    });
    p.document.querySelector('#text-results .catalog-button').click();
    check('Text product detail dialog uses actual metadata', () => {
      assert.match(text(p, 'catalog-product-dialog'), /Nike Running Shoes/);
      assert.match(text(p, 'catalog-product-dialog'), /Stock: 10/);
    });
    p.document.querySelector('#catalog-product-dialog button').click();
    edit(p, 'search-input', 'zzznomatchingproductzzz');
    p.document.getElementById('search-input').dispatchEvent(new p.window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await waitFor(() => text(p, 'text-status').includes('No products match'), 'no matching text');
    check('Enter and no-results handling clear old cards', () => assert.equal(cards(p, 'text-results').length, 0));
    edit(p, 'search-input', '<img src=x onerror=alert(1)>');
    p.document.getElementById('search-exec-btn').click();
    await waitFor(() => text(p, 'text-query-summary').includes('<img'), 'escaped query summary');
    check('Query text cannot inject markup into the summary', () => assert.equal(p.document.querySelector('#text-query-summary img'), null));
    p.document.getElementById('clear-search-btn').click();
    check('Clear resets the input and result state', () => {
      assert.equal(p.document.getElementById('search-input').value, '');
      assert.equal(cards(p, 'text-results').length, 0);
    });
    p.document.getElementById('quick-demo-btn').click();
    await waitFor(() => cards(p, 'text-results').length === 8, 'preset reset');
    check('Preset resets filters and reloads the real demo', () => assert.equal(p.document.getElementById('text-top-k').value, ''));
    p.window.fetch = () => Promise.reject(new TypeError('connection lost'));
    edit(p, 'search-input', 'red');
    p.document.getElementById('search-exec-btn').click();
    await waitFor(() => text(p, 'text-status').includes('Unable to connect'), 'connection error');
    check('Connection failure shows an error and clears stale results', () => assert.equal(cards(p, 'text-results').length, 0));
    assert.deepEqual(p.errors, []);
  } finally { p.window.close(); }
}

async function testVoice() {
  const p = await page('/voice-search');
  try {
    await waitFor(() => cards(p, 'voice-results').length > 0, 'voice default');
    check('Voice displays the identity transcription returned by Python', () => assert.equal(text(p, 'voice-transcribed'), 'find running shoes'));
    edit(p, 'voice-input', 'find black leather bag');
    p.document.getElementById('voice-input').dispatchEvent(new p.window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await waitFor(() => text(p, 'voice-transcribed') === 'find black leather bag', 'voice edit');
    check('Editable voice query retrieves Black Leather Bag first', () => assert.match(cards(p, 'voice-results')[0].textContent, /Black Leather Bag/));
    edit(p, 'voice-category', 'bag', 'change');
    await waitFor(() => cards(p, 'voice-results').length === 2, 'voice category');
    check('Voice category filter is applied by the backend', () => assert.equal(cards(p, 'voice-results').length, 2));
    p.document.getElementById('voice-list-btn').click();
    check('Voice grid/list toggle changes the displayed layout class', () => assert.ok(p.document.getElementById('voice-results').classList.contains('catalog-list')));
    p.document.getElementById('voice-clear-btn').click();
    check('Voice Clear resets transcript input and old results', () => {
      assert.equal(p.document.getElementById('voice-input').value, '');
      assert.equal(cards(p, 'voice-results').length, 0);
    });
    assert.deepEqual(p.errors, []);
  } finally { p.window.close(); }
}

async function testImage() {
  const p = await page('/image-search');
  try {
    await waitFor(() => cards(p, 'image-results').length === 10, 'image default');
    check('Image preset uses the actual artificial-vector index', () => assert.match(cards(p, 'image-results')[0].textContent, /Nike Running Shoes/));
    p.document.getElementById('btn-sample-2').click();
    await waitFor(() => cards(p, 'image-results')[0]?.textContent.includes('Black Leather Bag'), 'bag preset');
    check('Bag preset changes the image, vector and top result', () => assert.equal(p.document.getElementById('query-preview-img').getAttribute('src'), '/product-images/bag.svg'));
    edit(p, 'image-embedding', '1, 2');
    submit(p, 'image-search-form');
    check('Invalid dimension is shown without old image results', () => {
      assert.match(text(p, 'image-status'), /exactly 3/);
      assert.equal(cards(p, 'image-results').length, 0);
    });
    edit(p, 'image-embedding', '0, 0, 0');
    submit(p, 'image-search-form');
    await waitFor(() => cards(p, 'image-results').length === 10, 'zero image');
    check('Zero-vector image search returns finite zero scores', () => assert.match(cards(p, 'image-results')[0].textContent, /0\.0000/));
    edit(p, 'image-threshold', '0.99', 'change');
    submit(p, 'image-search-form');
    await waitFor(() => text(p, 'image-status').includes('No products match'), 'threshold');
    check('Similarity threshold is a real backend filter', () => assert.equal(cards(p, 'image-results').length, 0));
    edit(p, 'image-threshold', '', 'change');
    const file = new p.window.File([Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aN0sAAAAASUVORK5CYII=', 'base64')], 'sample.png', { type: 'image/png' });
    Object.defineProperty(p.document.getElementById('file-input'), 'files', { configurable: true, value: [file] });
    p.document.getElementById('file-input').dispatchEvent(new p.window.Event('change'));
    check('Custom image is preview-only and cannot reuse the old preset vector', () => {
      assert.equal(p.document.getElementById('image-embedding').value, '');
      assert.match(text(p, 'image-status'), /No feature extraction or upload/);
      assert.equal(cards(p, 'image-results').length, 0);
    });
    submit(p, 'image-search-form');
    check('Custom image requires a manually supplied vector', () => assert.match(text(p, 'image-status'), /Enter the artificial vector/));
    edit(p, 'image-embedding', '[0.12, 0.20, 0.93]');
    submit(p, 'image-search-form');
    await waitFor(() => cards(p, 'image-results')[0]?.textContent.includes('Black Leather Bag'), 'manual custom vector');
    check('Manual vector searches through the same cosine API', () => assert.match(cards(p, 'image-results')[0].textContent, /1\.0000/));
    Object.defineProperty(p.document.getElementById('file-input'), 'files', { configurable: true, value: [{ name: 'large.png', type: 'image/png', size: 13 * 1024 * 1024 }] });
    p.document.getElementById('file-input').dispatchEvent(new p.window.Event('change'));
    check('Image preview rejects files over the stated limit', () => assert.match(text(p, 'image-status'), /12 MB/));
    assert.deepEqual(p.errors, []);
  } finally { p.window.close(); }
}

async function testOrders() {
  const p = await page('/order-search');
  try {
    await waitFor(() => text(p, 'order-status').includes('Retrieved order'), 'default order');
    check('O001 details use actual items and computed total', () => {
      assert.match(text(p, 'order-details'), /Nike Running Shoes/);
      assert.match(text(p, 'order-details'), /\$175\.00/);
    });
    p.document.querySelector('[data-order-id="O002"]').click();
    await waitFor(() => text(p, 'order-status').includes('#O002'), 'second order');
    check('Quick order lookup changes status, items and total', () => {
      assert.match(text(p, 'order-details'), /Black Leather Bag/);
      assert.match(text(p, 'order-details'), /\$135\.00/);
      assert.match(text(p, 'order-status'), /Delivered/);
    });
    p.document.querySelector('[data-product-index]').click();
    check('Order product details omit an invented ranking score', () => {
      assert.match(text(p, 'catalog-product-dialog'), /Black Leather Bag/);
      assert.doesNotMatch(text(p, 'catalog-product-dialog'), /NaN|Ranking score/);
    });
    p.document.querySelector('#catalog-product-dialog button').click();
    p.document.querySelector('[data-print]').click();
    check('Order Print invokes the browser print action', () => assert.equal(p.window.printCount, 1));
    edit(p, 'order-id-input', 'UNKNOWN');
    submit(p, 'order-search-form');
    await waitFor(() => text(p, 'order-status').includes('not found'), 'unknown order');
    check('Unknown order clears the previous details', () => assert.doesNotMatch(text(p, 'order-details'), /Black Leather Bag|\$135/));
    p.document.getElementById('order-reset').click();
    check('Order reset clears the input and selected record', () => assert.equal(p.document.getElementById('order-id-input').value, ''));
    edit(p, 'order-id-input', 'o003');
    submit(p, 'order-search-form');
    await waitFor(() => text(p, 'order-status').includes('#O003'), 'third order');
    check('Case-insensitive order lookup computes the third total', () => assert.match(text(p, 'order-details'), /\$75\.00/));
    check('Unsupported purchase actions are visibly disabled', () => assert.ok(p.document.querySelector('#order-details button[disabled]')));
    assert.deepEqual(p.errors, []);
  } finally { p.window.close(); }
}

(async () => {
  await testText(); await testVoice(); await testImage(); await testOrders();
  console.log(`\n${checks} DOM/API interaction checks passed. Browser layout is not evaluated.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
