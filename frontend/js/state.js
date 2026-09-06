const listeners = new Set();

export const state = {
  meta: null,
  hazards: [],
  selectedId: null,
  loading: true,
  error: null,
  filters: {
    category: [],
    severity: [],
    hours: null,
    minReports: 1,
    minConfidence: 0,
  },
  listView: { sort: "reports", expanded: false },
};

export const LIST_PREVIEW = 5;

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setState(patch) {
  Object.assign(state, patch);
  for (const listener of listeners) listener(state);
}

export function setFilters(patch) {
  state.filters = { ...state.filters, ...patch };
  for (const listener of listeners) listener(state);
}

export function setListView(patch) {
  state.listView = { ...state.listView, ...patch };
  for (const listener of listeners) listener(state);
}

export function totals() {
  const hazards = state.hazards.length;
  const reports = state.hazards.reduce((sum, hazard) => sum + hazard.report_count, 0);
  return { hazards, reports };
}

export function filtersActive() {
  const { category, severity, hours, minReports, minConfidence } = state.filters;
  return Boolean(category.length || severity.length || hours || minReports > 1 || minConfidence > 0);
}
