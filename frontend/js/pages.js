import { escapeHtml } from "./format.js";

export function renderClusterTable(meta) {
  const table = document.getElementById("cluster-table");
  if (!table || !meta?.categories) return;
  table.innerHTML = meta.categories
    .map(
      (category) =>
        `<div class="kv__row">
           <span class="kv__k">${category.icon} ${escapeHtml(category.label)}</span>
           <span class="kv__v tnum">${category.cluster_radius_m}m · ${category.cluster_window_hours}h</span>
         </div>`
    )
    .join("");
}

export function viewFromHash() {
  const hash = (location.hash || "#map").slice(1);
  if (hash === "how-it-works" || hash === "about") return hash;
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
