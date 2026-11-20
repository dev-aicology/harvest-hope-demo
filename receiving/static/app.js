"use strict";

// All session tokens and unsaved data stay in memory. No cookies or browser storage.
const state = {
  token: null, actor: null, config: null, catalog: [], receipts: [], receipt: null,
  dirty: false, busy: false, handoffKeys: new Map(), photoUrls: [], photoRender: 0,
};
const $ = (id) => document.getElementById(id);
const statusNames = {
  draft: "Draft", in_review: "Needs review", approved: "Approved",
  sent_mock: "Mock handoff created", reconciled_mock: "Mock records match",
  mismatch_mock: "Mock mismatch",
};
const topFields = ["supplier", "delivery_ref", "warehouse", "purchase_order_ref", "received_on", "notes"];
const clone = (value) => JSON.parse(JSON.stringify(value));
function uuid() {
  if (globalThis.crypto && crypto.randomUUID) return crypto.randomUUID();
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
function today() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = text;
  return item;
}
function button(text, handler, className = "button quiet") {
  const result = node("button", className, text);
  result.type = "button";
  result.addEventListener("click", handler);
  return result;
}
function message(text, kind = "success") {
  const item = $("message");
  item.className = `message ${kind}`;
  item.setAttribute("role", kind === "error" ? "alert" : "status");
  item.setAttribute("aria-live", kind === "error" ? "assertive" : "polite");
  item.textContent = text;
  item.hidden = !text;
  if (kind === "error") item.focus({preventScroll: true});
}
function apiMessage(data, fallback) {
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((entry) => {
    const location = Array.isArray(entry.loc) ? entry.loc.filter((x) => x !== "body").join(" / ") : "Field";
    return `${location}: ${entry.msg || "Invalid value"}`;
  }).join(". ");
  return fallback;
}
async function api(path, options = {}) {
  const headers = {...options.headers};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let body = options.body;
  if (body !== undefined && !(body instanceof Blob) && !(body instanceof ArrayBuffer)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, {...options, headers, body, cache: "no-store", credentials: "omit"});
  } catch {
    throw new Error("The local server could not be reached. Your unsaved fields are still here. Check the server, then retry.");
  }
  if (!response.ok) {
    let data = {};
    try { data = await response.json(); } catch { /* Server may return a non-JSON error. */ }
    const text = apiMessage(data, `The request failed (${response.status}).`);
    const suffix = response.status === 409 ? " Your unsaved fields are still here. Reload the saved receipt before retrying a conflicting edit." : "";
    const error = new Error(text + suffix);
    error.status = response.status;
    throw error;
  }
  if (options.asBlob) return response.blob();
  if (response.status === 204) return null;
  return response.json();
}
async function work(callback) {
  if (state.busy) return;
  state.busy = true;
  document.body.classList.add("busy");
  setPermissions();
  try { await callback(); }
  catch (error) { message(error.message || "The request could not be completed.", "error"); }
  finally {
    state.busy = false;
    document.body.classList.remove("busy");
    setPermissions();
  }
}
function newLine() {
  return {line_id: uuid(), product_id: null, barcode: "", description: "", quantity: null,
    unit: null, measured_weight: null, weight_unit: null, lot: "", expiry_date: null,
    disposition: "available", checked: false};
}
function blankReceipt() {
  return {id: null, version: null, status: "draft", supplier: "", delivery_ref: "",
    warehouse: "DEMO-DOCK-1", purchase_order_ref: "", received_on: today(), notes: "",
    lines: [newLine()], flags: [], suggestions: [], photos: [], handoff: null};
}
function canEdit() {
  return state.actor?.role === "receiver" && ["draft", "in_review", "approved"].includes(state.receipt?.status);
}
function setDirty() {
  state.dirty = true;
  $("receipt-subtitle").textContent = "Unsaved changes. Save the draft before sending it for review.";
  $("check-count").textContent = "Saved checks may be out of date";
}
function askDiscard() {
  return !state.dirty || window.confirm("Discard your unsaved receipt changes?");
}
function setPermissions() {
  const receipt = state.receipt;
  const busy = state.busy || !state.actor;
  const editable = canEdit();
  const reviewer = state.actor?.role === "reviewer";
  const status = receipt?.status;
  for (const id of topFields) $(id).disabled = busy || !editable;
  for (const input of document.querySelectorAll(".line-card input,.line-card select,.line-card textarea,.line-card button")) input.disabled = busy || !editable;
  $("identity").disabled = busy;
  $("new-receipt").disabled = busy || state.actor?.role !== "receiver";
  $("sample-receipt").disabled = busy || !editable;
  $("add-line").disabled = busy || !editable;
  $("refresh-list").disabled = busy;
  $("save-receipt").hidden = reviewer || !editable;
  $("save-receipt").disabled = busy || !editable;
  $("submit-receipt").hidden = reviewer || !editable;
  $("submit-receipt").disabled = busy || !editable;
  $("reload-receipt").hidden = !receipt?.id;
  $("reload-receipt").disabled = busy || !receipt?.id;
  $("review-actions").hidden = !reviewer || status !== "in_review";
  $("review-note").disabled = busy;
  $("approve-receipt").disabled = busy;
  $("return-receipt").disabled = busy;
  $("handoff-actions").hidden = !reviewer || status !== "approved";
  $("handoff-receipt").disabled = busy;
  $("reconcile-actions").hidden = !reviewer || !["sent_mock", "mismatch_mock"].includes(status);
  $("reconcile-receipt").disabled = busy;
  $("mismatch-receipt").disabled = busy;
  $("photo-file").disabled = busy || state.actor?.role !== "receiver" || !receipt?.id || status !== "draft";
  $("photo-file").parentElement.classList.toggle("disabled", $("photo-file").disabled);
  $("load-audit").disabled = busy || !receipt?.id;
  $("export-receipt").disabled = busy || !receipt?.id;
  for (const item of document.querySelectorAll(".photo-delete")) item.disabled = busy || !editable || status !== "draft";
  for (const item of document.querySelectorAll(".receipt-card")) item.disabled = busy;
}
function renderList() {
  const list = $("receipt-list");
  list.replaceChildren();
  if (!state.receipts.length) {
    list.append(node("p", "empty-note", "No receipts yet. Create a synthetic example to try the workflow."));
    return;
  }
  for (const receipt of state.receipts) {
    const item = button("", () => work(async () => {
      if (askDiscard()) await loadReceipt(receipt.id);
    }), `receipt-card${receipt.id === state.receipt?.id ? " active" : ""}`);
    item.setAttribute("aria-current", receipt.id === state.receipt?.id ? "true" : "false");
    item.append(node("strong", "", receipt.delivery_ref || "Unnamed delivery"),
      node("p", "", receipt.supplier || "No supplier"),
      node("span", `status status-${receipt.status}`, statusNames[receipt.status] || receipt.status));
    list.append(item);
  }
}
function field(labelText, input, className = "") {
  const label = node("label", className);
  const caption = node("span", "", labelText);
  label.append(caption, input);
  return label;
}
function inputFor(line, key, type = "text", extra = {}) {
  const input = document.createElement("input");
  input.type = type;
  input.value = line[key] ?? "";
  input.dataset.line = line.line_id;
  input.dataset.field = key;
  if (type === "text") { input.autocomplete = "off"; input.maxLength = 300; }
  Object.assign(input, extra);
  input.addEventListener("input", () => {
    let value = input.value;
    if (type === "number") value = value === "" ? null : Number(value);
    if (type === "date") value = value || null;
    line[key] = value;
    line.checked = false;
    updateChecked(line.line_id, false);
    if (["barcode", "description"].includes(key)) {
      input.closest(".line-card")?.querySelector(".suggestion")?.remove();
    }
    setDirty();
  });
  return input;
}
function selectFor(line, key, choices) {
  const select = document.createElement("select");
  select.dataset.line = line.line_id;
  select.dataset.field = key;
  for (const [value, text] of choices) {
    const option = node("option", "", text);
    option.value = value;
    select.append(option);
  }
  select.value = line[key] ?? "";
  select.addEventListener("change", () => {
    line[key] = select.value || null;
    line.checked = false;
    updateChecked(line.line_id, false);
    if (key === "product_id") {
      const item = state.catalog.find((x) => x.product_id === line.product_id);
      if (item && !line.unit) line.unit = item.unit;
      renderLines();
      focusLineField(line.line_id, "product_id");
    }
    setDirty();
  });
  return select;
}
function updateChecked(id, checked) {
  for (const input of document.querySelectorAll("input[data-field=checked]")) {
    if (input.dataset.line === id) input.checked = checked;
  }
}
function focusLineField(id, fieldName) {
  for (const input of document.querySelectorAll(".line-card input,.line-card select")) {
    if (input.dataset.line === id && input.dataset.field === fieldName) {
      input.focus({preventScroll: true});
      return;
    }
  }
}
function latestSuggestion(id) {
  const candidates = (state.receipt.suggestions || []).filter((x) => x.line_id === id);
  const result = candidates[candidates.length - 1];
  const line = state.receipt.lines.find((item) => item.line_id === id);
  if (result?.input && (result.input.barcode !== line.barcode || result.input.label_text !== line.description)) return null;
  return result;
}
function renderLines() {
  const list = $("line-items");
  list.replaceChildren();
  state.receipt.lines.forEach((line, index) => {
    const card = node("article", "line-card");
    card.setAttribute("aria-labelledby", `line-heading-${line.line_id}`);
    const heading = node("div", "line-heading");
    const title = node("h4", "", `Item ${index + 1}`);
    title.id = `line-heading-${line.line_id}`;
    heading.append(title, button("Remove", () => {
      if (state.receipt.lines.length === 1) {
        message("Keep at least one item in the receipt, or start a new receipt.", "warning");
        return;
      }
      state.receipt.lines = state.receipt.lines.filter((item) => item.line_id !== line.line_id);
      setDirty(); renderLines();
      focusLineField(state.receipt.lines[Math.min(index, state.receipt.lines.length - 1)].line_id, "barcode");
    }, "button quiet danger-text"));
    card.append(heading);
    const fields = node("div", "fields line-fields");
    const barcode = inputFor(line, "barcode", "text", {inputMode: "numeric", maxLength: 32, placeholder: "Type or scan a barcode"});
    fields.append(field("Barcode", barcode, "wide"));
    fields.append(field("Label text / item description", inputFor(line, "description", "text", {placeholder: "Enter visible wording from the label"}), "wide"));
    const product = selectFor(line, "product_id", [["", "Choose a catalog item"], ...state.catalog.map((item) => [item.product_id, item.name])]);
    fields.append(field("Confirmed catalog item", product, "wide"));
    fields.append(field("Actual quantity", inputFor(line, "quantity", "number", {min: "0", step: "any", inputMode: "decimal"})));
    fields.append(field("Quantity unit", selectFor(line, "unit", [["", "Select unit"], ["case", "Cases"], ["each", "Each"], ["lb", "Pounds (lb)"], ["kg", "Kilograms (kg)"]])));
    fields.append(field("Measured weight", inputFor(line, "measured_weight", "number", {min: "0", step: "any", inputMode: "decimal"})));
    fields.append(field("Weight unit", selectFor(line, "weight_unit", [["", "Select unit"], ["lb", "Pounds (lb)"], ["kg", "Kilograms (kg)"]])));
    fields.append(field("Lot number", inputFor(line, "lot", "text", {maxLength: 120})));
    fields.append(field("Expiry date", inputFor(line, "expiry_date", "date")));
    fields.append(field("Disposition", selectFor(line, "disposition", [["available", "Available for receiving"], ["hold", "Hold for staff decision"]]), "wide"));
    const productInfo = state.catalog.find((item) => item.product_id === line.product_id);
    if (productInfo) {
      const needs = [`Catalog quantity unit: ${productInfo.unit}`];
      if (productInfo.requires_weight) needs.push("measured weight required");
      if (productInfo.requires_lot) needs.push("lot required");
      if (productInfo.requires_expiry) needs.push("expiry required");
      fields.append(node("p", "small muted span-all", needs.join(" · ")));
    }
    card.append(fields);
    const tools = node("div", "match-tools");
    let aiChoice = null;
    if (state.config?.ai_provider === "ollama") {
      const choice = node("label", "ai-choice");
      aiChoice = document.createElement("input"); aiChoice.type = "checkbox";
      choice.append(aiChoice, node("span", "", "Ask the configured local model"));
      tools.append(choice);
    }
    tools.prepend(button("Suggest catalog item", () => work(() => suggest(line.line_id, !!aiChoice?.checked)), "button secondary"));
    tools.append(node("span", "small muted", state.config?.ai_provider === "ollama" ? "Barcode / label rules first; AI is optional." : "Exact barcode and label rules. AI is disabled."));
    card.append(tools);
    const suggestion = latestSuggestion(line.line_id);
    if (suggestion) {
      const box = node("div", "suggestion");
      const text = node("div");
      const candidate = state.catalog.find((item) => item.product_id === suggestion.product_id);
      text.append(node("strong", "", candidate ? `Suggested: ${candidate.name}` : "No reliable item match"));
      text.append(node("p", "", suggestion.reason || "Please choose the item after checking the goods."));
      text.append(node("p", "small muted", `Method: ${suggestion.method || "unknown"}. Always review before accepting.`));
      box.append(text);
      if (candidate) box.append(button("Use this item", () => {
        line.product_id = candidate.product_id;
        if (!line.unit) line.unit = candidate.unit;
        line.checked = false;
        setDirty(); renderLines();
        focusLineField(line.line_id, "checked");
        message("Item selected. Check the actual quantity, unit, lot and weight before confirming the row.");
      }));
      card.append(box);
    }
    const confirmation = node("label", "confirmation");
    const check = document.createElement("input"); check.type = "checkbox"; check.checked = !!line.checked;
    check.dataset.field = "checked"; check.dataset.line = line.line_id;
    check.addEventListener("change", () => { line.checked = check.checked; setDirty(); });
    confirmation.append(check, node("span", "", "I checked this item and its actual quantity, unit, weight, and any required lot / expiry details."));
    card.append(confirmation);
    list.append(card);
  });
  setPermissions();
}
function renderFlags() {
  const list = $("validation-list"); list.replaceChildren();
  if (!state.receipt.id) {
    list.append(node("p", "small muted", "Save the draft to check catalog matches, units, and required receiving fields."));
    $("check-count").textContent = "Save to check";
    return;
  }
  const flags = state.receipt.flags || [];
  $("check-count").textContent = flags.length ? `${flags.length} item${flags.length === 1 ? "" : "s"} to check` : "No blocking fields";
  if (!flags.length) list.append(node("div", "clear-checks", "Required record checks passed. Staff review is still required."));
  for (const flag of flags) {
    const row = node("div", `flag ${flag.severity}`);
    const index = state.receipt.lines.findIndex((line) => line.line_id === flag.line_id);
    row.append(node("span", "flag-icon", flag.severity === "blocking" ? "!" : "•"), node("span", "", `${index >= 0 ? `Item ${index + 1}: ` : ""}${flag.message}`));
    list.append(row);
  }
}
function actionHint() {
  const status = state.receipt.status;
  const role = state.actor?.role;
  if (status === "reconciled_mock") return "The simulated response matches the approved record. This is a local demonstration, not confirmation from either warehouse system.";
  if (status === "mismatch_mock") return "The simulated response differs from the approved record. This receipt remains an exception; inspect its audit history.";
  if (status === "sent_mock") return role === "reviewer" ? "The mock handoff is stored. Compare the simulated return record with the approved receipt." : "The mock handoff is stored. Switch to Reviewer to compare the simulated return record.";
  if (status === "approved") return role === "reviewer" ? "The receipt is approved. Create a mock handoff using an existing purchase-order reference." : "The receipt is approved. Saving another edit will return it to draft and revoke approval.";
  if (status === "in_review") return role === "reviewer" ? "Check the receipt and its supporting evidence. Approve it or return it with a correction note." : "A reviewer can now check the receipt. Saving further edits returns it to draft.";
  return role === "reviewer" ? "This receipt is a draft. Switch to Receiver to finish it and send it for review." : "Save your progress, check each item, then send the receipt for review.";
}
function renderSummary() {
  const target = $("handoff-summary"); target.replaceChildren();
  const handoff = state.receipt.handoff;
  target.hidden = !handoff;
  if (!handoff) return;
  const box = node("div", "handoff-box");
  box.append(node("strong", "", "Stored local handoff"));
  box.append(node("p", "", `Reference: ${handoff.external_receipt_ref || handoff.id || "See JSON export"}`));
  box.append(node("p", "", "No request has been sent to WaerLinx or NetSuite."));
  target.append(box);
}
async function renderPhotos() {
  const generation = ++state.photoRender;
  for (const url of state.photoUrls) URL.revokeObjectURL(url);
  state.photoUrls = [];
  const target = $("photos"); target.replaceChildren();
  $("photo-policy").textContent = `Photo access expires after ${state.config?.photo_retention_days || 7} days. Files are removed when local retention cleanup runs. Metadata is stripped; no photo inference is performed.`;
  for (const photo of state.receipt.photos || []) {
    const card = node("figure", "photo-card");
    const image = document.createElement("img"); image.alt = `Supporting evidence: ${photo.name || "receipt photo"}`;
    card.append(image);
    card.append(node("figcaption", "", `${photo.name || "Photo"}${photo.expires_at ? ` · expires ${photo.expires_at.slice(0, 10)}` : ""}`));
    const remove = button("Remove photo", () => work(async () => {
      if (state.dirty) await saveReceipt(false);
      const receipt = await api(`/api/receipts/${state.receipt.id}/photos/${photo.id}?expected_version=${state.receipt.version}`, {method: "DELETE"});
      acceptReceipt(receipt);
      message("The stored photo copy was removed; the action remains in the audit history.");
    }), "button quiet danger-text photo-delete");
    card.append(remove); target.append(card);
    try {
      const blob = await api(`/api/photos/${photo.id}`, {asBlob: true});
      if (generation !== state.photoRender) return;
      const url = URL.createObjectURL(blob); state.photoUrls.push(url); image.src = url;
    } catch {
      if (generation !== state.photoRender) return;
      image.remove(); card.prepend(node("p", "small muted", "Photo is unavailable or its retention period has ended."));
    }
  }
  setPermissions();
}
function render() {
  const receipt = state.receipt;
  for (const name of topFields) $(name).value = receipt[name] ?? "";
  $("receipt-title").textContent = receipt.id ? receipt.delivery_ref || "Saved receipt" : "New receipt";
  $("receipt-subtitle").textContent = receipt.id ? `Saved version ${receipt.version} · ${receipt.warehouse}` : "Capture what arrived, then ask a colleague to review.";
  $("receipt-status").className = `status status-${receipt.status}`;
  $("receipt-status").textContent = receipt.id ? statusNames[receipt.status] || receipt.status : "Unsaved";
  const step = receipt.status === "draft" ? "capture" : receipt.status === "in_review" ? "review" : receipt.status === "approved" ? "handoff" : "compare";
  for (const item of document.querySelectorAll(".steps li")) {
    const current = item.dataset.step === step;
    item.classList.toggle("current", current);
    if (current) item.setAttribute("aria-current", "step"); else item.removeAttribute("aria-current");
  }
  $("action-hint").textContent = actionHint();
  $("record-panel").hidden = !receipt.id;
  $("audit-result").hidden = true;
  $("review-note").value = "";
  renderLines(); renderFlags(); renderSummary(); renderList();
  void renderPhotos(); setPermissions();
}
function acceptReceipt(receipt) {
  state.receipt = receipt;
  state.dirty = false;
  render();
}
async function refreshList() {
  const result = await api("/api/receipts");
  state.receipts = result.items;
  renderList(); setPermissions();
}
async function loadReceipt(id) {
  acceptReceipt(await api(`/api/receipts/${id}`));
  message("");
}
function payload() {
  const receipt = state.receipt;
  const result = {};
  for (const key of topFields) result[key] = typeof receipt[key] === "string" ? receipt[key].trim() : receipt[key];
  result.lines = clone(receipt.lines);
  return result;
}
async function saveReceipt(showMessage = true) {
  for (const key of ["supplier", "delivery_ref", "warehouse", "received_on"]) {
    if (!state.receipt[key]?.trim()) { $(key).focus(); throw new Error(`Please enter ${key.replaceAll("_", " ")} before saving.`); }
  }
  const data = payload();
  let receipt;
  if (state.receipt.id) receipt = await api(`/api/receipts/${state.receipt.id}`, {method: "PUT", body: {...data, expected_version: state.receipt.version}});
  else receipt = await api("/api/receipts", {method: "POST", body: data});
  acceptReceipt(receipt); await refreshList();
  if (showMessage) message("Draft saved. Record checks are shown below the items.");
  return receipt;
}
async function suggest(lineId, useAI) {
  if (state.dirty || !state.receipt.id || state.receipt.status !== "draft") await saveReceipt(false);
  const line = state.receipt.lines.find((item) => item.line_id === lineId);
  if (!line) throw new Error("Save the item before requesting a suggestion.");
  const result = await api(`/api/receipts/${state.receipt.id}/suggest`, {method: "POST", body: {
    expected_version: state.receipt.version, line_id: lineId,
    label_text: line.description || "", barcode: line.barcode || "", use_ai: useAI,
  }});
  acceptReceipt(result.receipt); await refreshList();
  message(result.suggestion.product_id ? "A suggested catalog item is ready to review. Nothing has been accepted or counted automatically." : "The matcher could not identify the item reliably. Choose it after checking the goods.");
}
async function transition(action, extra = {}) {
  if (!state.receipt.id) throw new Error("Save the draft first.");
  const result = await api(`/api/receipts/${state.receipt.id}/${action}`, {method: "POST", body: {expected_version: state.receipt.version, ...extra}});
  acceptReceipt(result.receipt || result); await refreshList();
}
async function startSession(identity, receiptId = null) {
  state.token = null; state.actor = null;
  state.handoffKeys.clear();
  const session = await api("/api/session", {method: "POST", body: {identity}});
  state.token = session.token; state.actor = session.actor;
  const [config, catalog, receipts] = await Promise.all([api("/api/config"), api("/api/catalog"), api("/api/receipts")]);
  state.config = config; state.catalog = catalog.items; state.receipts = receipts.items;
  if (receiptId) await loadReceipt(receiptId);
  else if (identity === "reviewer" && state.receipts.length) await loadReceipt(state.receipts[0].id);
  else acceptReceipt(blankReceipt());
  message(identity === "reviewer" ? "Reviewer demo identity selected. Open a submitted receipt to review it." : "Receiver demo identity selected. Use synthetic information for this draft.");
}
async function audit() {
  const result = await api(`/api/receipts/${state.receipt.id}/audit`);
  const target = $("audit-result"); target.replaceChildren(); target.hidden = false;
  target.append(node("p", result.valid ? "clear-checks" : "flag blocking", result.valid ? "Audit hash chain verified for the stored events." : "Audit verification failed. Inspect the database before relying on this record."));
  const list = node("ol", "audit-list");
  for (const event of result.events) {
    const item = node("li", "audit-event");
    item.append(node("h4", "", `${event.seq}. ${event.action.replaceAll("_", " ")}`));
    item.append(node("p", "", `${event.actor_id} · ${event.created_at}`));
    const detail = document.createElement("details");
    detail.append(node("summary", "", "Event details"), node("pre", "", JSON.stringify(event.payload, null, 2)));
    item.append(detail); list.append(item);
  }
  target.append(list);
}
function download(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2) + "\n"], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a"); link.href = url; link.download = filename;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
for (const key of topFields) $(key).addEventListener("input", () => {
  if (!state.receipt) return;
  state.receipt[key] = $(key).value; setDirty();
});
$("receipt-form").addEventListener("submit", (event) => { event.preventDefault(); void work(() => saveReceipt()); });
$("identity").addEventListener("change", () => {
  const requested = $("identity").value;
  if (!askDiscard()) { $("identity").value = state.actor.role; return; }
  void work(() => startSession(requested, state.receipt?.id));
});
$("refresh-list").addEventListener("click", () => work(refreshList));
$("new-receipt").addEventListener("click", () => {
  if (!askDiscard()) return;
  acceptReceipt(blankReceipt()); message(""); $("supplier").focus();
});
$("sample-receipt").addEventListener("click", () => {
  if (!askDiscard()) return;
  const receipt = blankReceipt();
  receipt.supplier = "Demo Food Cooperative";
  receipt.delivery_ref = `DEMO-${Date.now().toString(36).toUpperCase()}`;
  receipt.purchase_order_ref = "DEMO-PO-001";
  receipt.notes = "Synthetic example for an internal review. No actual goods or purchase order.";
  const product = state.catalog[0];
  if (product) {
    const line = receipt.lines[0];
    Object.assign(line, {product_id: product.product_id, barcode: product.barcode || "", description: product.name, quantity: 4, unit: product.unit});
    if (product.requires_lot) line.lot = "DEMO-LOT-001";
    if (product.requires_expiry) { const date = new Date(); date.setFullYear(date.getFullYear() + 1); line.expiry_date = date.toISOString().slice(0, 10); }
    if (product.requires_weight) { line.measured_weight = 12; line.weight_unit = "kg"; }
  }
  acceptReceipt(receipt); setDirty();
  message("Synthetic example loaded. Check the row, save it, and send it for review to try the workflow.");
});
$("add-line").addEventListener("click", () => {
  const line = newLine(); state.receipt.lines.push(line); setDirty(); renderLines();
  focusLineField(line.line_id, "barcode");
});
$("reload-receipt").addEventListener("click", () => work(async () => { if (askDiscard()) await loadReceipt(state.receipt.id); }));
$("submit-receipt").addEventListener("click", () => work(async () => {
  if (state.dirty || !state.receipt.id || state.receipt.status !== "draft") await saveReceipt(false);
  await transition("submit"); message("Receipt sent for review. Switch to the Reviewer demo identity to inspect and approve it.");
}));
$("approve-receipt").addEventListener("click", () => work(async () => {
  await transition("approve", {note: $("review-note").value.trim()});
  message("Receipt approved. You can now prepare a local mock handoff.");
}));
$("return-receipt").addEventListener("click", () => work(async () => {
  const note = $("review-note").value.trim();
  if (!note) { $("review-note").focus(); throw new Error("Add a review note explaining what needs correction."); }
  await transition("return", {note}); message("Receipt returned to draft with your correction note in the audit history.");
}));
$("handoff-receipt").addEventListener("click", () => work(async () => {
  const key = `${state.receipt.id}:${state.receipt.version}`;
  if (!state.handoffKeys.has(key)) state.handoffKeys.set(key, uuid());
  await transition("handoff", {idempotency_key: state.handoffKeys.get(key)});
  message("Mock handoff stored once. No live warehouse system was contacted.");
}));
$("reconcile-receipt").addEventListener("click", () => work(async () => {
  await transition("reconcile", {simulate_mismatch: false}); message("Mock comparison completed. See the receipt status and audit history.");
}));
$("mismatch-receipt").addEventListener("click", () => work(async () => {
  await transition("reconcile", {simulate_mismatch: true}); message("A deliberately mismatched mock response was compared. The receipt is flagged for investigation.", "warning");
}));
$("load-audit").addEventListener("click", () => work(audit));
$("export-receipt").addEventListener("click", () => work(async () => {
  const data = await api(`/api/receipts/${state.receipt.id}/export`);
  download(data, `receiving-${state.receipt.id}.json`);
  message("Draft JSON exported. It is not a WaerLinx or NetSuite import file.");
}));
$("photo-file").addEventListener("change", () => work(async () => {
  const file = $("photo-file").files[0];
  if (!file) return;
  try {
    if (!["image/png", "image/jpeg"].includes(file.type)) throw new Error("Choose a PNG or JPEG image.");
    if (file.size > (state.config.max_photo_bytes || 4194304)) throw new Error("The photo is too large. Choose a file smaller than 4 MB.");
    if (state.dirty) await saveReceipt(false);
    const receipt = await api(`/api/receipts/${state.receipt.id}/photos?expected_version=${state.receipt.version}`, {method: "POST", headers: {"Content-Type": file.type}, body: file});
    acceptReceipt(receipt); message("Supporting photo saved locally. No image inference was performed.");
  } finally { $("photo-file").value = ""; }
}));
window.addEventListener("beforeunload", (event) => { if (state.dirty) { event.preventDefault(); event.returnValue = ""; } });
void work(() => startSession("receiver"));
