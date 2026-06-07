(function () {
  function parseMarksData(raw) {
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.error("body-map: could not parse mark data", error);
      return [];
    }
  }

  function imageHasLayout(img) {
    const rect = img.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function whenImageReady(img, callback) {
    if (imageHasLayout(img)) {
      callback();
      return;
    }
    const done = () => {
      if (imageHasLayout(img)) callback();
    };
    img.addEventListener("load", done, { once: true });
    if (typeof img.decode === "function") {
      img.decode().then(done).catch(done);
    }
  }

  function initPinOverlay(container) {
    const svgImg = container.querySelector(".region-svg-img");
    const mapArea = container.querySelector(".region-map-inner");
    const overlay = container.querySelector(".pin-overlay");
    if (!svgImg || !mapArea || !overlay) return;

    const mirrored = container.dataset.mirrored === "true";
    const marks = parseMarksData(container.dataset.marks);
    renderPins(overlay, marks, mirrored);

    const clickable = container.dataset.clickable === "true";
    if (!clickable) {
      overlay.querySelectorAll(".map-pin").forEach((pin) => {
        pin.addEventListener("click", (event) => {
          event.stopPropagation();
          const url = pin.dataset.url;
          if (url) window.location.href = url;
        });
      });
      return;
    }

    const preview = container.querySelector(".placement-preview");
    const inputX = document.getElementById("map_x");
    const inputY = document.getElementById("map_y");
    const submitBtn = document.getElementById("placement-submit");

    function updatePreview(x, y) {
      if (!preview) return;
      preview.style.left = x * 100 + "%";
      preview.style.top = y * 100 + "%";
      preview.hidden = false;
    }

    if (marks.length && marks[0].map_x != null) {
      const displayX = mirrored ? 1 - marks[0].map_x : marks[0].map_x;
      updatePreview(displayX, marks[0].map_y);
    }

    function handlePlacementClick(event) {
      if (event.target.closest(".map-pin")) return;
      const rect = svgImg.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;

      const rawX = (event.clientX - rect.left) / rect.width;
      const rawY = (event.clientY - rect.top) / rect.height;
      if (rawX < 0 || rawX > 1 || rawY < 0 || rawY > 1) return;

      const x = mirrored ? 1 - rawX : rawX;
      if (inputX) inputX.value = x.toFixed(4);
      if (inputY) inputY.value = rawY.toFixed(4);
      updatePreview(mirrored ? rawX : x, rawY);
      if (submitBtn) submitBtn.disabled = false;
    }

    whenImageReady(svgImg, () => {
      container.classList.add("map-ready");
      mapArea.addEventListener("click", handlePlacementClick);
    });

    if (submitBtn) {
      submitBtn.disabled = !(inputX && inputX.value && inputY && inputY.value);
    }
  }

  function renderPins(overlay, marks, mirrored) {
    overlay.innerHTML = "";
    marks.forEach((mark) => {
      if (mark.map_x == null || mark.map_y == null) return;
      const pin = document.createElement("button");
      pin.type = "button";
      pin.className = "map-pin";
      const displayX = mirrored ? 1 - mark.map_x : mark.map_x;
      pin.style.left = displayX * 100 + "%";
      pin.style.top = mark.map_y * 100 + "%";
      pin.title = mark.label;
      pin.textContent = mark.id.replace("BM-", "");
      if (mark.url) pin.dataset.url = mark.url;
      overlay.appendChild(pin);
    });
  }

  document.querySelectorAll(".region-map-container").forEach(initPinOverlay);
})();
