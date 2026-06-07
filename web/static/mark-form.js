(function () {
  const select = document.getElementById("body_region");
  if (!select) return;

  const hotspots = document.querySelectorAll(".region-pick-hotspot");

  function syncHotspotSelection() {
    const value = select.value;
    hotspots.forEach((hotspot) => {
      const selected = hotspot.dataset.region === value;
      hotspot.classList.toggle("selected", selected);
      hotspot.setAttribute("aria-pressed", selected ? "true" : "false");
    });
  }

  hotspots.forEach((hotspot) => {
    hotspot.addEventListener("click", () => {
      select.value = hotspot.dataset.region;
      syncHotspotSelection();
    });
  });

  select.addEventListener("change", syncHotspotSelection);
  syncHotspotSelection();
})();
