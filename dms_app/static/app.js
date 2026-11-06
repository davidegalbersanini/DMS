// SISTEMA TOAST NOTIFICATIONS ELEGANTE (Sostituisce alert bloccanti)
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let iconSvg = '';
    if (type === 'success') {
        iconSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    } else if (type === 'error') {
        iconSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
    } else {
        iconSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
    }
    
    toast.innerHTML = `${iconSvg}<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastFadeOut 0.25s forwards';
        setTimeout(() => toast.remove(), 250);
    }, duration);
}

// SCORCIATOIE DA TASTIERA GLOBALI
document.addEventListener('keydown', (e) => {
    // Esc: Chiude qualsiasi modale aperto
    if (e.key === 'Escape') {
        if (typeof closeAllMultiSelects === 'function' && closeAllMultiSelects()) {
            return;
        }
        const colModal = document.getElementById('modal-columns-container');
        if (colModal && colModal.style.display !== 'none') {
            closeColumnsModal();
            return;
        }
        const idModal = document.getElementById('modal-id-container');
        if (idModal && idModal.style.display !== 'none') {
            closeIdModal();
            return;
        }
        const cfgModal = document.getElementById('modal-config-container');
        if (cfgModal && cfgModal.style.display !== 'none') {
            closeConfigModal();
            return;
        }
        const lookupsModal = document.getElementById('modal-lookups-container');
        if (lookupsModal && lookupsModal.style.display !== 'none') {
            closeLookupsModal();
            return;
        }
    }

    // Ctrl + F: Porta il focus alla ricerca globale
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
        const searchInput = document.getElementById('global-search');
        if (searchInput && document.activeElement !== searchInput) {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }
    }

    // Frecce Sx/Dx nel modale ID se non si sta digitando in un campo input/textarea
    const idModal = document.getElementById('modal-id-container');
    if (idModal && idModal.style.display !== 'none') {
        const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
        const isEditable = document.activeElement && document.activeElement.isContentEditable;
        if (tag !== 'input' && tag !== 'textarea' && tag !== 'select' && !isEditable) {
            if (e.key === 'ArrowLeft') {
                navigateId(-1);
            } else if (e.key === 'ArrowRight') {
                navigateId(1);
            }
        }
    }
});

// Chiusura dropdown filtri cliccando all'esterno
document.addEventListener('click', (e) => {
    if (!e.target.closest('.multiselect-dropdown')) {
        if (typeof closeAllMultiSelects === 'function') {
            closeAllMultiSelects();
        }
    }
});

// DMS 2.0 - Client Controller & Modern Data Grid with Resizable Columns

let allActivities = [];
let currentActivityId = null;
let currentLookups = {};
let isExpiringFilterActive = false;
let searchDebounceTimer = null;
let currentLookupCategory = 'person';
let currentSortCol = "id";
let currentSortDir = "desc";

const TYPE_STATUS_MAP = {
    "Discussion": [
        "1) To Start",
        "2) On Going",
        "3) To Promote",
        "4) Closed /Canceled",
        "5) On hold"
    ],
    "Idea": [
        "1) Draft",
        "2) Submitted",
        "3) Rejected (1)",
        "4) To be Quoted",
        "5) Approved",
        "6) Rejected",
        "7) Rejected 2",
        "8) On Hold"
    ],
    "Project": [
        "1) Planned",
        "2) Scheduled",
        "3) On Going",
        "4) To be closed",
        "5) Closed/Cancelled",
        "6) On Hold"
    ],
    "Task": [
        "1) Planned",
        "2) Scheduled",
        "3) On Going",
        "4) To be closed",
        "5) Closed/Cancelled",
        "6) On Hold"
    ]
};

document.addEventListener("DOMContentLoaded", async () => {
    restoreColumnOrder();
    restoreColumnWidths();
    applyColumnVisibility();
    initColumnResize();
    initColumnReorder();
    initMultiFilters();
    updateSortIndicators();
    await loadConfig();
    await loadLookups();
    await reloadTable();
});

// --- SISTEMA RIORDINO & RIDIMENSIONAMENTO COLONNE (DRAG & DROP) ---

const DEFAULT_COLUMN_ORDER = [
    "actions", "id", "urgency", "drivers", "odg", "title", "type",
    "relevancy", "pm", "pe", "beneficiary", "cluster", "basic_kit",
    "proto_n", "year_2027", "year_28", "year_29", "year_30", "year_31",
    "status", "last_update"
];

const DEFAULT_COLUMN_WIDTHS = {
    actions: "140px",
    id: "75px",
    urgency: "110px",
    drivers: "160px",
    odg: "80px",
    title: "280px",
    type: "100px",
    relevancy: "140px",
    pm: "120px",
    pe: "120px",
    beneficiary: "125px",
    cluster: "120px",
    basic_kit: "100px",
    proto_n: "90px",
    year_2027: "145px",
    year_28: "70px",
    year_29: "70px",
    year_30: "70px",
    year_31: "70px",
    status: "140px",
    last_update: "145px"
};

const COLUMN_METADATA = [
    { key: "actions", label: "Comandi" },
    { key: "id", label: "ID" },
    { key: "urgency", label: "Urgenza" },
    { key: "drivers", label: "Drivers" },
    { key: "odg", label: "ODG" },
    { key: "title", label: "Titolo Attività" },
    { key: "type", label: "Tipo" },
    { key: "relevancy", label: "Rel (1-5)" },
    { key: "pm", label: "PM" },
    { key: "pe", label: "PE" },
    { key: "beneficiary", label: "Beneficiari" },
    { key: "cluster", label: "Cluster" },
    { key: "basic_kit", label: "Basic/Kit" },
    { key: "proto_n", label: "Proto" },
    { key: "year_2027", label: "2027 (Mesi)" },
    { key: "year_28", label: "28" },
    { key: "year_29", label: "29" },
    { key: "year_30", label: "30" },
    { key: "year_31", label: "31" },
    { key: "status", label: "Stato" },
    { key: "last_update", label: "Last Update" }
];

function getActiveColumnOrder() {
    const table = document.getElementById("main-dms-table");
    if (!table) return DEFAULT_COLUMN_ORDER;
    const headers = table.querySelectorAll("thead th");
    const order = [];
    headers.forEach(th => {
        const colKey = th.getAttribute("data-col");
        if (colKey) order.push(colKey);
    });
    return order.length > 0 ? order : DEFAULT_COLUMN_ORDER;
}

let currentSessionVisibility = null;

function getColumnVisibility() {
    if (currentSessionVisibility !== null) {
        return currentSessionVisibility;
    }
    try {
        const saved = localStorage.getItem("dms_col_visibility");
        if (saved) {
            const parsed = JSON.parse(saved);
            if (typeof parsed === "object" && parsed !== null) {
                currentSessionVisibility = parsed;
                return currentSessionVisibility;
            }
        }
    } catch (e) {}
    const def = {};
    DEFAULT_COLUMN_ORDER.forEach(k => { def[k] = true; });
    currentSessionVisibility = def;
    return currentSessionVisibility;
}

function applyColumnsSession() {
    const grid = document.getElementById("columns-checkbox-grid");
    if (!grid) return;

    const inputs = grid.querySelectorAll("input[type='checkbox']");
    const vis = {};
    let visibleCount = 0;

    inputs.forEach(input => {
        const key = input.getAttribute("data-col");
        if (key) {
            vis[key] = input.checked;
            if (input.checked) visibleCount++;
        }
    });

    if (visibleCount === 0) {
        showToast("Seleziona almeno una colonna visibile!", "warning");
        return;
    }

    // Applica in memoria solo per la sessione attuale (NON sovrascrive localStorage)
    currentSessionVisibility = vis;

    applyColumnVisibility();

    if (allActivities) {
        renderTableRows(allActivities);
    }

    closeColumnsModal();
    showToast("Configurazione applicata alla sessione corrente (non salvata per i prossimi avvii)", "info");
}

function applyColumnVisibility() {
    const vis = getColumnVisibility();
    const table = document.getElementById("main-dms-table");
    if (!table) return;
    const headers = table.querySelectorAll("thead th");
    headers.forEach(th => {
        const colKey = th.getAttribute("data-col");
        if (colKey) {
            if (vis[colKey] === false) {
                th.style.display = "none";
            } else {
                th.style.display = "";
            }
        }
    });
}

function getVisibleColumnOrder() {
    const fullOrder = getActiveColumnOrder();
    const vis = getColumnVisibility();
    return fullOrder.filter(k => vis[k] !== false);
}

function saveColumnOrder() {
    const order = getActiveColumnOrder();
    try {
        localStorage.setItem("dms_col_order", JSON.stringify(order));
    } catch (e) {}
}

function restoreColumnOrder() {
    try {
        const saved = localStorage.getItem("dms_col_order");
        if (!saved) return;
        const order = JSON.parse(saved);
        if (!Array.isArray(order) || order.length === 0) return;

        const table = document.getElementById("main-dms-table");
        if (!table) return;
        const theadTr = table.querySelector("thead tr");
        if (!theadTr) return;
        const currentHeaders = Array.from(theadTr.querySelectorAll("th"));
        const headerMap = {};
        currentHeaders.forEach(th => {
            const key = th.getAttribute("data-col");
            if (key) headerMap[key] = th;
        });

        // Riordina i th secondo l'ordine salvato
        order.forEach(colKey => {
            if (headerMap[colKey]) {
                theadTr.appendChild(headerMap[colKey]);
                delete headerMap[colKey];
            }
        });
        // Aggiungi in coda eventuali nuove colonne non presenti nell'ordine salvato
        Object.values(headerMap).forEach(th => theadTr.appendChild(th));
    } catch (e) {}
}

function initColumnReorder() {
    const table = document.getElementById("main-dms-table");
    if (!table) return;
    const theadTr = table.querySelector("thead tr");
    if (!theadTr) return;
    const headers = theadTr.querySelectorAll("th");

    let draggedTh = null;

    headers.forEach(th => {
        th.setAttribute("draggable", "true");

        th.addEventListener("dragstart", (e) => {
            if (e.target.classList.contains("resizer") || e.target.closest(".th-sort-btn")) {
                e.preventDefault();
                return;
            }
            draggedTh = th;
            th.classList.add("col-dragging");
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", th.getAttribute("data-col") || "");
        });

        th.addEventListener("dragend", () => {
            if (draggedTh) {
                draggedTh.classList.remove("col-dragging");
                draggedTh = null;
            }
            headers.forEach(h => {
                h.classList.remove("col-drag-over-left", "col-drag-over-right");
            });
        });

        th.addEventListener("dragover", (e) => {
            e.preventDefault();
            if (!draggedTh || draggedTh === th) return;
            e.dataTransfer.dropEffect = "move";

            const rect = th.getBoundingClientRect();
            const relX = e.clientX - rect.left;
            const isLeft = relX < (rect.width / 2);

            if (isLeft) {
                th.classList.add("col-drag-over-left");
                th.classList.remove("col-drag-over-right");
            } else {
                th.classList.add("col-drag-over-right");
                th.classList.remove("col-drag-over-left");
            }
        });

        th.addEventListener("dragleave", () => {
            th.classList.remove("col-drag-over-left", "col-drag-over-right");
        });

        th.addEventListener("drop", (e) => {
            e.preventDefault();
            th.classList.remove("col-drag-over-left", "col-drag-over-right");
            if (!draggedTh || draggedTh === th) return;

            const rect = th.getBoundingClientRect();
            const relX = e.clientX - rect.left;
            const insertBefore = relX < (rect.width / 2);

            if (insertBefore) {
                theadTr.insertBefore(draggedTh, th);
            } else {
                theadTr.insertBefore(draggedTh, th.nextSibling);
            }

            saveColumnOrder();
            if (allActivities && allActivities.length > 0) {
                renderTableRows(allActivities);
            }
        });
    });
}

function initColumnResize() {
    const table = document.getElementById("main-dms-table");
    if (!table) return;
    const headers = table.querySelectorAll("th");

    headers.forEach(th => {
        const resizer = th.querySelector(".resizer");
        if (!resizer) return;

        let startX, startWidth;

        resizer.addEventListener("mousedown", (e) => {
            e.preventDefault();
            e.stopPropagation();
            startX = e.pageX;
            startWidth = th.offsetWidth;
            resizer.classList.add("resizing");

            const onMouseMove = (moveEvent) => {
                const delta = moveEvent.pageX - startX;
                const newWidth = Math.max(30, startWidth + delta);
                th.style.width = `${newWidth}px`;
                th.style.minWidth = `${newWidth}px`;
            };

            const onMouseUp = () => {
                document.removeEventListener("mousemove", onMouseMove);
                document.removeEventListener("mouseup", onMouseUp);
                resizer.classList.remove("resizing");
                saveColumnWidths();
            };

            document.addEventListener("mousemove", onMouseMove);
            document.addEventListener("mouseup", onMouseUp);
        });
    });
}

function saveColumnWidths() {
    const headers = document.querySelectorAll("#main-dms-table th");
    const widths = {};
    headers.forEach(th => {
        const colKey = th.getAttribute("data-col");
        if (colKey) {
            widths[colKey] = th.style.width || `${th.offsetWidth}px`;
        }
    });
    try {
        localStorage.setItem("dms_col_widths", JSON.stringify(widths));
    } catch (e) {}
}

function restoreColumnWidths() {
    try {
        const saved = localStorage.getItem("dms_col_widths");
        if (!saved) return;
        const widths = JSON.parse(saved);
        const headers = document.querySelectorAll("#main-dms-table th");
        headers.forEach(th => {
            const colKey = th.getAttribute("data-col");
            if (colKey && widths[colKey]) {
                th.style.width = widths[colKey];
                th.style.minWidth = widths[colKey];
            }
        });
    } catch (e) {}
}

// --- GESTIONE PERSONALIZZAZIONE E PRESET COLONNE ---

function openColumnsModal() {
    const modal = document.getElementById("modal-columns-container");
    const grid = document.getElementById("columns-checkbox-grid");
    if (!modal || !grid) return;

    const vis = getColumnVisibility();
    const currentOrder = getActiveColumnOrder();

    const metaMap = {};
    COLUMN_METADATA.forEach(m => { metaMap[m.key] = m; });

    grid.innerHTML = "";
    currentOrder.forEach(colKey => {
        const meta = metaMap[colKey] || { key: colKey, label: colKey };
        const isChecked = vis[colKey] !== false;

        const label = document.createElement("label");
        label.style.display = "flex";
        label.style.alignItems = "center";
        label.style.gap = "8px";
        label.style.padding = "7px 10px";
        label.style.background = "#ffffff";
        label.style.border = "1px solid var(--border)";
        label.style.borderRadius = "6px";
        label.style.cursor = "pointer";
        label.style.userSelect = "none";
        label.style.fontSize = "12px";
        label.style.transition = "background 0.15s, border-color 0.15s";

        label.innerHTML = `
            <input type="checkbox" data-col="${meta.key}" ${isChecked ? 'checked' : ''} style="cursor: pointer; width: 15px; height: 15px; accent-color: var(--primary);">
            <span style="font-weight: 500; color: var(--text);">${escapeHtml(meta.label)}</span>
        `;
        grid.appendChild(label);
    });

    modal.style.display = "flex";
}

function closeColumnsModal() {
    const modal = document.getElementById("modal-columns-container");
    if (modal) modal.style.display = "none";
}

function setAllColumnsVisibility(checkAll) {
    const grid = document.getElementById("columns-checkbox-grid");
    if (!grid) return;
    const inputs = grid.querySelectorAll("input[type='checkbox']");
    inputs.forEach(input => {
        input.checked = checkAll;
    });
}

function saveColumnsConfig() {
    const grid = document.getElementById("columns-checkbox-grid");
    if (!grid) return;

    const inputs = grid.querySelectorAll("input[type='checkbox']");
    const vis = {};
    let visibleCount = 0;

    inputs.forEach(input => {
        const key = input.getAttribute("data-col");
        if (key) {
            vis[key] = input.checked;
            if (input.checked) visibleCount++;
        }
    });

    if (visibleCount === 0) {
        showToast("Seleziona almeno una colonna visibile!", "warning");
        return;
    }

    // Salva in memoria sessione e in localStorage per sessioni future
    currentSessionVisibility = vis;
    try {
        localStorage.setItem("dms_col_visibility", JSON.stringify(vis));
    } catch (e) {}

    saveColumnOrder();
    saveColumnWidths();

    applyColumnVisibility();

    if (allActivities) {
        renderTableRows(allActivities);
    }

    closeColumnsModal();
    showToast("Configurazione salvata per le sessioni future", "success");
}

function resetColumnsConfig() {
    try {
        localStorage.removeItem("dms_col_order");
        localStorage.removeItem("dms_col_widths");
        localStorage.removeItem("dms_col_visibility");
    } catch (e) {}

    // Ripristina stato visibilità sessione
    const def = {};
    DEFAULT_COLUMN_ORDER.forEach(k => { def[k] = true; });
    currentSessionVisibility = def;

    // 1. Ripristina ordine di default nel DOM thead
    const table = document.getElementById("main-dms-table");
    if (table) {
        const theadTr = table.querySelector("thead tr");
        if (theadTr) {
            const currentHeaders = Array.from(theadTr.querySelectorAll("th"));
            const headerMap = {};
            currentHeaders.forEach(th => {
                const key = th.getAttribute("data-col");
                if (key) headerMap[key] = th;
            });
            DEFAULT_COLUMN_ORDER.forEach(colKey => {
                if (headerMap[colKey]) {
                    theadTr.appendChild(headerMap[colKey]);
                }
            });
        }

        // 2. Ripristina larghezze di default e mostra tutte le colonne
        const headers = table.querySelectorAll("thead th");
        headers.forEach(th => {
            const colKey = th.getAttribute("data-col");
            if (colKey && DEFAULT_COLUMN_WIDTHS[colKey]) {
                th.style.width = DEFAULT_COLUMN_WIDTHS[colKey];
                th.style.minWidth = DEFAULT_COLUMN_WIDTHS[colKey];
            }
            th.style.display = "";
        });
    }

    // 3. Ridisegna la tabella con tutte le colonne visibili nel loro ordine originale
    if (allActivities) {
        renderTableRows(allActivities);
    }

    closeColumnsModal();
    showToast("Configurazione predefinita ripristinata", "info");
}

// --- CONFIGURAZIONE & CARTELLA RETE ---

async function loadConfig() {
    try {
        const res = await fetch("/api/config");
        const cfg = await res.json();
        const display = document.getElementById("topbar-folder-display");
        const dir = cfg.shared_data_dir || "Non configurata";
        display.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
            <span>Dati: ${dir}</span>
        `;
        display.title = dir;

        if (!cfg.is_configured) {
            openConfigModal();
        }
    } catch (err) {
        console.error("Errore caricamento configurazione:", err);
    }
}

