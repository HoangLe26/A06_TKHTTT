"use strict";

(() => {
  const $ = id => document.getElementById(id);
  const presets = {};
  let previewURL = null, selection = null, lastEmbedding = null;
  let requestVersion = 0, pending = false, ready = false, disposed = false;
  const status = (message, error = false) => Catalog.setStatus($("image-status"), message, error);
  function controls() {
    if (!disposed) $("btn-search-trigger").disabled = pending || !ready || !selection;
  }
  function releasePreview() {
    if (previewURL) URL.revokeObjectURL(previewURL);
    previewURL = null;
  }
  function clearResults(message = "Query changed. Search to refresh results.") {
    requestVersion++;
    lastEmbedding = null;
    $("image-vector-download").disabled = true;
    $("image-vector-preview").value = "";
    const note = document.createElement("p"); note.textContent = message;
    $("image-results").replaceChildren(note);
    $("image-count").textContent = "Awaiting query";
    $("image-result-count").textContent = "No current results";
    $("image-duration").textContent = "Not yet searched";
    $("image-best-match").textContent = "Best Match: —";
    $("image-query-summary").textContent = "Image → CLIP → 512-dimensional vector";
    $("image-detected-object").textContent = "Not yet recognized";
    $("image-filter-summary").textContent = "Optional category, stock and similarity filters";
    controls();
  }
  function presetStyle(key) {
    document.querySelectorAll("[data-preset]").forEach(button => {
      const selected = button.dataset.preset === key;
      button.setAttribute("aria-pressed", String(selected));
      button.classList.toggle("active-preset", selected);
      button.style.borderColor = selected ? "#914724" : "";
    });
  }
  function selectPreset(key) {
    const preset = presets[key];
    if (!preset) return;
    releasePreview(); selection = { product_id: preset.id };
    $("file-input").value = "";
    $("query-preview-img").src = preset.image;
    $("query-preview-img").alt = `Manufacturer product image of ${preset.label}`;
    $("query-file-label").textContent = preset.label;
    $("embedding-state").textContent = "IMAGE READY";
    presetStyle(key); clearResults();
    status(`${preset.label} selected. Search to extract its real image features.`);
  }
  function selectFile(file) {
    if (!file) return;
    // Đổi ảnh luôn xóa kết quả cũ; không dùng lại vector preset trước đó.
    releasePreview(); selection = null; presetStyle(null);
    clearResults("New image selected. Search to recognize it and rank products.");
    $("query-preview-img").removeAttribute("src");
    $("query-file-label").textContent = "No valid image selected";
    $("embedding-state").textContent = "AWAITING IMAGE";
    if (!["image/jpeg", "image/png"].includes(file.type) || !file.size) {
      $("file-input").value = ""; status("Choose a nonempty JPEG or PNG image.", true); return;
    }
    if (file.size > 12 * 1024 * 1024) {
      $("file-input").value = ""; status("Image exceeds the 12 MB limit.", true); return;
    }
    selection = { file }; previewURL = URL.createObjectURL(file);
    $("query-preview-img").src = previewURL;
    $("query-preview-img").alt = `Preview of ${file.name}`;
    $("query-file-label").textContent = file.name;
    $("embedding-state").textContent = "IMAGE READY";
    controls();
    status("Image ready. Search sends it only to your local Python server, not a cloud API.");
  }
  function fileBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",")[1]);
      reader.onerror = () => reject(new Error("Unable to read the selected image."));
      reader.onabort = () => reject(new Error("Image reading was cancelled."));
      reader.readAsDataURL(file);
    });
  }
  async function search() {
    if (pending || disposed) return;
    if (!ready || !selection) {
      status(!ready ? "Local image model is not ready. Check the model status." : "Choose a JPEG/PNG image or a reference product.", true); return;
    }
    const raw = $("image-threshold").value.trim();
    const threshold = raw === "" ? null : Number(raw);
    if (threshold !== null && (!Number.isFinite(threshold) || threshold < -1 || threshold > 1)) {
      clearResults("No query submitted: correct the filters.");
      status("Minimum similarity must be between -1 and 1.", true); return;
    }
    const source = selection;
    clearResults("Extracting image features and ranking products...");
    const version = requestVersion;
    pending = true; controls();
    status("Recognizing the image with local CLIP. The first search may take longer while the model loads...");
    const payload = {
      top_k: $("image-top-k").value ? Number($("image-top-k").value) : null,
      filters: { category: $("image-category").value || null, in_stock: $("image-in-stock").checked },
      min_similarity: threshold
    };
    try {
      if (source.file) payload.image_base64 = await fileBase64(source.file);
      else payload.product_id = source.product_id;
      if (disposed || version !== requestVersion) return;
      const data = await Catalog.searchImage(payload);
      if (disposed || version !== requestVersion) return;
      Catalog.renderProducts($("image-results"), data.results, { scoreLabel: "cosine similarity" });
      lastEmbedding = data.embedding;
      $("image-vector-preview").value = JSON.stringify(data.embedding);
      $("image-vector-download").disabled = false;
      $("image-duration").textContent = `Service duration: ${Number(data.duration_ms).toFixed(2)} ms`;
      $("image-count").textContent = `${data.filtered_count} of ${data.candidate_count} candidates`;
      $("image-result-count").textContent = `${data.returned_count} ranked results`;
      $("image-query-summary").textContent = `${data.vector_dimension} dimensions · CLIP ViT-B/32 · normalized`;
      $("image-detected-object").textContent = `Predicted object: ${data.detected_object}`;
      $("image-filter-summary").textContent = threshold === null ? "No minimum similarity threshold" : `Minimum similarity: ${threshold}`;
      $("image-best-match").textContent = data.results.length ? `Best Match: ${Number(data.results[0].score).toFixed(4)}` : "Best Match: —";
      $("embedding-state").textContent = "512-D VECTOR READY";
      status(data.results.length ? `Returned ${data.returned_count} products ranked by image similarity.` : "No products match the selected filters.");
    } catch (error) {
      if (disposed || version !== requestVersion) return;
      clearResults("Image search failed. No previous results are shown."); status(error.message || "Image search failed.", true);
    } finally { pending = false; controls(); }
  }
  document.querySelectorAll("[data-preset]").forEach(button => button.addEventListener("click", () => {
    selectPreset(button.dataset.preset); search();
  }));
  $("image-search-form").addEventListener("submit", event => { event.preventDefault(); search(); });
  ["image-category", "image-top-k", "image-threshold", "image-in-stock"].forEach(id => $(id).addEventListener("change", () => {
    clearResults(); status("Filters changed. Search to refresh results.");
  }));
  $("file-input").addEventListener("change", event => selectFile(event.target.files[0]));
  $("image-clear").addEventListener("click", () => {
    releasePreview(); selection = null; presetStyle(null); $("file-input").value = "";
    $("query-preview-img").removeAttribute("src"); $("query-file-label").textContent = "No image selected";
    $("embedding-state").textContent = "AWAITING IMAGE"; clearResults("Choose an image to begin.");
    status(pending ? "Selection cleared. The current request will finish, but its result will be discarded." : "Choose an image to begin.");
  });
  $("query-preview-img").addEventListener("error", () => {
    if (previewURL) {
      releasePreview(); selection = null; clearResults("Choose another image.");
      status("The selected image cannot be previewed. Choose another JPEG or PNG.", true);
    }
  });
  const dropzone = $("image-dropzone");
  ["dragenter", "dragover"].forEach(name => dropzone.addEventListener(name, event => {
    event.preventDefault(); dropzone.style.borderColor = "#914724";
  }));
  dropzone.addEventListener("dragleave", () => { dropzone.style.borderColor = ""; });
  dropzone.addEventListener("drop", event => {
    event.preventDefault(); dropzone.style.borderColor = ""; selectFile(event.dataTransfer.files[0]);
  });
  $("image-vector-download").addEventListener("click", () => {
    if (!lastEmbedding) return;
    const blob = new Blob([JSON.stringify({ model: "openai/clip-vit-base-patch32", dimension: 512, embedding: lastEmbedding }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a"); link.href = url; link.download = "image-vector.json";
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  window.addEventListener("beforeunload", () => { disposed = true; requestVersion++; releasePreview(); });
  const headerPreset = document.querySelector("header button");
  if (headerPreset) headerPreset.addEventListener("click", () => {
    $("image-presets").scrollIntoView({ behavior: "smooth", block: "center" }); $("btn-sample-1").focus();
  });
  controls();
  (async () => {
    try {
      const [catalog, health] = await Promise.all([Catalog.getCatalog(), Catalog.getHealth()]);
      if (disposed) return;
      catalog.categories.forEach(category => {
        const option = document.createElement("option"); option.value = category;
        option.textContent = Catalog.categoryLabel(category); $("image-category").append(option);
      });
      document.querySelectorAll("[data-preset]").forEach(button => {
        const key = button.dataset.preset, product = catalog.products.find(item => item.category === key);
        button.disabled = !product;
        if (product) {
          presets[key] = { id: product.id, image: product.image_url, label: product.name };
          button.textContent = `${Catalog.categoryLabel(key)}: ${product.name}`;
        }
      });
      ready = Boolean(health.image_api?.configured);
      Catalog.setStatus($("image-model-status"), ready ? "CLIP ready · CPU · Offline · No API key" : health.image_api?.error || "Local CLIP is not configured.", !ready);
      if (!selection) selectPreset("phone");
      if (!ready) status(health.image_api?.error || "Install the local image model first.", true);
      controls();
    } catch (error) {
      if (disposed) return;
      status(error.message || "Unable to load the local application.", true);
      Catalog.setStatus($("image-model-status"), "Unable to check local model status.", true);
    }
  })();
})();
