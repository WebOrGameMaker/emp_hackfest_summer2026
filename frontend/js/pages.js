import { escapeHtml, iconHtml } from "./format.js";

export function renderClusterTable(meta) {
  const table = document.getElementById("cluster-table");
  if (!table || !meta?.categories) return;
  table.innerHTML = meta.categories
    .map(
      (category) =>
        `<div class="kv__row">
           <span class="kv__k">${iconHtml(category.icon, "icon-img--inline")} ${escapeHtml(category.label)}</span>
           <span class="kv__v tnum">${category.cluster_radius_m}m · ${category.cluster_window_hours}h</span>
         </div>`
    )
    .join("");
}

export function renderAiStatus(meta) {
  const box = document.getElementById("ai-status");
  if (!box || !meta?.ai) return;
  const label = meta.ai.is_demo ? "Built-in analyzer" : "Hosted model";
  const note = meta.ai.note || "";
  box.hidden = !note;
  box.innerHTML = `<strong>${escapeHtml(label)}</strong><br>${escapeHtml(note)}`;
}

export function viewFromHash() {
  const hash = (location.hash || "#map").slice(1);
  if (hash === "how-it-works" || hash === "how-ai-works" || hash === "about") return hash;
  return "map";
}

export function showView(name) {
  document.querySelectorAll("[data-view]").forEach((node) => {
    node.hidden = node.dataset.view !== name;
  });
  document.querySelectorAll("[data-nav]").forEach((link) => {
    if (link.dataset.nav === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
}
