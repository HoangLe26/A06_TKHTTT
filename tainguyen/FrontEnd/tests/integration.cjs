/* DOM + real API integration checks. This does not measure browser layout. */
const assert = require('node:assert/strict');
const { JSDOM, ResourceLoader, VirtualConsole } = require('jsdom');
const base = process.env.SEARCH_BASE_URL || process.argv[2] || 'http://127.0.0.1:8000';
const baseOrigin = new URL(base).origin;
let checks = 0;
let catalog, orders;
const product = id => catalog.products.find(item => item.id === id);
const amount = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

class LocalResources extends ResourceLoader {
  fetch(url, options) {
    // Verify local scripts without requiring external CSS/font/CDN services.
    if (new URL(url).origin !== baseOrigin) return null;
    return super.fetch(url, options);
  }
}

async function waitFor(predicate, label) {
  const deadline = Date.now() + 30000;
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
  await waitFor(() => dom.window.Catalog && dom.window.document.querySelector('.catalog-mobile-nav'), 'application shell');
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
const englishCategories = { phone: 'Phones', tablet: 'Tablets', laptop: 'Laptops', accessory: 'Accessories' };

function checkEnglishUI(p, mode) {
  check(`${mode} interface and category labels are English`, () => {
    assert.equal(p.document.documentElement.lang, 'en');
    const vietnameseLetters = /[\u00c0-\u024f\u1e00-\u1eff]/u;
    assert.doesNotMatch(p.document.body.textContent, vietnameseLetters);
    for (const node of p.document.querySelectorAll('[aria-label], [placeholder], [title], img[alt]')) {
      for (const attribute of ['aria-label', 'placeholder', 'title', 'alt']) {
        assert.doesNotMatch(node.getAttribute(attribute) || '', vietnameseLetters);
      }
    }
    for (const [category, label] of Object.entries(englishCategories)) {
      const control = p.document.querySelector(`[data-category="${category}"], option[value="${category}"]`);
      if (control) assert.equal(control.textContent.trim(), label);
      const preset = p.document.querySelector(`[data-preset="${category}"]`);
      if (preset) assert.ok(preset.textContent.startsWith(label + ':'));
    }
  });
}

function checkRemovedIntro(p, mode) {
  check(`${mode} has no removed demo intro or connection banner`, () => {
    assert.equal(p.document.getElementById('catalog-connection'), null);
    assert.equal(p.document.getElementById('quick-demo-btn'), null);
    assert.doesNotMatch(p.document.body.textContent,
      /Demo 1: Text|Demo 1: Keyword Matching|auto_fix_high|Demo 2: Active|Simulated speech-to-text\s*·?\s*enter your transcript below|Demo 03 \/ Image Similarity|Visual Similarity & Artificial Embedding Search|Connected\s*·\s*20 products/);
    assert.equal(p.document.querySelectorAll('.catalog-mobile-nav a').length, 4);
    if (mode === 'Text') {
      assert.ok(p.document.getElementById('text-preset-btn'));
      assert.match(p.document.body.textContent, /Keyword Retrieval:.*Active/s);
      assert.match(p.document.body.textContent, /One Point per Matching Keyword/);
    } else if (mode === 'Voice') {
      assert.ok(p.document.getElementById('voice-banner-latency'));
      assert.match(p.document.body.textContent, /English Voice Search · Record & Transcribe/);
    } else if (mode === 'Image') {
      assert.match(p.document.body.textContent, /Local CLIP · Real image features · 512 dimensions/);
    }
  });
}

function checkCleanProductLabels(p, mode, resultsId) {
  check(`${mode} has no Demo text or category/color labels on product cards`, () => {
    assert.doesNotMatch(p.document.body.textContent, /\bdemo\b/i);
    for (const node of p.document.querySelectorAll('[aria-label], [placeholder], [title], img[alt]')) {
      for (const attribute of ['aria-label', 'placeholder', 'title', 'alt']) {
        assert.doesNotMatch(node.getAttribute(attribute) || '', /\bdemo\b/i);
      }
    }
    if (resultsId) {
      for (const card of cards(p, resultsId)) {
        const item = catalog.products.find(item => item.name === card.querySelector('h3').textContent);
        assert.ok(item);
        assert.ok(!card.textContent.includes(`${englishCategories[item.category]} · ${item.color}`));
      }
    } else {
      for (const button of p.document.querySelectorAll('[data-product-index]')) {
        const row = button.parentElement.parentElement;
        const item = catalog.products.find(item => item.name === row.querySelector('h3').textContent);
        assert.ok(item);
        assert.ok(!row.textContent.includes(`${item.category} · ${item.color}`));
      }
    }
  });
}

async function testText() {
  const p = await page('/text-search');
  try {
    await waitFor(() => cards(p, 'text-results').length === 5, 'default text results');
    checkEnglishUI(p, 'Text');
    checkRemovedIntro(p, 'Text');
    checkCleanProductLabels(p, 'Text', 'text-results');
    check('Text default results come from the 20-product catalogue', () => assert.ok(cards(p, 'text-results')[0].textContent.includes(product(1).name)));
    check('Navigation links resolve to the four application routes', () => {
      for (const link of p.document.querySelectorAll('a[data-path]')) assert.equal(link.pathname, '/' + link.dataset.path);
    });
    for (const category of ['tablet', 'laptop', 'accessory', '', 'phone']) {
      edit(p, 'search-input', 'phone');
      p.document.getElementById('text-top-k').value = '3';
      p.document.querySelector(`[data-category="${category}"]`).click();
      const expected = catalog.products.filter(item => !category || item.category === category);
      await waitFor(() => !p.document.getElementById('search-exec-btn').disabled
        && cards(p, 'text-results').length === expected.length, `browse ${category || 'all'}`);
      check(`Category ${category || 'All Categories'} shows its actual products despite the old keyword`, () => {
        assert.deepEqual(cards(p, 'text-results').map(card => card.querySelector('h3').textContent), expected.map(item => item.name));
        assert.equal(p.document.getElementById('search-input').value, '');
        assert.equal(p.document.getElementById('text-top-k').value, '');
        const payload = JSON.parse(p.requests.filter(r => r.path === '/api/search').at(-1).options.body);
        assert.equal(payload.browse_catalog, true);
        assert.equal(payload.query, '');
        assert.equal(payload.filters.category, category || null);
        assert.doesNotMatch(cards(p, 'text-results')[0].textContent, /Keyword score/);
      });
    }
    edit(p, 'search-input', 'iphone');
    p.document.getElementById('search-exec-btn').click();
    await waitFor(() => !p.document.getElementById('search-exec-btn').disabled
      && cards(p, 'text-results')[0]?.textContent.includes('Keyword score'), 'keyword search after browsing');
    check('Typing a keyword after browsing still searches within the selected category', () => {
      assert.equal(cards(p, 'text-results').length, 5);
      const payload = JSON.parse(p.requests.filter(r => r.path === '/api/search').at(-1).options.body);
      assert.equal(payload.browse_catalog, false);
      assert.equal(payload.filters.category, 'phone');
    });
    edit(p, 'text-top-k', '3', 'change');
    await waitFor(() => cards(p, 'text-results').length === 3, 'text top-k');
    check('Text top-k truncates after ranking', () => assert.match(text(p, 'text-count'), /3 shown/));
    check('Text stock-only control is removed and does not silently filter products', () => {
      assert.equal(p.document.getElementById('in-stock-filter'), null);
      const facets = p.document.querySelector('[data-category="phone"]').parentElement;
      assert.doesNotMatch(facets.textContent, /In Stock Only|check_circle/);
      const payload = JSON.parse(p.requests.filter(r => r.path === '/api/search').at(-1).options.body);
      assert.equal(payload.filters.in_stock, undefined);
    });
    p.document.querySelector('#text-results .catalog-button').click();
    check('Text product detail dialog uses actual metadata', () => {
      assert.ok(text(p, 'catalog-product-dialog').includes(product(1).name));
      assert.ok(text(p, 'catalog-product-dialog').includes(`Stock: ${product(1).stock}`));
      assert.doesNotMatch(text(p, 'catalog-product-dialog'), /\bdemo\b/i);
      assert.equal(p.document.querySelector('#catalog-product-dialog a').href, product(1).source_url);
      assert.ok(text(p, 'catalog-product-dialog').includes('Category: Phones'));
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
    p.document.getElementById('text-preset-btn').click();
    await waitFor(() => cards(p, 'text-results').length === 5, 'preset reset');
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
    await waitFor(() => text(p, 'voice-api-status') !== 'Checking local voice model...', 'voice health check');
    check('Voice starts empty and does not auto-submit paid audio requests', () => {
      assert.equal(p.document.getElementById('voice-input').value, '');
      assert.equal(cards(p, 'voice-results').length, 0);
      assert.ok(!p.requests.some(request => request.path === '/api/voice-search'));
    });
    checkEnglishUI(p, 'Voice');
    checkRemovedIntro(p, 'Voice');
    checkCleanProductLabels(p, 'Voice', 'voice-results');
    p.document.getElementById('voice-preset-btn').click();
    await waitFor(() => cards(p, 'voice-results').length === 5, 'typed voice preset');
    check('Voice typed fallback displays the transcript returned by Python', () => assert.equal(text(p, 'voice-transcribed'), 'find laptop'));
    edit(p, 'voice-input', 'find tablet');
    p.document.getElementById('voice-input').dispatchEvent(new p.window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await waitFor(() => text(p, 'voice-transcribed') === 'find tablet', 'voice edit');
    check('Editable voice query retrieves a real tablet first', () => assert.ok(cards(p, 'voice-results')[0].textContent.includes(product(6).name)));
    edit(p, 'voice-category', 'tablet', 'change');
    await waitFor(() => cards(p, 'voice-results').length === 5, 'voice category');
    check('Voice category filter is applied by the backend', () => assert.equal(cards(p, 'voice-results').length, 5));
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
    await waitFor(() => text(p, 'image-model-status').includes('CLIP ready'), 'image model ready');
    checkEnglishUI(p, 'Image');
    checkRemovedIntro(p, 'Image');
    check('Image does not auto-run inference or require a manual vector', () => {
      assert.equal(cards(p, 'image-results').length, 0);
      assert.equal(p.document.getElementById('image-embedding'), null);
      assert.ok(!p.requests.some(r => r.path === '/api/image-search'));
    });
    submit(p, 'image-search-form');
    await waitFor(() => cards(p, 'image-results').length === 20, 'image reference results');
    checkCleanProductLabels(p, 'Image', 'image-results');
    check('Image reference is encoded by CLIP on the backend', () => {
      assert.ok(cards(p, 'image-results')[0].textContent.includes(product(1).name));
      assert.match(text(p, 'image-detected-object'), /phone/);
      assert.equal(JSON.parse(p.document.getElementById('image-vector-preview').value).length, 512);
      assert.equal(p.document.getElementById('image-vector-download').disabled, false);
      const request = JSON.parse(p.requests.filter(r => r.path === '/api/image-search').at(-1).options.body);
      assert.equal(request.product_id, 1);
      assert.equal(request.embedding, undefined);
    });
    for (const [buttonId, productId, label] of [
      ['btn-sample-2', 6, 'tablet'], ['btn-sample-3', 11, 'laptop'], ['btn-sample-4', 16, 'mouse']]) {
      p.document.getElementById(buttonId).click();
      await waitFor(() => !p.document.getElementById('btn-search-trigger').disabled
        && cards(p, 'image-results')[0]?.textContent.includes(product(productId).name), 'reference ' + productId);
      check('Real reference image is recognized: ' + label, () => {
        assert.equal(p.document.getElementById('query-preview-img').getAttribute('src'), product(productId).image_url);
        assert.match(text(p, 'image-detected-object'), new RegExp(label));
      });
    }
    edit(p, 'image-top-k', '3', 'change');
    submit(p, 'image-search-form');
    await waitFor(() => cards(p, 'image-results').length === 3, 'image top k');
    check('Image top-k is applied after ranking', () => assert.match(text(p, 'image-result-count'), /3 ranked/));
    edit(p, 'image-category', 'laptop', 'change');
    edit(p, 'image-threshold', '0.9999', 'change');
    submit(p, 'image-search-form');
    await waitFor(() => text(p, 'image-status').includes('No products match'), 'image threshold');
    check('Image category and threshold filter the real cosine results', () => assert.equal(cards(p, 'image-results').length, 0));
    edit(p, 'image-threshold', '', 'change');
    edit(p, 'image-category', '', 'change');
    const bytes = require('node:fs').readFileSync(require('node:path').join(__dirname,
      '../../../CodePython/data/images', product(16).image));
    const file = new p.window.File([bytes], 'mouse.png', { type: 'image/png' });
    Object.defineProperty(p.document.getElementById('file-input'), 'files', { configurable: true, value: [file] });
    p.document.getElementById('file-input').dispatchEvent(new p.window.Event('change'));
    check('Custom image replaces the reference and clears old vectors', () => {
      assert.equal(p.document.getElementById('image-vector-preview').value, '');
      assert.equal(cards(p, 'image-results').length, 0);
      assert.match(text(p, 'image-status'), /local Python server/);
    });
    submit(p, 'image-search-form');
    await waitFor(() => cards(p, 'image-results')[0]?.textContent.includes(product(16).name), 'real file upload');
    check('File upload creates a real vector without manual input', () => {
      assert.match(text(p, 'image-detected-object'), /mouse/);
      assert.equal(JSON.parse(p.document.getElementById('image-vector-preview').value).length, 512);
      const request = JSON.parse(p.requests.filter(r => r.path === '/api/image-search').at(-1).options.body);
      assert.equal(request.product_id, undefined);
      assert.equal(Buffer.from(request.image_base64, 'base64').compare(bytes), 0);
    });
    const bad = new p.window.File(['broken image'], 'bad.png', { type: 'image/png' });
    Object.defineProperty(p.document.getElementById('file-input'), 'files', { configurable: true, value: [bad] });
    p.document.getElementById('file-input').dispatchEvent(new p.window.Event('change'));
    submit(p, 'image-search-form');
    await waitFor(() => text(p, 'image-status').includes('corrupt'), 'bad image server validation');
    check('Corrupt image is rejected without showing fake results', () => {
      assert.equal(cards(p, 'image-results').length, 0);
      assert.equal(p.document.getElementById('image-vector-preview').value, '');
      assert.equal(p.document.getElementById('image-vector-download').disabled, true);
    });
    Object.defineProperty(p.document.getElementById('file-input'), 'files', {
      configurable: true, value: [{ name: 'large.png', type: 'image/png', size: 13 * 1024 * 1024 }] });
    p.document.getElementById('file-input').dispatchEvent(new p.window.Event('change'));
    check('Oversized image cannot leave the old reference active', () => {
      assert.match(text(p, 'image-status'), /12 MB/);
      assert.equal(p.document.getElementById('btn-search-trigger').disabled, true);
    });
    p.document.getElementById('image-clear').click();
    check('Clear removes image, vector and results', () => {
      assert.equal(p.document.getElementById('query-preview-img').getAttribute('src'), null);
      assert.equal(p.document.getElementById('image-vector-preview').value, '');
      assert.equal(cards(p, 'image-results').length, 0);
    });
    assert.deepEqual(p.errors, []);
  } finally { p.window.close(); }
}

async function testOrders() {
  const p = await page('/order-search');
  try {
    await waitFor(() => text(p, 'order-status').includes('Retrieved order'), 'default order');
    checkEnglishUI(p, 'Order');
    checkRemovedIntro(p, 'Order');
    checkCleanProductLabels(p, 'Order');
    check('O001 details use actual items and computed total', () => {
      assert.ok(text(p, 'order-details').includes(product(1).name));
      assert.ok(text(p, 'order-details').includes(amount(orders[0].total)));
    });
    p.document.querySelector('[data-order-id="O002"]').click();
    await waitFor(() => text(p, 'order-status').includes('#O002'), 'second order');
    check('Quick order lookup changes status, items and total', () => {
      assert.ok(text(p, 'order-details').includes(product(6).name));
      assert.ok(text(p, 'order-details').includes(amount(orders[1].total)));
      assert.match(text(p, 'order-status'), /Delivered/);
    });
    p.document.querySelector('[data-product-index]').click();
    check('Order product details omit an invented ranking score', () => {
      assert.ok(text(p, 'catalog-product-dialog').includes(product(6).name));
      assert.doesNotMatch(text(p, 'catalog-product-dialog'), /NaN|Ranking score/);
    });
    p.document.querySelector('#catalog-product-dialog button').click();
    p.document.querySelector('[data-print]').click();
    check('Order Print invokes the browser print action', () => assert.equal(p.window.printCount, 1));
    edit(p, 'order-id-input', 'UNKNOWN');
    submit(p, 'order-search-form');
    await waitFor(() => text(p, 'order-status').includes('not found'), 'unknown order');
    check('Unknown order clears the previous details', () => assert.ok(!text(p, 'order-details').includes(product(6).name)));
    p.document.getElementById('order-reset').click();
    check('Order reset clears the input and selected record', () => assert.equal(p.document.getElementById('order-id-input').value, ''));
    edit(p, 'order-id-input', 'o003');
    submit(p, 'order-search-form');
    await waitFor(() => text(p, 'order-status').includes('#O003'), 'third order');
    check('Case-insensitive order lookup computes the third total', () => assert.ok(text(p, 'order-details').includes(amount(orders[2].total))));
    check('Unsupported purchase actions are visibly disabled', () => assert.ok(p.document.querySelector('#order-details button[disabled]')));
    assert.deepEqual(p.errors, []);
  } finally { p.window.close(); }
}

(async () => {
  catalog = await (await fetch(base + '/api/catalog')).json();
  orders = await Promise.all(['O001', 'O002', 'O003'].map(async id => (await (await fetch(base + '/api/orders/' + id)).json()).order));
  check('Catalogue contains five products in each of the four groups', () => {
    assert.equal(catalog.products.length, 20);
    assert.deepEqual(catalog.category_labels, englishCategories);
    for (const category of ['phone', 'tablet', 'laptop', 'accessory']) assert.equal(catalog.products.filter(p => p.category === category).length, 5);
  });
  for (const item of catalog.products) {
    const response = await fetch(base + item.image_url);
    check(`Real product image is available: ${item.name}`, () => {
      assert.equal(response.status, 200);
      assert.match(response.headers.get('content-type'), /^image\/(jpeg|png|webp)/);
      assert.equal(item.image_is_illustration, false);
    });
  }
  await testText(); await testVoice(); await testImage(); await testOrders();
  console.log(`\n${checks} DOM/API interaction checks passed. Browser layout is not evaluated.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
