import sqlite3
import datetime
import os
from config import get_db_path

# Mappatura Tipo -> Stati consentiti da specifica
TYPE_STATUS_MAP = {
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
}

def get_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Ottimizzazioni per concorrenza su rete
    conn.execute("PRAGMA busy_timeout = 30000;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except Exception:
        pass
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabella Attività principale
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL DEFAULT '',
        type TEXT NOT NULL DEFAULT 'Project',
        status TEXT NOT NULL DEFAULT '1) Planned',
        urgency TEXT NOT NULL DEFAULT 'MEDIUM',
        relevancy INTEGER NOT NULL DEFAULT 3,
        beneficiary TEXT NOT NULL DEFAULT '',
        cluster TEXT NOT NULL DEFAULT '',
        basic_kit TEXT NOT NULL DEFAULT 'Basic',
        proto_n TEXT NOT NULL DEFAULT '',
        odg TEXT NOT NULL DEFAULT 'N',
        safety INTEGER NOT NULL DEFAULT 0,
        pm TEXT NOT NULL DEFAULT '',
        pe TEXT NOT NULL DEFAULT '',
        supplier TEXT NOT NULL DEFAULT '',
        year_2027 TEXT NOT NULL DEFAULT '',
        year_28 INTEGER NOT NULL DEFAULT 0,
        year_29 INTEGER NOT NULL DEFAULT 0,
        year_30 INTEGER NOT NULL DEFAULT 0,
        year_31 INTEGER NOT NULL DEFAULT 0,
        afc1 TEXT NOT NULL DEFAULT '',
        afc2 TEXT NOT NULL DEFAULT '',
        notes_actions TEXT NOT NULL DEFAULT '',
        plan_deliverables TEXT NOT NULL DEFAULT '',
        clarity TEXT NOT NULL DEFAULT '',
        ispi TEXT NOT NULL DEFAULT '',
        other_id TEXT NOT NULL DEFAULT '',
        bcr TEXT NOT NULL DEFAULT '',
        cr TEXT NOT NULL DEFAULT '',
        qsd TEXT NOT NULL DEFAULT '',
        ndc TEXT NOT NULL DEFAULT '',
        wbs_code TEXT NOT NULL DEFAULT '',
        wbs_description TEXT NOT NULL DEFAULT '',
        booking_n TEXT NOT NULL DEFAULT '',
        rda_record TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        last_update TEXT NOT NULL
    );
    """)

    # Tabella tag/attributi multipli (Drivers, Streams, Platforms)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        tag_name TEXT NOT NULL,
        FOREIGN KEY (activity_id) REFERENCES activities (id) ON DELETE CASCADE,
        UNIQUE (activity_id, category, tag_name)
    );
    """)

    # Tabella Action Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id INTEGER NOT NULL,
        action_text TEXT NOT NULL DEFAULT '',
        owner TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'OPEN',
        target_date TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (activity_id) REFERENCES activities (id) ON DELETE CASCADE
    );
    """)

    # Tabella Team
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id INTEGER NOT NULL,
        function_name TEXT NOT NULL DEFAULT '',
        person_name TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (activity_id) REFERENCES activities (id) ON DELETE CASCADE
    );
    """)

    # Tabella AFC (Matrice Finanziaria / Ore)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS afc_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        full_life TEXT NOT NULL DEFAULT '',
        curr_bdg TEXT NOT NULL DEFAULT '',
        curr_actual TEXT NOT NULL DEFAULT '',
        curr_remaining TEXT NOT NULL DEFAULT '',
        curr_forecast TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (activity_id) REFERENCES activities (id) ON DELETE CASCADE,
        UNIQUE (activity_id, category)
    );
    """)

    # Tabella Gestione Liste e Anagrafiche
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lookups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER NOT NULL DEFAULT 0,
        UNIQUE (category, name)
    );
    """)

    # Indici mirati per velocizzare le query su volumi consistenti e concorrenza di rete
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_type_status ON activities(type, status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_urgency ON activities(urgency);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_pm ON activities(pm);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_beneficiary ON activities(beneficiary);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_cluster ON activities(cluster);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_act_status ON actions(activity_id, status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_tags_search ON activity_tags(activity_id, category);")

    conn.commit()

    # Seed iniziale dei lookups se vuoti
    cursor.execute("SELECT COUNT(*) as count FROM lookups;")
    if cursor.fetchone()["count"] == 0:
        seed_lookups(cursor)
        conn.commit()

    # Se non ci sono attività, creiamo un paio di attività demo per facilitare il collaudo
    cursor.execute("SELECT COUNT(*) as count FROM activities;")
    if cursor.fetchone()["count"] == 0:
        seed_demo_activities(cursor)
        conn.commit()

    conn.close()

def seed_lookups(cursor):
    initial_lookups = [
        # Beneficiaries da specifica
        ("beneficiary", "TCO"),
        ("beneficiary", "PSE"),
        ("beneficiary", "P&SC"),
        ("beneficiary", "OPS"),
        ("beneficiary", "Customer"),

        # Clusters da specifica
        ("cluster", "PMoD"),
        ("cluster", "NMH"),
        ("cluster", "Other Contracts"),
        ("cluster", "Internal Commitment"),
        ("cluster", "OBSO"),
        ("cluster", "SAFETY"),

        # Proto da specifica
        ("proto", "P3"),
        ("proto", "P5"),
        ("proto", "P6"),

        # Drivers standard modificabili
        ("driver", "Safety"),
        ("driver", "Obsolescence"),
        ("driver", "Cost Reduction"),
        ("driver", "Quality & Reliability"),
        ("driver", "Innovation"),
        ("driver", "Customer Request"),
        ("driver", "Standardization"),

        # Streams standard modificabili
        ("stream", "Mechanical"),
        ("stream", "Electronics"),
        ("stream", "Software"),
        ("stream", "Systems Engineering"),
        ("stream", "Testing & V&V"),
        ("stream", "Industrialization"),

        # Platforms standard modificabili
        ("platform", "Platform Alpha"),
        ("platform", "Platform Beta"),
        ("platform", "Platform Gamma"),
        ("platform", "Legacy System"),

        # Persone standard modificabili (per PM, PE, Action Owner, Team)
        ("person", "Mario Rossi"),
        ("person", "Luca Bianchi"),
        ("person", "Anna Verdi"),
        ("person", "Marco Neri"),
        ("person", "Giulia Romano"),
        ("person", "Paolo Ferrari"),

        # Funzioni / Ruoli del Team modificabili
        ("function", "Project Manager"),
        ("function", "Lead Engineer"),
        ("function", "System Architect"),
        ("function", "Design Engineer"),
        ("function", "Validation Specialist"),
        ("function", "Buyer / Procurement"),
        ("function", "Quality Assurance")
    ]

    for idx, (cat, name) in enumerate(initial_lookups):
        cursor.execute(
            "INSERT OR IGNORE INTO lookups (category, name, sort_order) VALUES (?, ?, ?);",
            (cat, name, idx)
        )

def seed_demo_activities(cursor):
    today = datetime.date.today().strftime("%Y-%m-%d")
    in_3_days = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    in_15_days = (datetime.date.today() + datetime.timedelta(days=15)).strftime("%Y-%m-%d")

    # Attività 1
    cursor.execute("""
    INSERT INTO activities (
        title, type, status, urgency, relevancy, beneficiary, cluster, basic_kit, proto_n, odg, safety,
        pm, pe, supplier, year_2027, year_28, year_29, year_30, year_31, afc1, afc2,
        notes_actions, plan_deliverables, clarity, wbs_code, wbs_description, created_at, last_update
    ) VALUES (
        'Sviluppo Nuovo Modulo di Controllo Elettronico', 'Project', '3) On Going', 'HIGH', 4, 'PSE', 'PMoD', 'Basic', 'P3', 'Y', 1,
        'Mario Rossi', 'Luca Bianchi', 'Elettronica SpA', 'Gen-Giu', 1, 1, 0, 0, 'BDG', 'PI',
        '<p>Verificare specifica di interfaccia con <strong>fornitore</strong>.</p>',
        '<p>Milestone 1: Design Review (fine mese)<br>Milestone 2: Prototipazione P3</p>',
        'CLR-2027-091', 'WBS-EL-9921', 'Engineering & Dev Elettronica', ?, ?
    );
    """, (today, today))
    act1_id = cursor.lastrowid

    # Tag per Attività 1
    cursor.execute("INSERT INTO activity_tags (activity_id, category, tag_name) VALUES (?, 'driver', 'Safety');", (act1_id,))
    cursor.execute("INSERT INTO activity_tags (activity_id, category, tag_name) VALUES (?, 'driver', 'Quality & Reliability');", (act1_id,))
    cursor.execute("INSERT INTO activity_tags (activity_id, category, tag_name) VALUES (?, 'stream', 'Electronics');", (act1_id,))
    cursor.execute("INSERT INTO activity_tags (activity_id, category, tag_name) VALUES (?, 'stream', 'Software');", (act1_id,))
    cursor.execute("INSERT INTO activity_tags (activity_id, category, tag_name) VALUES (?, 'platform', 'Platform Alpha');", (act1_id,))

    # Azione in scadenza (< 5gg) per Attività 1
    cursor.execute("""
    INSERT INTO actions (activity_id, action_text, owner, status, target_date)
    VALUES (?, 'Completamento report analisi termica preliminare', 'Luca Bianchi', 'OPEN', ?);
    """, (act1_id, in_3_days))

    # Team per Attività 1
    cursor.execute("INSERT INTO team_members (activity_id, function_name, person_name) VALUES (?, 'Project Manager', 'Mario Rossi');", (act1_id,))
    cursor.execute("INSERT INTO team_members (activity_id, function_name, person_name) VALUES (?, 'Lead Engineer', 'Luca Bianchi');", (act1_id,))

    # AFC per Attività 1
    for cat in ['ENG HRS', 'OTHER HRS', 'NRC VENDOR']:
        cursor.execute("""
        INSERT INTO afc_records (activity_id, category, full_life, curr_bdg, curr_actual, curr_remaining, curr_forecast)
        VALUES (?, ?, '1200', '400', '150', '250', '400');
        """, (act1_id, cat))

    # Attività 2 (Task)
    cursor.execute("""
    INSERT INTO activities (
        title, type, status, urgency, relevancy, beneficiary, cluster, basic_kit, proto_n, odg, safety,
        pm, pe, supplier, year_2027, year_28, year_29, year_30, year_31, afc1, afc2,
        notes_actions, plan_deliverables, clarity, wbs_code, wbs_description, created_at, last_update
    ) VALUES (
        'Aggiornamento documentazione e cablaggi di bordo', 'Task', '2) Scheduled', 'MEDIUM', 3, 'OPS', 'OBSO', 'Kit', 'P5', 'N', 0,
        'Anna Verdi', 'Marco Neri', 'CaviTech Srl', 'Lug-Dic', 0, 1, 0, 0, 'EXTRA BDG', 'CP',
        '<p>Revisione schemi secondo normativa aggiornata.</p>',
        '<p>Rilascio pacchetto di produzione.</p>',
        'CLR-2027-104', 'WBS-DOC-0044', 'Aggiornamento schemi cavi', ?, ?
    );
    """, (today, today))
    act2_id = cursor.lastrowid

    cursor.execute("INSERT INTO activity_tags (activity_id, category, tag_name) VALUES (?, 'driver', 'Obsolescence');", (act2_id,))
    cursor.execute("INSERT INTO activity_tags (activity_id, category, tag_name) VALUES (?, 'stream', 'Mechanical');", (act2_id,))
    cursor.execute("INSERT INTO activity_tags (activity_id, category, tag_name) VALUES (?, 'platform', 'Platform Beta');", (act2_id,))

    cursor.execute("""
    INSERT INTO actions (activity_id, action_text, owner, status, target_date)
    VALUES (?, 'Allineamento con produzione per tempistiche fermo linea', 'Marco Neri', 'OPEN', ?);
    """, (act2_id, in_15_days))

    cursor.execute("INSERT INTO team_members (activity_id, function_name, person_name) VALUES (?, 'Project Manager', 'Anna Verdi');", (act2_id,))
    cursor.execute("INSERT INTO team_members (activity_id, function_name, person_name) VALUES (?, 'Design Engineer', 'Marco Neri');", (act2_id,))

    for cat in ['ENG HRS', 'OTHER HRS', 'NRC VENDOR']:
        cursor.execute("""
        INSERT INTO afc_records (activity_id, category, full_life, curr_bdg, curr_actual, curr_remaining, curr_forecast)
        VALUES (?, ?, '600', '200', '50', '150', '200');
        """, (act2_id, cat))

# --- Funzioni CRUD ---

def get_lookups():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, name, is_active FROM lookups ORDER BY category, sort_order, name;")
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for r in rows:
        cat = r["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append({
            "id": r["id"],
            "name": r["name"],
            "is_active": r["is_active"]
        })
    return result

def add_lookup(category, name):
    name = name.strip()
    if not name:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO lookups (category, name) VALUES (?, ?);", (category, name))
        conn.commit()
        lid = cursor.lastrowid
        conn.close()
        return lid
    except sqlite3.IntegrityError:
        conn.close()
        return None

def update_lookup(lookup_id, name):
    name = name.strip()
    if not name:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE lookups SET name = ? WHERE id = ?;", (name, lookup_id))
    conn.commit()
    conn.close()
    return True

def delete_lookup(lookup_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lookups WHERE id = ?;", (lookup_id,))
    conn.commit()
    conn.close()
    return True

def get_activities_list(search=None, urgency=None, status_exclude=None, type_exclude=None,
                        expiring_in_5_days=False, sort_by="id_desc"):
    """
    Ritorna le attività con i campi aggregati per la tabella principale.
    """
    conn = get_connection()
    cursor = conn.cursor()

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    in_5_days_str = (datetime.date.today() + datetime.timedelta(days=5)).strftime("%Y-%m-%d")

    # Query di base
    query = """
    SELECT a.*,
        (SELECT GROUP_CONCAT(tag_name, ', ') FROM activity_tags WHERE activity_id = a.id AND category = 'driver') as drivers_str,
        (SELECT GROUP_CONCAT(tag_name, ', ') FROM activity_tags WHERE activity_id = a.id AND category = 'stream') as streams_str,
        (SELECT GROUP_CONCAT(tag_name, ', ') FROM activity_tags WHERE activity_id = a.id AND category = 'platform') as platforms_str,
        (SELECT COUNT(*) FROM actions WHERE activity_id = a.id AND status != 'CLOSED' AND target_date != '' AND target_date <= ?) as urgent_actions_count
    FROM activities a
    WHERE 1=1
    """
    params = [in_5_days_str]

    if expiring_in_5_days:
        query += " AND a.id IN (SELECT DISTINCT activity_id FROM actions WHERE status != 'CLOSED' AND target_date != '' AND target_date <= ?)"
        params.append(in_5_days_str)

    if urgency:
        query += " AND a.urgency = ?"
        params.append(urgency)

    if status_exclude and len(status_exclude) > 0:
        placeholders = ",".join("?" for _ in status_exclude)
        # Esclusione per pattern di stato (es. Closed, Cancelled, On hold, Rejected)
        conditions = []
        for s in status_exclude:
            conditions.append("a.status LIKE ?")
            params.append(f"%{s}%")
        if conditions:
            query += " AND NOT (" + " OR ".join(conditions) + ")"

    if type_exclude and len(type_exclude) > 0:
        placeholders = ",".join("?" for _ in type_exclude)
        query += f" AND a.type NOT IN ({placeholders})"
        params.extend(type_exclude)

    if search:
        search_term = f"%{search}%"
        query += """ AND (
            CAST(a.id AS TEXT) LIKE ? OR
            a.title LIKE ? OR
            a.pm LIKE ? OR
            a.pe LIKE ? OR
            a.supplier LIKE ? OR
            a.wbs_code LIKE ? OR
            a.wbs_description LIKE ? OR
            a.clarity LIKE ? OR
            a.beneficiary LIKE ? OR
            a.cluster LIKE ? OR
            a.notes_actions LIKE ?
        )"""
        params.extend([search_term] * 11)

    # Ordinamento da specifica:
    # Il tasto Ordina permette di ordinare gli ID in base a Urgenza o Rilevanza o primo anno attivo
    if sort_by == "urgency":
        query += """ ORDER BY 
            CASE a.urgency 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                WHEN 'LOW' THEN 4 
                WHEN 'MINOR' THEN 5 
                ELSE 6 
            END ASC, a.id DESC"""
    elif sort_by == "relevancy":
        query += " ORDER BY a.relevancy DESC, a.id DESC"
    elif sort_by == "first_year":
        query += """ ORDER BY 
            CASE 
                WHEN a.year_2027 != '' THEN 2027
                WHEN a.year_28 = 1 THEN 2028
                WHEN a.year_29 = 1 THEN 2029
                WHEN a.year_30 = 1 THEN 2030
                WHEN a.year_31 = 1 THEN 2031
                ELSE 9999
            END ASC, a.id DESC"""
    else:
        query += " ORDER BY a.id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result

def get_activity_detail(activity_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM activities WHERE id = ?;", (activity_id,))
    act = cursor.fetchone()
    if not act:
        conn.close()
        return None

    data = dict(act)

    # Tag
    cursor.execute("SELECT category, tag_name FROM activity_tags WHERE activity_id = ?;", (activity_id,))
    tags = cursor.fetchall()
    data["drivers"] = [t["tag_name"] for t in tags if t["category"] == "driver"]
    data["streams"] = [t["tag_name"] for t in tags if t["category"] == "stream"]
    data["platforms"] = [t["tag_name"] for t in tags if t["category"] == "platform"]

    # Actions
    cursor.execute("SELECT * FROM actions WHERE activity_id = ? ORDER BY target_date ASC, id ASC;", (activity_id,))
    data["actions"] = [dict(a) for a in cursor.fetchall()]

    # Team
    cursor.execute("SELECT * FROM team_members WHERE activity_id = ? ORDER BY id ASC;", (activity_id,))
    data["team"] = [dict(t) for t in cursor.fetchall()]

    # AFC
    cursor.execute("SELECT * FROM afc_records WHERE activity_id = ?;", (activity_id,))
    afc_dict = {r["category"]: dict(r) for r in cursor.fetchall()}
    # Garantisci che esistano le 3 categorie
    for cat in ['ENG HRS', 'OTHER HRS', 'NRC VENDOR']:
        if cat not in afc_dict:
            afc_dict[cat] = {
                "category": cat,
                "full_life": "",
                "curr_bdg": "",
                "curr_actual": "",
                "curr_remaining": "",
                "curr_forecast": ""
            }
    data["afc"] = afc_dict

    conn.close()
    return data

def create_activity():
    today = datetime.date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO activities (
        title, type, status, urgency, relevancy, created_at, last_update
    ) VALUES (
        'Nuova Attività', 'Project', '1) Planned', 'MEDIUM', 3, ?, ?
    );
    """, (today, today))
    new_id = cursor.lastrowid

    # Inizializza record AFC vuoti
    for cat in ['ENG HRS', 'OTHER HRS', 'NRC VENDOR']:
        cursor.execute("""
        INSERT INTO afc_records (activity_id, category, full_life, curr_bdg, curr_actual, curr_remaining, curr_forecast)
        VALUES (?, ?, '', '', '', '', '');
        """, (new_id, cat))

    conn.commit()
    conn.close()
    return new_id

def update_activity_field(activity_id, field_name, value):
    """Aggiorna un singolo campo direttamente dalla tabella (inline editing)"""
    allowed_fields = [
        'title', 'type', 'status', 'urgency', 'relevancy', 'beneficiary', 'cluster',
        'basic_kit', 'proto_n', 'odg', 'safety', 'pm', 'pe', 'supplier',
        'year_2027', 'year_28', 'year_29', 'year_30', 'year_31',
        'afc1', 'afc2'
    ]
    if field_name not in allowed_fields:
        return False

    today = datetime.date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()

    # Se cambia il tipo, verifichiamo che lo stato rimanga consistente
    if field_name == 'type' and value in TYPE_STATUS_MAP:
        allowed_statuses = TYPE_STATUS_MAP[value]
        # Recupera lo stato attuale
        cursor.execute("SELECT status FROM activities WHERE id = ?;", (activity_id,))
        curr_row = cursor.fetchone()
        if curr_row and curr_row["status"] not in allowed_statuses:
            # Imposta il primo stato valido per il nuovo tipo
            cursor.execute(
                "UPDATE activities SET type = ?, status = ?, last_update = ? WHERE id = ?;",
                (value, allowed_statuses[0], today, activity_id)
            )
            conn.commit()
            conn.close()
            return True

    cursor.execute(
        f"UPDATE activities SET {field_name} = ?, last_update = ? WHERE id = ?;",
        (value, today, activity_id)
    )
    conn.commit()
    conn.close()
    return True

def cancel_activity(activity_id):
    """Mette l'attività in stato Cancelled (secondo la logica del tasto Cancel)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT type FROM activities WHERE id = ?;", (activity_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    act_type = row["type"]
    today = datetime.date.today().strftime("%Y-%m-%d")

    # Trova la variante di stato cancelled adeguata per il tipo
    if act_type == "Discussion":
        new_status = "4) Closed /Canceled"
    elif act_type == "Idea":
        new_status = "6) Rejected"
    else:
        new_status = "5) Closed/Cancelled"

    cursor.execute("UPDATE activities SET status = ?, last_update = ? WHERE id = ?;", (new_status, today, activity_id))
    conn.commit()
    conn.close()
    return True

def save_full_activity(activity_id, data):
    """Salva tutti i dati della finestra singolo ID"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()

    # Aggiorna campi principali
    cursor.execute("""
    UPDATE activities SET
        title = ?,
        type = ?,
        status = ?,
        urgency = ?,
        relevancy = ?,
        beneficiary = ?,
        cluster = ?,
        basic_kit = ?,
        proto_n = ?,
        odg = ?,
        safety = ?,
        pm = ?,
        pe = ?,
        supplier = ?,
        year_2027 = ?,
        year_28 = ?,
        year_29 = ?,
        year_30 = ?,
        year_31 = ?,
        afc1 = ?,
        afc2 = ?,
        notes_actions = ?,
        plan_deliverables = ?,
        clarity = ?,
        ispi = ?,
        other_id = ?,
        bcr = ?,
        cr = ?,
        qsd = ?,
        ndc = ?,
        wbs_code = ?,
        wbs_description = ?,
        booking_n = ?,
        rda_record = ?,
        last_update = ?
    WHERE id = ?;
    """, (
        data.get("title", ""),
        data.get("type", "Project"),
        data.get("status", "1) Planned"),
        data.get("urgency", "MEDIUM"),
        data.get("relevancy", 3),
        data.get("beneficiary", ""),
        data.get("cluster", ""),
        data.get("basic_kit", "Basic"),
        data.get("proto_n", ""),
        data.get("odg", "N"),
        1 if data.get("safety") else 0,
        data.get("pm", ""),
        data.get("pe", ""),
        data.get("supplier", ""),
        data.get("year_2027", ""),
        1 if data.get("year_28") else 0,
        1 if data.get("year_29") else 0,
        1 if data.get("year_30") else 0,
        1 if data.get("year_31") else 0,
        data.get("afc1", ""),
        data.get("afc2", ""),
        data.get("notes_actions", ""),
        data.get("plan_deliverables", ""),
        data.get("clarity", ""),
        data.get("ispi", ""),
        data.get("other_id", ""),
        data.get("bcr", ""),
        data.get("cr", ""),
        data.get("qsd", ""),
        data.get("ndc", ""),
        data.get("wbs_code", ""),
        data.get("wbs_description", ""),
        data.get("booking_n", ""),
        data.get("rda_record", ""),
        today,
        activity_id
    ))

    # Aggiorna Tag (Drivers, Streams, Platforms)
    cursor.execute("DELETE FROM activity_tags WHERE activity_id = ?;", (activity_id,))
    for cat in ["driver", "stream", "platform"]:
        tags_list = data.get(f"{cat}s", [])
        for t in tags_list:
            if t:
                cursor.execute(
                    "INSERT OR IGNORE INTO activity_tags (activity_id, category, tag_name) VALUES (?, ?, ?);",
                    (activity_id, cat, t)
                )

    # Aggiorna Actions
    cursor.execute("DELETE FROM actions WHERE activity_id = ?;", (activity_id,))
    for act in data.get("actions", []):
        cursor.execute("""
        INSERT INTO actions (activity_id, action_text, owner, status, target_date)
        VALUES (?, ?, ?, ?, ?);
        """, (
            activity_id,
            act.get("action_text", ""),
            act.get("owner", ""),
            act.get("status", "OPEN"),
            act.get("target_date", "")
        ))

    # Aggiorna Team
    cursor.execute("DELETE FROM team_members WHERE activity_id = ?;", (activity_id,))
    for tm in data.get("team", []):
        if tm.get("person_name") or tm.get("function_name"):
            cursor.execute("""
            INSERT INTO team_members (activity_id, function_name, person_name)
            VALUES (?, ?, ?);
            """, (
                activity_id,
                tm.get("function_name", ""),
                tm.get("person_name", "")
            ))

    # Aggiorna AFC
    afc_data = data.get("afc", {})
    for cat in ['ENG HRS', 'OTHER HRS', 'NRC VENDOR']:
        cat_data = afc_data.get(cat, {})
        cursor.execute("""
        INSERT INTO afc_records (activity_id, category, full_life, curr_bdg, curr_actual, curr_remaining, curr_forecast)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(activity_id, category) DO UPDATE SET
            full_life = excluded.full_life,
            curr_bdg = excluded.curr_bdg,
            curr_actual = excluded.curr_actual,
            curr_remaining = excluded.curr_remaining,
            curr_forecast = excluded.curr_forecast;
        """, (
            activity_id,
            cat,
            cat_data.get("full_life", ""),
            cat_data.get("curr_bdg", ""),
            cat_data.get("curr_actual", ""),
            cat_data.get("curr_remaining", ""),
            cat_data.get("curr_forecast", "")
        ))

    conn.commit()
    conn.close()
    return True
