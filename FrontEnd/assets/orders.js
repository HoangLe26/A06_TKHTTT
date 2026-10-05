"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const recent = new Map();
  let requestVersion = 0;

  function escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[character]);
  }

  function money(value) { return escape(Catalog.formatPrice(value)); }
  function title(value) {
    const text = String(value ?? "");
    return text ? text[0].toUpperCase() + text.slice(1) : "Unknown";
  }

  function status(message, error = false) {
    Catalog.setStatus($("order-status"), message, error);
  }

  function clearDetails(message = "Retrieve an order to see its details.") {
    $("order-ref").textContent = "Ref: —";
    $("order-summary").replaceChildren();
    $("order-details").replaceChildren();
    [$("order-summary"), $("order-details")].forEach((container) => {
      const paragraph = document.createElement("p");
      paragraph.className = "font-body-sm text-on-surface-variant p-space-md";
      paragraph.textContent = message;
      container.append(paragraph);
    });
    $("order-duration").textContent = "Awaiting lookup";
  }

  function updateRecent(order) {
    recent.delete(order.id);
    recent.set(order.id, { id: order.id, customer: order.customer_name, status: order.status });
    if (recent.size > 5) recent.delete(recent.keys().next().value);
    $("order-recent").replaceChildren();
    [...recent.values()].reverse().forEach((entry) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "text-left p-space-sm rounded-xl bg-surface-container-low border border-outline-variant/30 font-label-sm";
      button.textContent = `#${entry.id} · ${entry.customer} · ${title(entry.status)}`;
      button.addEventListener("click", () => {
        $("order-id-input").value = entry.id;
        lookup();
      });
      $("order-recent").append(button);
    });
  }

  function renderOrder(order) {
    const events = Array.isArray(order.tracking_events) ? order.tracking_events : [];
    const completed = events.filter((event) => event.completed).length;
    const progress = events.length ? Math.round(completed / events.length * 100) : 0;
    const units = order.items.reduce((sum, item) => sum + item.quantity, 0);
    $("order-ref").textContent = `Ref: #${order.id}`;
    $("order-summary").innerHTML = `
      <div class="flex items-start justify-between gap-space-sm"><div><span class="font-label-sm text-primary uppercase tracking-wider">Ledger Record</span><h2 class="font-headline-md font-serif text-headline-md">Order #${escape(order.id)}</h2></div><span class="bg-secondary/15 text-secondary border border-secondary/30 px-3 py-1 rounded-full font-label-sm">${escape(title(order.status))}</span></div>
      <div class="grid grid-cols-2 gap-space-sm bg-surface-container-low/70 border border-outline-variant/30 p-4 rounded-xl"><div><span class="font-label-sm uppercase text-on-surface-variant">Customer</span><p class="font-body-md font-medium">${escape(order.customer_name)}</p><span class="font-label-sm text-primary">ID: ${escape(order.customer_id)}</span></div><div><span class="font-label-sm uppercase text-on-surface-variant">Order Date</span><p class="font-body-sm">${escape(order.date)}</p></div></div>
      <div><div class="flex justify-between font-label-sm"><span>Recorded events completed</span><span>${completed}/${events.length}</span></div><div class="w-full h-1.5 bg-surface-container-high rounded-full overflow-hidden mt-space-xs"><div class="h-full bg-primary rounded-full" style="width:${progress}%"></div></div></div>
      <div class="flex justify-between pt-space-sm border-t border-outline-variant/20"><div><span class="font-label-sm uppercase text-on-surface-variant">Order Total</span><p class="font-headline-md font-serif text-primary">${money(order.total)}</p></div><div><span class="font-label-sm uppercase text-on-surface-variant">Manifest</span><p class="font-body-sm">${order.items.length} product lines · ${units} units</p></div></div>
      <button type="button" data-print class="w-full bg-surface-container-low py-2.5 rounded-xl border border-outline-variant/40 font-label-md">Print Order Summary</button>`;

    const tracking = events.length ? events.map((event, index) => `
      <div class="flex flex-col gap-1.5 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/30"><div class="flex justify-between"><span class="font-label-sm uppercase text-on-surface-variant">Step ${String(index + 1).padStart(2, "0")}</span><span class="font-label-sm ${event.completed ? "text-secondary" : "text-on-surface-variant"}">${event.completed ? "Complete" : "Pending"}</span></div><span class="font-headline-sm font-serif">${escape(event.label)}</span><span class="font-label-sm text-on-surface-variant">${escape(event.date || "Pending")}</span><div class="w-full h-1 ${event.completed ? "bg-secondary" : "bg-surface-container"} rounded-full mt-1"></div></div>`).join("") : '<p class="font-body-sm text-on-surface-variant">No tracking events recorded.</p>';

    const items = order.items.map((item, index) => {
      const product = item.product;
      const image = product.image_url && product.image_url.startsWith("/product-images/") ? product.image_url : "/product-images/shoe.svg";
      return `<div class="bg-surface-container-low/60 border border-outline-variant/30 p-4 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div class="flex items-center gap-4"><img class="w-16 h-16 rounded-xl object-contain border border-outline-variant/30 bg-surface-container" src="${escape(image)}" alt="${escape(product.name)}"><div><h3 class="font-headline-sm font-serif text-headline-sm">${escape(product.name)}</h3><p class="font-label-sm text-on-surface-variant">${escape(product.category)} · ${escape(product.color)} · Product #${escape(product.id)}</p><p class="font-label-sm text-on-surface-variant">Unit price: ${money(item.unit_price)}</p></div></div>
      <div class="flex items-center justify-between gap-4"><div class="sm:text-right"><span class="font-label-sm text-on-surface-variant">Qty: ${item.quantity}</span><p class="font-headline-sm font-serif">${money(item.quantity * item.unit_price)}</p></div><button type="button" data-product-index="${index}" class="px-space-sm py-space-xs rounded-lg bg-surface-container border border-outline-variant/30 font-label-sm">View Details</button></div></div>`;
    }).join("");

    $("order-details").innerHTML = `<div class="bg-surface-container-lowest p-6 md:p-8 rounded-2xl border border-outline-variant/40 shadow-sm flex flex-col gap-space-lg">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-space-md pb-5 border-b border-outline-variant/30"><div><span class="font-label-sm text-primary uppercase tracking-wider">Receipt &amp; Dispatch Ledger · Reference #${escape(order.id)}</span><h2 class="font-headline-lg font-serif text-headline-lg">Order #${escape(order.id)} Details</h2></div><div class="flex gap-space-xs"><button type="button" data-print class="bg-surface-container-low px-4 py-2 rounded-xl font-label-md border border-outline-variant/30">Print / Save PDF</button><button id="order-back" type="button" class="bg-surface-container px-4 py-2 rounded-xl font-label-md text-primary">Back to Search</button></div></div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-space-md"><div class="bg-surface-container-low/70 p-5 rounded-2xl border border-outline-variant/30"><span class="font-label-sm uppercase text-on-surface-variant">Customer Details</span><h3 class="font-headline-sm font-serif text-headline-sm">${escape(order.customer_name)}</h3><p class="font-body-sm">Customer ID: ${escape(order.customer_id)}</p><p class="font-label-sm text-on-surface-variant">Local sample customer record</p></div><div class="bg-surface-container-low/70 p-5 rounded-2xl border border-outline-variant/30"><span class="font-label-sm uppercase text-on-surface-variant">Shipping Destination</span><p class="font-body-sm" style="white-space:pre-line">${escape(order.shipping_address)}</p><p class="font-label-sm text-primary">Status: ${escape(title(order.status))}</p></div></div>
      <div class="flex flex-col gap-4 bg-surface-container-low/50 p-6 rounded-2xl border border-outline-variant/30"><span class="font-label-sm uppercase text-on-surface-variant">Fulfillment Progress · Recorded Events</span><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">${tracking}</div></div>
      <div class="flex flex-col gap-3"><div class="flex justify-between"><span class="font-label-sm uppercase text-on-surface-variant">Items in This Order</span><span class="font-label-sm">${order.items.length} product lines · ${units} units</span></div>${items}</div>
      <div class="bg-surface-container-low/70 p-6 rounded-2xl border border-outline-variant/30 flex flex-col gap-3"><div class="flex justify-between"><span>Subtotal</span><span>${money(order.subtotal)}</span></div><div class="flex justify-between"><span>Shipping</span><span>${money(order.shipping)}</span></div><div class="flex justify-between"><span>Tax</span><span>${money(order.tax)}</span></div><div class="flex justify-between pt-space-sm border-t border-outline-variant/30"><div><span class="font-headline-sm font-serif">Total Amount</span><p class="font-label-sm text-on-surface-variant">Payment: ${escape(order.payment_method)}</p></div><span class="font-headline-lg font-serif text-primary">${money(order.total)}</span></div></div>
      <div class="flex flex-wrap gap-space-sm pt-space-sm border-t border-outline-variant/20"><button type="button" disabled title="This prototype supports order lookup only; contact is not implemented." class="px-4 py-2 rounded-xl bg-surface-container-low border border-outline-variant/30 font-label-sm">Contact Support</button><button type="button" disabled title="Purchases and reorder are outside this prototype." class="px-4 py-2 rounded-xl bg-surface-container-low border border-outline-variant/30 font-label-sm">Reorder</button><button type="button" disabled title="Order status is read-only in this sample ledger." class="px-4 py-2 rounded-xl bg-surface-container-low border border-outline-variant/30 font-label-sm">Update Status</button><p class="font-label-sm text-on-surface-variant">Read-only sample ledger. Use your browser's print dialog to print or save a PDF.</p></div>
      </div>`;
    document.querySelectorAll("[data-print]").forEach((button) => button.addEventListener("click", () => window.print()));
    $("order-back").addEventListener("click", () => {
      $("order-search-form").scrollIntoView({ behavior: "smooth", block: "center" });
      $("order-id-input").focus();
    });
    document.querySelectorAll("[data-product-index]").forEach((button) => button.addEventListener("click", () => {
      Catalog.showProduct(order.items[Number(button.dataset.productIndex)].product);
    }));
  }

  async function lookup() {
    const id = $("order-id-input").value.trim().toUpperCase();
    $("order-id-input").value = id;
    const version = ++requestVersion;
    clearDetails("Retrieving the requested order…");
    if (!id) {
      status("Enter an order ID such as O001, O002 or O003.", true);
      $("order-id-input").focus();
      return;
    }
    $("btn-search").disabled = true;
    status(`Looking up order ${id} in the Python repository…`);
    try {
      const data = await Catalog.getOrder(id);
      if (version !== requestVersion) return;
      renderOrder(data.order);
      updateRecent(data.order);
      $("order-duration").textContent = `Lookup duration: ${Number(data.duration_ms).toFixed(2)} ms`;
      status(`Retrieved order #${data.order.id}: ${title(data.order.status)}.`);
    } catch (error) {
      if (version !== requestVersion) return;
      clearDetails("No order record is available for this lookup.");
      status(error.message || `Order ${id} was not found.`, true);
    } finally {
      if (version === requestVersion) $("btn-search").disabled = false;
    }
  }

  $("order-search-form").addEventListener("submit", (event) => { event.preventDefault(); lookup(); });
  $("order-reset").addEventListener("click", () => {
    requestVersion += 1;
    $("order-id-input").value = "";
    $("btn-search").disabled = false;
    clearDetails();
    status("Search reset. Enter an order ID to retrieve its record.");
    $("order-id-input").focus();
  });
  $("order-id-input").addEventListener("input", () => {
    requestVersion += 1;
    $("btn-search").disabled = false;
    clearDetails();
    status("Order ID changed. Retrieve the order to refresh its details.");
  });
  $("focus-order-search").addEventListener("click", () => $("order-id-input").focus());
  document.querySelectorAll("[data-order-id]").forEach((button) => button.addEventListener("click", () => {
    $("order-id-input").value = button.dataset.orderId;
    lookup();
  }));
  lookup();
})();
