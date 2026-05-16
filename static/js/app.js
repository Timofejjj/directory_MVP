const state = {
  catalogKey: null,
  columns: [],
  records: [],
  selectOptions: {},
  selectedRecordId: null,
  sortKey: null,
  sortDir: "asc",
  dialogMode: "create",
};

const $ = (sel) => document.querySelector(sel);

const catalogSelect = $("#catalogSelect");
const catalogTitle = $("#catalogTitle");
const statusMessage = $("#statusMessage");
const dataTable = $("#dataTable");
const thead = dataTable.querySelector("thead");
const tbody = dataTable.querySelector("tbody");
const emptyHint = $("#emptyHint");
const recordDialog = $("#recordDialog");
const recordForm = $("#recordForm");
const formFields = $("#formFields");
const dialogTitle = $("#dialogTitle");
const btnSave = $("#btnSave");

function setStatus(text, type = "") {
  statusMessage.textContent = text || "";
  statusMessage.className = "status" + (type ? ` ${type}` : "");
}

function displayColumns() {
  return state.columns.filter((c) => c.key !== "department_id" || c.display_key);
}

function cellValue(record, col) {
  const key = col.display_key || col.key;
  return record[key] ?? "";
}

function parseDisplayDate(str) {
  if (!str || typeof str !== "string") return null;
  const m = str.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if (!m) return null;
  const d = Number(m[1]);
  const mo = Number(m[2]);
  const y = Number(m[3]);
  const dt = new Date(y, mo - 1, d);
  if (
    dt.getFullYear() !== y ||
    dt.getMonth() !== mo - 1 ||
    dt.getDate() !== d
  ) {
    return null;
  }
  return dt.getTime();
}

function compareRecords(a, b, col) {
  const key = col.display_key || col.key;
  const va = a[key];
  const vb = b[key];

  if (col.sort === "number") {
    const na = Number(String(va).replace(",", "."));
    const nb = Number(String(vb).replace(",", "."));
    return na - nb;
  }

  if (col.sort === "date") {
    const da = parseDisplayDate(String(va)) ?? 0;
    const db = parseDisplayDate(String(vb)) ?? 0;
    return da - db;
  }

  return String(va).localeCompare(String(vb), "ru", { sensitivity: "base" });
}

function sortedRecords() {
  if (!state.sortKey) return [...state.records];
  const col = state.columns.find((c) => c.key === state.sortKey);
  if (!col) return [...state.records];

  const sorted = [...state.records].sort((a, b) => compareRecords(a, b, col));
  if (state.sortDir === "desc") sorted.reverse();
  return sorted;
}

function renderTable() {
  const cols = displayColumns();
  const rows = sortedRecords();

  thead.innerHTML = "";
  const headRow = document.createElement("tr");
  cols.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col.label;
    th.classList.add("sortable");
    th.dataset.colKey = col.key;

    const indicator = document.createElement("span");
    indicator.className = "sort-indicator";
    if (state.sortKey === col.key) {
      indicator.textContent = state.sortDir === "asc" ? "▲" : "▼";
    } else {
      indicator.textContent = "⇅";
    }
    th.appendChild(indicator);

    th.addEventListener("click", () => {
      if (state.sortKey === col.key) {
        state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      } else {
        state.sortKey = col.key;
        state.sortDir = "asc";
      }
      renderTable();
    });

    headRow.appendChild(th);
  });
  thead.appendChild(headRow);

  tbody.innerHTML = "";
  rows.forEach((rec) => {
    const tr = document.createElement("tr");
    tr.dataset.recordId = String(rec.id);

    cols.forEach((col) => {
      const td = document.createElement("td");
      const val = cellValue(rec, col);
      td.textContent = val;
      if (col.sort === "number") td.classList.add("num");
      tr.appendChild(td);
    });

    if (rec.id === state.selectedRecordId) {
      tr.classList.add("selected");
    }

    tr.addEventListener("click", () => selectRecord(rec.id));
    tr.addEventListener("dblclick", () => openDialog("edit"));
    tbody.appendChild(tr);
  });

  emptyHint.classList.toggle("hidden", rows.length > 0);
  updateToolbar();
}

function selectRecord(id) {
  state.selectedRecordId = id;
  tbody.querySelectorAll("tr").forEach((tr) => {
    tr.classList.toggle("selected", Number(tr.dataset.recordId) === id);
  });
  updateToolbar();
}

