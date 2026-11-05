// DMS 2.0 - Client Controller & Modern Data Grid with Resizable Columns

let allActivities = [];
let currentActivityId = null;
let currentLookups = {};
let isExpiringFilterActive = false;
let searchDebounceTimer = null;
let currentLookupCategory = 'person';

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
    restoreColumnWidths();
    initColumnResize();
    await loadConfig();
    await loadLookups();
    await reloadTable();
});

// --- SISTEMA RIDIMENSIONAMENTO COLONNE (DRAG & DROP) ---

function initColumnResize() {
    const table = document.getElementById("main-dms-table");
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
        alert("Errore chiamata server: " + err);
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

function populateFilterDropdowns() {
    populateSelect("filter-beneficiary", currentLookups.beneficiary || [], "Beneficiary (Tutti)");
    populateSelect("filter-cluster", currentLookups.cluster || [], "Cluster (Tutti)");
    populateSelect("filter-pm", currentLookups.person || [], "PM (Tutti)");
    populateSelect("filter-proto", currentLookups.proto || [], "Proto (Tutti)");
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

    const urgency = document.getElementById("filter-urgency").value;
    if (urgency) params.set("urgency", urgency);

    const search = document.getElementById("global-search").value.trim();
    if (search) params.set("search", search);

    if (isExpiringFilterActive) {
        params.set("expiring_in_5_days", "true");
    }

    const sortBy = document.getElementById("sort-select").value;
    if (sortBy) params.set("sort_by", sortBy);

    return params;
}

async function reloadTable() {
    const params = getFilterParams();

    try {
        const res = await fetch(`/api/activities?${params.toString()}`);
        let activities = await res.json();

        const fYear = document.getElementById("filter-year").value;
        const fBen = document.getElementById("filter-beneficiary").value;
        const fClu = document.getElementById("filter-cluster").value;
        const fPm = document.getElementById("filter-pm").value;
        const fProto = document.getElementById("filter-proto").value;

        if (fYear) {
            activities = activities.filter(a => {
                if (fYear === "2027") return a.year_2027 && a.year_2027.trim() !== "";
                if (fYear === "2028") return a.year_28 == 1;
                if (fYear === "2029") return a.year_29 == 1;
                if (fYear === "2030") return a.year_30 == 1;
                if (fYear === "2031") return a.year_31 == 1;
                return true;
            });
        }
        if (fBen) activities = activities.filter(a => a.beneficiary === fBen);
        if (fClu) activities = activities.filter(a => a.cluster === fClu);
        if (fPm) activities = activities.filter(a => a.pm === fPm);
        if (fProto) activities = activities.filter(a => a.proto_n === fProto);

        allActivities = activities;
        renderTableRows(activities);
    } catch (err) {
        console.error("Errore caricamento tabella:", err);
    }
}

function renderTableRows(activities) {
    const tbody = document.getElementById("activities-table-body");
    tbody.innerHTML = "";

    if (activities.length === 0) {
        tbody.innerHTML = `<tr><td colspan="21" style="text-align:center; padding: 32px; color: var(--text-muted); font-size: 13px;">Nessuna attività trovata con i filtri attuali.</td></tr>`;
        return;
    }

    activities.forEach(act => {
        const tr = document.createElement("tr");
        if (act.urgent_actions_count > 0) {
            tr.classList.add("urgent-item");
        }

        const formattedId = String(act.id).padStart(5, '0');
        const allowedStatuses = TYPE_STATUS_MAP[act.type] || [];

        tr.innerHTML = `
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
            <td><span class="badge-id">${formattedId}</span></td>
            <td>
                <select class="select-modern badge-urg-${act.urgency}" style="font-weight: 700; border: none; padding: 2px 4px;" onchange="saveInlineField(${act.id}, 'urgency', this.value); this.className='select-modern badge-urg-' + this.value;">
                    ${["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINOR"].map(u => 
                        `<option value="${u}" ${act.urgency === u ? 'selected' : ''}>${u}</option>`
                    ).join('')}
                </select>
            </td>
            <td style="color: var(--text-secondary); font-size: 11px;" title="${act.drivers_str || ''}">
                ${act.drivers_str || '-'}
            </td>
            <td style="text-align: center;">
                <input type="checkbox" ${act.odg === 'Y' ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'odg', this.checked ? 'Y' : 'N')">
            </td>
            <td>
                <input type="text" class="cell-input cell-title-text" value="${escapeHtml(act.title)}" onchange="saveInlineField(${act.id}, 'title', this.value)">
            </td>
            <td>
                <select class="select-modern badge-type-${act.type}" style="font-weight: 600; border: none; padding: 2px 4px;" onchange="handleTypeChangeInline(${act.id}, this.value)">
                    ${["Project", "Task", "Idea", "Discussion"].map(t => 
                        `<option value="${t}" ${act.type === t ? 'selected' : ''}>${t}</option>`
                    ).join('')}
                </select>
            </td>
            <td style="text-align: center;">
                <select class="cell-input" style="text-align: center; font-weight: 600;" onchange="saveInlineField(${act.id}, 'relevancy', this.value)">
                    ${[1, 2, 3, 4, 5].map(r => 
                        `<option value="${r}" ${act.relevancy == r ? 'selected' : ''}>${r}</option>`
                    ).join('')}
                </select>
            </td>
            <td>
                <select class="cell-input" onchange="saveInlineField(${act.id}, 'pm', this.value)">
                    <option value="">--</option>
                    ${(currentLookups.person || []).map(p => 
                        `<option value="${p.name}" ${act.pm === p.name ? 'selected' : ''}>${p.name}</option>`
                    ).join('')}
                </select>
            </td>
            <td>
                <select class="cell-input" onchange="saveInlineField(${act.id}, 'pe', this.value)">
                    <option value="">--</option>
                    ${(currentLookups.person || []).map(p => 
                        `<option value="${p.name}" ${act.pe === p.name ? 'selected' : ''}>${p.name}</option>`
                    ).join('')}
                </select>
            </td>
            <td>
                <select class="cell-input" onchange="saveInlineField(${act.id}, 'beneficiary', this.value)">
                    <option value="">--</option>
                    ${(currentLookups.beneficiary || []).map(b => 
                        `<option value="${b.name}" ${act.beneficiary === b.name ? 'selected' : ''}>${b.name}</option>`
                    ).join('')}
                </select>
            </td>
            <td>
                <select class="cell-input" onchange="saveInlineField(${act.id}, 'cluster', this.value)">
                    <option value="">--</option>
                    ${(currentLookups.cluster || []).map(c => 
                        `<option value="${c.name}" ${act.cluster === c.name ? 'selected' : ''}>${c.name}</option>`
                    ).join('')}
                </select>
            </td>
            <td>
                <select class="cell-input" onchange="saveInlineField(${act.id}, 'basic_kit', this.value)">
                    <option value="Basic" ${act.basic_kit === 'Basic' ? 'selected' : ''}>Basic</option>
                    <option value="Kit" ${act.basic_kit === 'Kit' ? 'selected' : ''}>Kit</option>
                </select>
            </td>
            <td>
                <select class="cell-input" onchange="saveInlineField(${act.id}, 'proto_n', this.value)">
                    <option value="">--</option>
                    ${(currentLookups.proto || []).map(pr => 
                        `<option value="${pr.name}" ${act.proto_n === pr.name ? 'selected' : ''}>${pr.name}</option>`
                    ).join('')}
                </select>
            </td>
            <td>
                <input type="text" class="cell-input" value="${escapeHtml(act.year_2027 || '')}" placeholder="Mesi..." onchange="saveInlineField(${act.id}, 'year_2027', this.value)">
            </td>
            <td style="text-align: center;">
                <input type="checkbox" ${act.year_28 == 1 ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'year_28', this.checked ? 1 : 0)">
            </td>
            <td style="text-align: center;">
                <input type="checkbox" ${act.year_29 == 1 ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'year_29', this.checked ? 1 : 0)">
            </td>
            <td style="text-align: center;">
                <input type="checkbox" ${act.year_30 == 1 ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'year_30', this.checked ? 1 : 0)">
            </td>
            <td style="text-align: center;">
                <input type="checkbox" ${act.year_31 == 1 ? 'checked' : ''} onchange="saveInlineField(${act.id}, 'year_31', this.checked ? 1 : 0)">
            </td>
            <td>
                <select class="cell-input" style="font-weight: 500;" id="inline-status-${act.id}" onchange="saveInlineField(${act.id}, 'status', this.value)">
                    ${allowedStatuses.map(s => 
                        `<option value="${s}" ${act.status === s ? 'selected' : ''}>${s}</option>`
                    ).join('')}
                </select>
            </td>
            <td style="color: var(--text-muted); font-size: 10.5px;">${act.last_update || '-'}</td>
        `;

        tbody.appendChild(tr);
    });
}

async function saveInlineField(activityId, fieldName, value) {
    try {
        await fetch(`/api/activities/${activityId}/field`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ field: fieldName, value: value })
        });
    } catch (err) {
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
        alert("Errore creazione nuovo ID: " + err);
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
            alert("Errore operazione: " + err);
        }
    }
}

async function handleOpenFolder(activityId) {
    try {
        const res = await fetch(`/api/activities/${activityId}/folder`, { method: "POST" });
        const data = await res.json();
        if (!data.success) {
            alert("Errore apertura cartella: " + (data.error || ""));
        }
    } catch (err) {
        alert("Errore chiamata server: " + err);
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
        alert("Errore apertura scheda: " + err);
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
        alert("Errore chiamata server: " + err);
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
