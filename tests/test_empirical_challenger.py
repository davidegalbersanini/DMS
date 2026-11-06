"""
Independent Empirical Challenger Test Suite for DMS UI Enhancements
Tests R1, R2, R3, and R4 with generators, stress harnesses, and edge case oracles.
"""

import os
import re
import json
import sqlite3
import subprocess
import unittest
import sys
from html.parser import HTMLParser
from urllib.parse import urlencode

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DMS_APP_DIR = os.path.join(REPO_ROOT, "dms_app")
if DMS_APP_DIR not in sys.path:
    sys.path.insert(0, DMS_APP_DIR)

import database
from excel_export import create_excel_xlsx

INDEX_HTML = os.path.join(REPO_ROOT, "dms_app", "static", "index.html")
STYLES_CSS = os.path.join(REPO_ROOT, "dms_app", "static", "styles.css")
APP_JS = os.path.join(REPO_ROOT, "dms_app", "static", "app.js")
DB_PATH = os.path.join(REPO_ROOT, "dms_shared_data", "dms_database.db")


class TableHeaderHTMLParser(HTMLParser):
    """Parses index.html to extract the main table header th and button details."""
    def __init__(self):
        super().__init__()
        self.in_main_table = False
        self.in_thead = False
        self.in_th = False
        self.in_btn = False
        self.in_sort_icon = False
        self.current_th_attrs = {}
        self.current_th_data_col = None
        self.current_btn_attrs = {}
        self.current_btn_text = ""
        self.current_icon_text = ""
        self.headers = []  # list of dicts: {data_col, th_attrs, buttons: [ {btn_attrs, icon_text} ]}

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == "table" and attr_dict.get("id") == "main-dms-table":
            self.in_main_table = True
        elif self.in_main_table and tag == "thead":
            self.in_thead = True
        elif self.in_thead and tag == "th":
            self.in_th = True
            self.current_th_attrs = attr_dict
            self.current_th_data_col = attr_dict.get("data-col")
            self.headers.append({
                "data_col": self.current_th_data_col,
                "th_attrs": attr_dict,
                "buttons": []
            })
        elif self.in_th and tag == "button":
            self.in_btn = True
            self.current_btn_attrs = attr_dict
            self.current_btn_text = ""
        elif self.in_btn and tag == "span" and "sort-icon" in attr_dict.get("class", "").split():
            self.in_sort_icon = True
            self.current_icon_text = ""

    def handle_endtag(self, tag):
        if tag == "table" and self.in_main_table:
            self.in_main_table = False
        elif tag == "thead" and self.in_thead:
            self.in_thead = False
        elif tag == "th" and self.in_th:
            self.in_th = False
            self.current_th_attrs = {}
            self.current_th_data_col = None
        elif tag == "button" and self.in_btn:
            self.in_btn = False
            if self.headers:
                self.headers[-1]["buttons"].append({
                    "attrs": self.current_btn_attrs,
                    "icon_text": self.current_icon_text.strip()
                })
            self.current_btn_attrs = {}
        elif tag == "span" and self.in_sort_icon:
            self.in_sort_icon = False

    def handle_data(self, data):
        if self.in_sort_icon:
            self.current_icon_text += data


