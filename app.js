/**
 * BBS Automation — frontend logic v2
 *
 * Key changes vs v1:
 *   - Conditional fields per element type (beam/column/slab)
 *   - Element-aware payload builder (sends only relevant fields)
 *   - Renders backend verification banner + warnings
 *   - Calculation-steps toggle
 *   - "Engineering Verified Mode" — blocks export on verification failure
 */

const API_BASE = window.location.origin;

let currentType = "beam";
let lastPayload = null;
let lastResult  = null;

/* ---------------- Element-type toggle ---------------- */

const toggleBtns = document.querySelectorAll(".toggle-btn");
toggleBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    toggleBtns.forEach(b => {
      b.classList.remove("active", "text-white");
      b.classList.add("bg-slate-50", "text-slate-700");
    });
    btn.classList.add("active");
    btn.classList.remove("bg-slate-50", "text-slate-700");
    currentType = btn.dataset.type;
    refreshConditionalFields();
  });
});

/** Show/hide form sections based on currentType. */
function refreshConditionalFields() {
  const beamColDims = document.getElementById("beamColumnDims");
  const slabDims    = document.getElementById("slabDims");
  const stirrups    = document.getElementById("stirrupSection");
  const ties        = document.getElementById("tieSection");
  const dist        = document.getElementById("distSection");
  const mainQty     = document.getElementById("mainQtyField");
  const mainSpc     = document.getElementById("mainSpacingField");
  const depthLabel  = document.querySelector(".dim-depth-label");
  const lengthLabel = document.querySelector(".dim-length-label");

  // Default: hide everything element-specific
  [slabDims, ties, dist, mainSpc].forEach(el => el.classList.add("hidden-section"));
  [beamColDims, stirrups, mainQty].forEach(el => el.classList.remove("hidden-section"));

  if (currentType === "beam") {
    depthLabel.textContent  = "Depth (mm)";
    lengthLabel.textContent = "Length / Span (mm)";
  }
  else if (currentType === "column") {
    depthLabel.textContent  = "Depth (mm)";
    lengthLabel.textContent = "Height (mm)";
    stirrups.classList.add("hidden-section");
    ties.classList.remove("hidden-section");
  }
  else if (currentType === "slab") {
    beamColDims.classList.add("hidden-section");
    slabDims.classList.remove("hidden-section");
    stirrups.classList.add("hidden-section");
    mainQty.classList.add("hidden-section");
    mainSpc.classList.remove("hidden-section");
    dist.classList.remove("hidden-section");
  }
}
refreshConditionalFields();   // run once on load

/* ---------------- Quantity Mode hint ---------------- */
const qtyModeHints = {
  "standard":     "— floor(L/s) + 1",
  "conservative": "— floor(L/s) + 2  (+1 extra for site safety)",
  "exact":        "— ceil(L/s) + 1",
};
const qtyModeSelect = document.getElementById("qtyModeSelect");
const qtyModeHintEl = document.getElementById("qtyModeHint");
if (qtyModeSelect && qtyModeHintEl) {
  qtyModeSelect.addEventListener("change", () => {
    qtyModeHintEl.textContent = qtyModeHints[qtyModeSelect.value] || "";
  });
}

/* ---------------- Helpers ---------------- */

function showError(msgs) {
  const box = document.getElementById("errorBox");
  if (!Array.isArray(msgs)) msgs = [msgs];
  box.innerHTML = "<b>Validation failed:</b><ul class='list-disc ml-5 mt-1'>" +
    msgs.map(m => `<li>${m}</li>`).join("") + "</ul>";
  box.classList.remove("hidden");
}
function clearError() {
  document.getElementById("errorBox").classList.add("hidden");
}
function showWarnings(msgs) {
  const box = document.getElementById("warnBox");
  if (!msgs || !msgs.length) { box.classList.add("hidden"); return; }
  box.innerHTML = "<b>⚠ Warnings:</b><ul class='list-disc ml-5 mt-1'>" +
    msgs.map(m => `<li>${m}</li>`).join("") + "</ul>";
  box.classList.remove("hidden");
}

