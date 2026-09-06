import {
  accessWord, animateNumber, clear, clockTime, confidenceWord, el, escapeHtml,
  locationWord, pct, severityChip, timeAgo,
} from "./format.js";

const root = () => document.getElementById("detail-root");

let currentId = null;
let lastRenderedConfidence = null;

export function closeCard() {
  clear(root());
  currentId = null;
  lastRenderedConfidence = null;
}

export function openHazardId() {
  return currentId;
}

export function renderCard(hazard, { onClose, animateFrom = null } = {}) {
  const container = root();
  const isSameHazard = currentId === hazard.id;
  const from = animateFrom ?? (isSameHazard ? lastRenderedConfidence : null);
  clear(container);
  currentId = hazard.id;
  lastRenderedConfidence = hazard.confidence;
  const card = el("aside", {
    class: "detail",
    role: "dialog",
    "aria-label": `${hazard.label} hazard detail`,
    tabindex: "-1",
  });
  const reportWord = hazard.report_count === 1 ? "report" : "reports";
  const breakdown = hazard.confidence_breakdown;
  card.innerHTML = `
    <div class="detail__head">
      <div class="detail__glyph" aria-hidden="true">${hazard.icon}</div>
      <div class="detail__titles">
        <div class="detail__title">${escapeHtml(hazard.label)}</div>
        <div class="detail__place">${escapeHtml(hazard.place)}</div>
      </div>
      <button class="detail__close" type="button" aria-label="Close hazard detail">&times;</button>
    </div>

    <div class="detail__scroll">
      <div class="detail__row">
        ${severityChip(hazard.severity)}
        <span class="badge">${escapeHtml(locationWord(hazard.location_type))}</span>
        ${
          hazard.obstruction
            ? '<span class="badge" style="border-color:rgba(239,109,61,.35);color:var(--sev-high)">Obstruction</span>'
            : ""
        }
      </div>

      <div class="block">
        <div class="block__head">
          <span class="eyebrow">Confidence</span>
          <span class="eyebrow">${escapeHtml(confidenceWord(hazard.confidence))}</span>
        </div>
        <div class="detail__row" style="gap:var(--s3)">
          <span class="tnum" id="detail-conf" style="font-size:30px;font-weight:750;letter-spacing:-.03em;line-height:1;color:var(--accent)">${pct(hazard.confidence)}</span>
          <div style="flex:1;min-width:90px">
            <div class="confmeter">
              <div class="confmeter__fill" id="detail-conf-bar" style="width:${(from ?? hazard.confidence) * 100}%"></div>
            </div>
            <div class="dim" style="font-size:10.5px;margin-top:5px">
              from <strong style="color:var(--text-muted)">${hazard.report_count} ${reportWord}</strong>
            </div>
          </div>
        </div>
      </div>

      <div class="detail__summary">
        ${escapeHtml(hazard.summary)}
        <cite>Summary from the strongest report</cite>
      </div>

      <div class="stat2">
        <div class="stat">
          <div class="stat__label">First reported</div>
          <div class="stat__value tnum">${clockTime(hazard.first_reported_at)}</div>
          <div class="stat__sub">${timeAgo(hazard.first_reported_at)}</div>
        </div>
        <div class="stat">
          <div class="stat__label">Last reported</div>
          <div class="stat__value tnum">${clockTime(hazard.last_reported_at)}</div>
          <div class="stat__sub">${timeAgo(hazard.last_reported_at)}</div>
        </div>
      </div>

      <div class="kv">
        <div class="kv__row">
          <span class="kv__k">Vehicle access</span>
          <span class="kv__v kv__v--${hazard.vehicle_access}">${accessWord(hazard.vehicle_access)}</span>
        </div>
        <div class="kv__row">
          <span class="kv__k">Pedestrian access</span>
          <span class="kv__v kv__v--${hazard.pedestrian_access}">${accessWord(hazard.pedestrian_access)}</span>
        </div>
        <div class="kv__row">
          <span class="kv__k">Reports with photos</span>
          <span class="kv__v tnum">${hazard.photo_count} of ${hazard.report_count}</span>
        </div>
        <div class="kv__row">
          <span class="kv__k">Distance between reports</span>
          <span class="kv__v tnum">${hazard.report_count > 1 ? `${hazard.spread_m.toFixed(0)}m` : "single point"}</span>
        </div>
      </div>

      ${breakdown ? confidenceSection(breakdown) : ""}

      <div class="block">
        <div class="block__head">
          <span class="eyebrow">Reports</span>
          <span class="eyebrow tnum">${hazard.report_count}</span>
        </div>
        <div class="timeline">${timeline(hazard)}</div>
      </div>
    </div>`;

  card.querySelector(".detail__close").addEventListener("click", () => {
    closeCard();
    onClose?.();
  });
  card.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeCard();
      onClose?.();
    }
  });
  container.append(card);
  const bar = card.querySelector("#detail-conf-bar");
  requestAnimationFrame(() => {
    bar.style.width = `${hazard.confidence * 100}%`;
  });
  if (from != null && Math.abs(from - hazard.confidence) > 0.001) {
    animateNumber(card.querySelector("#detail-conf"), from, hazard.confidence);
  }
  return card;
}