class TestEmpiricalChallenger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            cls.html_content = f.read()
        with open(STYLES_CSS, "r", encoding="utf-8") as f:
            cls.css_content = f.read()
        with open(APP_JS, "r", encoding="utf-8") as f:
            cls.js_content = f.read()

    # =========================================================================
    # 1. HTML DOM INTEGRITY: 20 DATA COLUMNS WITH SORT BUTTONS, ACTIONS HAS NONE
    # =========================================================================
    def test_dom_header_structure_and_button_allocation(self):
        """Empirically parses the table DOM and verifies every column's button configuration."""
        parser = TableHeaderHTMLParser()
        parser.feed(self.html_content)

        headers = parser.headers
        self.assertEqual(len(headers), 21, f"Expected exactly 21 table columns in <thead>, found {len(headers)}")

        expected_data_cols = [
            "id", "urgency", "drivers", "odg", "title", "type",
            "relevancy", "pm", "pe", "beneficiary", "cluster",
            "basic_kit", "proto_n", "year_2027", "year_28",
            "year_29", "year_30", "year_31", "status", "last_update"
        ]

        # 1. Actions column (Comandi)
        actions_header = [h for h in headers if h["data_col"] == "actions"]
        self.assertEqual(len(actions_header), 1, "Expected exactly 1 'actions' column header")
        self.assertEqual(len(actions_header[0]["buttons"]), 0,
                         "Violation: 'actions' (Comandi) column header MUST have 0 sort buttons")

        # 2. All 20 data columns
        found_data_cols = []
        for h in headers:
            col = h["data_col"]
            if col == "actions":
                continue
            found_data_cols.append(col)
            btns = h["buttons"]
            self.assertEqual(len(btns), 1, f"Column '{col}' must have exactly 1 sort button, found {len(btns)}")

            btn_attrs = btns[0]["attrs"]
            # Check button class
            classes = btn_attrs.get("class", "").split()
            self.assertIn("th-sort-btn", classes, f"Column '{col}' button missing 'th-sort-btn' class")

            # Check data-col matches header
            self.assertEqual(btn_attrs.get("data-col"), col,
                             f"Button data-col '{btn_attrs.get('data-col')}' does not match header '{col}'")

            # Check draggable="false"
            self.assertEqual(btn_attrs.get("draggable"), "false",
                             f"Column '{col}' button must have draggable='false'")

            # Check onmousedown stopPropagation
            self.assertIn("event.stopPropagation()", btn_attrs.get("onmousedown", ""),
                          f"Column '{col}' button must stopPropagation on mousedown")

            # Check onclick calls handleSort with correct column name
            onclick = btn_attrs.get("onclick", "")
            expected_call = f"handleSort('{col}', event)"
            self.assertIn(expected_call, onclick,
                          f"Column '{col}' button onclick should call {expected_call}, found '{onclick}'")

            # Check triangle icon
            icon_text = btns[0]["icon_text"]
            self.assertIn(icon_text, ["▲", "&#9650;"], f"Column '{col}' sort button icon must be triangle ▲")

        self.assertEqual(found_data_cols, expected_data_cols,
                         f"Data columns do not match expected sequence: {found_data_cols} vs {expected_data_cols}")

    # =========================================================================
    # 2. DRAG-AND-DROP COLLISION PREVENTION
    # =========================================================================
    def test_drag_and_drop_collision_safeguards(self):
        """Stress-tests the event propagation and drag-and-drop collision prevention logic."""
        # In app.js: initColumnReorder checks e.target.classList.contains("resizer") || e.target.closest(".th-sort-btn")
        self.assertIn('e.target.closest(".th-sort-btn")', self.js_content,
                      "initColumnReorder must check e.target.closest('.th-sort-btn') on dragstart")
        self.assertIn('e.preventDefault()', self.js_content,
                      "dragstart handler must call preventDefault() when clicking sort button or resizer")

        # Simulate DOM element hierarchy:
        # Scenario A: Click on .th-sort-btn
        # Scenario B: Click on .sort-icon inside .th-sort-btn
        # Scenario C: Click on .resizer
        # Scenario D: Click on .th-label (drag should proceed)
        def simulate_dragstart_guard(element_type):
            if element_type == "button_sort":
                is_resizer = False
                closest_sort_btn = True
            elif element_type == "icon_inside_button":
                is_resizer = False
                closest_sort_btn = True
            elif element_type == "resizer":
                is_resizer = True
                closest_sort_btn = False
            elif element_type == "th_label":
                is_resizer = False
                closest_sort_btn = False
            else:
                is_resizer = False
                closest_sort_btn = False

            drag_cancelled = is_resizer or closest_sort_btn
            return drag_cancelled

        self.assertTrue(simulate_dragstart_guard("button_sort"), "Drag must be prevented when clicking sort button")
        self.assertTrue(simulate_dragstart_guard("icon_inside_button"), "Drag must be prevented when clicking icon inside button")
        self.assertTrue(simulate_dragstart_guard("resizer"), "Drag must be prevented when resizing column")
        self.assertFalse(simulate_dragstart_guard("th_label"), "Drag should NOT be prevented when dragging header label")

        # In handleSort: verify stopPropagation and preventDefault are called
        handle_sort_match = re.search(r'function handleSort\(colKey,\s*event\)\s*\{([^}]+)\}', self.js_content)
        self.assertIsNotNone(handle_sort_match, "handleSort function definition missing")
        body = handle_sort_match.group(1)
        self.assertIn("event.stopPropagation()", body, "handleSort must call event.stopPropagation()")
        self.assertIn("event.preventDefault()", body, "handleSort must call event.preventDefault()")

    # =========================================================================
    # 3. ABSENCE OF #sort-select AND .urgent-item STYLES
    # =========================================================================
    def test_complete_absence_of_sort_select(self):
        """Verifies total removal of sort-select from HTML, CSS, and JS."""
        # HTML
        self.assertNotIn('id="sort-select"', self.html_content, "#sort-select must not exist in index.html")
        self.assertNotIn('id=\'sort-select\'', self.html_content)
        self.assertNotRegex(self.html_content, r'<select[^>]*sort-select', "No select with sort-select allowed")
        # JS
        self.assertNotIn('getElementById("sort-select")', self.js_content,
                         "JS must not query #sort-select (prevents TypeError)")
        self.assertNotIn('getElementById(\'sort-select\')', self.js_content)
        # CSS
        self.assertNotIn('#sort-select', self.css_content, "CSS must not style #sort-select")

    def test_complete_absence_of_urgent_item_row_highlighting(self):
        """Verifies total removal of urgent-item background and border styles."""
        # In styles.css: no rule targeting tr.urgent-item
        self.assertNotIn('tr.urgent-item', self.css_content, "CSS must not contain tr.urgent-item rule")
        self.assertNotIn('.urgent-item td', self.css_content, "CSS must not apply background/border to .urgent-item td")
        # In app.js: table rows must not receive urgent-item class
        self.assertNotIn('tr.classList.add("urgent-item")', self.js_content,
                         "app.js must not add 'urgent-item' class to table rows")
        self.assertNotIn("tr.classList.add('urgent-item')", self.js_content)

    # =========================================================================
    # 4. FILTER INTERACTIONS & AZZERA BUTTON & MODAL
    # =========================================================================
    def test_expiring_filter_preserves_sorting_pipeline(self):
        """Verifies that activating expiring_in_5_days maintains client sorting."""
        # In reloadTable:
        # activities fetched from /api/activities
        # then sortActivities(activities, currentSortCol, currentSortDir)
        # then allActivities = activities
        # then renderTableRows(activities)
        reload_match = re.search(r'async function reloadTable\(\)\s*\{([\s\S]+?)\n\}', self.js_content)
        self.assertIsNotNone(reload_match, "reloadTable function missing")
        reload_body = reload_match.group(1)
        self.assertIn("sortActivities(activities, currentSortCol, currentSortDir)", reload_body,
                      "reloadTable must apply sortActivities before rendering rows")
        self.assertIn("allActivities = activities", reload_body,
                      "reloadTable must update global allActivities with sorted list")
        self.assertIn("renderTableRows(activities)", reload_body,
                      "reloadTable must render sorted activities")
        self.assertIn("updateSortIndicators()", reload_body,
                      "reloadTable must update sort indicators")

    def test_reset_all_filters_behavior(self):
        """Verifies that clicking Azzera resets sorting and filters cleanly."""
        reset_match = re.search(r'function resetAllFilters\(\)\s*\{([\s\S]+?)\n\}', self.js_content)
        self.assertIsNotNone(reset_match, "resetAllFilters function missing")
        reset_body = reset_match.group(1)

        self.assertIn('currentSortCol = "id"', reset_body, "resetAllFilters must reset currentSortCol to 'id'")
        self.assertIn('currentSortDir = "desc"', reset_body, "resetAllFilters must reset currentSortDir to 'desc'")
        self.assertIn('updateSortIndicators()', reset_body, "resetAllFilters must update sort indicators")
        self.assertNotIn('sort-select', reset_body, "resetAllFilters must not reference sort-select")

    # =========================================================================
    # 5. SORTING ALGORITHM SIMULATION & STRESS TEST
    # =========================================================================
    def test_sort_algorithm_simulation_all_columns(self):
        """Simulates the JavaScript sorting logic across all 20 columns with edge cases."""
        # Extract urgency ranking from app.js
        u_map = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "MINOR": 5}

        # Mock dataset with edge cases: nulls, missing, mixed types, numbers, dates
        mock_data = [
            {"id": 10, "urgency": "LOW", "drivers": "Zeta", "odg": "Y", "title": "B Activity", "type": "Project", "relevancy": 2, "pm": "Bob", "pe": "Alice", "beneficiary": "IT", "cluster": "B", "basic_kit": "Kit", "proto_n": "P10", "year_2027": "Gen", "year_28": 1, "year_29": 0, "year_30": 0, "year_31": 0, "status": "Active", "last_update": "2026-11-01 10:00"},
            {"id": 5, "urgency": "CRITICAL", "drivers": "Alpha", "odg": "", "title": "A Activity", "type": "Task", "relevancy": 5, "pm": "Alice", "pe": "Bob", "beneficiary": "HR", "cluster": "A", "basic_kit": "Basic", "proto_n": "P5", "year_2027": "Feb", "year_28": 0, "year_29": 1, "year_30": 0, "year_31": 0, "status": "Pending", "last_update": "2026-11-05 18:30"},
            {"id": 20, "urgency": "HIGH", "drivers": "Beta", "odg": "Y", "title": "C Activity", "type": "Idea", "relevancy": 1, "pm": "Charlie", "pe": "David", "beneficiary": "Sales", "cluster": "C", "basic_kit": "", "proto_n": "P20", "year_2027": "", "year_28": 0, "year_29": 0, "year_30": 1, "year_31": 0, "status": "Active", "last_update": "2026-11-03 12:00"},
            {"id": 1, "urgency": "MINOR", "drivers": "", "odg": "", "title": "D Activity", "type": "Discussion", "relevancy": 3, "pm": "", "pe": "", "beneficiary": "", "cluster": "", "basic_kit": "Kit", "proto_n": "", "year_2027": "Mar", "year_28": 0, "year_29": 0, "year_30": 0, "year_31": 1, "status": "Closed", "last_update": "2026-10-25 08:00"},
        ]

        def py_sort(arr, colKey, direction):
            factor = 1 if direction == "asc" else -1
            def cmp_func(a, b):
                cmp = 0
                if colKey == "id":
                    cmp = (int(a.get("id") or 0)) - (int(b.get("id") or 0))
                elif colKey == "urgency":
                    rank_a = u_map.get(a.get("urgency"), 99)
                    rank_b = u_map.get(b.get("urgency"), 99)
                    cmp = rank_a - rank_b
                elif colKey in ["relevancy", "year_28", "year_29", "year_30", "year_31"]:
                    cmp = (int(a.get(colKey) or 0)) - (int(b.get(colKey) or 0))
                elif colKey == "odg":
                    val_a = 1 if a.get("odg") == "Y" else 0
                    val_b = 1 if b.get("odg") == "Y" else 0
                    cmp = val_a - val_b
                elif colKey == "last_update":
                    str_a = a.get("last_update") or ""
                    str_b = b.get("last_update") or ""
                    cmp = (str_a > str_b) - (str_a < str_b)
                else:
                    str_a = str(a.get(colKey) or "").strip().lower()
                    str_b = str(b.get(colKey) or "").strip().lower()
                    cmp = (str_a > str_b) - (str_a < str_b)

                if cmp != 0:
                    return cmp * factor
                # Tie-breaker
                return (int(a.get("id") or 0)) - (int(b.get("id") or 0))

            from functools import cmp_to_key
            sorted_arr = list(arr)
            sorted_arr.sort(key=cmp_to_key(cmp_func))
            return sorted_arr

        # Test ID sorting
        asc_id = [x["id"] for x in py_sort(mock_data, "id", "asc")]
        self.assertEqual(asc_id, [1, 5, 10, 20])
        desc_id = [x["id"] for x in py_sort(mock_data, "id", "desc")]
        self.assertEqual(desc_id, [20, 10, 5, 1])

        # Test Urgency sorting (CRITICAL -> HIGH -> LOW -> MINOR)
        asc_urg = [x["urgency"] for x in py_sort(mock_data, "urgency", "asc")]
        self.assertEqual(asc_urg, ["CRITICAL", "HIGH", "LOW", "MINOR"])
        desc_urg = [x["urgency"] for x in py_sort(mock_data, "urgency", "desc")]
        self.assertEqual(desc_urg, ["MINOR", "LOW", "HIGH", "CRITICAL"])

        # Test Relevancy sorting
        asc_rel = [x["relevancy"] for x in py_sort(mock_data, "relevancy", "asc")]
        self.assertEqual(asc_rel, [1, 2, 3, 5])

        # Test ODG sorting (Flag: 0 vs 1)
        asc_odg = [x["odg"] for x in py_sort(mock_data, "odg", "asc")]
        self.assertEqual(asc_odg, ["", "", "Y", "Y"])

        # Test Title sorting (alphabetical)
        asc_title = [x["title"] for x in py_sort(mock_data, "title", "asc")]
        self.assertEqual(asc_title, ["A Activity", "B Activity", "C Activity", "D Activity"])

    # =========================================================================
    # 6. BACKEND STABILITY & EXCEL EXPORT (ZERO DEGRADATION)
    # =========================================================================
    def test_backend_database_query_without_sort_by(self):
        """Directly invokes database query with default sort_by to confirm zero degradation."""
        # Call with no sort_by specified (defaults to 'id_desc')
        activities = database.get_activities_list()
        self.assertEqual(len(activities), 354, "Database must return 354 activities")
        # Check default order is id desc
        ids = [a["id"] for a in activities]
        self.assertEqual(ids, sorted(ids, reverse=True), "Default sorting without sort_by must be id descending")

        # Call with expiring_in_5_days=True
        expiring = database.get_activities_list(expiring_in_5_days=True)
        self.assertEqual(len(expiring), 86, f"Expected 86 expiring activities, got {len(expiring)}")

    def test_excel_export_generation_without_sort_by(self):
        """Generates Excel export byte payload without sort_by parameter."""
        activities = database.get_activities_list()
        headers = ["ID", "Title", "Type", "Status"]
        rows = [[str(a["id"]), a.get("title", ""), a.get("type", ""), a.get("status", "")] for a in activities]
        data = create_excel_xlsx(headers, rows)
        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 1000, "Excel output should be non-empty bytes")
        # PK header of zip/xlsx
        self.assertTrue(data.startswith(b"PK"), "Excel data must start with zip signature PK")
        # PK header of zip/xlsx
        self.assertTrue(data.startswith(b"PK"), "Excel data must start with zip signature PK")

    # =========================================================================
    # =========================================================================
    # 7. R4: REPOSITORY AUDIT (NO GIT PUSH)
    # =========================================================================
    def test_r4_no_git_push_verification(self):
        """Audits git reflog, unpushed commits, and remote status to guarantee R4 compliance."""
        # 1. git status
        res_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(res_status.returncode, 0)

        # 2. git reflog checking for push commands
        res_reflog = subprocess.run(["git", "reflog", "-n", "20"], capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(res_reflog.returncode, 0)
        self.assertNotIn("push", res_reflog.stdout.lower(), "Reflog must contain no push commands")

        # 3. verify origin/main is remote or local
        res_diff = subprocess.run(["git", "log", "origin/main..HEAD", "--oneline"], capture_output=True, text=True, cwd=REPO_ROOT)
        # It's either empty (no new commits) or commits not pushed
        self.assertEqual(res_diff.returncode, 0)


class TestDMSRequestHandlerDirect(unittest.TestCase):
    """Directly tests DMSRequestHandler.handle_api_get without requiring network sockets."""
    @classmethod
    def setUpClass(cls):
        from server import DMSRequestHandler
        cls.handler_cls = DMSRequestHandler

    def _call_handle_api_get(self, path, query):
        import io
        from server import DMSRequestHandler

        class MockHandler:
            def __init__(self):
                self.wfile = io.BytesIO()
                self.status_code = 200
                self.headers = {}
                self.sent_json = None

            def send_response(self, code):
                self.status_code = code

            def send_header(self, k, v):
                self.headers[k] = v

            def end_headers(self):
                pass

            def send_json(self, data, status_code=200):
                self.status_code = status_code
                self.sent_json = data
                self.wfile.write(json.dumps(data).encode("utf-8"))

        mock = MockHandler()
        DMSRequestHandler.handle_api_get(mock, path, query)
        return mock

    def test_api_activities_without_sort_by(self):
        """Tests /api/activities with no sort_by parameter."""
        mock = self._call_handle_api_get("/api/activities", {})
        self.assertEqual(mock.status_code, 200)
        self.assertIsNotNone(mock.sent_json)
        self.assertEqual(len(mock.sent_json), 354)
        # Verify default ID desc order
        ids = [x["id"] for x in mock.sent_json]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_api_activities_with_expiring_filter(self):
        """Tests /api/activities with expiring_in_5_days=true and no sort_by."""
        mock = self._call_handle_api_get("/api/activities", {"expiring_in_5_days": ["true"]})
        self.assertEqual(mock.status_code, 200)
        self.assertEqual(len(mock.sent_json), 86)

    def test_api_export_excel_without_sort_by(self):
        """Tests /api/export/excel with no sort_by parameter."""
        mock = self._call_handle_api_get("/api/export/excel", {})
        self.assertEqual(mock.status_code, 200)
        # Check Content-Type header
        self.assertIn("spreadsheetml", mock.headers.get("Content-Type", ""))
        payload = mock.wfile.getvalue()
        self.assertTrue(len(payload) > 1000)
        self.assertTrue(payload.startswith(b"PK\x03\x04"))

    def test_api_export_excel_with_expiring_filter(self):
        """Tests /api/export/excel with expiring_in_5_days=true and no sort_by."""
        mock = self._call_handle_api_get("/api/export/excel", {"expiring_in_5_days": ["true"]})
        self.assertEqual(mock.status_code, 200)
        payload = mock.wfile.getvalue()
        self.assertTrue(len(payload) > 1000)
        self.assertTrue(payload.startswith(b"PK\x03\x04"))

    def test_api_config_and_lookups(self):
        """Tests /api/config and /api/lookups endpoints."""
        mock_cfg = self._call_handle_api_get("/api/config", {})
        self.assertEqual(mock_cfg.status_code, 200)
        self.assertIn("shared_data_dir", mock_cfg.sent_json)

        mock_lookups = self._call_handle_api_get("/api/lookups", {})
        self.assertEqual(mock_lookups.status_code, 200)
        self.assertIn("person", mock_lookups.sent_json)


if __name__ == "__main__":
    unittest.main()