/** Build only the fields relevant to the current element type. */
function gatherPayload() {
  const v = name => {
    const el = document.querySelector(`[name="${name}"]`);
    if (!el) return null;
    const raw = el.value;
    return raw === "" ? null : Number(raw);
  };
  // String-valued field reader (for qty_mode etc.)
  const s = name => {
    const el = document.querySelector(`[name="${name}"]`);
    return el ? el.value : null;
  };

  const common = {
    element_type: currentType,
    cover:        v("cover"),
    main_bar_dia: v("main_bar_dia"),
    hook_type:    parseInt(v("hook_type")),
    lap_length:   v("lap_length") || 0,
    qty_mode:     s("qty_mode") || "standard",
  };

  if (currentType === "beam") {
    return { ...common,
      width:           v("width"),
      depth:           v("depth"),
      length:          v("length"),
      main_bar_qty:    v("main_bar_qty"),
      stirrup_dia:     v("stirrup_dia"),
      stirrup_spacing: v("stirrup_spacing"),
    };
  }
  if (currentType === "column") {
    // Map "tie" UI fields to backend's stirrup_* parameter names
    return { ...common,
      width:           v("width"),
      depth:           v("depth"),
      length:          v("length"),
      main_bar_qty:    v("main_bar_qty"),
      stirrup_dia:     v("tie_dia"),
      stirrup_spacing: v("tie_spacing"),
    };
  }
  if (currentType === "slab") {
    return { ...common,
      short_span:        v("short_span"),
      long_span:         v("long_span"),
      main_bar_spacing:  v("main_bar_spacing"),
      dist_bar_dia:      v("dist_bar_dia"),
      dist_bar_spacing:  v("dist_bar_spacing"),
    };
  }
}

/** Client-side sanity validation — element-aware mm-range check. */
function clientValidate(p) {
  const errs = [];
  const ranges = {
    width: [50, 5000], depth: [50, 5000], length: [200, 30000],
    short_span: [200, 30000], long_span: [200, 30000],
    cover: [10, 100],
    main_bar_dia: [6, 50], stirrup_dia: [6, 25], dist_bar_dia: [6, 25],
    main_bar_spacing: [50, 500], stirrup_spacing: [50, 500], dist_bar_spacing: [50, 500],
    main_bar_qty: [1, 100],
  };

  for (const [k, val] of Object.entries(p)) {
    if (val === null || val === undefined || val === "") {
      // Skip optional fields
      if (["lap_length"].includes(k)) continue;
      // element_type and hook_type aren't in `ranges`
      if (k === "element_type" || k === "hook_type") continue;
      if (!(k in ranges)) continue;
      errs.push(`Missing or invalid: ${k}`);
      continue;
    }
    if (k in ranges) {
      const [lo, hi] = ranges[k];
      if (val < lo || val > hi) {
        errs.push(`${k} = ${val} is outside the valid mm range [${lo}, ${hi}]. Did you enter cm/m?`);
      }
    }
  }

  // Slab-specific: backend auto-swaps short/long now, so this is just info-level.
  // (We don't push to errs anymore — backend handles it gracefully with a warning.)

  // Beam/column geometry sanity
  if ((p.element_type === "beam" || p.element_type === "column")
      && p.cover != null && p.width != null && p.depth != null) {
    if (2 * p.cover >= Math.min(p.width, p.depth)) {
      errs.push("Cover is too large for the section.");
    }
  }
  return errs;
}

/* ---------------- Render results ---------------- */

