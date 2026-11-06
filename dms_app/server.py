import http.server
import socketserver
import urllib.parse
import json
import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog

from config import load_config, save_config, get_files_dir, get_bundle_dir
import database
from excel_export import create_excel_xlsx

class DMSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # La directory dei file statici
        self.static_dir = os.path.join(get_bundle_dir(), "static")
        super().__init__(*args, directory=self.static_dir, **kwargs)

    def log_message(self, format, *args):
        # Sopprime il log su sys.stderr per evitare crash in Windows con --noconsole
        pass

    def end_headers(self):
        # Aggiungiamo header CORS e no-cache per prevenire caching nei client
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def parse_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode('utf-8'))
        return {}

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path.startswith("/api/"):
            self.handle_api_get(path, query)
        else:
            # File statici
            if path == "/" or path == "":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/"):
            self.handle_api_post(path)
        else:
            self.send_error(404, "Not Found")

    def do_PUT(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/"):
            self.handle_api_put(path)
        else:
            self.send_error(404, "Not Found")

    def do_PATCH(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/"):
            self.handle_api_patch(path)
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/"):
            self.handle_api_delete(path)
        else:
            self.send_error(404, "Not Found")

    # --- API Handlers ---

    def handle_api_get(self, path, query):
        if path == "/api/config":
            cfg = load_config()
            self.send_json(cfg)

        elif path == "/api/lookups":
            lookups = database.get_lookups()
            self.send_json(lookups)

        elif path == "/api/activities":
            search = query.get("search", [None])[0]
            urgency = query.get("urgency", [None])[0]
            status_exclude = query.get("status_exclude", [])
            type_exclude = query.get("type_exclude", [])
            expiring_in_5_days = query.get("expiring_in_5_days", ["false"])[0].lower() == "true"
            sort_by = query.get("sort_by", ["id_desc"])[0]

            acts = database.get_activities_list(
                search=search,
                urgency=urgency,
                status_exclude=status_exclude,
                type_exclude=type_exclude,
                expiring_in_5_days=expiring_in_5_days,
                sort_by=sort_by
            )
            self.send_json(acts)

        elif path.startswith("/api/activities/") and not path.endswith("/folder"):
            act_id_str = path.split("/")[3]
            try:
                act_id = int(act_id_str)
                data = database.get_activity_detail(act_id)
                if data:
                    self.send_json(data)
                else:
                    self.send_json({"error": "Attività non trovata"}, 404)
            except ValueError:
                self.send_json({"error": "ID non valido"}, 400)

        elif path == "/api/export/excel":
            search = query.get("search", [None])[0]
            urgency_list = query.get("urgency", [])
            status_exclude = query.get("status_exclude", [])
            type_exclude = query.get("type_exclude", [])
            expiring_in_5_days = query.get("expiring_in_5_days", ["false"])[0].lower() == "true"
            sort_by = query.get("sort_by", ["id_desc"])[0]

            acts = database.get_activities_list(
                search=search,
                status_exclude=status_exclude,
                type_exclude=type_exclude,
                expiring_in_5_days=expiring_in_5_days,
                sort_by=sort_by
            )

            # Filtri multi-selezione per Excel
            year_list = query.get("year", [])
            ben_list = query.get("beneficiary", [])
            clu_list = query.get("cluster", [])
            pm_list = query.get("pm", [])
            proto_list = query.get("proto", [])

            if year_list:
                acts = [a for a in acts if any(
                    (y == "2027" and a.get("year_2027") and a.get("year_2027").strip() != "") or
                    (y == "2028" and a.get("year_28") == 1) or
                    (y == "2029" and a.get("year_29") == 1) or
                    (y == "2030" and a.get("year_30") == 1) or
                    (y == "2031" and a.get("year_31") == 1)
                    for y in year_list
                )]
            if urgency_list:
                acts = [a for a in acts if a.get("urgency") in urgency_list]
            if ben_list:
                acts = [a for a in acts if a.get("beneficiary") in ben_list]
            if clu_list:
                acts = [a for a in acts if a.get("cluster") in clu_list]
            if pm_list:
                acts = [a for a in acts if a.get("pm") in pm_list]
            if proto_list:
                acts = [a for a in acts if a.get("proto_n") in proto_list]

            headers = [
                "ID", "Title", "Type", "Status", "Urgency", "Relevancy", "ODG", "Drivers",
                "PM", "PE", "Beneficiary", "Cluster", "Basic/Kit", "Proto n.", "Supplier",
                "2027", "2028", "2029", "2030", "2031", "AFC1", "AFC2", "WBS Code", "WBS Description", "Last Update"
            ]
            rows = []
            for a in acts:
                formatted_id = str(a["id"]).zfill(5)
                rows.append([
                    formatted_id,
                    a.get("title", ""),
                    a.get("type", ""),
                    a.get("status", ""),
                    a.get("urgency", ""),
                    a.get("relevancy", ""),
                    a.get("odg", "N"),
                    a.get("drivers_str", "") or "",
                    a.get("pm", ""),
                    a.get("pe", ""),
                    a.get("beneficiary", ""),
                    a.get("cluster", ""),
                    a.get("basic_kit", ""),
                    a.get("proto_n", ""),
                    a.get("supplier", ""),
                    a.get("year_2027", ""),
                    "SI" if a.get("year_28") else "NO",
                    "SI" if a.get("year_29") else "NO",
                    "SI" if a.get("year_30") else "NO",
                    "SI" if a.get("year_31") else "NO",
                    a.get("afc1", ""),
                    a.get("afc2", ""),
                    a.get("wbs_code", ""),
                    a.get("wbs_description", ""),
                    a.get("last_update", "")
                ])

            xlsx_bytes = create_excel_xlsx(headers, rows, sheet_name="DMS Database")

            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Disposition', 'attachment; filename="DMS_Export.xlsx"')
            self.end_headers()
            self.wfile.write(xlsx_bytes)

        else:
            self.send_json({"error": "Endpoint non trovato"}, 404)

    def handle_api_post(self, path):
        if path == "/api/config":
            body = self.parse_body()
            shared_dir = body.get("shared_data_dir", "").strip()
            if not shared_dir:
                self.send_json({"error": "Percorso non specificato"}, 400)
                return
            new_cfg = save_config(shared_dir)
            database.init_db()
            self.send_json({"success": True, "config": new_cfg})

        elif path == "/api/choose_folder_dialog":
            # Apre una finestra nativa Windows per selezionare la cartella
            try:
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                selected_dir = filedialog.askdirectory(title="Seleziona Cartella Dati Condivisa DMS")
                root.destroy()
                if selected_dir:
                    self.send_json({"selected_dir": os.path.abspath(selected_dir)})
                else:
                    self.send_json({"selected_dir": None})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif path == "/api/lookups":
            body = self.parse_body()
            cat = body.get("category", "")
            name = body.get("name", "")
            lid = database.add_lookup(cat, name)
            if lid:
                self.send_json({"success": True, "id": lid})
            else:
                self.send_json({"error": "Elemento già presente o non valido"}, 400)

        elif path == "/api/activities/new":
            new_id = database.create_activity()
            self.send_json({"success": True, "id": new_id, "formatted_id": str(new_id).zfill(5)})

        elif path.startswith("/api/activities/") and path.endswith("/cancel"):
            act_id_str = path.split("/")[3]
            act_id = int(act_id_str)
            res = database.cancel_activity(act_id)
            self.send_json({"success": res})

        elif path.startswith("/api/activities/") and path.endswith("/folder"):
            act_id_str = path.split("/")[3]
            act_id = int(act_id_str)
            formatted_id = str(act_id).zfill(5)
            files_root = get_files_dir()
            activity_folder = os.path.join(files_root, formatted_id)
            os.makedirs(activity_folder, exist_ok=True)

            # Apertura cartella in Esplora Risorse di Windows
            try:
                if sys.platform == "win32":
                    os.startfile(activity_folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", activity_folder])
                else:
                    subprocess.Popen(["xdg-open", activity_folder])
                self.send_json({"success": True, "path": activity_folder})
            except Exception as e:
                self.send_json({"error": f"Impossibile aprire la cartella: {e}"}, 500)

        else:
            self.send_json({"error": "Endpoint non trovato"}, 404)

    def handle_api_put(self, path):
        if path.startswith("/api/lookups/"):
            lookup_id = int(path.split("/")[3])
            body = self.parse_body()
            name = body.get("name", "")
            res = database.update_lookup(lookup_id, name)
            self.send_json({"success": res})

        elif path.startswith("/api/activities/"):
            act_id = int(path.split("/")[3])
            body = self.parse_body()
            res = database.save_full_activity(act_id, body)
            self.send_json({"success": res})

        else:
            self.send_json({"error": "Endpoint non trovato"}, 404)

    def handle_api_patch(self, path):
        if path.startswith("/api/activities/") and path.endswith("/field"):
            act_id = int(path.split("/")[3])
            body = self.parse_body()
            field_name = body.get("field")
            value = body.get("value")
            res = database.update_activity_field(act_id, field_name, value)
            self.send_json({"success": res})
        else:
            self.send_json({"error": "Endpoint non trovato"}, 404)

    def handle_api_delete(self, path):
        if path.startswith("/api/lookups/"):
            lookup_id = int(path.split("/")[3])
            res = database.delete_lookup(lookup_id)
            self.send_json({"success": res})
        else:
            self.send_json({"error": "Endpoint non trovato"}, 404)

def run_server(port=8765):
    database.init_db()
    with socketserver.ThreadingTCPServer(("", port), DMSRequestHandler) as httpd:
        print(f"DMS Server avviato su http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nArresto del server DMS...")
            httpd.shutdown()

if __name__ == "__main__":
    port = 8765
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)
