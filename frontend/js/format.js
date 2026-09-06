export const SEVERITY_BARS = { low: 1, moderate: 2, high: 3 };

export function pct(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

export function timeAgo(iso) {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const seconds = Math.max(0, (Date.now() - then) / 1000);
  if (seconds < 45) return "just now";
  const minutes = seconds / 60;
  if (minutes < 60) return `${Math.round(minutes)} min ago`;
  const hours = minutes / 60;
  if (hours < 24) {
    const rounded = hours < 10 ? Math.round(hours * 10) / 10 : Math.round(hours);
    return `${rounded}h ago`;
  }
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export function clockTime(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export function distance(meters) {
  if (meters == null) return "—";
  if (meters < 1000) return `${Math.round(meters)}m`;
  return `${(meters / 1000).toFixed(1)}km`;
}

export function accessWord(value) {
  return { open: "Open", limited: "Limited", blocked: "Blocked", unknown: "Unknown" }[value] || "Unknown";
}

export function locationWord(value) {
  return {
    roadway: "Roadway",
    intersection: "Intersection",
    sidewalk: "Sidewalk",
    highway: "Highway",
    park: "Park",
    public_space: "Public space",
    unknown: "Unspecified",
  }[value] || "Unspecified";
}

export function confidenceWord(value) {
  if (value >= 0.9) return "High confidence";
  if (value >= 0.75) return "Supported";
  if (value >= 0.6) return "Likely";
  if (value >= 0.4) return "Single report";
  return "Low confidence";
}

export function severityBars(severity, extraClass = "") {
  const on = SEVERITY_BARS[severity] || 1;
  const bars = [1, 2, 3].map((index) => `<i class="${index <= on ? "on" : ""}"></i>`).join("");
  return `<span class="sevbars ${extraClass}" aria-hidden="true">${bars}</span>`;
}

export function severityChip(severity) {
  const label = severity.charAt(0).toUpperCase() + severity.slice(1);
  return `<span class="sev sev--${severity}">${severityBars(severity)}${label}</span>`;
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(child));
  }
  return node;
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function iconHtml(icon, extraClass = "") {
  const value = String(icon ?? "");
  const cls = extraClass ? `icon-img ${extraClass}` : "icon-img";
  if (value.startsWith("/") || /^https?:\/\//.test(value)) {
    return `<img class="${cls}" src="${escapeHtml(value)}" alt="" />`;
  }
  return escapeHtml(value);
}

export function clear(node) {
  if (!node) return node;
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

export function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function animateNumber(node, from, to, duration = 900) {
  if (prefersReducedMotion() || duration <= 0) {
    node.textContent = pct(to);
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const start = performance.now();
    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      node.textContent = pct(from + (to - from) * eased);
      if (t < 1) requestAnimationFrame(frame);
      else resolve();
    }
    requestAnimationFrame(frame);
  });
}