function renderVerifyBanner(v) {
  const el = document.getElementById("verifyBanner");
  el.classList.remove("hidden");
  if (v.passed) {
    el.className = "rounded-xl card-shadow p-3 sm:p-4 flex flex-wrap items-center justify-between gap-2 bg-emerald-50 border border-emerald-200";
    el.innerHTML = `
      <div class="flex items-center gap-2 min-w-0">
        <span class="text-xl sm:text-2xl shrink-0">✓</span>
        <div class="min-w-0">
          <div class="font-semibold text-emerald-800 text-sm sm:text-base">Engineering Verified</div>
          <div class="text-[10px] sm:text-xs text-emerald-700 truncate">${v.method}</div>
        </div>
      </div>
      <div class="text-[10px] sm:text-xs text-emerald-700 font-mono whitespace-nowrap">double-check passed</div>
    `;
  } else {
    el.className = "rounded-xl card-shadow p-3 sm:p-4 bg-rose-50 border border-rose-200";
    el.innerHTML = `
      <div class="font-semibold text-rose-800 text-sm sm:text-base">✗ Verification FAILED</div>
      <ul class="text-[11px] sm:text-xs text-rose-700 list-disc ml-5 mt-1 space-y-0.5">
        ${v.issues.map(i => `<li class="break-words">${i}</li>`).join("")}
      </ul>`;
  }
}

function renderSummary(s) {
  const cards = [
    { label: "Element",      value: s.element_type.toUpperCase(), color: "bg-blue-50 text-blue-700" },
    { label: "Total Bars",   value: s.total_bars,                  color: "bg-purple-50 text-purple-700" },
    { label: "Net Weight",   value: s.total_weight_kg_net + " kg", color: "bg-emerald-50 text-emerald-700" },
    { label: "Order Weight", value: s.total_weight_kg_with_wastage + " kg", color: "bg-amber-50 text-amber-700" },
  ];
  const wrap = document.getElementById("summaryCards");
  wrap.classList.remove("hidden");
  wrap.innerHTML = cards.map(c => `
    <div class="bg-white rounded-xl card-shadow p-3 sm:p-4">
      <div class="text-[10px] sm:text-xs uppercase tracking-wide text-slate-500">${c.label}</div>
      <div class="text-base sm:text-xl font-bold mt-1 ${c.color} inline-block px-2 py-0.5 rounded break-words max-w-full">${c.value}</div>
    </div>
  `).join("");
}

function renderBBS(rows) {
  document.getElementById("bbsCard").classList.remove("hidden");
  const tb = document.getElementById("bbsTableBody");
  tb.innerHTML = rows.map(r => `
    <tr class="table-row border-b border-slate-100">
      <td class="px-3 py-2 font-semibold" data-label="Bar">${r.bar_mark}</td>
      <td class="px-3 py-2" data-label="Element">${(r.element_type || "-").toUpperCase()}</td>
      <td class="px-3 py-2" data-label="Description">${r.description}<br>
          <span class="text-xs text-slate-500">${r.shape}</span></td>
      <td class="px-3 py-2 text-center" data-label="Dia (mm)">${r.dia_mm}</td>
      <td class="px-3 py-2 text-center" data-label="Cut Len (mm)">${r.cutting_length_mm}</td>
      <td class="px-3 py-2 text-center" data-label="Qty">${r.quantity}</td>
      <td class="px-3 py-2 text-center" data-label="Total Len (m)">${r.total_length_m}</td>
      <td class="px-3 py-2 text-center font-semibold" data-label="Weight (kg)">${r.total_weight_kg}</td>
    </tr>
  `).join("");
}

function renderOrder(rows) {
  document.getElementById("orderCard").classList.remove("hidden");
  const tb = document.getElementById("orderTableBody");
  tb.innerHTML = rows.map(r => `
    <tr class="table-row border-b border-slate-100">
      <td class="px-3 py-2 text-center font-semibold" data-label="Dia (mm)">${r.dia_mm}</td>
      <td class="px-3 py-2 text-center" data-label="Net Len (m)">${r.net_length_m}</td>
      <td class="px-3 py-2 text-center" data-label="Net Wt (kg)">${r.net_weight_kg}</td>
      <td class="px-3 py-2 text-center" data-label="Wastage">${r.wastage_pct}%</td>
      <td class="px-3 py-2 text-center" data-label="Order Len (m)">${r.order_length_m}</td>
      <td class="px-3 py-2 text-center font-semibold" data-label="Order Wt (kg)">${r.order_weight_kg}</td>
      <td class="px-3 py-2 text-center font-bold text-[#1F4E78]" data-label="12m Rods">${r.rods_12m_required}</td>
    </tr>
  `).join("");
}

