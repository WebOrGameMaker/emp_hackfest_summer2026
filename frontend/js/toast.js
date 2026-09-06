import { el } from "./format.js";

export function toast(message, kind = "info", duration = 4200) {
  const host = document.getElementById("toasts");
  if (!host) return;
  const extra = kind === "error" ? " toast--error" : kind === "ok" ? " toast--ok" : "";
  const node = el("div", { class: `toast${extra}`, text: message });
  host.append(node);
  const remove = () => {
    node.style.transition = "opacity 200ms, transform 200ms";
    node.style.opacity = "0";
    node.style.transform = "translateY(8px)";
    setTimeout(() => node.remove(), 220);
  };
  const timer = setTimeout(remove, duration);
  node.addEventListener("click", () => {
    clearTimeout(timer);
    remove();
  });
}
