/* Device-free UI tests for upload lifecycle; real CLIP is tested in Python/HTTP. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const root = path.resolve(__dirname, '../../..');
const html = fs.readFileSync(path.join(root, 'FrontEnd/image_search_vintage_editorial/code.html'), 'utf8');
const code = fs.readFileSync(path.join(root, 'FrontEnd/assets/image.js'), 'utf8');
const pause = () => new Promise(resolve => setTimeout(resolve, 10));
const vector = Array.from({ length: 512 }, (_, i) => i === 0 ? 1 : 0);
const result = { embedding: vector, detected_object: 'mouse', vector_dimension: 512,
  duration_ms: 5, filtered_count: 1, candidate_count: 20, returned_count: 1,
  results: [{ product: { id: 16, name: 'Mouse' }, score: 1, rank: 1 }] };
let checks = 0;
async function test(label, action) { await action(); checks++; console.log('PASS ' + label); }
async function harness(configured = true) {
  const dom = new JSDOM(html, { url: 'http://127.0.0.1:8000/image-search', runScripts: 'outside-only' });
  const w = dom.window, $ = id => w.document.getElementById(id);
  const calls = [], revoked = [], downloads = [];
  w.URL.createObjectURL = () => 'blob:fake-' + Math.random();
  w.URL.revokeObjectURL = url => revoked.push(url);
  w.HTMLAnchorElement.prototype.click = function () { downloads.push(this.download); };
  w.HTMLElement.prototype.scrollIntoView = () => {};
  let reply = async () => result;
  w.Catalog = {
    getCatalog: async () => ({ categories: ['phone', 'accessory'], products: [
      { id:1, category:'phone', name:'Phone', image_url:'/phone.jpg' },
      { id:16, category:'accessory', name:'Mouse', image_url:'/mouse.png' }] }),
    getHealth: async () => ({ image_api: { configured, error: configured ? null : 'Install local CLIP model.' } }),
    categoryLabel: name => name === 'phone' ? 'Phones' : 'Accessories',
    setStatus: (target, message) => { if (target) target.textContent = message; },
    searchImage: async payload => { calls.push(payload); return reply(payload); },
    renderProducts: (target, rows) => {
      target.replaceChildren();
      rows.forEach(row => { const article = w.document.createElement('article'); article.className = 'catalog-result-card'; article.textContent = row.product.name; target.append(article); });
    }
  };
  w.eval(code);
  for (let n = 0; n < 100 && $('image-model-status').textContent.startsWith('Checking'); n++) await pause();
  return { w, $, calls, revoked, downloads, reply: fn => { reply = fn; },
    submit: () => $('image-search-form').dispatchEvent(new w.Event('submit', { cancelable:true })),
    select: file => { Object.defineProperty($('file-input'), 'files', { configurable:true, value:[file] }); $('file-input').dispatchEvent(new w.Event('change')); },
    file: () => new w.File(['real file bytes'], 'mouse.png', { type:'image/png' }),
    close: () => { w.dispatchEvent(new w.Event('beforeunload')); w.close(); }
  };
}
(async () => {
  await test('No automatic model inference or manual vector input', async () => {
    const h = await harness(); assert.equal(h.calls.length, 0); assert.equal(h.$('image-embedding'), null); h.close();
  });
  await test('Missing model disables search and does not fake results', async () => {
    const h = await harness(false); h.submit(); await pause(); assert.equal(h.calls.length, 0); assert.equal(h.$('btn-search-trigger').disabled, true); h.close();
  });
  await test('Upload sends bytes, not preset ID or manual embedding', async () => {
    const h = await harness(); h.select(h.file()); h.submit(); await pause(); await pause();
    assert.equal(h.calls.length, 1); assert.equal(Buffer.from(h.calls[0].image_base64, 'base64').toString(), 'real file bytes');
    assert.equal(h.calls[0].product_id, undefined); assert.equal(h.calls[0].embedding, undefined);
    assert.equal(JSON.parse(h.$('image-vector-preview').value).length, 512); h.close();
  });
  await test('Reference uses local catalog ID and real backend recognition', async () => {
    const h = await harness(); h.$('btn-sample-4').click(); await pause(); assert.equal(h.calls[0].product_id, 16); h.close();
  });
  await test('Unsupported, empty and oversized files clear previous selection', async () => {
    const h = await harness();
    for (const file of [{ type:'image/gif', size:10 }, { type:'image/png', size:0 }, { type:'image/png', size:13*1024*1024 }]) {
      h.select(file); h.submit(); assert.equal(h.$('btn-search-trigger').disabled, true);
    }
    assert.equal(h.calls.length, 0); h.close();
  });
  await test('Duplicate submissions do not duplicate image inference', async () => {
    const h = await harness(); let resolve; h.reply(() => new Promise(r => { resolve = r; }));
    h.submit(); h.submit(); assert.equal(h.calls.length, 1); resolve(result); await pause(); h.close();
  });
  await test('Clear during inference discards the late result', async () => {
    const h = await harness(); let resolve; h.reply(() => new Promise(r => { resolve = r; }));
    h.submit(); h.$('image-clear').click(); resolve(result); await pause();
    assert.equal(h.$('image-vector-preview').value, ''); assert.equal(h.$('image-results').querySelector('article'), null); h.close();
  });
  await test('Changing filters discards a response for old filters', async () => {
    const h = await harness(); let resolve; h.reply(() => new Promise(r => { resolve = r; }));
    h.submit(); h.$('image-category').value = 'accessory'; h.$('image-category').dispatchEvent(new h.w.Event('change'));
    resolve(result); await pause(); assert.equal(h.$('image-vector-preview').value, ''); h.close();
  });
  await test('Unreadable file is reported before a request', async () => {
    const h = await harness(); h.w.FileReader = class { readAsDataURL() { this.onerror(); } };
    h.select(h.file()); h.submit(); await pause(); assert.equal(h.calls.length, 0); assert.match(h.$('image-status').textContent, /Unable to read/); h.close();
  });
  await test('Model/server error leaves no stale vector or results', async () => {
    const h = await harness(); h.reply(async () => { throw new Error('Local model failed.'); });
    h.submit(); await pause(); assert.match(h.$('image-status').textContent, /Local model failed/);
    assert.equal(h.$('image-vector-download').disabled, true); assert.equal(h.$('image-vector-preview').value, ''); h.close();
  });
  await test('Vector can be exported as JSON and preview URLs are released', async () => {
    const h = await harness(); h.select(h.file()); h.select(h.file()); assert.equal(h.revoked.length, 1);
    h.submit(); await pause(); await pause(); h.$('image-vector-download').click(); assert.deepEqual(h.downloads, ['image-vector.json']); h.close();
  });
  await test('Closing the page during inference does not update a disposed DOM', async () => {
    const h = await harness(); let resolve; h.reply(() => new Promise(r => { resolve = r; }));
    h.submit(); h.close(); resolve(result); await pause();
  });
  console.log('\n' + checks + ' image upload UI checks passed (mock model; no browser layout evaluation).');
})().catch(error => { console.error(error); process.exitCode = 1; });
