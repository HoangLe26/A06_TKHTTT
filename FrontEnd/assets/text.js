/* Connect the editorial text-search screen to the local Python services. */
(() => {
  'use strict';
  const input = document.getElementById('search-input');
  const button = document.getElementById('search-exec-btn');
  const results = document.getElementById('text-results');
  const status = document.getElementById('text-status');
  const limit = document.getElementById('text-top-k');
  const chips = [...document.querySelectorAll('[data-category]')];
  let category = null;
  let requestNumber = 0;

  function updateFilters() {
    chips.forEach(chip => {
      const active = (chip.dataset.category || null) === category;
      chip.setAttribute('aria-pressed', String(active));
      ['bg-primary', 'text-on-primary', 'active-filter', 'font-medium', 'shadow-xs'].forEach(name => chip.classList.toggle(name, active));
      ['bg-surface-container', 'text-on-surface-variant'].forEach(name => chip.classList.toggle(name, !active));
    });
  }

  function resetMetrics(label = 'No search yet') {
    document.getElementById('text-count').textContent = label;
    document.getElementById('text-candidates').textContent = '—';
    document.getElementById('text-query-summary').textContent = '—';
    document.getElementById('text-latency').textContent = 'Timing appears after search';
  }

  async function search() {
    const currentRequest = ++requestNumber;
    const query = input.value;
    const browseCatalog = !query.trim();
    results.replaceChildren();
    results.setAttribute('aria-busy', 'true');
    resetMetrics('Searching…');
    button.disabled = true;
    Catalog.setStatus(status, 'Searching the local catalog…');
    try {
      const response = await Catalog.search({
        type: 'text', query, browse_catalog: browseCatalog,
        top_k: limit.value ? Number(limit.value) : null,
        filters: {category}
      });
      if (currentRequest !== requestNumber) return;
      Catalog.renderProducts(results, response.results, {
        scoreLabel: 'Keyword score', hideScore: browseCatalog,
        onDetails: (product, score) => Catalog.showProduct(product, browseCatalog ? undefined : score)
      });
      document.getElementById('text-query-summary').textContent = browseCatalog
        ? (category ? `Catalog: ${chips.find(chip => chip.dataset.category === category).textContent}` : 'All catalog products')
        : `(${response.query.query})`;
      document.getElementById('text-candidates').textContent = `${response.candidate_count} Products`;
      document.getElementById('text-count').textContent = `${response.returned_count} shown · ${response.filtered_count} matches`;
      document.getElementById('text-latency').textContent = `Search: ${Number(response.duration_ms).toFixed(2)} ms`;
      Catalog.setStatus(status, response.results.length
        ? (browseCatalog ? `${response.filtered_count} products in the selected catalog. No keyword filter applied.`
          : `${response.filtered_count} products match your query and filters. Higher keyword scores appear first.`)
        : 'No products match this query and the selected filters. Try another keyword or All Categories.');
    } catch (error) {
      if (currentRequest !== requestNumber) return;
      resetMetrics('Search failed');
      Catalog.setStatus(status, error.message || 'Unable to search the catalog.', true);
    } finally {
      if (currentRequest === requestNumber) {
        button.disabled = false;
        results.setAttribute('aria-busy', 'false');
      }
    }
  }

  function clear() {
    ++requestNumber;
    input.value = '';
    results.replaceChildren();
    results.setAttribute('aria-busy', 'false');
    button.disabled = false;
    resetMetrics('Search cleared');
    Catalog.setStatus(status, 'Enter a keyword, category, or color to search.');
    input.focus();
  }

  function preset() {
    input.value = 'phone';
    category = null;
    limit.value = '';
    updateFilters();
    search();
  }

  button.addEventListener('click', search);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); search(); }
  });
  input.addEventListener('input', () => {
    ++requestNumber;
    button.disabled = false;
    results.replaceChildren();
    results.setAttribute('aria-busy', 'false');
    resetMetrics('Ready to search');
    Catalog.setStatus(status, 'Query edited. Select Search or press Enter to refresh results.');
  });
  document.getElementById('clear-search-btn').addEventListener('click', clear);
  document.getElementById('text-preset-btn').addEventListener('click', preset);
  document.getElementById('text-voice-link').addEventListener('click', () => { window.location.href = '/voice-search'; });
  document.getElementById('text-image-link').addEventListener('click', () => { window.location.href = '/image-search'; });
  chips.forEach(chip => chip.addEventListener('click', () => {
    category = chip.dataset.category || null;
    input.value = '';
    limit.value = '';
    updateFilters();
    search();
  }));
  limit.addEventListener('change', search);
  updateFilters();
  search();
})();