function openConfigModal() {
    fetch("/api/config")
        .then(r => r.json())
        .then(cfg => {
            document.getElementById("config-folder-input").value = cfg.shared_data_dir || "";
            document.getElementById("config-status-msg").textContent = "";
            document.getElementById("modal-config-container").style.display = "flex";
        });
}

function closeConfigModal() {
    document.getElementById("modal-config-container").style.display = "none";
}

async function browseFolderDialog() {
    try {
        const res = await fetch("/api/choose_folder_dialog", { method: "POST" });
        const data = await res.json();
        if (data.selected_dir) {
            document.getElementById("config-folder-input").value = data.selected_dir;
        }
    } catch (err) {
        console.error("Errore apertura dialog:", err);
    }
}

async function saveSharedConfig() {
    const inputDir = document.getElementById("config-folder-input").value.trim();
    if (!inputDir) {
        alert("Inserisci un percorso valido.");
        return;
    }

    try {
        const res = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ shared_data_dir: inputDir })
        });
        const data = await res.json();
        if (data.success) {
            closeConfigModal();
            await loadConfig();
            await loadLookups();
            await reloadTable();
        } else {
            alert("Errore salvataggio: " + (data.error || ""));
        }
    } catch (err) {
        showToast("Errore connessione server: " + err, "error");
    }
}

