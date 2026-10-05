/* The voice prototype accepts an editable, already-transcribed text input. */
(() => {
  'use strict';
  const input = document.getElementById('voice-input');
  const button = document.getElementById('simulateVoiceBtn');
  const results = document.getElementById('voice-results');
  const status = document.getElementById('voice-status');
  const category = document.getElementById('voice-category');
  const inStock = document.getElementById('voice-in-stock');
  const limit = document.getElementById('voice-top-k');
  let requestNumber = 0;

  function resetMetrics(message = 'No search yet') {
    document.getElementById('voice-transcribed').textContent = '—';
    document.getElementById('voice-candidates').textContent = '—';
    document.getElementById('voice-flow-count').textContent = message;
    document.getElementById('voice-count').textContent = message;
    document.getElementById('voice-pipeline-status').textContent = message;
    document.getElementById('voice-latency').textContent = 'Latency: —';
    document.getElementById('voice-banner-latency').textContent = 'Timing appears after search';
  }

  async function search() {
    const currentRequest = ++requestNumber;
    results.replaceChildren();
    results.setAttribute('aria-busy', 'true');
    button.disabled = true;
    resetMetrics('Searching…');
    Catalog.setStatus(status, 'Passing your transcript through the simulated SpeechService…');
    try {
      const response = await Catalog.search({
        type: 'voice', query: input.value,
        top_k: limit.value ? Number(limit.value) : null,
        filters: {category: category.value || null, in_stock: inStock.checked}
      });
      if (currentRequest !== requestNumber) return;
      Catalog.renderProducts(results, response.results, {
        scoreLabel: 'Keyword score', onDetails: (product, score) => Catalog.showProduct(product, score)
      });
      document.getElementById('voice-transcribed').textContent = response.transcribed_text || '(empty transcript)';
      document.getElementById('voice-candidates').textContent = `${response.candidate_count} retrieved · ${response.filtered_count} after filters`;
      document.getElementById('voice-flow-count').textContent = `${response.returned_count} Results`;
      document.getElementById('voice-count').textContent = `${response.returned_count} Ranked Results`;
      document.getElementById('voice-pipeline-status').textContent = 'Simulated STT → Keyword Search → Ranking';
      const timing = `Latency: ${Number(response.duration_ms).toFixed(2)} ms`;
      document.getElementById('voice-latency').textContent = timing;
      document.getElementById('voice-banner-latency').textContent = timing;
      Catalog.setStatus(status, response.results.length
        ? 'Transcript processed. Products are ranked by matching keywords; no audio confidence is calculated.'
        : 'No matching products. Edit the transcript or broaden your category filter.');
    } catch (error) {
      if (currentRequest !== requestNumber) return;
      resetMetrics('Search failed');
      Catalog.setStatus(status, error.message || 'Unable to search with this transcript.', true);
    } finally {
      if (currentRequest === requestNumber) {
        button.disabled = false;
        results.setAttribute('aria-busy', 'false');
      }
    }
  }

  function preset() {
    input.value = 'find laptop';
    category.value = '';
    inStock.checked = false;
    limit.value = '';
    search();
  }

  button.addEventListener('click', search);
  document.getElementById('voice-preset-btn').addEventListener('click', preset);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); search(); }
  });
  input.addEventListener('input', () => {
    ++requestNumber;
    button.disabled = false;
    results.replaceChildren();
    results.setAttribute('aria-busy', 'false');
    resetMetrics('Ready to search');
    Catalog.setStatus(status, 'Transcript edited. Run Simulate Voice Search or press Enter to refresh.');
  });
  [category, inStock, limit].forEach(control => control.addEventListener('change', search));
  document.getElementById('voice-clear-btn').addEventListener('click', () => {
    ++requestNumber;
    input.value = '';
    results.replaceChildren();
    results.setAttribute('aria-busy', 'false');
    button.disabled = false;
    resetMetrics('Search cleared');
    Catalog.setStatus(status, 'Type an already-transcribed voice query to begin.');
    input.focus();
  });
  const gridButton = document.getElementById('voice-grid-btn');
  const listButton = document.getElementById('voice-list-btn');
  function setView(list) {
    results.classList.toggle('md:grid-cols-2', !list);
    results.classList.toggle('lg:grid-cols-3', !list);
    results.classList.toggle('catalog-list', list);
    gridButton.setAttribute('aria-pressed', String(!list));
    listButton.setAttribute('aria-pressed', String(list));
  }
  gridButton.addEventListener('click', () => setView(false));
  listButton.addEventListener('click', () => setView(true));
  search();
})();
