async function request(url, options = {}) {
  let response;
  try {
    response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  } catch (cause) {
    throw new Error("Could not reach the HazardMap server.", { cause });
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail) && body.detail.length) message = body.detail[0].msg || message;
    } catch {
      /* keep the status-code message */
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  meta: () => request("/api/meta"),
  scenarios: () => request("/api/scenarios"),
  hazards(filters = {}) {
    const params = new URLSearchParams();
    (filters.category || []).forEach((value) => params.append("category", value));
    (filters.severity || []).forEach((value) => params.append("severity", value));
    if (filters.hours) params.set("hours", String(filters.hours));
    if (filters.minReports && filters.minReports > 1) params.set("min_reports", String(filters.minReports));
    if (filters.minConfidence) params.set("min_confidence", String(filters.minConfidence));
    const query = params.toString();
    return request(`/api/hazards${query ? `?${query}` : ""}`);
  },
  analyze: (payload) => request("/api/analyze", { method: "POST", body: JSON.stringify(payload) }),
  submit: (payload) => request("/api/reports", { method: "POST", body: JSON.stringify(payload) }),
  resetDemo: () => request("/api/demo/reset", { method: "POST" }),
};

export function connectStream({ onHazard, onReset }) {
  let source;
  function open() {
    source = new EventSource("/api/stream");
    source.addEventListener("hazard", (event) => {
      try {
        onHazard?.(JSON.parse(event.data));
      } catch {
        /* ignore a malformed frame */
      }
    });
    source.addEventListener("reset", () => onReset?.());
    source.addEventListener("error", () => {
      if (source.readyState === EventSource.CLOSED) setTimeout(open, 3000);
    });
  }
  open();
  return () => source?.close();
}