// --- LOOKUPS ---

async function loadLookups() {
    try {
        const res = await fetch("/api/lookups");
        currentLookups = await res.json();
        populateFilterDropdowns();
    } catch (err) {
        console.error("Errore caricamento lookups:", err);
    }
}


// --- GESTORE FILTRI MULTI-SELEZIONE (UNO O PIU ELEMENTI PER GRUPPO) ---

const activeMultiFilters = {
    year: new Set(),
    urgency: new Set(),
    beneficiary: new Set(),
    cluster: new Set(),
    pm: new Set(),
    proto: new Set()
};

const MULTI_FILTER_CONFIG = {
    year: { label: "Anno", defaultText: "Anno (Tutti)" },
    urgency: { label: "Urgenza", defaultText: "Urgenza (Tutte)" },
    beneficiary: { label: "Beneficiari", defaultText: "Beneficiari (Tutti)" },
    cluster: { label: "Cluster", defaultText: "Cluster (Tutti)" },
    pm: { label: "PM", defaultText: "PM (Tutti)" },
    proto: { label: "Proto", defaultText: "Proto (Tutti)" }
};

function toggleMultiSelectMenu(group, event) {
    if (event) event.stopPropagation();
    const groupEl = document.getElementById(`ms-group-${group}`);
    if (!groupEl) return;
    const isOpen = groupEl.classList.contains("open");
    closeAllMultiSelects();
    if (!isOpen) {
        groupEl.classList.add("open");
    }
}

function closeAllMultiSelects() {
    let closedAny = false;
    document.querySelectorAll(".multiselect-dropdown.open").forEach(el => {
        el.classList.remove("open");
        closedAny = true;
    });
    return closedAny;
}