/** Build the human-readable calculation step trace from BBS rows. */
function renderSteps(rows) {
  const lines = [];
  rows.forEach(r => {
    lines.push(`▶ ${r.bar_mark} — ${r.description}`);
    lines.push(`   • Diameter        : ${r.dia_mm} mm`);
    lines.push(`   • Shape           : ${r.shape}`);
    lines.push(`   • Cutting length  : ${r.cutting_length_mm} mm  (= ${r.cutting_length_m} m)`);
    lines.push(`   • Quantity        : ${r.quantity} nos.`);
    lines.push(`   • Total length    : ${r.cutting_length_m} m × ${r.quantity}  =  ${r.total_length_m} m`);
    lines.push(`   • Unit weight     : d²/162 = ${r.dia_mm}²/162 = ${r.unit_weight_kg_m} kg/m`);
    lines.push(`   • Total weight    : ${r.total_length_m} m × ${r.unit_weight_kg_m} kg/m  =  ${r.total_weight_kg} kg`);
    lines.push("");
  });
  document.getElementById("stepsPanel").textContent = lines.join("\n");
}

/* ---------------- Calculate ---------------- */

document.getElementById("bbsForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError(); showWarnings(null);

  const payload = gatherPayload();
  const errs = clientValidate(payload);
  if (errs.length) { showError(errs); return; }

  const btn = document.getElementById("calcBtn");
  const spin = document.getElementById("calcSpinner");
  btn.disabled = true; spin.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/calculate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const json = await res.json();
    if (!json.success) {
      showError(json.errors || ["Server returned an error."]);
      if (json.warnings) showWarnings(json.warnings);
      return;
    }
    lastPayload = payload;
    lastResult  = json.data;

    document.getElementById("emptyState").classList.add("hidden");
    renderVerifyBanner(json.data.verification);
    renderSummary(json.data.summary);
    renderBBS(json.data.bbs);
    renderOrder(json.data.final_order);
    renderSteps(json.data.bbs);
    showWarnings(json.data.warnings);
  } catch (err) {
    showError("Network error: " + err.message);
  } finally {
    btn.disabled = false; spin.classList.add("hidden");
  }
});

/* ---------------- Steps toggle ---------------- */

document.getElementById("toggleSteps").addEventListener("click", () => {
  const panel = document.getElementById("stepsPanel");
  panel.classList.toggle("hidden");
  document.getElementById("toggleSteps").textContent =
    panel.classList.contains("hidden")
      ? "📋 Show calculation steps"
      : "📋 Hide calculation steps";
});

/* ---------------- Downloads ---------------- */

async function download(endpoint, fallbackName) {
  if (!lastPayload) { showError("Please calculate first."); return; }

  // Engineering Verified Mode: block export if last verification failed
  const verified = document.getElementById("engVerifiedMode").checked;
  if (verified && lastResult && lastResult.verification && !lastResult.verification.passed) {
    showError("Engineering Verified Mode is ON and double-check failed. "
              + "Export blocked. Recheck inputs or disable the mode.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lastPayload),
    });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      showError(j.errors || [`Failed to generate ${endpoint}`]);
      return;
    }
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "";
    const m = /filename="?([^"]+)"?/.exec(cd);
    const filename = m ? m[1] : fallbackName;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    showError("Download failed: " + err.message);
  }
}

document.getElementById("downloadExcel").addEventListener("click",
  () => download("download-excel", "BBS_Report.xlsx"));
document.getElementById("downloadPdf").addEventListener("click",
  () => download("download-pdf", "BBS_Report.pdf"));
