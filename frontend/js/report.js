import { api } from "./api.js";
import { accessWord, clear, distance, el, escapeHtml, iconHtml, locationWord, pct, severityChip } from "./format.js";
import { BASEMAPS } from "./map.js";
import { closeModal, openModal } from "./modal.js";
import { applyTileTheme, getTheme, onThemeChange } from "./theme.js";
import { toast } from "./toast.js";

const MAX_UPLOAD_BYTES = 6 * 1024 * 1024;

export function openReportFlow({ meta, scenarios, onSubmitted }) {
  const draft = {
    mode: null,
    text: "",
    imageB64: null,
    imageName: null,
    scenarioId: null,
    lat: meta.demo_pin[0],
    lon: meta.demo_pin[1],
    reporter: "you",
    analysis: null,
    nearby: [],
    place: "",
  };

  const stepDots = el("div", { class: "steps", "aria-hidden": "true" });
  let pinMap = null;
  let stopPinTheme = null;

  function releasePinMap() {
    stopPinTheme?.();
    stopPinTheme = null;
    pinMap?.remove();
    pinMap = null;
  }

  const host = openModal({
    title: "Report a hazard",
    wide: true,
    body: el("div"),
    headerExtra: stepDots,
    onClose: releasePinMap,
  });

  function setSteps(active) {
    clear(stepDots);
    for (let index = 0; index < 4; index += 1) {
      const state = index < active ? " steps__dot--done" : index === active ? " steps__dot--active" : "";
      stepDots.append(el("span", { class: `steps__dot${state}` }));
    }
  }

  function renderChoice() {
    setSteps(0);
    releasePinMap();
    const body = el("div");
    body.innerHTML = `
      <p class="muted" style="margin-bottom:var(--s5);line-height:1.55">
        A photo, a short description, or both. HazardMap will classify what you send.
      </p>`;
    const photo = el("button", { class: "choice__btn", type: "button" });
    photo.innerHTML = `
      <span class="choice__title">Upload a photo</span>
      <span class="choice__hint">
        We’ll identify the hazard and whether the road or sidewalk is blocked.
      </span>`;
    photo.addEventListener("click", () => {
      draft.mode = "photo";
      renderInput();
    });
    const text = el("button", { class: "choice__btn", type: "button" });
    text.innerHTML = `
      <span class="choice__title">Describe the hazard</span>
      <span class="choice__hint">
        Write what you see, including whether it blocks cars or people walking if you can
      </span>`;
    text.addEventListener("click", () => {
      draft.mode = "text";
      renderInput();
    });
    const choice = el("div", { class: "choice" });
    choice.append(photo, text);
    body.append(choice);
    body.append(el("p", {
      class: "dim",
      style: "margin-top:var(--s5);font-size:11.5px;line-height:1.5;text-align:center",
      text: "Never report an in-progress emergency here. Call 911 instead. HazardMap is an awareness tool.",
    }));
    host.setBody(body);
    host.setFooter(null);
  }

  function renderInput() {
    setSteps(1);
    const body = el("div", { style: "display:flex;flex-direction:column;gap:var(--s5)" });
    if (draft.mode === "photo") {
      body.append(photoSection());
      body.append(section(
        "Add a description (optional)",
        "A photo and a note together make the reading more reliable.",
        textArea(false),
      ));
    } else {
      body.append(section(
        "What do you see?",
        "Write what you see, including whether it blocks cars or people walking if you can",
        textArea(true),
      ));
    }
    body.append(section(
      "Where is it?",
      "Drag the pin to the exact spot so nearby reports can be matched.",
      pinPicker(),
    ));
    const footer = el("div", { class: "modal__foot" });
    const back = el("button", { class: "btn", type: "button", text: "Back", onClick: renderChoice });
    const next = el("button", {
      class: "btn btn--primary",
      type: "button",
      text: "Review report",
      onClick: () => void runAnalysis(next, back),
    });
    footer.append(back, el("span", { class: "spacer" }), next);
    function syncNext() {
      const hasInput = Boolean(draft.text.trim() || draft.imageB64);
      next.disabled = !hasInput;
      next.title = hasInput ? "" : "Add a photo or a description first";
    }
    body.addEventListener("input", syncNext);
    body.addEventListener("change", syncNext);
    body.addEventListener("hazardmap:input", syncNext);
    host.setBody(body);
    host.setFooter(footer);
    syncNext();
  }

  function section(title, hint, content) {
    const wrap = el("div");
    wrap.append(el("div", { class: "eyebrow", style: "margin-bottom:5px", text: title }));
    if (hint) {
      wrap.append(el("p", {
        class: "dim",
        style: "font-size:11.5px;line-height:1.5;margin-bottom:var(--s3)",
        text: hint,
      }));
    }
    wrap.append(content);
    return wrap;
  }

  function textArea(autofocus) {
    const area = el("textarea", {
      class: "textarea",
      placeholder: "e.g. A large tree has come down across both lanes and cars can't get through.",
      "aria-label": "Describe the hazard",
    });
    if (autofocus) area.setAttribute("data-autofocus", "true");
    area.value = draft.text;
    area.addEventListener("input", () => { draft.text = area.value; });
    return area;
  }

  function photoSection() {
    const wrap = el("div");
    if (draft.imageB64) {
      wrap.append(el("div", { class: "eyebrow", style: "margin-bottom:var(--s3)", text: "Your photo" }));
      const preview = el("div", { class: "preview" });
      preview.innerHTML = `<img src="${escapeHtml(draft.imageB64)}" alt="Selected hazard photo" />`;
      preview.append(el("button", {
        class: "preview__clear",
        type: "button",
        html: "&times;",
        "aria-label": "Remove photo and choose another",
        onClick: () => {
          draft.imageB64 = null;
          draft.imageName = null;
          draft.scenarioId = null;
          renderInput();
        },
      }));
      wrap.append(preview);
      return wrap;
    }
    wrap.append(el("div", { class: "eyebrow", style: "margin-bottom:var(--s3)", text: "Choose a demo scene" }));
    const grid = el("div", { class: "scenes" });
    for (const scenario of scenarios) {
      const button = el("button", {
        class: "scene",
        type: "button",
        "aria-pressed": String(draft.scenarioId === scenario.id),
        "aria-label": `Use demo scene: ${scenario.label}`,
      });
      button.innerHTML = `
        <img src="${escapeHtml(scenario.image)}" alt="" />
        <span class="scene__cap">
          <span aria-hidden="true">${iconHtml(scenario.icon)}</span>
          ${escapeHtml(scenario.label)}
        </span>`;
      button.addEventListener("click", async () => {
        await selectScenario(scenario);
        renderInput();
      });
      grid.append(button);
    }
    wrap.append(grid, uploadZone());
    return wrap;
  }

  function uploadZone() {
    const input = el("input", { type: "file", accept: "image/*", style: "display:none", "aria-hidden": "true" });
    const zone = el("button", { class: "dropzone", type: "button", style: "margin-top:var(--s3);width:100%" });
    zone.innerHTML = `
      <span style="font-size:20px" aria-hidden="true">\u2191</span>
      <span style="font-size:12.5px;font-weight:600">Or upload your own photo</span>
      <span class="dim" style="font-size:11px">PNG or JPEG, up to 6 MB</span>`;
    zone.addEventListener("click", () => input.click());
    ["dragover", "dragenter"].forEach((type) =>
      zone.addEventListener(type, (event) => {
        event.preventDefault();
        zone.classList.add("dropzone--over");
      })
    );
    ["dragleave", "drop"].forEach((type) =>
      zone.addEventListener(type, () => zone.classList.remove("dropzone--over"))
    );
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      const file = event.dataTransfer?.files?.[0];
      if (file) void loadFile(file);
    });
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      if (file) void loadFile(file);
    });
    const wrap = el("div");
    wrap.append(zone, input);
    return wrap;
  }

  async function loadFile(file) {
    if (!file.type.startsWith("image/")) {
      toast("That file is not an image.", "error");
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      toast("That image is larger than 6 MB. Pick a smaller one.", "error");
      return;
    }
    try {
      draft.imageB64 = await readAsDataUrl(file);
      draft.imageName = file.name;
      draft.scenarioId = null;
      renderInput();
    } catch {
      toast("Could not read that image.", "error");
    }
  }

  async function selectScenario(scenario) {
    try {
      const response = await fetch(scenario.image);
      const blob = await response.blob();
      draft.imageB64 = await readAsDataUrl(blob);
      draft.imageName = `demo:${scenario.id}`;
      draft.scenarioId = scenario.id;
    } catch {
      toast("Could not load that demo scene.", "error");
    }
  }

  function pinPicker() {
    const holder = el("div", { class: "pinpick" });
    requestAnimationFrame(() => {
      releasePinMap();
      pinMap = L.map(holder, {
        center: [draft.lat, draft.lon],
        zoom: 16,
        zoomControl: false,
        attributionControl: false,
      });
      const tiles = L.tileLayer(BASEMAPS[0].url, { maxZoom: 19 }).addTo(pinMap);
      applyTileTheme(tiles, getTheme());
      stopPinTheme = onThemeChange((theme) => applyTileTheme(tiles, theme));
      const marker = L.marker([draft.lat, draft.lon], {
        draggable: true,
        keyboard: true,
        alt: "Hazard location, draggable",
      }).addTo(pinMap);
      const readout = el("div", {
        class: "dim",
        style: "font-size:10.5px;margin-top:6px;font-variant-numeric:tabular-nums",
        text: `${draft.lat.toFixed(5)}, ${draft.lon.toFixed(5)}`,
      });
      holder.after(readout);
      function update(latlng) {
        draft.lat = latlng.lat;
        draft.lon = latlng.lng;
        readout.textContent = `${draft.lat.toFixed(5)}, ${draft.lon.toFixed(5)}`;
      }
      marker.on("dragend", () => update(marker.getLatLng()));
      pinMap.on("click", (event) => {
        marker.setLatLng(event.latlng);
        update(event.latlng);
      });
      pinMap.invalidateSize();
    });
    return holder;
  }

  async function runAnalysis(next, back) {
    setSteps(2);
    if (next) {
      next.disabled = true;
      clear(next).append(el("span", { class: "spinner", "aria-hidden": "true" }), "Reviewing");
    }
    if (back) back.disabled = true;
    try {
      const result = await api.analyze({
        lat: draft.lat,
        lon: draft.lon,
        text: draft.text || null,
        image_b64: draft.imageB64,
        image_name: draft.imageName,
      });
      releasePinMap();
      draft.analysis = result.analysis;
      draft.nearby = result.nearby || [];
      draft.place = result.place || "";
      renderResult(result.ai);
    } catch (error) {
      releasePinMap();
      renderError(error);
    }
  }

  function renderError(error) {
    const body = el("div", { class: "empty" });
    body.innerHTML = `
      <span class="empty__glyph" aria-hidden="true">!</span>
      <span class="empty__title">Could not review this report</span>
      <span class="empty__hint">${escapeHtml(error?.message || "Something went wrong.")}</span>`;
    host.setBody(body);
    const footer = el("div", { class: "modal__foot" });
    footer.append(
      el("button", { class: "btn", type: "button", text: "Back", onClick: renderInput }),
      el("span", { class: "spacer" }),
      el("button", { class: "btn btn--primary", type: "button", text: "Try again", onClick: runAnalysis }),
    );
    host.setFooter(footer);
  }

  function renderResult(aiStatus) {
    setSteps(3);
    const analysis = draft.analysis;
    const merging = draft.nearby.filter((match) => match.would_merge);
    const nearMisses = draft.nearby.filter((match) => !match.would_merge);
    const body = el("div", { class: "result" });
    body.append(el("div", { class: "eyebrow", text: "We identified" }));
    const hero = el("div", { class: "result__hero" });
    hero.innerHTML = `
      <div class="result__glyph" aria-hidden="true">${iconHtml(categoryIcon(analysis.category))}</div>
      <div style="flex:1;min-width:0">
        <div class="result__label">${escapeHtml(categoryLabel(analysis.category))}</div>
        <div class="detail__row" style="margin-top:7px">
          ${severityChip(analysis.severity)}
          <span class="badge">${escapeHtml(locationWord(analysis.location_type))}</span>
        </div>
      </div>
      <div style="text-align:right;flex:none">
        <div class="tnum" style="font-size:24px;font-weight:750;color:var(--accent);line-height:1">${pct(analysis.confidence)}</div>
        <div class="eyebrow" style="margin-top:2px">Classification confidence</div>
      </div>`;
    body.append(hero);
    const kv = el("div", { class: "kv" });
    kv.innerHTML = `
      <div class="kv__row">
        <span class="kv__k">Obstruction</span>
        <span class="kv__v">${analysis.obstruction ? "Yes" : "No"}</span>
      </div>
      <div class="kv__row">
        <span class="kv__k">Vehicle access</span>
        <span class="kv__v kv__v--${analysis.vehicle_access}">${accessWord(analysis.vehicle_access)}</span>
      </div>
      <div class="kv__row">
        <span class="kv__k">Pedestrian access</span>
        <span class="kv__v kv__v--${analysis.pedestrian_access}">${accessWord(analysis.pedestrian_access)}</span>
      </div>
      <div class="kv__row">
        <span class="kv__k">Location</span>
        <span class="kv__v">${escapeHtml(draft.place || "Unknown")}</span>
      </div>`;
    body.append(kv);
    body.append(el("div", {
      class: "detail__summary",
      html: `${escapeHtml(analysis.summary)}<cite>Summary</cite>`,
    }));
    if (analysis.evidence?.length) {
      const block = el("div", { class: "block" });
      block.append(el("div", { class: "eyebrow", text: "What the model picked up on" }));
      const groups = new Map();
      for (const evidence of analysis.evidence.slice(0, 6)) {
        if (!groups.has(evidence.detail)) groups.set(evidence.detail, []);
        groups.get(evidence.detail).push(evidence.cue);
      }
      const items = el("div", { class: "contrib" });
      for (const [detail, cues] of groups) {
        const item = el("div", { class: "contrib__item", style: "grid-template-columns:1fr" });
        item.innerHTML = `
          <div>
            <div class="cuelist">${cues.map((cue) => `<span class="cue">${escapeHtml(cue)}</span>`).join("")}</div>
            <div class="contrib__detail">${escapeHtml(detail)}</div>
          </div>`;
        items.append(item);
      }
      block.append(items);
      body.append(block);
    }
    const nearbyBlock = el("div", { class: "block" });
    nearbyBlock.append(
      el("div", { class: "block__head" }, [
        el("span", { class: "eyebrow", text: "Nearby reports" }),
        el("span", {
          class: "eyebrow",
          text: merging.length ? `${merging.length} likely match` : "no match in range",
        }),
      ])
    );
    if (!draft.nearby.length) {
      nearbyBlock.append(el("p", {
        class: "dim",
        style: "font-size:12px;line-height:1.5",
        text: "No other reports of this type nearby. This will start a new hazard.",
      }));
    } else {
      const list = el("div", { class: "nearby" });
      for (const match of [...merging, ...nearMisses].slice(0, 4)) {
        const item = el("div", { class: `nearby__item${match.would_merge ? " nearby__item--merge" : ""}` });
        item.innerHTML = `
          <span class="nearby__glyph" aria-hidden="true">${iconHtml(match.icon)}</span>
          <span style="min-width:0">
            <span style="font-size:12.5px;font-weight:600">
              ${match.report_count} report${match.report_count === 1 ? "" : "s"} · ${distance(match.distance_m)} away · ${pct(match.confidence)}
            </span>
            <span class="nearby__why">${escapeHtml(match.reason)}</span>
          </span>
          <span class="nearby__tag ${match.would_merge ? "nearby__tag--merge" : "nearby__tag--sep"}">${match.would_merge ? "Will join this hazard" : "New hazard"}</span>`;
        list.append(item);
      }
      nearbyBlock.append(list);
    }
    body.append(nearbyBlock);
    if (aiStatus?.is_demo) {
      body.append(el("div", { class: "note", text: `Demo analyzer: ${aiStatus.note}` }));
    }
    host.setBody(body);
    const footer = el("div", { class: "modal__foot" });
    const back = el("button", { class: "btn", type: "button", text: "Edit report", onClick: renderInput });
    const submit = el("button", {
      class: "btn btn--primary",
      type: "button",
      text: merging.length ? "Submit and add to this hazard" : "Submit report",
    });
    submit.addEventListener("click", () => void submitReport(submit));
    footer.append(back, el("span", { class: "spacer" }), submit);
    host.setFooter(footer);
  }

  async function submitReport(button) {
    button.disabled = true;
    clear(button).append(el("span", { class: "spinner", "aria-hidden": "true" }), "Submitting");
    try {
      const result = await api.submit({
        lat: draft.lat,
        lon: draft.lon,
        text: draft.text || null,
        image_b64: draft.imageB64,
        image_name: draft.imageName,
        reporter: draft.reporter,
        analysis: draft.analysis,
      });
      closeModal();
      onSubmitted?.(result);
    } catch (error) {
      button.disabled = false;
      clear(button).append(document.createTextNode("Submit report"));
      toast(error.message || "Could not submit the report.", "error");
    }
  }

  function categoryMeta(key) {
    return meta.categories.find((category) => category.key === key);
  }

  function categoryLabel(key) {
    return categoryMeta(key)?.label || "Other Hazard";
  }

  function categoryIcon(key) {
    return categoryMeta(key)?.icon || "/assets/icons/other.png";
  }

  renderChoice();
}

function readAsDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}