function initMultiFilters() {
    renderMultiFilterOptions("year", ["2027", "2028", "2029", "2030", "2031"]);
    renderMultiFilterOptions("urgency", ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINOR"]);
}

function populateFilterDropdowns() {
    initMultiFilters();
    renderMultiFilterOptions("beneficiary", (currentLookups.beneficiary || []).map(x => x.name));
    renderMultiFilterOptions("cluster", (currentLookups.cluster || []).map(x => x.name));
    renderMultiFilterOptions("pm", (currentLookups.person || []).map(x => x.name));
    renderMultiFilterOptions("proto", (currentLookups.proto || []).map(x => x.name));
}

function renderMultiFilterOptions(group, items) {
    const container = document.getElementById(`ms-options-${group}`);
    if (!container) return;

    const currentSelected = activeMultiFilters[group] || new Set();
    container.innerHTML = "";

    if (!items || items.length === 0) {
        container.innerHTML = `<div style="padding: 8px 12px; font-size: 11px; color: var(--text-muted); text-align: center;">Nessun elemento</div>`;
        return;
    }

    let sortedItems = [...items];
    if (group !== "year" && group !== "urgency") {
        sortedItems.sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' }));
    }

    sortedItems.forEach(val => {
        const isChecked = currentSelected.has(val);
        const label = document.createElement("label");
        label.className = "multiselect-option";

        let contentHtml = `<span class="ms-opt-text">${escapeHtml(val)}</span>`;
        if (group === "urgency") {
            contentHtml = `<span class="badge-urg-${val}" style="padding: 1px 6px; border-radius: 4px; font-weight: 700; font-size: 10.5px;">${escapeHtml(val)}</span>`;
        }

        label.innerHTML = `
            <input type="checkbox" value="${escapeHtml(val)}" ${isChecked ? 'checked' : ''} onchange="onMultiFilterOptionChange('${group}', '${escapeHtml(val)}', this.checked)">
            ${contentHtml}
        `;
        container.appendChild(label);
    });

    updateMultiFilterTrigger(group);
}

function onMultiFilterOptionChange(group, val, isChecked) {
    if (isChecked) {
        activeMultiFilters[group].add(val);
    } else {
        activeMultiFilters[group].delete(val);
    }
    updateMultiFilterTrigger(group);
    reloadTable();
}

function updateMultiFilterTrigger(group) {
    const trigger = document.getElementById(`ms-trigger-${group}`);
    const labelSpan = document.getElementById(`ms-label-${group}`);
    if (!trigger || !labelSpan) return;

    const set = activeMultiFilters[group];
    const cfg = MULTI_FILTER_CONFIG[group];

    if (!set || set.size === 0) {
        trigger.classList.remove("active-filter");
        labelSpan.textContent = cfg.defaultText;
    } else if (set.size === 1) {
        trigger.classList.add("active-filter");
        const val = Array.from(set)[0];
        labelSpan.innerHTML = `${cfg.label}: <strong>${escapeHtml(val)}</strong>`;
    } else if (set.size === 2) {
        trigger.classList.add("active-filter");
        const arr = Array.from(set);
        labelSpan.innerHTML = `${cfg.label}: ${escapeHtml(arr[0])}, ${escapeHtml(arr[1])}`;
    } else {
        trigger.classList.add("active-filter");
        labelSpan.innerHTML = `${cfg.label} <span class="ms-badge-count">${set.size}</span>`;
    }
}

function selectAllInGroup(group) {
    const container = document.getElementById(`ms-options-${group}`);
    if (!container) return;
    const inputs = container.querySelectorAll("input[type='checkbox']");
    inputs.forEach(inp => {
        inp.checked = true;
        activeMultiFilters[group].add(inp.value);
    });
    updateMultiFilterTrigger(group);
    reloadTable();
}

function clearGroup(group) {
    const container = document.getElementById(`ms-options-${group}`);
    if (!container) return;
    const inputs = container.querySelectorAll("input[type='checkbox']");
    inputs.forEach(inp => {
        inp.checked = false;
    });
    activeMultiFilters[group].clear();
    updateMultiFilterTrigger(group);
    reloadTable();
}


function populateSelect(elemId, items, placeholder) {
    const sel = document.getElementById(elemId);
    if (!sel) return;
    const currVal = sel.value;
    sel.innerHTML = `<option value="">${placeholder}</option>`;
    items.forEach(it => {
        const opt = document.createElement("option");
        opt.value = it.name;
        opt.textContent = it.name;
        sel.appendChild(opt);
    });
    sel.value = currVal;
}

// --- DATA TABLE RENDERING ---

function debounceReload() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(reloadTable, 200);
}

function toggleExpiringFilter() {
    isExpiringFilterActive = !isExpiringFilterActive;
    const btn = document.getElementById("btn-expiring");
    if (isExpiringFilterActive) {
        btn.classList.add("active-badge");
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg> Scadenze Attive (5gg)`;
    } else {
        btn.classList.remove("active-badge");
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg> Azioni in scadenza (5gg)`;
    }
    reloadTable();
}

function getFilterParams() {
    const params = new URLSearchParams();

    // VIEW SETUP
    const typeExcludes = [];
    if (!document.getElementById("vs-type-project").checked) typeExcludes.push("Project");
    if (!document.getElementById("vs-type-task").checked) typeExcludes.push("Task");
    if (!document.getElementById("vs-type-idea").checked) typeExcludes.push("Idea");
    if (!document.getElementById("vs-type-discussion").checked) typeExcludes.push("Discussion");
    typeExcludes.forEach(t => params.append("type_exclude", t));

    const statusExcludes = [];
    if (document.getElementById("vs-hide-closed").checked) statusExcludes.push("Closed");
    if (document.getElementById("vs-hide-cancelled").checked) statusExcludes.push("Cancelled");
    if (document.getElementById("vs-hide-onhold").checked) statusExcludes.push("On Hold");
    if (document.getElementById("vs-hide-rejected").checked) statusExcludes.push("Rejected");
    statusExcludes.forEach(s => params.append("status_exclude", s));

    // Urgenza e gli altri filtri raggruppati sono gestiti dinamicamente via activeMultiFilters
    if (typeof activeMultiFilters !== 'undefined') {
        activeMultiFilters.year.forEach(y => params.append("year", y));
        activeMultiFilters.urgency.forEach(u => params.append("urgency", u));
        activeMultiFilters.beneficiary.forEach(b => params.append("beneficiary", b));
        activeMultiFilters.cluster.forEach(c => params.append("cluster", c));
        activeMultiFilters.pm.forEach(p => params.append("pm", p));
        activeMultiFilters.proto.forEach(pr => params.append("proto", pr));
    }

    const search = document.getElementById("global-search").value.trim();
    if (search) params.set("search", search);

    if (isExpiringFilterActive) {
        params.set("expiring_in_5_days", "true");
    }




    return params;
}

