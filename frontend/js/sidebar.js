import { clear, el, escapeHtml, iconHtml, pct, severityBars, timeAgo } from "./format.js";
import { filtersActive, LIST_PREVIEW, setFilters, setListView, state } from "./state.js";

export class Sidebar {
  constructor({ onSelect }) {
    this.onSelect = onSelect;
    this.categoryList = document.getElementById("category-list");
    this.hazardList = document.getElementById("hazard-list");
    this.hazardCount = document.getElementById("hazard-list-count");
    this.hazardMore = document.getElementById("hazard-list-more");
    this.#wireFilters();
    this.#wireListView();
  }

  #wireFilters() {
    const severity = document.getElementById("filter-severity");
    severity?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-severity]");
      if (!button) return;
      const value = button.dataset.severity;
      setFilters({ severity: value === "all" ? [] : [value] });
      this.#syncSegmented(severity, "severity", value);
    });
    const time = document.getElementById("filter-time");
    time?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-hours]");
      if (!button) return;
      const value = button.dataset.hours;
      setFilters({ hours: value === "all" ? null : Number(value) });
      this.#syncSegmented(time, "hours", value);
    });
    const reports = document.getElementById("filter-reports");
    reports?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-min]");
      if (!button) return;
      setFilters({ minReports: Number(button.dataset.min) });
      this.#syncSegmented(reports, "min", button.dataset.min);
    });
    const confidence = document.getElementById("filter-confidence");
    const confidenceValue = document.getElementById("filter-confidence-value");
    confidence?.addEventListener("input", () => {
      if (confidenceValue) confidenceValue.textContent = `${confidence.value}%`;
      setFilters({ minConfidence: Number(confidence.value) / 100 });
    });
    document.getElementById("btn-clear-filters")?.addEventListener("click", () => this.resetFilters());
  }

  #wireListView() {
    document.getElementById("hazard-sort")?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-sort]");
      if (!button) return;
      setListView({ sort: button.dataset.sort });
    });
  }

  #syncSegmented(group, key, value) {
    if (!group) return;
    group.querySelectorAll("button").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset[key] === value));
    });
  }

  resetFilters() {
    setFilters({ category: [], severity: [], hours: null, minReports: 1, minConfidence: 0 });
    this.#syncSegmented(document.getElementById("filter-severity"), "severity", "all");
    this.#syncSegmented(document.getElementById("filter-time"), "hours", "all");
    this.#syncSegmented(document.getElementById("filter-reports"), "min", "1");
    const confidence = document.getElementById("filter-confidence");
    if (confidence) confidence.value = "0";
    const confidenceValue = document.getElementById("filter-confidence-value");
    if (confidenceValue) confidenceValue.textContent = "0%";
  }

  renderCategories(categories) {
    if (!this.categoryList) return;
    const active = new Set(state.filters.category);
    clear(this.categoryList);
    for (const category of categories || []) {
      const button = el("button", {
        class: "cat",
        type: "button",
        "aria-pressed": String(active.has(category.key)),
        "data-empty": String(category.hazard_count === 0),
        title: `${category.blurb} Groups reports within ${category.cluster_radius_m}m over ${category.cluster_window_hours}h.`,
        onClick: () => this.#toggleCategory(category.key),
      });
      button.innerHTML = `
        <span class="cat__glyph" aria-hidden="true">${iconHtml(category.icon)}</span>
        <span class="cat__label">${escapeHtml(category.label)}</span>
        <span class="cat__n tnum">${category.hazard_count}</span>
        <span class="cat__reports tnum">${category.report_count} rep</span>`;
      button.setAttribute(
        "aria-label",
        `${category.label}: ${category.hazard_count} hazards from ${category.report_count} reports`
      );
      this.categoryList.append(button);
    }
  }

  #toggleCategory(key) {
    const current = new Set(state.filters.category);
    if (current.has(key)) current.delete(key);
    else current.add(key);
    setFilters({ category: [...current] });
  }

  renderHazards(hazards) {
    if (!this.hazardList) return;
    clear(this.hazardList);
    clear(this.hazardMore);
    this.#syncListView();
    if (state.loading) {
      if (this.hazardCount) this.hazardCount.textContent = "";
      for (let index = 0; index < 4; index += 1) {
        this.hazardList.append(el("div", { class: "skeleton", style: "height:62px" }));
      }
      return;
    }
    if (!hazards.length) {
      if (this.hazardCount) this.hazardCount.textContent = "";
      this.hazardList.append(this.#emptyState());
      return;
    }
    const ordered = sortHazards(hazards, state.listView.sort);
    const collapsed = !state.listView.expanded && ordered.length > LIST_PREVIEW;
    const visible = collapsed ? ordered.slice(0, LIST_PREVIEW) : ordered;
    if (this.hazardCount) {
      this.hazardCount.textContent = collapsed
        ? `(${visible.length} of ${ordered.length})`
        : `(${ordered.length})`;
    }
    for (const hazard of visible) this.hazardList.append(this.#hazardRow(hazard));
    if (this.hazardMore) {
      clear(this.hazardMore);
      if (ordered.length > LIST_PREVIEW) {
        this.hazardMore.append(this.#listToggle(ordered.length, collapsed));
      }
    }
  }

  #syncListView() {
    this.#syncSegmented(document.getElementById("hazard-sort"), "sort", state.listView.sort);
  }

  #hazardRow(hazard) {
    const reportWord = hazard.report_count === 1 ? "report" : "reports";
    const row = el("button", {
      class: "hzrow",
      type: "button",
      role: "listitem",
      "aria-current": String(hazard.id === state.selectedId),
      onClick: () => this.onSelect?.(hazard.id),
    });
    row.innerHTML = `
      <span class="hzrow__glyph" aria-hidden="true">${iconHtml(hazard.icon)}</span>
      <span class="hzrow__main">
        <span class="hzrow__title">
          ${escapeHtml(hazard.label)}
          ${severityBars(hazard.severity)}
        </span>
        <span class="hzrow__meta">${escapeHtml(hazard.place)} · ${timeAgo(hazard.last_reported_at)}</span>
      </span>
      <span class="hzrow__conf">
        <span class="hzrow__pct tnum">${pct(hazard.confidence)}</span>
        <span class="hzrow__n tnum">${hazard.report_count} ${reportWord}</span>
      </span>`;
    row.setAttribute(
      "aria-label",
      `${hazard.label}, ${hazard.severity} severity, ${hazard.report_count} ${reportWord}, ${pct(hazard.confidence)} confidence, ${hazard.place}, last reported ${timeAgo(hazard.last_reported_at)}`
    );
    return row;
  }

  #listToggle(total, collapsed) {
    return el("button", {
      class: "btn btn--sm btn--block hzlist__more",
      type: "button",
      text: collapsed ? `Show all ${total} hazards` : `Show ${LIST_PREVIEW} hazards`,
      "aria-expanded": String(!collapsed),
      onClick: () => setListView({ expanded: collapsed }),
    });
  }

  #emptyState() {
    const filtered = filtersActive();
    const node = el("div", { class: "empty" });
    node.innerHTML = `
      <span class="empty__glyph" aria-hidden="true">${filtered ? "\u2298" : "\u2713"}</span>
      <span class="empty__title">${filtered ? "No hazards match these filters" : "No hazards reported"}</span>
      <span class="empty__hint">${
        filtered
          ? "Try a wider time range or a lower minimum confidence."
          : "Nothing is currently reported in this area. Submit a report to start."
      }</span>`;
    if (filtered) {
      node.append(el("button", {
        class: "btn btn--sm",
        type: "button",
        text: "Reset filters",
        onClick: () => this.resetFilters(),
      }));
    }
    return node;
  }
}

function recency(hazard) {
  return new Date(hazard.last_reported_at) - 0;
}

function sortHazards(hazards, sort) {
  const ordered = [...hazards];
  if (sort === "hazard") {
    ordered.sort((a, b) =>
      a.label.localeCompare(b.label) ||
      a.category.localeCompare(b.category) ||
      b.report_count - a.report_count ||
      recency(b) - recency(a)
    );
    return ordered;
  }
  ordered.sort((a, b) => b.report_count - a.report_count || recency(b) - recency(a));
  return ordered;
}