function confidenceSection(breakdown) {
  const max = Math.max(0.2, ...breakdown.contributions.map((item) => Math.abs(item.logit_delta)));
  const items = breakdown.contributions
    .map((item) => {
      const negative = item.logit_delta < -0.0001;
      const zero = Math.abs(item.logit_delta) <= 0.0001;
      const width = (Math.abs(item.logit_delta) / max) * 100;
      const deltaClass = negative ? "contrib__delta--neg" : zero ? "contrib__delta--zero" : "";
      const delta = zero
        ? "—"
        : `${item.logit_delta > 0 ? "+" : "\u2212"}${Math.abs(item.logit_delta).toFixed(2)}`;
      return `
        <div class="contrib__item">
          <div>
            <div class="contrib__label">${escapeHtml(item.label)}</div>
            <div class="contrib__detail">${escapeHtml(item.detail)}</div>
            <div class="contrib__bar ${negative ? "contrib__bar--neg" : ""}" style="margin-top:6px">
              <span style="width:${zero ? 0 : width}%"></span>
            </div>
          </div>
          <div class="contrib__delta ${deltaClass}">${delta}</div>
        </div>`;
    })
    .join("");
  return `
    <div class="block">
      <div class="block__head">
        <span class="eyebrow">Why this score</span>
      </div>
      <div class="contrib">${items}</div>
      ${breakdown.capped ? `<div class="note">${escapeHtml(breakdown.cap_reason)}</div>` : ""}
    </div>`;
}

function timeline(hazard) {
  const reports = [...hazard.reports].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return reports
    .map((report, index) => {
      const number = reports.length - index;
      const analysis = report.analysis || {};
      return `
        <div class="tl">
          <div class="tl__dot tnum">${number}</div>
          <div class="tl__body">
            <div class="tl__meta">
              <span class="tl__who">@${escapeHtml(report.reporter)}</span>
              <span aria-hidden="true">·</span>
              <span>${timeAgo(report.created_at)}</span>
              ${report.has_photo ? '<span aria-hidden="true">·</span><span>photo</span>' : ""}
            </div>
            <div class="tl__text">
              ${report.text ? `<q>${escapeHtml(report.text)}</q>` : '<span class="dim">Photo report with no description</span>'}
            </div>
            <span class="tl__norm">
              <span aria-hidden="true">${hazard.icon}</span>
              classified as ${escapeHtml(hazard.label)} · ${pct(analysis.confidence || 0)} confidence
            </span>
            ${
              report.photo_url
                ? `<span class="tl__photo"><img src="${escapeHtml(report.photo_url)}" alt="Photo submitted with report ${number}" loading="lazy" /></span>`
                : ""
            }
          </div>
        </div>`;
    })
    .join("");
}
