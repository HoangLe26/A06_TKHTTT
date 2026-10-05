/* Shared browser adapter; the Python application remains the source of results. */
(() => {
  'use strict';
  const routes = { 'text-search': '/text-search', 'voice-search': '/voice-search',
    'image-search': '/image-search', 'order-search': '/order-search' };

  async function request(path, options = {}) {
    if (location.protocol === 'file:') {
      throw new Error('Open this page through the local application server to connect the catalogue.');
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(path, {
        ...options, signal: controller.signal,
        headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
      });
      let result;
      try { result = await response.json(); }
      catch { throw new Error('The application returned an unreadable response.'); }
      if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);
      return result;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('The request timed out. Please try again.');
      if (error.name === 'TypeError') throw new Error('Unable to connect to the local application. Check that the server is running.');
      throw error;
    } finally { clearTimeout(timeout); }
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function setStatus(target, message, isError = false) {
    if (!target) return;
    if (typeof target === 'string') target = document.getElementById(target);
    if (!target) return;
    target.textContent = message;
    target.setAttribute('role', isError ? 'alert' : 'status');
    target.classList.toggle('catalog-error', isError);
  }

  const priceFormatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
  function formatPrice(value) { return priceFormatter.format(Number(value)); }

  function productImage(product) {
    const image = element('img', 'catalog-product-image');
    image.src = product.image_url || '/product-images/accessory.svg';
    image.alt = `Sample illustration for ${product.name}`;
    image.loading = 'lazy';
    image.addEventListener('error', () => {
      if (!image.src.endsWith('/product-images/accessory.svg')) image.src = '/product-images/accessory.svg';
    });
    return image;
  }

  function showProduct(product, score) {
    let dialog = document.getElementById('catalog-product-dialog');
    if (!dialog) {
      dialog = element('dialog', 'catalog-product-dialog');
      dialog.id = 'catalog-product-dialog';
      document.body.append(dialog);
      dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
    }
    dialog.replaceChildren();
    const heading = element('h2', '', product.name);
    heading.id = 'catalog-product-title';
    dialog.setAttribute('aria-labelledby', heading.id);
    const close = element('button', 'catalog-button', 'Close');
    close.type = 'button';
    close.autofocus = true;
    close.addEventListener('click', () => dialog.close());
    dialog.append(heading, productImage(product));
    const fields = [['ID', product.id], ['Category', product.category], ['Color', product.color],
      ['Sample price (USD)', formatPrice(product.price)], ['Stock', product.stock]];
    if (typeof score === 'number' && Number.isFinite(score)) fields.push(['Ranking score', score.toFixed(4)]);
    if (product.embedding) fields.push(['Artificial embedding', JSON.stringify(product.embedding)]);
    for (const [label, value] of fields) {
      dialog.append(element('p', '', `${label}: ${value}`));
    }
    dialog.append(element('p', 'catalog-muted', 'Local sample product; the illustration is not encoded into an image embedding.'), close);
    dialog.showModal();
  }

  function renderProducts(container, results, options = {}) {
    if (typeof container === 'string') container = document.getElementById(container);
    if (!container) return;
    container.replaceChildren();
    if (!results.length) {
      container.append(element('p', 'catalog-empty', 'No products found. Try another query or adjust the filters.'));
      return;
    }
    for (const result of results) {
      const { product, score, rank } = result;
      const card = element('article', 'catalog-result-card');
      const image = productImage(product);
      const details = element('div', 'catalog-card-details');
      details.append(element('span', 'catalog-rank', `Rank #${rank} · ${options.scoreLabel || 'score'} ${Number(score).toFixed(4)}`));
      details.append(element('h3', '', product.name));
      details.append(element('p', 'catalog-muted', `${product.category} · ${product.color}`));
      details.append(element('p', '', `Stock: ${product.stock}`));
      details.append(element('strong', 'catalog-price', formatPrice(product.price)));
      const button = element('button', 'catalog-button', 'View Details');
      button.type = 'button';
      button.addEventListener('click', () => (options.onDetails || showProduct)(product, score));
      details.append(button);
      card.append(image, details);
      container.append(card);
    }
  }

  async function initializeShell() {
    document.querySelectorAll('a[data-path]').forEach(link => {
      const route = routes[link.dataset.path];
      if (route) link.href = route;
    });
    const main = document.querySelector('main');
    if (!main) return;
    const mobileNav = element('nav', 'catalog-mobile-nav');
    mobileNav.setAttribute('aria-label', 'Search modes');
    for (const [mode, route] of Object.entries(routes)) {
      const link = element('a', '', mode.replace('-', ' '));
      link.href = route;
      if (location.pathname === route) link.setAttribute('aria-current', 'page');
      mobileNav.append(link);
    }
    const connection = element('div', 'catalog-connection', 'Connecting to local catalogue…');
    connection.id = 'catalog-connection';
    connection.setAttribute('role', 'status');
    main.prepend(mobileNav, connection);
    try {
      const health = await request('/api/health');
      setStatus(connection, `Connected · ${health.product_count} sample products · ${health.order_count} sample orders · simulated voice · ${health.vector_dimension}-dim artificial image vectors`);
    } catch (error) { setStatus(connection, error.message, true); }
  }

  window.Catalog = {
    request,
    search: payload => request('/api/search', { method: 'POST', body: payload }),
    getCatalog: () => request('/api/catalog'),
    getOrder: id => request('/api/orders/' + encodeURIComponent(id)),
    getOrders: () => request('/api/orders'),
    formatPrice, setStatus, renderProducts, showProduct,
    imageFor: product => product.image_url || '/product-images/accessory.svg',
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeShell);
  else initializeShell();
})();