function updateToolbar() {
  const has = state.selectedRecordId != null;
  $("#btnEdit").disabled = !has;
  $("#btnView").disabled = !has;
  $("#btnHistory").disabled = !has;
  $("#btnDelete").disabled = !has;
}

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Ошибка ${res.status}`);
  }
  return data;
}

async function loadCatalogs() {
  const catalogs = await api("/api/catalogs");
  catalogSelect.innerHTML = "";
  catalogs.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.key;
    opt.textContent = c.label;
    catalogSelect.appendChild(opt);
  });
  if (catalogs.length) {
    state.catalogKey = catalogs[0].key;
    catalogSelect.value = state.catalogKey;
    await loadRecords();
  }
}

async function loadRecords() {
  state.catalogKey = catalogSelect.value;
  state.selectedRecordId = null;
  state.sortKey = null;
  state.sortDir = "asc";
  setStatus("Загрузка…");

  const data = await api(`/api/catalogs/${state.catalogKey}/records`);
  state.columns = data.columns;
  state.records = data.records;
  state.selectOptions = data.selectOptions || {};

  catalogTitle.textContent = catalogSelect.selectedOptions[0].textContent;
  setStatus(`Записей: ${state.records.length}`, "success");
  renderTable();
}

function isoFromDisplay(display) {
  const m = String(display).match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if (!m) return "";
  return `${m[3]}-${m[2]}-${m[1]}`;
}

function displayFromIso(iso) {
  if (!iso) return "";
  const p = iso.split("-");
  if (p.length !== 3) return iso;
  return `${p[2]}.${p[1]}.${p[0]}`;
}

function buildSelectField(col, value, readonly) {
  const wrap = document.createElement("div");
  wrap.className = "field" + (readonly ? " readonly" : "");

  const label = document.createElement("label");
  label.htmlFor = `f_${col.key}`;
  label.textContent = col.label;
  wrap.appendChild(label);

  const select = document.createElement("select");
  select.id = `f_${col.key}`;
  select.name = col.key;
  select.required = !readonly;
  if (readonly) select.disabled = true;

  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "— выберите —";
  select.appendChild(empty);

  const options = state.selectOptions[col.key] || [];
  options.forEach((opt) => {
    const o = document.createElement("option");
    o.value = String(opt.id);
    o.textContent = opt.label;
    select.appendChild(o);
  });

  if (value != null && value !== "") {
    select.value = String(value);
  }

  wrap.appendChild(select);
  return wrap;
}

function buildFormField(col, record, readonly) {
  if (col.type === "select") {
    return buildSelectField(col, record[col.key], readonly);
  }

  const wrap = document.createElement("div");
  wrap.className = "field" + (readonly ? " readonly" : "");

  const label = document.createElement("label");
  label.htmlFor = `f_${col.key}`;
  label.textContent = col.label;
  wrap.appendChild(label);

  let input;
  const val = record[col.key] ?? "";

  switch (col.type) {
    case "textarea": {
      input = document.createElement("textarea");
      input.value = val;
      break;
    }
    case "date": {
      input = document.createElement("input");
      input.type = "date";
      input.value = isoFromDisplay(val) || val;
      break;
    }
    case "integer": {
      input = document.createElement("input");
      input.type = "number";
      input.step = "1";
      input.value = val;
      if (col.min != null) input.min = String(col.min);
      if (col.max != null) input.max = String(col.max);
      break;
    }
    case "decimal": {
      input = document.createElement("input");
      input.type = "number";
      input.step = "0.01";
      input.min = "0";
      input.value = val;
      break;
    }
    default: {
      input = document.createElement("input");
      input.type = "text";
      input.value = val;
    }
  }

  input.id = `f_${col.key}`;
  input.name = col.key;
  if (col.type !== "textarea") input.required = !readonly && col.type !== "textarea";
  if (readonly) input.readOnly = true;

  wrap.appendChild(input);
  return wrap;
}

async function openDialog(mode) {
  state.dialogMode = mode;
  const readonly = mode === "view";

  let record = {};
  if (mode !== "create") {
    if (state.selectedRecordId == null) return;
    record = await api(
      `/api/catalogs/${state.catalogKey}/records/${state.selectedRecordId}`
    );
  }

  if (state.catalogKey === "projects" && !state.selectOptions.department_id) {
    const data = await api(`/api/catalogs/projects/records`);
    state.selectOptions = data.selectOptions || {};
  }

  formFields.innerHTML = "";
  state.columns.forEach((col) => {
    formFields.appendChild(buildFormField(col, record, readonly));
  });

  const titles = {
    create: "Новая запись",
    edit: "Редактирование",
    view: "Просмотр записи",
  };
  dialogTitle.textContent = titles[mode];
  btnSave.classList.toggle("hidden", readonly);
  recordDialog.showModal();
}

function collectFormData() {
  const payload = {};
  state.columns.forEach((col) => {
    const el = formFields.querySelector(`[name="${col.key}"]`);
    if (!el) return;

    if (col.type === "date") {
      payload[col.key] = displayFromIso(el.value);
    } else if (col.type === "select") {
      payload[col.key] = el.value;
    } else {
      payload[col.key] = el.value;
    }
  });
  return payload;
}

async function saveRecord(event) {
  event.preventDefault();
  const payload = collectFormData();

  try {
    if (state.dialogMode === "create") {
      await api(`/api/catalogs/${state.catalogKey}/records`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setStatus("Запись добавлена", "success");
    } else {
      await api(
        `/api/catalogs/${state.catalogKey}/records/${state.selectedRecordId}`,
        { method: "PUT", body: JSON.stringify(payload) }
      );
      setStatus("Запись сохранена", "success");
    }
    recordDialog.close();
    await loadRecords();
  } catch (e) {
    setStatus(e.message, "error");
  }
}

function historyDisplayColumns() {
  return state.columns.map((col) => {
    if (col.display_key) {
      return { key: col.display_key, label: col.label };
    }
    return { key: col.key, label: col.label };
  });
}

async function openHistory() {
  if (state.selectedRecordId == null) return;

  const rec = state.records.find((r) => r.id === state.selectedRecordId);
  const label = rec?.name || rec?.title || "запись";
  $("#historyDialogTitle").textContent = `История: ${label}`;

  const historyTable = $("#historyTable");
  const histHead = historyTable.querySelector("thead");
  const histBody = historyTable.querySelector("tbody");
  const historyEmpty = $("#historyEmpty");

  try {
    const data = await api(
      `/api/catalogs/${state.catalogKey}/records/${state.selectedRecordId}/history`
    );
    const cols = [
      { key: "changed_at", label: "Когда" },
      { key: "operation_label", label: "Действие" },
      ...historyDisplayColumns(),
    ];

    histHead.innerHTML = "";
    const headRow = document.createElement("tr");
    cols.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col.label;
      headRow.appendChild(th);
    });
    histHead.appendChild(headRow);

    histBody.innerHTML = "";
    data.entries.forEach((entry) => {
      const tr = document.createElement("tr");
      cols.forEach((col) => {
        const td = document.createElement("td");
        td.textContent = entry[col.key] ?? "";
        tr.appendChild(td);
      });
      histBody.appendChild(tr);
    });

    const empty = data.entries.length === 0;
    historyEmpty.classList.toggle("hidden", !empty);
    historyTable.classList.toggle("hidden", empty);
    $("#historyDialog").showModal();
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function deleteRecord() {
  if (state.selectedRecordId == null) return;
  const rec = state.records.find((r) => r.id === state.selectedRecordId);
  const label =
    rec?.name || rec?.title || rec?.department_label || "выбранную запись";
  if (
    !confirm(
      `Снять «${label}» с учёта?\n\nДанные останутся в базе; связанные записи не изменятся.`
    )
  ) {
    return;
  }

  try {
    await api(
      `/api/catalogs/${state.catalogKey}/records/${state.selectedRecordId}`,
      { method: "DELETE" }
    );
    setStatus("Запись снята с учёта (сохранена в истории)", "success");
    await loadRecords();
  } catch (e) {
    setStatus(e.message, "error");
  }
}

function wireEvents() {
  catalogSelect.addEventListener("change", () => loadRecords());
  $("#btnAdd").addEventListener("click", () => openDialog("create"));
  $("#btnEdit").addEventListener("click", () => openDialog("edit"));
  $("#btnView").addEventListener("click", () => openDialog("view"));
  $("#btnHistory").addEventListener("click", openHistory);
  $("#btnDelete").addEventListener("click", deleteRecord);
  $("#btnHistoryClose").addEventListener("click", () => $("#historyDialog").close());
  $("#btnCloseHistory").addEventListener("click", () => $("#historyDialog").close());
  recordForm.addEventListener("submit", saveRecord);
  $("#btnCancel").addEventListener("click", () => recordDialog.close());
  $("#btnCloseDialog").addEventListener("click", () => recordDialog.close());
}

document.addEventListener("DOMContentLoaded", async () => {
  wireEvents();
  try {
    await loadCatalogs();
  } catch (e) {
    setStatus(e.message, "error");
  }
});
