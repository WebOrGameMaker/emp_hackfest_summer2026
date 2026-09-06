import { api, connectStream } from "./api.js";
import { pct } from "./format.js";
import { closeCard, openHazardId, renderCard } from "./hazardcard.js";
import { HazardMap } from "./map.js";
import { closeModal, isOpen as modalIsOpen } from "./modal.js";
import { renderAiStatus, renderClusterTable, showView, viewFromHash } from "./pages.js";
import { openReportFlow } from "./report.js";
import { Sidebar } from "./sidebar.js";
import { setState, state, subscribe, totals } from "./state.js";
import { applyTileTheme, getTheme, onThemeChange, syncThemeButton, toggleTheme } from "./theme.js";
import { toast } from "./toast.js";

const REQUIRED_IDS = ["category-list", "hazard-list", "hazard-list-count", "pill-hazards", "pill-reports", "map"];

let hazardMap;
let sidebar;
let scenarios = [];
let refreshTimer = null;
let newHazardId = null;

function syncMapTheme(theme) {
  if (typeof hazardMap?.setTheme === "function") {
    hazardMap.setTheme(theme);
    return;
  }
  applyTileTheme(hazardMap?.baseLayer, theme);
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function mapViewVisible() {
  const view = document.getElementById("view-map");
  return Boolean(view) && !view.hidden;
}

function assertShell() {
  const missing = REQUIRED_IDS.filter((id) => !document.getElementById(id));
  if (missing.length) console.error(`HazardMap: missing required elements: ${missing.join(", ")}`);
}

async function refresh({ newId = null } = {}) {
  try {
    const hazards = await api.hazards(state.filters);
    newHazardId = newId;
    setState({ hazards, loading: false, error: null });
  } catch (error) {
    setState({ loading: false, error: error.message });
    toast(error.message, "error");
  }
}

async function refreshMeta() {
  try {
    setState({ meta: await api.meta() });
  } catch {
    /* keep previous counts */
  }
}

function render() {
  const { hazards, meta } = state;
  if (meta) {
    renderClusterTable(meta);
    renderAiStatus(meta);
  }
  if (!mapViewVisible()) return;
  if (meta) sidebar?.renderCategories(meta.categories);
  sidebar?.renderHazards(hazards);
  hazardMap?.render(hazards, { newHazardId });
  hazardMap?.select(state.selectedId);
  newHazardId = null;
  const visible = totals();
  setText("pill-hazards", visible.hazards);
  setText("pill-reports", visible.reports);
  const openId = openHazardId();
  if (openId) {
    const hazard = hazards.find((item) => item.id === openId);
    if (hazard) renderCard(hazard, cardHandlers());
    else closeCard();
  }
}

function cardHandlers() {
  return { onClose: () => setState({ selectedId: null }) };
}

async function select(hazardId) {
  if (!hazardId) {
    closeCard();
    setState({ selectedId: null });
    return;
  }
  setState({ selectedId: hazardId });
  const hazard = state.hazards.find((item) => item.id === hazardId);
  if (!hazard) return;
  hazardMap?.select(hazardId);
  hazardMap?.panTo(hazard.lat, hazard.lon);
  renderCard(hazard, cardHandlers());
}

async function handleSubmitted(result) {
  const { hazard, merged } = result;
  await refresh({ newId: merged ? null : hazard.id });
  await refreshMeta();
  hazardMap?.flyTo(hazard.lat, hazard.lon, 16);
  if (merged) {
    toast(`Added to an existing hazard — now ${hazard.report_count} reports`, "ok");
    hazardMap?.pulse(hazard.id);
  } else {
    toast("New hazard opened from your report", "ok");
    hazardMap?.bump(hazard.id);
  }
  setState({ selectedId: hazard.id });
  renderCard(hazard, cardHandlers());
}

function applyView(name) {
  showView(name);
  if (name !== "map") {
    closeCard();
    closeModal();
    if (state.selectedId != null) setState({ selectedId: null });
    return;
  }
  requestAnimationFrame(() => {
    hazardMap?.invalidate();
    render();
  });
}

async function boot() {
  assertShell();
  const [meta, scenarioList] = await Promise.all([api.meta(), api.scenarios().catch(() => [])]);
  scenarios = scenarioList;
  hazardMap = new HazardMap("map", {
    center: meta.map_center,
    zoom: meta.thresholds.map_zoom || 14,
    onSelect: select,
  });
  syncMapTheme(getTheme());
  const themeButton = document.getElementById("btn-theme");
  syncThemeButton(themeButton);
  themeButton?.addEventListener("click", () => toggleTheme());
  onThemeChange((theme) => {
    syncMapTheme(theme);
    syncThemeButton(themeButton);
  });
  sidebar = new Sidebar({ onSelect: select });
  subscribe(render);
  setState({ meta });
  applyView(viewFromHash());
  await refresh();

  document.getElementById("btn-report")?.addEventListener("click", () => {
    applyView("map");
    if (location.hash && location.hash !== "#map") location.hash = "map";
    openReportFlow({ meta: state.meta, scenarios, onSubmitted: handleSubmitted });
  });

  document.getElementById("btn-reset-demo")?.addEventListener("click", async () => {
    try {
      closeCard();
      closeModal();
      setState({ selectedId: null, loading: true });
      sidebar.resetFilters();
      await api.resetDemo();
      await refreshMeta();
      await refresh();
      toast("Demo data reset", "ok");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  window.addEventListener("hashchange", () => applyView(viewFromHash()));

  let lastFilters = JSON.stringify(state.filters);
  subscribe(() => {
    const current = JSON.stringify(state.filters);
    if (current === lastFilters) return;
    lastFilters = current;
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => refresh(), 160);
  });

  window.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || modalIsOpen() || !openHazardId()) return;
    closeCard();
    setState({ selectedId: null });
  });

  window.addEventListener("resize", () => hazardMap?.invalidate());

  connectStream({
    onHazard: async (payload) => {
      if (payload?.report?.reporter === "you") return;
      await refresh({ newId: payload.merged ? null : payload.hazard.id });
      await refreshMeta();
      if (payload?.hazard) {
        const verb = payload.merged ? "added to" : "started";
        toast(`New report ${verb} ${payload.hazard.label} · ${pct(payload.hazard.confidence)}`, "ok");
        if (payload.merged) hazardMap?.pulse(payload.hazard.id);
      }
    },
    onReset: async () => {
      closeCard();
      setState({ selectedId: null });
      await refreshMeta();
      await refresh();
    },
  });

  setInterval(() => {
    if (state.hazards.length) render();
  }, 60_000);
}

boot().catch((error) => {
  const list = document.getElementById("hazard-list");
  if (list) {
    list.innerHTML = `
    <div class="empty">
      <span class="empty__glyph">!</span>
      <span class="empty__title">Could not start HazardMap</span>
      <span class="empty__hint">${error.message}</span>
    </div>`;
  }
  toast(error.message, "error");
});
