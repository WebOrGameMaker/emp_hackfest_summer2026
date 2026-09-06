import { clear, el } from "./format.js";

const root = () => document.getElementById("modal-root");

let activeClose = null;
let restoreFocusTo = null;

export function isOpen() {
  return Boolean(activeClose);
}

export function closeModal() {
  if (!activeClose) return;
  const close = activeClose;
  activeClose = null;
  close();
  clear(root());
  restoreFocusTo?.focus?.({ preventScroll: true });
  restoreFocusTo = null;
}

export function openModal({
  title, wide = false, body, footer = null, headerExtra = null, onClose = null,
} = {}) {
  closeModal();
  restoreFocusTo = document.activeElement;
  const container = clear(root());
  const overlay = el("div", { class: "overlay" });
  const modal = el("div", {
    class: `modal${wide ? " modal--wide" : ""}`,
    role: "dialog",
    "aria-modal": "true",
    "aria-label": title,
  });
  const closeButton = el("button", {
    class: "detail__close",
    type: "button",
    "aria-label": "Close",
    html: "&times;",
    onClick: closeModal,
  });
  modal.append(
    el("div", { class: "modal__head" }, el("div", { class: "modal__title", text: title }), headerExtra, closeButton),
    el("div", { class: "modal__body" }, body),
  );
  if (footer) modal.append(footer);
  overlay.append(modal);
  overlay.addEventListener("mousedown", (event) => {
    if (event.target === overlay) closeModal();
  });
  const onKeyDown = (event) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      closeModal();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...modal.querySelectorAll(
      'a[href], button:not(:disabled), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    )].filter((node) => node.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
  modal.addEventListener("keydown", onKeyDown);
  container.append(overlay);
  const bodyNode = modal.querySelector(".modal__body");
  const initial =
    modal.querySelector("[data-autofocus]") ||
    modal.querySelector("textarea, input, button.choice__btn, button.btn--primary") ||
    closeButton;
  requestAnimationFrame(() => initial.focus({ preventScroll: true }));
  activeClose = () => onClose?.();
  return {
    modal,
    body: bodyNode,
    setBody(next) { clear(bodyNode).append(next); },
    setFooter(next) {
      modal.querySelector(".modal__foot")?.remove();
      if (next) modal.append(next);
    },
    close: closeModal,
  };
}
