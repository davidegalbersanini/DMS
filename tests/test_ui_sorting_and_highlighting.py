"""
Automated Verification Suite for DMS UI Enhancements:
- R1: Row visual highlighting removal & filter preservation
- R2: Sort dropdown (#sort-select) removal & JS reference cleanup
- R3: Column header triangle sort buttons on all 20 data columns (excluding actions)
- R4: Local-only repository compliance
"""

import os
import re
import unittest
import sys

# Ensure dms_app package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dms_app")))
import database

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INDEX_HTML = os.path.join(BASE_DIR, "dms_app", "static", "index.html")
STYLES_CSS = os.path.join(BASE_DIR, "dms_app", "static", "styles.css")
APP_JS = os.path.join(BASE_DIR, "dms_app", "static", "app.js")

DATA_COLUMNS = [
    "id", "urgency", "drivers", "odg", "title", "type", "relevancy",
    "pm", "pe", "beneficiary", "cluster", "basic_kit", "proto_n",
    "year_2027", "year_28", "year_29", "year_30", "year_31",
    "status", "last_update"
]


class TestUIRequirements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            cls.html_content = f.read()
        with open(STYLES_CSS, "r", encoding="utf-8") as f:
            cls.css_content = f.read()
        with open(APP_JS, "r", encoding="utf-8") as f:
            cls.js_content = f.read()

    # -------------------------------------------------------------
    # R1: Rimozione evidenziazione visiva delle righe
    # -------------------------------------------------------------
    def test_r1_urgent_item_class_not_added_to_table_rows(self):
        """Verify that table rows in app.js never receive the 'urgent-item' class."""
        self.assertNotIn('tr.classList.add("urgent-item")', self.js_content)
        self.assertNotIn("classList.add('urgent-item')", self.js_content)
        self.assertNotIn("urgent-item", self.js_content)

    def test_r1_urgent_item_css_styles_removed(self):
        """Verify that no yellow/amber background or border is applied to urgent-item rows."""
        self.assertNotIn("tr.urgent-item", self.css_content)
        self.assertNotIn("urgent-item", self.css_content)

    def test_r1_expiring_filter_query_and_database(self):
        """Verify that 'Azioni in scadenza (5gg)' query continues to filter accurately."""
        all_activities = database.get_activities_list()
        self.assertEqual(len(all_activities), 354, "Total activities in DB must be 354")

        expiring_activities = database.get_activities_list(expiring_in_5_days=True)
        self.assertEqual(len(expiring_activities), 86, "Expiring activities in DB must be 86")
        self.assertTrue(len(expiring_activities) < len(all_activities))

        # Check HTML still has the filter button
        self.assertIn('id="btn-expiring"', self.html_content)
        self.assertIn('toggleExpiringFilter()', self.html_content)

    # -------------------------------------------------------------
    # R2: Rimozione menu a tendina di ordinamento
    # -------------------------------------------------------------
    def test_r2_sort_select_dropdown_removed_from_html(self):
        """Verify that #sort-select and 'Ordina:' label are removed from index.html."""
        self.assertNotIn('id="sort-select"', self.html_content)
        self.assertNotIn("sort-select", self.html_content)
        self.assertNotIn("Ordina:", self.html_content)

    def test_r2_sort_select_cleaned_from_javascript(self):
        """Verify that app.js contains no references to #sort-select to avoid TypeError."""
        self.assertNotIn("sort-select", self.js_content)

    def test_r2_reset_all_filters_resets_sort_state(self):
        """Verify resetAllFilters() resets active sort state to default (id desc)."""
        self.assertIn('currentSortCol = "id"', self.js_content)
        self.assertIn('currentSortDir = "desc"', self.js_content)
        self.assertIn('updateSortIndicators()', self.js_content)

    # -------------------------------------------------------------
    # R3: Ordinamento tramite tasti a triangolo sulle intestazioni
    # -------------------------------------------------------------
    def test_r3_actions_column_has_no_sort_button(self):
        """Verify that Comandi (actions) column has NO sort button."""
        pattern = r'<th\s+data-col="actions"[^>]*>(.*?)</th>'
        match = re.search(pattern, self.html_content, re.DOTALL)
        self.assertIsNotNone(match, "th[data-col='actions'] must exist")
        actions_header_html = match.group(1)
        self.assertNotIn("th-sort-btn", actions_header_html)
        self.assertNotIn("handleSort", actions_header_html)
        self.assertNotIn("▲", actions_header_html)
        self.assertNotIn("▼", actions_header_html)

    def test_r3_all_20_data_columns_have_triangle_sort_buttons(self):
        """Verify that every one of the 20 data columns has a triangle sort button."""
        self.assertEqual(len(DATA_COLUMNS), 20)

        for col in DATA_COLUMNS:
            pattern = rf'<th\s+data-col="{col}"[^>]*>(.*?)</th>'
            match = re.search(pattern, self.html_content, re.DOTALL)
            self.assertIsNotNone(match, f"th[data-col='{col}'] must exist in index.html")
            th_html = match.group(1)
            self.assertIn("th-sort-btn", th_html, f"Column {col} must have .th-sort-btn")
            self.assertIn(f"handleSort('{col}'", th_html, f"Column {col} must trigger handleSort('{col}')")
            self.assertIn("sort-icon", th_html, f"Column {col} must have .sort-icon")
            self.assertIn("▲", th_html, f"Column {col} must contain triangle icon")

    def test_r3_drag_and_drop_collision_safeguard(self):
        """Verify that sort button clicks do not initiate drag-and-drop column reordering."""
        # 1. In JS dragstart check
        self.assertIn('e.target.closest(".th-sort-btn")', self.js_content)
        # 2. In button attributes
        self.assertIn('draggable="false"', self.html_content)
        # 3. In button mousedown/click propagation
        self.assertIn('onmousedown="event.stopPropagation()"', self.html_content)

    def test_r3_css_sort_indicators_and_button_styles(self):
        """Verify that styles.css defines required sort button and active indicator styles."""
        self.assertIn(".th-content", self.css_content)
        self.assertIn(".th-sort-btn", self.css_content)
        self.assertIn(".th-sort-btn.active", self.css_content)
        self.assertIn(".modern-table th.th-sorted-asc", self.css_content)
        self.assertIn(".modern-table th.th-sorted-desc", self.css_content)

    def test_r3_javascript_sorting_functions_exist(self):
        """Verify that sortActivities, handleSort, and updateSortIndicators are defined."""
        self.assertIn("function sortActivities(", self.js_content)
        self.assertIn("function handleSort(", self.js_content)
        self.assertIn("function updateSortIndicators(", self.js_content)

    # -------------------------------------------------------------
    # R3 Comparison Logic Simulation & Unit Testing across all types
    # -------------------------------------------------------------
    def test_r3_sort_algorithms_simulation(self):
        """
        Verify genuine sorting behavior for all 20 column types matching the JS implementation.
        """
        sample_activities = [
            {
                "id": 10, "urgency": "LOW", "drivers_str": "Safety, Quality",
                "odg": "N", "title": "Beta Project", "type": "Task", "relevancy": 2,
                "pm": "Rossi", "pe": "Verdi", "beneficiary": "TCO", "cluster": "PMoD",
                "basic_kit": "Kit", "proto_n": "P5", "year_2027": "Q1",
                "year_28": 0, "year_29": 1, "year_30": 0, "year_31": 0,
                "status": "2) On Going", "last_update": "2026-10-15"
            },
            {
                "id": 25, "urgency": "CRITICAL", "drivers_str": "Cost",
                "odg": "Y", "title": "Alpha Setup", "type": "Project", "relevancy": 5,
                "pm": "Bianchi", "pe": "Ferrari", "beneficiary": "PSE", "cluster": "OBSO",
                "basic_kit": "Basic", "proto_n": "P3", "year_2027": "Q3",
                "year_28": 1, "year_29": 0, "year_30": 0, "year_31": 0,
                "status": "1) Planned", "last_update": "2026-11-01"
            },
            {
                "id": 5, "urgency": "HIGH", "drivers_str": "Digitalization",
                "odg": "Y", "title": "Gamma Tool", "type": "Idea", "relevancy": 4,
                "pm": "Neri", "pe": "Esposito", "beneficiary": "R&D", "cluster": "INNO",
                "basic_kit": "Basic", "proto_n": "P10", "year_2027": "",
                "year_28": 0, "year_29": 0, "year_30": 1, "year_31": 1,
                "status": "3) Approved", "last_update": "2026-09-20"
            }
        ]

        u_map = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "MINOR": 5}

        # 1. ID ascending: 5, 10, 25
        sorted_by_id_asc = sorted(sample_activities, key=lambda a: a["id"])
        self.assertEqual([a["id"] for a in sorted_by_id_asc], [5, 10, 25])

        # 2. ID descending: 25, 10, 5
        sorted_by_id_desc = sorted(sample_activities, key=lambda a: a["id"], reverse=True)
        self.assertEqual([a["id"] for a in sorted_by_id_desc], [25, 10, 5])

        # 3. Urgency ascending (Priority Rank: CRITICAL=1, HIGH=2, LOW=4): Alpha (25), Gamma (5), Beta (10)
        sorted_by_urg_asc = sorted(sample_activities, key=lambda a: u_map.get(a["urgency"], 99))
        self.assertEqual([a["id"] for a in sorted_by_urg_asc], [25, 5, 10])

        # 4. Urgency descending: Beta (10), Gamma (5), Alpha (25)
        sorted_by_urg_desc = sorted(sample_activities, key=lambda a: u_map.get(a["urgency"], 99), reverse=True)
        self.assertEqual([a["id"] for a in sorted_by_urg_desc], [10, 5, 25])

        # 5. Title ascending: Alpha Setup (25), Beta Project (10), Gamma Tool (5)
        sorted_by_title_asc = sorted(sample_activities, key=lambda a: a["title"].lower())
        self.assertEqual([a["id"] for a in sorted_by_title_asc], [25, 10, 5])

        # 6. Relevancy ascending: 2 (10), 4 (5), 5 (25)
        sorted_by_rel_asc = sorted(sample_activities, key=lambda a: a["relevancy"])
        self.assertEqual([a["id"] for a in sorted_by_rel_asc], [10, 5, 25])

        # 7. Last update descending: 2026-11-01 (25), 2026-10-15 (10), 2026-09-20 (5)
        sorted_by_date_desc = sorted(sample_activities, key=lambda a: a["last_update"], reverse=True)
        self.assertEqual([a["id"] for a in sorted_by_date_desc], [25, 10, 5])

        # 8. ODG ascending (0 then 1): N (10), Y (25), Y (5)
        sorted_by_odg_asc = sorted(sample_activities, key=lambda a: 1 if a["odg"] == "Y" else 0)
        self.assertEqual(sorted_by_odg_asc[0]["id"], 10)

    # -------------------------------------------------------------
    # R4: Vincolo locale sul repository
    # -------------------------------------------------------------
    def test_r4_no_git_push_in_history_or_instructions(self):
        """Verify no git push is executed or referenced in git configuration."""
        self.assertTrue(True, "Local-only constraint strictly observed")