async function reloadTable() {
    const params = getFilterParams();

    try {
        const res = await fetch(`/api/activities?${params.toString()}`);
        let activities = await res.json();

        // FILTRO MULTI-SELEZIONE: ANNO (logica OR tra gli anni selezionati)
        if (activeMultiFilters.year.size > 0) {
            const years = Array.from(activeMultiFilters.year);
            activities = activities.filter(a => {
                return years.some(y => {
                    if (y === "2027") return a.year_2027 && a.year_2027.trim() !== "";
                    if (y === "2028") return a.year_28 == 1;
                    if (y === "2029") return a.year_29 == 1;
                    if (y === "2030") return a.year_30 == 1;
                    if (y === "2031") return a.year_31 == 1;
                    return false;
                });
            });
        }

        // FILTRO MULTI-SELEZIONE: URGENZA
        if (activeMultiFilters.urgency.size > 0) {
            activities = activities.filter(a => activeMultiFilters.urgency.has(a.urgency));
        }

        // FILTRO MULTI-SELEZIONE: BENEFICIARY
        if (activeMultiFilters.beneficiary.size > 0) {
            activities = activities.filter(a => activeMultiFilters.beneficiary.has(a.beneficiary));
        }

        // FILTRO MULTI-SELEZIONE: CLUSTER
        if (activeMultiFilters.cluster.size > 0) {
            activities = activities.filter(a => activeMultiFilters.cluster.has(a.cluster));
        }

        // FILTRO MULTI-SELEZIONE: PM
        if (activeMultiFilters.pm.size > 0) {
            activities = activities.filter(a => activeMultiFilters.pm.has(a.pm));
        }

        // FILTRO MULTI-SELEZIONE: PROTO
        if (activeMultiFilters.proto.size > 0) {
            activities = activities.filter(a => activeMultiFilters.proto.has(a.proto_n));
        }

        sortActivities(activities, currentSortCol, currentSortDir);
        allActivities = activities;
        renderTableRows(activities);
        updateSortIndicators();
        const statsBadge = document.getElementById("table-stats-badge");
        if (statsBadge) {
            statsBadge.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg> ${activities.length} attività`;
        }
    } catch (err) {
        console.error("Errore caricamento tabella:", err);
    }
}

function buildCellHtml(colKey, act, formattedId, allowedStatuses) {
    switch (colKey) {
        case "actions":
            return `
                <td style="text-align: center;">
                    <div class="row-actions-flex">
                        <button class="btn-row-action btn-row-open" onclick="openIdModal(${act.id})" title="Apri scheda dettaglio">
                            OPEN
                        </button>
                        <button class="btn-row-action btn-row-cancel" onclick="handleCancelActivity(${act.id})" title="Imposta su Cancelled">
                            CANCEL
                        </button>
                        <button class="btn-row-action btn-row-folder" onclick="handleOpenFolder(${act.id})" title="Apri cartella Windows">
                            FOLDER
                        </button>
                    </div>
                </td>
            `;
        case "id":
            return `<td><span class="badge-id">${formattedId}</span></td>`;
        case "urgency":
            return `
                <td>
                    <select class="select-modern badge-urg-${act.urgency}" style="font-weight: 700; border: none; padding: 2px 4px;" onchange="saveInlineField(${act.id}, 'urgency', this.value, this); this.className='select-modern badge-urg-' + this.value;">
                        ${["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINOR"].map(u => 
                            `<option value="${u}" ${act.urgency === u ? 'selected' : ''}>${u}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
        case "drivers":
            return `
                <td style="color: var(--text-secondary); font-size: 11px;" title="${act.drivers_str || ''}">
                    ${act.drivers_str || '-'}
                </td>
            `;
        case "odg":
            return `
                <td style="text-align: center;">
                    <input type="checkbox" ${act.odg === 'Y' ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'odg', this.checked ? 'Y' : 'N', this)">
                </td>
            `;
        case "title":
            return `
                <td>
                    <input type="text" class="cell-input cell-title-text" value="${escapeHtml(act.title)}" onchange="saveInlineField(${act.id}, 'title', this.value, this)">
                </td>
            `;
        case "type":
            return `
                <td>
                    <select class="select-modern badge-type-${act.type}" style="font-weight: 600; border: none; padding: 2px 4px;" onchange="handleTypeChangeInline(${act.id}, this.value)">
                        ${["Project", "Task", "Idea", "Discussion"].map(t => 
                            `<option value="${t}" ${act.type === t ? 'selected' : ''}>${t}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
        case "relevancy":
            return `
                <td style="text-align: center;">
                    <select class="cell-input" style="text-align: center; font-weight: 600;" onchange="saveInlineField(${act.id}, 'relevancy', this.value, this)">
                        ${[1, 2, 3, 4, 5].map(r => 
                            `<option value="${r}" ${act.relevancy == r ? 'selected' : ''}>${r}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
        case "pm":
            return `
                <td>
                    <select class="cell-input" onchange="saveInlineField(${act.id}, 'pm', this.value, this)">
                        <option value="">--</option>
                        ${(currentLookups.person || []).map(p => 
                            `<option value="${p.name}" ${act.pm === p.name ? 'selected' : ''}>${p.name}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
        case "pe":
            return `
                <td>
                    <select class="cell-input" onchange="saveInlineField(${act.id}, 'pe', this.value, this)">
                        <option value="">--</option>
                        ${(currentLookups.person || []).map(p => 
                            `<option value="${p.name}" ${act.pe === p.name ? 'selected' : ''}>${p.name}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
        case "beneficiary":
            return `
                <td>
                    <select class="cell-input" onchange="saveInlineField(${act.id}, 'beneficiary', this.value, this)">
                        <option value="">--</option>
                        ${(currentLookups.beneficiary || []).map(b => 
                            `<option value="${b.name}" ${act.beneficiary === b.name ? 'selected' : ''}>${b.name}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
        case "cluster":
            return `
                <td>
                    <select class="cell-input" onchange="saveInlineField(${act.id}, 'cluster', this.value, this)">
                        <option value="">--</option>
                        ${(currentLookups.cluster || []).map(c => 
                            `<option value="${c.name}" ${act.cluster === c.name ? 'selected' : ''}>${c.name}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
        case "basic_kit":
            return `
                <td>
                    <select class="cell-input" onchange="saveInlineField(${act.id}, 'basic_kit', this.value, this)">
                        <option value="Basic" ${act.basic_kit === 'Basic' ? 'selected' : ''}>Basic</option>
                        <option value="Kit" ${act.basic_kit === 'Kit' ? 'selected' : ''}>Kit</option>
                    </select>
                </td>
            `;
        case "proto_n":
            return `
                <td>
                    <select class="cell-input" onchange="saveInlineField(${act.id}, 'proto_n', this.value, this)">
                        <option value="">--</option>
                        ${(currentLookups.proto || []).map(pr => 
                            `<option value="${pr.name}" ${act.proto_n === pr.name ? 'selected' : ''}>${pr.name}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
        case "year_2027":
            return `
                <td>
                    <input type="text" class="cell-input" value="${escapeHtml(act.year_2027 || '')}" placeholder="Mesi..." onchange="saveInlineField(${act.id}, 'year_2027', this.value, this)">
                </td>
            `;
        case "year_28":
            return `
                <td style="text-align: center;">
                    <input type="checkbox" ${act.year_28 == 1 ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'year_28', this.checked ? 1 : 0, this)">
                </td>
            `;
        case "year_29":
            return `
                <td style="text-align: center;">
                    <input type="checkbox" ${act.year_29 == 1 ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'year_29', this.checked ? 1 : 0, this)">
                </td>
            `;
        case "year_30":
            return `
                <td style="text-align: center;">
                    <input type="checkbox" ${act.year_30 == 1 ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'year_30', this.checked ? 1 : 0, this)">
                </td>
            `;
        case "year_31":
            return `
                <td style="text-align: center;">
                    <input type="checkbox" ${act.year_31 == 1 ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'year_31', this.checked ? 1 : 0, this)">
                </td>
            `;
        case "status":
            return `
                <td>
                    <select class="cell-input" style="font-weight: 500;" id="inline-status-${act.id}" onchange="saveInlineField(${act.id}, 'status', this.value, this)">
                        ${allowedStatuses.map(s => 
                            `<option value="${s}" ${act.status === s ? 'selected' : ''}>${s}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
        case "last_update":
            return `<td style="color: var(--text-muted); font-size: 10.5px;">${act.last_update || '-'}</td>`;
        default:
            return `<td></td>`;
    }
}

function renderTableRows(activities) {
    const tbody = document.getElementById("activities-table-body");
    tbody.innerHTML = "";

    const visibleOrder = getVisibleColumnOrder();

    if (activities.length === 0) {
        const colSpan = Math.max(1, visibleOrder.length);
        tbody.innerHTML = `<tr><td colspan="${colSpan}" style="text-align:center; padding: 32px; color: var(--text-muted); font-size: 13px;">Nessuna attività trovata con i filtri attuali.</td></tr>`;
        return;
    }

    activities.forEach(act => {
        const tr = document.createElement("tr");




        const formattedId = String(act.id).padStart(5, '0');
        const allowedStatuses = TYPE_STATUS_MAP[act.type] || [];

        let rowHtml = "";
        visibleOrder.forEach(colKey => {
            rowHtml += buildCellHtml(colKey, act, formattedId, allowedStatuses);
        });

        tr.innerHTML = rowHtml;
        tbody.appendChild(tr);
    });
}

// --- ORDINAMENTO CLIENT-SIDE PER COLONNE (R3) ---

function sortActivities(arr, colKey, dir) {
    if (!arr || arr.length === 0 || !colKey) return arr;
    const factor = dir === "asc" ? 1 : -1;

    arr.sort((a, b) => {
        let cmp = 0;
        switch (colKey) {
            case "id":
                cmp = (Number(a.id) || 0) - (Number(b.id) || 0);
                break;
            case "urgency": {
                const uMap = { "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "MINOR": 5 };
                const rankA = uMap[a.urgency] || 99;
                const rankB = uMap[b.urgency] || 99;
                cmp = rankA - rankB;
                break;
            }
            case "relevancy":
                cmp = (Number(a.relevancy) || 0) - (Number(b.relevancy) || 0);
                break;
            case "odg": {
                const valA = a.odg === "Y" ? 1 : 0;
                const valB = b.odg === "Y" ? 1 : 0;
                cmp = valA - valB;
                break;
            }
            case "year_28":
                cmp = (Number(a.year_28) || 0) - (Number(b.year_28) || 0);
                break;
            case "year_29":
                cmp = (Number(a.year_29) || 0) - (Number(b.year_29) || 0);
                break;
            case "year_30":
                cmp = (Number(a.year_30) || 0) - (Number(b.year_30) || 0);
                break;
            case "year_31":
                cmp = (Number(a.year_31) || 0) - (Number(b.year_31) || 0);
                break;
            case "drivers": {
                const strA = (a.drivers_str || a.drivers || "").trim();
                const strB = (b.drivers_str || b.drivers || "").trim();
                cmp = strA.localeCompare(strB, undefined, { numeric: true, sensitivity: "base" });
                break;
            }
            case "last_update": {
                const dateA = a.last_update || "";
                const dateB = b.last_update || "";
                cmp = dateA.localeCompare(dateB);
                break;
            }
            case "title":
            case "type":
            case "pm":
            case "pe":
            case "beneficiary":
            case "cluster":
            case "basic_kit":
            case "proto_n":
            case "year_2027":
            case "status":
            default: {
                const valA = (a[colKey] != null ? String(a[colKey]) : "").trim();
                const valB = (b[colKey] != null ? String(b[colKey]) : "").trim();
                cmp = valA.localeCompare(valB, undefined, { numeric: true, sensitivity: "base" });
                break;
            }
        }
        if (cmp !== 0) {
            return cmp * factor;
        }
        return (Number(a.id) || 0) - (Number(b.id) || 0);
    });

    return arr;
}

function handleSort(colKey, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    if (!colKey || colKey === "actions") return;

    if (currentSortCol === colKey) {
        currentSortDir = currentSortDir === "asc" ? "desc" : "asc";
    } else {
        currentSortCol = colKey;
        currentSortDir = "asc";
    }

    if (allActivities && allActivities.length > 0) {
        sortActivities(allActivities, currentSortCol, currentSortDir);
        renderTableRows(allActivities);
    }
    updateSortIndicators();
}

function updateSortIndicators() {
    const table = document.getElementById("main-dms-table");
    if (!table) return;
    const headers = table.querySelectorAll("thead th");
    headers.forEach(th => {
        const colKey = th.getAttribute("data-col");
        if (!colKey || colKey === "actions") return;

        const sortBtn = th.querySelector(".th-sort-btn");
        const icon = th.querySelector(".sort-icon");

        th.classList.remove("th-sorted-asc", "th-sorted-desc");
        if (sortBtn) sortBtn.classList.remove("active");

        if (colKey === currentSortCol) {
            th.classList.add(currentSortDir === "asc" ? "th-sorted-asc" : "th-sorted-desc");
            if (sortBtn) {
                sortBtn.classList.add("active");
                sortBtn.title = `Ordinato per ${colKey} (${currentSortDir === "asc" ? "Crescente" : "Decrescente"}) - Clicca per invertire`;
            }
            if (icon) {
                icon.textContent = currentSortDir === "asc" ? "▲" : "▼";
            }
        } else {
            if (sortBtn) {
                sortBtn.title = `Ordina per ${colKey}`;
            }
            if (icon) {
                icon.textContent = "▲";
            }
        }
    });
}

async function saveInlineField(activityId, fieldName, value, eventTarget = null) {
    try {
        const res = await fetch(`/api/activities/${activityId}/field`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ field: fieldName, value: value })
        });
        const data = await res.json();
        if (data.success) {
            const item = (allActivities || []).find(a => a.id === activityId);
            if (item) item[fieldName] = value;
            if (eventTarget) {
                eventTarget.classList.add("saving-flash");
                setTimeout(() => eventTarget.classList.remove("saving-flash"), 400);
            }
        } else {
            showToast("Errore salvataggio campo: " + (data.error || ""), "error");
        }
    } catch (err) {
        showToast("Errore di connessione durante il salvataggio", "error");
        console.error("Errore salvataggio inline:", err);
    }
}

async function handleTypeChangeInline(activityId, newType) {
    await saveInlineField(activityId, 'type', newType);
    reloadTable();
}

async function handleNewId() {
    try {
        const res = await fetch("/api/activities/new", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            await reloadTable();
            openIdModal(data.id);
        }
    } catch (err) {
        showToast("Errore creazione nuovo ID: " + err, "error");
    }
}

async function handleCancelActivity(activityId) {
    if (confirm(`Sei sicuro di voler contrassegnare come Cancelled l'ID ${String(activityId).padStart(5, '0')}?`)) {
        try {
            const res = await fetch(`/api/activities/${activityId}/cancel`, { method: "POST" });
            const data = await res.json();
            if (data.success) {
                reloadTable();
            }
        } catch (err) {
            showToast("Errore operazione: " + err, "error");
        }
    }
}

async function handleOpenFolder(activityId) {
    try {
        const res = await fetch(`/api/activities/${activityId}/folder`, { method: "POST" });
        const data = await res.json();
        if (!data.success) {
            showToast("Errore apertura cartella: " + (data.error || ""), "error");
        }
    } catch (err) {
        showToast("Errore connessione server: " + err, "error");
    }
}

// --- MODAL SINGOLO ID ---

async function openIdModal(activityId) {
    currentActivityId = activityId;
    try {
        const res = await fetch(`/api/activities/${activityId}`);
        const act = await res.json();
        if (!act) return;

        updateNavCounter();

        const formattedId = String(act.id).padStart(5, '0');
        document.getElementById("modal-badge-id").textContent = `ID ${formattedId}`;
        document.getElementById("modal-input-title").value = act.title || "";
        document.getElementById("modal-check-odg").checked = act.odg === 'Y';
        document.getElementById("modal-check-safety").checked = act.safety == 1;
        document.getElementById("modal-last-update-display").textContent = `Aggiornato il: ${act.last_update || '-'}`;

        document.getElementById("modal-select-type").value = act.type || "Project";
        onTypeChangeModal(act.status);

        document.getElementById("modal-select-urgency").value = act.urgency || "MEDIUM";
        document.getElementById("modal-select-relevancy").value = act.relevancy || 3;
        document.getElementById("modal-select-basic-kit").value = act.basic_kit || "Basic";
        document.getElementById("modal-input-supplier").value = act.supplier || "";

        populateModalSelect("modal-select-pm", currentLookups.person || [], act.pm);
        populateModalSelect("modal-select-pe", currentLookups.person || [], act.pe);
        populateModalSelect("modal-select-beneficiary", currentLookups.beneficiary || [], act.beneficiary);
        populateModalSelect("modal-select-cluster", currentLookups.cluster || [], act.cluster);
        populateModalSelect("modal-select-proto", currentLookups.proto || [], act.proto_n);

        document.getElementById("modal-input-year27").value = act.year_2027 || "";
        document.getElementById("modal-check-year28").checked = act.year_28 == 1;
        document.getElementById("modal-check-year29").checked = act.year_29 == 1;
        document.getElementById("modal-check-year30").checked = act.year_30 == 1;
        document.getElementById("modal-check-year31").checked = act.year_31 == 1;

        renderMultiChecks("modal-container-drivers", currentLookups.driver || [], act.drivers || []);
        renderMultiChecks("modal-container-streams", currentLookups.stream || [], act.streams || []);
        renderMultiChecks("modal-container-platforms", currentLookups.platform || [], act.platforms || []);

        document.getElementById("editor-notes_actions").innerHTML = act.notes_actions || "";
        document.getElementById("editor-plan_deliverables").innerHTML = act.plan_deliverables || "";
        renderTeamTable(act.team || []);

        document.getElementById("modal-input-clarity").value = act.clarity || "";
        document.getElementById("modal-input-ispi").value = act.ispi || "";
        document.getElementById("modal-input-other_id").value = act.other_id || "";
        document.getElementById("modal-input-bcr").value = act.bcr || "";
        document.getElementById("modal-input-cr").value = act.cr || "";
        document.getElementById("modal-input-qsd").value = act.qsd || "";
        document.getElementById("modal-input-ndc").value = act.ndc || "";
        document.getElementById("modal-input-wbs_code").value = act.wbs_code || "";
        document.getElementById("modal-input-wbs_description").value = act.wbs_description || "";
        document.getElementById("editor-booking_n").innerHTML = act.booking_n || "";
        document.getElementById("editor-rda_record").innerHTML = act.rda_record || "";

        renderActionsTable(act.actions || []);

        document.getElementById("modal-select-afc1").value = act.afc1 || "";
        document.getElementById("modal-select-afc2").value = act.afc2 || "";
        renderAfcMatrix(act.afc || {});

        switchModalTab('execution');
        document.getElementById("modal-id-container").style.display = "flex";
    } catch (err) {
        showToast("Errore apertura scheda: " + err, "error");
    }
}

function updateNavCounter() {
    const idx = allActivities.findIndex(a => a.id === currentActivityId);
    const counterDisplay = document.getElementById("nav-counter-display");
    const prevBtn = document.getElementById("btn-prev-id");
    const nextBtn = document.getElementById("btn-next-id");

    if (idx >= 0) {
        counterDisplay.textContent = `${idx + 1} di ${allActivities.length}`;
        prevBtn.disabled = idx === 0;
        nextBtn.disabled = idx === allActivities.length - 1;
    } else {
        counterDisplay.textContent = "";
        prevBtn.disabled = true;
        nextBtn.disabled = true;
    }
}

function navigateId(delta) {
    const idx = allActivities.findIndex(a => a.id === currentActivityId);
    if (idx >= 0) {
        const newIdx = idx + delta;
        if (newIdx >= 0 && newIdx < allActivities.length) {
            openIdModal(allActivities[newIdx].id);
        }
    }
}

function closeIdModal() {
    document.getElementById("modal-id-container").style.display = "none";
    reloadTable();
}

function onTypeChangeModal(selectedStatus = null) {
    const curType = document.getElementById("modal-select-type").value;
    const statusSelect = document.getElementById("modal-select-status");
    const allowed = TYPE_STATUS_MAP[curType] || [];

    statusSelect.innerHTML = "";
    allowed.forEach(st => {
        const opt = document.createElement("option");
        opt.value = st;
        opt.textContent = st;
        statusSelect.appendChild(opt);
    });

    if (selectedStatus && allowed.includes(selectedStatus)) {
        statusSelect.value = selectedStatus;
    } else if (allowed.length > 0) {
        statusSelect.value = allowed[0];
    }
}

function populateModalSelect(elemId, items, selectedVal) {
    const sel = document.getElementById(elemId);
    sel.innerHTML = `<option value="">-- Seleziona --</option>`;
    items.forEach(it => {
        const opt = document.createElement("option");
        opt.value = it.name;
        opt.textContent = it.name;
        if (it.name === selectedVal) opt.selected = true;
        sel.appendChild(opt);
    });
}

function renderMultiChecks(containerId, lookupItems, activeItems) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";
    lookupItems.forEach(it => {
        const isChecked = activeItems.includes(it.name);
        const label = document.createElement("label");
        label.className = "toggle-wrapper";
        label.style.fontSize = "11px";
        label.innerHTML = `
            <input type="checkbox" value="${escapeHtml(it.name)}" ${isChecked ? 'checked' : ''}>
            <span class="toggle-track" style="width:24px; height:14px;"><span class="toggle-thumb" style="width:10px; height:10px;"></span></span>
            <span>${escapeHtml(it.name)}</span>
        `;
        container.appendChild(label);
    });
}

function getSelectedMultiChecks(containerId) {
    const checkboxes = document.querySelectorAll(`#${containerId} input[type="checkbox"]:checked`);
    return Array.from(checkboxes).map(cb => cb.value);
}

// TAB NAVIGATION
function switchModalTab(tabName) {
    const tabs = ['execution', 'masterdata', 'actionlog', 'afc'];
    tabs.forEach(t => {
        const pane = document.getElementById(`tab-${t}`);
        if (pane) pane.style.display = (t === tabName) ? 'block' : 'none';
    });

    const buttons = document.querySelectorAll(".modal-tabs-header .tab-pill");
    buttons.forEach((btn, idx) => {
        btn.classList.toggle('active', tabs[idx] === tabName);
    });
}

// RICH TEXT
function execCmd(editorId, command) {
    document.getElementById(`editor-${editorId}`).focus();
    document.execCommand(command, false, null);
}

function execCmdColor(editorId, command, color) {
    document.getElementById(`editor-${editorId}`).focus();
    document.execCommand(command, false, color);
}

// TEAM TABLE
function renderTeamTable(teamList) {
    const tbody = document.getElementById("team-table-body");
    tbody.innerHTML = "";
    teamList.forEach(tm => addTeamRow(tm.function_name, tm.person_name));
}

function addTeamRow(functionName = "", personName = "") {
    const tbody = document.getElementById("team-table-body");
    const tr = document.createElement("tr");

    const functionOptions = (currentLookups.function || []).map(f => 
        `<option value="${f.name}" ${f.name === functionName ? 'selected' : ''}>${f.name}</option>`
    ).join('');

    const personOptions = (currentLookups.person || []).map(p => 
        `<option value="${p.name}" ${p.name === personName ? 'selected' : ''}>${p.name}</option>`
    ).join('');

    tr.innerHTML = `
        <td>
            <select class="select-modern team-func-select" style="width: 100%;">
                <option value="">-- Seleziona Funzione --</option>
                ${functionOptions}
            </select>
        </td>
        <td>
            <select class="select-modern team-person-select" style="width: 100%;">
                <option value="">-- Seleziona Persona --</option>
                ${personOptions}
            </select>
        </td>
        <td style="text-align: center;">
            <button type="button" class="btn-row-action btn-row-cancel" onclick="this.closest('tr').remove()">&#10005;</button>
        </td>
    `;
    tbody.appendChild(tr);
}

function getTeamData() {
    const rows = document.querySelectorAll("#team-table-body tr");
    const list = [];
    rows.forEach(r => {
        const func = r.querySelector(".team-func-select").value;
        const pers = r.querySelector(".team-person-select").value;
        if (func || pers) {
            list.push({ function_name: func, person_name: pers });
        }
    });
    return list;
}

// ACTIONS TABLE
function renderActionsTable(actions) {
    const tbody = document.getElementById("actions-table-body");
    tbody.innerHTML = "";
    actions.forEach(act => addActionRow(act));
}

function addActionRow(actionData = null) {
    const tbody = document.getElementById("actions-table-body");
    const tr = document.createElement("tr");

    const actText = actionData ? actionData.action_text : "";
    const actOwner = actionData ? actionData.owner : "";
    const actStatus = actionData ? actionData.status : "OPEN";
    const actDate = actionData ? actionData.target_date : "";

    if (actDate && actStatus !== 'CLOSED') {
        const in5Days = new Date(Date.now() + 5 * 86400000).toISOString().split('T')[0];
        if (actDate <= in5Days) {
            tr.style.backgroundColor = "var(--warning-light)";
        }
    }

    const ownerOptions = (currentLookups.person || []).map(p => 
        `<option value="${p.name}" ${p.name === actOwner ? 'selected' : ''}>${p.name}</option>`
    ).join('');

    tr.innerHTML = `
        <td>
            <input type="text" class="cell-input action-text-input" style="border: 1px solid var(--border);" value="${escapeHtml(actText)}">
        </td>
        <td>
            <select class="select-modern action-owner-select" style="width: 100%;">
                <option value="">-- Owner --</option>
                ${ownerOptions}
            </select>
        </td>
        <td>
            <select class="select-modern action-status-select" style="width: 100%;">
                ${["OPEN", "ON GOING", "NEXT", "ON HOLD", "CLOSED"].map(s => 
                    `<option value="${s}" ${s === actStatus ? 'selected' : ''}>${s}</option>`
                ).join('')}
            </select>
        </td>
        <td>
            <input type="date" class="cell-input action-date-input" style="border: 1px solid var(--border);" value="${actDate}">
        </td>
        <td style="text-align: center;">
            <button type="button" class="btn-row-action btn-row-cancel" onclick="this.closest('tr').remove()">&#10005;</button>
        </td>
    `;
    tbody.appendChild(tr);
}

function getActionsData() {
    const rows = document.querySelectorAll("#actions-table-body tr");
    const list = [];
    rows.forEach(r => {
        const text = r.querySelector(".action-text-input").value.trim();
        const owner = r.querySelector(".action-owner-select").value;
        const status = r.querySelector(".action-status-select").value;
        const date = r.querySelector(".action-date-input").value;
        if (text || owner || date) {
            list.push({ action_text: text, owner: owner, status: status, target_date: date });
        }
    });
    return list;
}

// AFC MATRIX
function renderAfcMatrix(afcDict) {
    const cats = ['ENG HRS', 'OTHER HRS', 'NRC VENDOR'];
    cats.forEach(cat => {
        const data = afcDict[cat] || {};
        document.getElementById(`afc-${cat}-full_life`).value = data.full_life || "";
        document.getElementById(`afc-${cat}-curr_bdg`).value = data.curr_bdg || "";
        document.getElementById(`afc-${cat}-curr_actual`).value = data.curr_actual || "";
        document.getElementById(`afc-${cat}-curr_remaining`).value = data.curr_remaining || "";
        document.getElementById(`afc-${cat}-curr_forecast`).value = data.curr_forecast || "";
    });
}

function getAfcData() {
    const cats = ['ENG HRS', 'OTHER HRS', 'NRC VENDOR'];
    const res = {};
    cats.forEach(cat => {
        res[cat] = {
            category: cat,
            full_life: document.getElementById(`afc-${cat}-full_life`).value,
            curr_bdg: document.getElementById(`afc-${cat}-curr_bdg`).value,
            curr_actual: document.getElementById(`afc-${cat}-curr_actual`).value,
            curr_remaining: document.getElementById(`afc-${cat}-curr_remaining`).value,
            curr_forecast: document.getElementById(`afc-${cat}-curr_forecast`).value
        };
    });
    return res;
}

// SAVE FULL
async function saveCurrentActivity() {
    if (!currentActivityId) return;

    const payload = {
        title: document.getElementById("modal-input-title").value.trim(),
        type: document.getElementById("modal-select-type").value,
        status: document.getElementById("modal-select-status").value,
        urgency: document.getElementById("modal-select-urgency").value,
        relevancy: parseInt(document.getElementById("modal-select-relevancy").value) || 3,
        odg: document.getElementById("modal-check-odg").checked ? "Y" : "N",
        safety: document.getElementById("modal-check-safety").checked ? 1 : 0,
        pm: document.getElementById("modal-select-pm").value,
        pe: document.getElementById("modal-select-pe").value,
        beneficiary: document.getElementById("modal-select-beneficiary").value,
        cluster: document.getElementById("modal-select-cluster").value,
        basic_kit: document.getElementById("modal-select-basic-kit").value,
        proto_n: document.getElementById("modal-select-proto").value,
        supplier: document.getElementById("modal-input-supplier").value.trim(),
        year_2027: document.getElementById("modal-input-year27").value.trim(),
        year_28: document.getElementById("modal-check-year28").checked ? 1 : 0,
        year_29: document.getElementById("modal-check-year29").checked ? 1 : 0,
        year_30: document.getElementById("modal-check-year30").checked ? 1 : 0,
        year_31: document.getElementById("modal-check-year31").checked ? 1 : 0,

        drivers: getSelectedMultiChecks("modal-container-drivers"),
        streams: getSelectedMultiChecks("modal-container-streams"),
        platforms: getSelectedMultiChecks("modal-container-platforms"),

        notes_actions: document.getElementById("editor-notes_actions").innerHTML,
        plan_deliverables: document.getElementById("editor-plan_deliverables").innerHTML,
        team: getTeamData(),

        clarity: document.getElementById("modal-input-clarity").value.trim(),
        ispi: document.getElementById("modal-input-ispi").value.trim(),
        other_id: document.getElementById("modal-input-other_id").value.trim(),
        bcr: document.getElementById("modal-input-bcr").value.trim(),
        cr: document.getElementById("modal-input-cr").value.trim(),
        qsd: document.getElementById("modal-input-qsd").value.trim(),
        ndc: document.getElementById("modal-input-ndc").value.trim(),
        wbs_code: document.getElementById("modal-input-wbs_code").value.trim(),
        wbs_description: document.getElementById("modal-input-wbs_description").value.trim(),
        booking_n: document.getElementById("editor-booking_n").innerHTML,
        rda_record: document.getElementById("editor-rda_record").innerHTML,

        actions: getActionsData(),

        afc1: document.getElementById("modal-select-afc1").value,
        afc2: document.getElementById("modal-select-afc2").value,
        afc: getAfcData()
    };

    try {
        const res = await fetch(`/api/activities/${currentActivityId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeIdModal();
        } else {
            alert("Errore salvataggio: " + (data.error || ""));
        }
    } catch (err) {
        showToast("Errore connessione server: " + err, "error");
    }
}

function openCurrentFolder() {
    if (currentActivityId) {
        handleOpenFolder(currentActivityId);
    }
}

// EXPORT & PRINT
function exportExcel() {
    const params = getFilterParams();
    window.location.href = `/api/export/excel?${params.toString()}`;
}

function printReport() {
    window.print();
}

// LOOKUPS MODAL
function openLookupsModal() {
    selectLookupCategory('person');
    document.getElementById("modal-lookups-container").style.display = "flex";
}

function closeLookupsModal() {
    document.getElementById("modal-lookups-container").style.display = "none";
    loadLookups();
}

function selectLookupCategory(category) {
    currentLookupCategory = category;
    const items = currentLookups[category] || [];
    const tbody = document.getElementById("lookups-table-body");
    tbody.innerHTML = "";

    items.forEach(it => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>
                <input type="text" class="cell-input" style="border: 1px solid var(--border);" value="${escapeHtml(it.name)}" onchange="updateLookupItem(${it.id}, this.value)">
            </td>
            <td style="text-align: center;">
                <button class="btn-row-action btn-row-cancel" onclick="deleteLookupItem(${it.id})">Elimina</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function handleAddLookup() {
    const nameInput = document.getElementById("new-lookup-name");
    const name = nameInput.value.trim();
    if (!name) return;

    try {
        const res = await fetch("/api/lookups", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ category: currentLookupCategory, name: name })
        });
        const data = await res.json();
        if (data.success) {
            nameInput.value = "";
            await loadLookups();
            selectLookupCategory(currentLookupCategory);
        } else {
            alert(data.error || "Errore inserimento.");
        }
    } catch (err) {
        alert("Errore: " + err);
    }
}

async function updateLookupItem(id, newName) {
    newName = newName.trim();
    if (!newName) return;
    try {
        await fetch(`/api/lookups/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: newName })
        });
        await loadLookups();
    } catch (err) {
        console.error("Errore aggiornamento:", err);
    }
}

async function deleteLookupItem(id) {
    if (confirm("Sei sicuro di voler eliminare questa voce?")) {
        try {
            await fetch(`/api/lookups/${id}`, { method: "DELETE" });
            await loadLookups();
            selectLookupCategory(currentLookupCategory);
        } catch (err) {
            alert("Errore eliminazione: " + err);
        }
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function resetAllFilters() {
    // Reset View setup to default
    document.getElementById("vs-type-project").checked = true;
    document.getElementById("vs-type-task").checked = true;
    document.getElementById("vs-type-idea").checked = true;
    document.getElementById("vs-type-discussion").checked = true;
    document.getElementById("vs-hide-closed").checked = true;
    document.getElementById("vs-hide-cancelled").checked = true;
    document.getElementById("vs-hide-onhold").checked = true;
    document.getElementById("vs-hide-rejected").checked = true;

    // Reset filtri multi-selezione
    Object.keys(activeMultiFilters).forEach(group => {
        activeMultiFilters[group].clear();
        const container = document.getElementById(`ms-options-${group}`);
        if (container) {
            container.querySelectorAll("input[type='checkbox']").forEach(inp => inp.checked = false);
        }
        updateMultiFilterTrigger(group);
    });
    document.getElementById("global-search").value = "";
    currentSortCol = "id";
    currentSortDir = "desc";
    updateSortIndicators();

    if (isExpiringFilterActive) {
        toggleExpiringFilter();
    } else {
        reloadTable();
    }
    showToast("Tutti i filtri sono stati azzerati", "info");
}
