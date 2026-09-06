import { SEVERITY_BARS, escapeHtml, pct } from "./format.js";
import { applyTileTheme } from "./theme.js";

export const BASEMAPS = [
  {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
  {
    url: "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
];

export class HazardMap {
  constructor(elementId, { center, zoom, onSelect }) {
    this.onSelect = onSelect;
    this.markers = new Map();
    this.selectedId = null;
    this.theme = "light";
    this.map = L.map(elementId, {
      center,
      zoom,
      // default top-left zoom would collide with the stats pill
      zoomControl: false,
      attributionControl: true,
      keyboard: true,
    });
    L.control.zoom({ position: "bottomright" }).addTo(this.map);
    this.#addBasemap(0);
  }

  #addBasemap(index) {
    const source = BASEMAPS[index];
    if (!source) {
      this.#useFallbackGrid();
      return;
    }
    let failures = 0;
    const layer = L.tileLayer(source.url, { attribution: source.attribution, maxZoom: 19 });
    layer.on("tileerror", () => {
      failures += 1;
      if (failures === 6) {
        this.map.removeLayer(layer);
        this.#addBasemap(index + 1);
      }
    });
    layer.addTo(this.map);
    this.baseLayer = layer;
    applyTileTheme(layer, this.theme);
  }

  setTheme(theme) {
    this.theme = theme === "dark" ? "dark" : "light";
    applyTileTheme(this.baseLayer, this.theme);
  }

  #useFallbackGrid() {
    const stage = document.getElementById("map");
    if (stage && !stage.querySelector(".map-fallback")) {
      stage.append(Object.assign(document.createElement("div"), { className: "map-fallback" }));
    }
  }

  #icon(hazard, { isNew = false } = {}) {
    const bars = SEVERITY_BARS[hazard.severity] || 1;
    const barHtml = [1, 2, 3].map((index) => `<i class="${index <= bars ? "on" : ""}"></i>`).join("");
    const corroborated = hazard.report_count > 1;
    return L.divIcon({
      className: "hz-marker",
      iconSize: [40, 40],
      iconAnchor: [20, 20],
      html: `
        <div class="hz-pin hz-pin--${hazard.severity}${
        corroborated ? " hz-pin--corroborated" : ""
      }${isNew ? " hz-pin--new" : ""}" data-hazard="${escapeHtml(hazard.id)}">
          <span class="hz-pin__ring"></span>
          <span class="hz-pin__glyph">${hazard.icon}</span>
          <span class="hz-pin__count tnum">${hazard.report_count}</span>
          <span class="hz-pin__bars">${barHtml}</span>
        </div>`,
    });
  }

  #label(hazard) {
    return (
      `${hazard.label}, ${hazard.severity} severity, ` +
      `${hazard.report_count} report${hazard.report_count === 1 ? "" : "s"}, ` +
      `${pct(hazard.confidence)} confidence, ${hazard.place}`
    );
  }

  render(hazards, { newHazardId = null } = {}) {
    const seen = new Set();
    for (const hazard of hazards) {
      seen.add(hazard.id);
      const existing = this.markers.get(hazard.id);
      const isNew = hazard.id === newHazardId;
      if (existing) {
        existing.setLatLng([hazard.lat, hazard.lon]);
        existing.setIcon(this.#icon(hazard, { isNew: false }));
        existing.options.alt = this.#label(hazard);
        existing.hazard = hazard;
      } else {
        const marker = L.marker([hazard.lat, hazard.lon], {
          icon: this.#icon(hazard, { isNew }),
          keyboard: true,
          alt: this.#label(hazard),
          riseOnHover: true,
          zIndexOffset: hazard.report_count > 1 ? 200 : 0,
        });
        marker.hazard = hazard;
        marker.on("click", () => this.onSelect?.(hazard.id));
        marker.on("keypress", (event) => {
          if (event.originalEvent?.key === "Enter") this.onSelect?.(hazard.id);
        });
        marker.addTo(this.map);
        this.markers.set(hazard.id, marker);
      }
    }
    for (const [id, marker] of this.markers) {
      if (!seen.has(id)) {
        this.map.removeLayer(marker);
        this.markers.delete(id);
      }
    }
    if (this.selectedId) this.#applySelection();
  }

  #applySelection() {
    for (const [id, marker] of this.markers) {
      const pin = marker.getElement()?.querySelector(".hz-pin");
      if (!pin) continue;
      pin.classList.toggle("hz-pin--selected", id === this.selectedId);
    }
  }

  select(hazardId) {
    this.selectedId = hazardId;
    this.#applySelection();
  }

  pulse(hazardId) {
    const marker = this.markers.get(hazardId);
    const pin = marker?.getElement()?.querySelector(".hz-pin");
    if (!pin) return;
    const halo = document.createElement("span");
    halo.className = "hz-halo";
    pin.append(halo);
    setTimeout(() => halo.remove(), 3200);
  }

  bump(hazardId) {
    const marker = this.markers.get(hazardId);
    const pin = marker?.getElement()?.querySelector(".hz-pin");
    if (!pin) return;
    pin.classList.remove("hz-pin--new");
    void pin.offsetWidth;
    pin.classList.add("hz-pin--new");
  }

  flyTo(lat, lon, zoom = 16) {
    this.map.flyTo([lat, lon], zoom, { duration: 0.9 });
  }

  panTo(lat, lon) {
    this.map.panTo([lat, lon], { animate: true, duration: 0.6 });
  }

  invalidate() {
    this.map.invalidateSize();
  }
}