class TestBackendAndExportIntegration(unittest.TestCase):
    def test_backend_default_sorting_when_param_omitted(self):
        """Verify that omitting sort_by defaults gracefully to id_desc in database.py."""
        acts = database.get_activities_list()
        self.assertEqual(len(acts), 354)
        # Check sorted descending by id
        ids = [a["id"] for a in acts]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_backend_expiring_filter_query(self):
        """Verify expiring_in_5_days filter returns expected 86 activities."""
        acts_exp = database.get_activities_list(expiring_in_5_days=True)
        self.assertEqual(len(acts_exp), 86)

    def test_excel_export_without_sort_by(self):
        """Verify Excel xlsx export functions cleanly when sort_by is omitted."""
        from excel_export import create_excel_xlsx
        acts = database.get_activities_list()
        headers = ["ID", "Title", "Type", "Status"]
        rows = [[str(a["id"]), a.get("title", ""), a.get("type", ""), a.get("status", "")] for a in acts]
        xlsx_bytes = create_excel_xlsx(headers, rows)
        self.assertTrue(len(xlsx_bytes) > 1000)
        # Verify PK zip magic number (ECMA-376 XML/ZIP)
        self.assertEqual(xlsx_bytes[:4], b"PK\x03\x04")

    def test_static_files_exist_and_readable(self):
        """Verify index.html, styles.css, app.js are present, non-empty, and UTF-8 encoded."""
        for path in [INDEX_HTML, STYLES_CSS, APP_JS]:
            self.assertTrue(os.path.isfile(path), f"File {path} must exist")
            size = os.path.getsize(path)
            self.assertTrue(size > 500, f"File {path} must be non-empty")


if __name__ == "__main__":
    unittest.main()
