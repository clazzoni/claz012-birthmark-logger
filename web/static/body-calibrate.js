(function () {
  const maps = document.querySelectorAll(".overview-map[data-calibrate]");
  if (!maps.length) return;

  const exportBox = document.getElementById("calibrate-export");
  const copyBtn = document.getElementById("calibrate-copy");

  function parseHotspots(map) {
    return JSON.parse(map.dataset.hotspots || "{}");
  }

  function applyRect(el, rect) {
    el.style.left = rect.left + "%";
    el.style.top = rect.top + "%";
    el.style.width = rect.width + "%";
    el.style.height = rect.height + "%";
  }

  function readRect(el) {
    return {
      left: parseFloat(el.style.left),
      top: parseFloat(el.style.top),
      width: parseFloat(el.style.width),
      height: parseFloat(el.style.height),
    };
  }

  function collectState() {
    const state = { front: {}, back: {} };
    maps.forEach((map) => {
      const side = map.dataset.calibrate;
      map.querySelectorAll(".region-hotspot").forEach((el) => {
        const region = el.dataset.region;
        state[side][region] = readRect(el);
      });
    });
    return state;
  }

  function formatExport(state) {
    const lines = ['FIGURE_REGIONS = {'];
    for (const side of ["front", "back"]) {
      lines.push(`    "${side}": {`);
      const entries = Object.entries(state[side]).sort(([a], [b]) => a.localeCompare(b));
      for (const [region, rect] of entries) {
        const box = CALIBRATE_FIGURE_BBOX[side];
        const x0 = ((rect.left - box.left) / box.width).toFixed(3);
        const y0 = ((rect.top - box.top) / box.height).toFixed(3);
        const x1 = ((rect.left + rect.width - box.left) / box.width).toFixed(3);
        const y1 = ((rect.top + rect.height - box.top) / box.height).toFixed(3);
        lines.push(`        "${region}": (${x0}, ${y0}, ${x1}, ${y1}),`);
      }
      lines.push("    },");
    }
    lines.push("}");
    return lines.join("\n");
  }

  function updateExport() {
    if (!exportBox) return;
    exportBox.value = formatExport(collectState());
  }

  function startDrag(el, map, mode, event) {
    event.preventDefault();
    const mapRect = map.getBoundingClientRect();
    const start = readRect(el);
    const originX = event.clientX;
    const originY = event.clientY;

    function onMove(moveEvent) {
      const dx = ((moveEvent.clientX - originX) / mapRect.width) * 100;
      const dy = ((moveEvent.clientY - originY) / mapRect.height) * 100;
      if (mode === "move") {
        applyRect(el, {
          left: Math.max(0, Math.min(100 - start.width, start.left + dx)),
          top: Math.max(0, Math.min(100 - start.height, start.top + dy)),
          width: start.width,
          height: start.height,
        });
      } else {
        applyRect(el, {
          left: start.left,
          top: start.top,
          width: Math.max(3, start.width + dx),
          height: Math.max(3, start.height + dy),
        });
      }
      updateExport();
    }

    function onUp() {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    }

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }

  maps.forEach((map) => {
    const hotspots = parseHotspots(map);
    Object.entries(hotspots).forEach(([region, rect]) => {
      const el = document.createElement("div");
      el.className = "region-hotspot calibrate-hotspot";
      el.dataset.region = region;
      applyRect(el, rect);
      el.innerHTML =
        '<span class="region-hotspot-label">' +
        region +
        '</span><span class="calibrate-resize" title="Drag to resize"></span>';
      el.addEventListener("pointerdown", (event) => {
        if (event.target.classList.contains("calibrate-resize")) {
          startDrag(el, map, "resize", event);
        } else {
          startDrag(el, map, "move", event);
        }
      });
      map.appendChild(el);
    });
  });

  function flashCopyButton(message) {
    if (!copyBtn) return;
    const original = "Copy coordinates";
    copyBtn.textContent = message;
    setTimeout(() => {
      copyBtn.textContent = original;
    }, 2000);
  }

  if (copyBtn && exportBox) {
    copyBtn.addEventListener("click", async () => {
      updateExport();
      if (!exportBox.value.trim()) {
        flashCopyButton("Nothing to copy");
        return;
      }
      try {
        await navigator.clipboard.writeText(exportBox.value);
        flashCopyButton("Copied!");
      } catch {
        exportBox.focus();
        exportBox.select();
        flashCopyButton("Selected — press Ctrl+C");
      }
    });
  }

  updateExport();
})();
