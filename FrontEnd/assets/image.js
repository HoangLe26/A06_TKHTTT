"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const presets = {};
  let previewURL = null;
  let requestVersion = 0;
  let dimension = 3;

  function status(message, error = false) {
    Catalog.setStatus($("image-status"), message, error);
  }

  function clearResults(message = "Query changed. Search to refresh results.") {
    requestVersion += 1;
    $("btn-search-trigger").disabled = false;
    const note = document.createElement("p");
    note.className = "font-body-sm text-on-surface-variant";
    note.textContent = message;
    $("image-results").replaceChildren(note);
    $("image-count").textContent = "Awaiting query";
    $("image-result-count").textContent = "No current results";
    $("image-duration").textContent = "Not yet searched";
    $("image-best-match").textContent = "Best Match: —";
    $("image-query-summary").textContent = "3-dimensional preset / manual input";
    $("image-filter-summary").textContent = "Optional stock, category and similarity filters";
  }

  function releasePreview() {
    if (previewURL) URL.revokeObjectURL(previewURL);
    previewURL = null;
  }

  function selectPreset(key) {
    const preset = presets[key];
    if (!preset) return;
    releasePreview();
    $("file-input").value = "";
    $("query-preview-img").src = preset.image;
    $("query-preview-img").alt = `Manufacturer product image of ${preset.label}`;
    $("query-file-label").textContent = `${preset.label} · real product image`;
    $("image-embedding").value = preset.vector.join(", ");
    $("embedding-state").textContent = "PRESET VECTOR READY";
    document.querySelectorAll("[data-preset]").forEach((button) => {
      const selected = button.dataset.preset === key;
      button.setAttribute("aria-pressed", String(selected));
      button.classList.toggle("active-preset", selected);
      button.style.borderColor = selected ? "#914724" : "";
    });
    clearResults();
    status(`${preset.label} preset selected. Its artificial vector is ready.`);
  }

  function localPreview(file) {
    if (!file) return;
    if (!["image/jpeg", "image/png"].includes(file.type)) {
      $("file-input").value = "";
      status("Choose a JPEG or PNG image for local preview.", true);
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      $("file-input").value = "";
      status("Image exceeds the 12 MB preview limit.", true);
      return;
    }
    releasePreview();
    clearResults("Custom image preview selected. Enter its artificial vector before searching.");
    previewURL = URL.createObjectURL(file);
    $("query-preview-img").src = previewURL;
    $("query-preview-img").alt = `Local preview of ${file.name}`;
    $("query-file-label").textContent = file.name;
    $("image-embedding").value = "";
    $("embedding-state").textContent = "MANUAL VECTOR REQUIRED";
    document.querySelectorAll("[data-preset]").forEach((button) => {
      button.setAttribute("aria-pressed", "false");
      button.classList.remove("active-preset");
      button.style.borderColor = "";
    });
    status("Image is previewed locally only. No feature extraction or upload occurs. Enter three vector values.");
    $("image-embedding").focus();
  }

  function parseVector() {
    const raw = $("image-embedding").value.trim();
    if (!raw) throw new Error("Enter the artificial vector for this image before searching.");
    let values;
    if (raw.startsWith("[")) {
      try { values = JSON.parse(raw); }
      catch { throw new Error("The vector must be a valid JSON array or comma-separated numbers."); }
      if (!Array.isArray(values) || values.some((value) => typeof value !== "number")) {
        throw new Error("The vector must be a flat array of numbers.");
      }
    } else {
      const fields = raw.includes(",") ? raw.split(",") : raw.split(/\s+/);
      if (fields.some((field) => !field.trim())) throw new Error("Vector components cannot be blank.");
      values = fields.map(Number);
    }
    if (values.length !== dimension || values.some((value) => !Number.isFinite(value))) {
      throw new Error(`Enter exactly ${dimension} finite numeric vector values.`);
    }
    return values;
  }

  async function search() {
    let embedding;
    let threshold;
    try {
      embedding = parseVector();
      const raw = $("image-threshold").value.trim();
      threshold = raw === "" ? null : Number(raw);
      if (threshold !== null && (!Number.isFinite(threshold) || threshold < -1 || threshold > 1)) {
        throw new Error("Minimum similarity must be between -1 and 1.");
      }
    } catch (error) {
      clearResults("No query submitted: correct the vector or filters.");
      status(error.message, true);
      return;
    }
    const version = ++requestVersion;
    $("btn-search-trigger").disabled = true;
    status("Comparing the supplied vector with the Python product index…");
    try {
      const data = await Catalog.search({
        type: "image", embedding,
        top_k: $("image-top-k").value ? Number($("image-top-k").value) : null,
        filters: { category: $("image-category").value || null, in_stock: $("image-in-stock").checked },
        min_similarity: threshold
      });
      if (version !== requestVersion) return;
      Catalog.renderProducts($("image-results"), data.results, {
        scoreLabel: "similarity", onDetails: (product, score) => Catalog.showProduct(product, score)
      });
      $("image-duration").textContent = `Service duration: ${Number(data.duration_ms).toFixed(2)} ms`;
      $("image-count").textContent = `${data.filtered_count} of ${data.candidate_count} candidates`;
      $("image-result-count").textContent = `${data.returned_count} ranked results`;
      $("image-query-summary").textContent = `[${embedding.join(", ")}]`;
      $("image-filter-summary").textContent = threshold === null ? "No minimum similarity threshold" : `Minimum similarity: ${threshold}`;
      $("image-best-match").textContent = data.results.length ? `Best Match: ${Number(data.results[0].score).toFixed(4)}` : "Best Match: —";
      $("embedding-state").textContent = "VECTOR VALIDATED";
      status(data.results.length ? `Returned ${data.returned_count} products ranked by cosine similarity.` : "No products match the selected filters.");
    } catch (error) {
      if (version !== requestVersion) return;
      clearResults("The service returned no results for this request.");
      status(error.message || "Image search failed. Check the local server connection.", true);
    } finally {
      if (version === requestVersion) $("btn-search-trigger").disabled = false;
    }
  }

  document.querySelectorAll("[data-preset]").forEach((button) => button.addEventListener("click", () => {
    selectPreset(button.dataset.preset);
    search();
  }));
  $("image-search-form").addEventListener("submit", (event) => { event.preventDefault(); search(); });
  $("image-embedding").addEventListener("input", () => {
    clearResults();
    $("embedding-state").textContent = "MANUAL VECTOR";
    status("Manual vector changed. Search to compare it with the catalogue.");
  });
  ["image-category", "image-top-k", "image-threshold", "image-in-stock"].forEach((id) => $(id).addEventListener("change", () => {
    clearResults();
    status("Filters changed. Search to refresh the results.");
  }));
  $("file-input").addEventListener("change", (event) => localPreview(event.target.files[0]));
  $("query-preview-img").addEventListener("error", () => {
    if (previewURL) {
      releasePreview();
      status("The selected image could not be decoded. Choose another JPEG or PNG.", true);
    }
  });
  const dropzone = $("image-dropzone");
  ["dragenter", "dragover"].forEach((name) => dropzone.addEventListener(name, (event) => {
    event.preventDefault(); dropzone.style.borderColor = "#914724";
  }));
  dropzone.addEventListener("dragleave", () => { dropzone.style.borderColor = ""; });
  dropzone.addEventListener("drop", (event) => {
    event.preventDefault(); dropzone.style.borderColor = "";
    localPreview(event.dataTransfer.files[0]);
  });
  window.addEventListener("beforeunload", releasePreview);
  const headerPreset = document.querySelector("header button");
  if (headerPreset) headerPreset.addEventListener("click", () => {
    $("image-presets").scrollIntoView({ behavior: "smooth", block: "center" });
    $("btn-sample-1").focus();
  });
  (async () => {
    try {
      const data = await Catalog.getCatalog();
      dimension = data.vector_dimension || 3;
      data.categories.forEach((category) => {
        const option = document.createElement("option");
        option.value = category; option.textContent = Catalog.categoryLabel(category);
        $("image-category").append(option);
      });
      document.querySelectorAll("[data-preset]").forEach((button) => {
        const key = button.dataset.preset;
        const product = data.products.find((item) => item.category === key);
        button.disabled = !product;
        if (product) {
          presets[key] = { vector: product.embedding, image: product.image_url, label: product.name };
          button.textContent = `${Catalog.categoryLabel(key)}: ${product.name}`;
        }
      });
      selectPreset('phone');
      await search();
    } catch (error) {
      status(error.message || "Unable to load the catalogue. Start the Python web server.", true);
    }
  })();
})();
