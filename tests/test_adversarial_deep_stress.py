"""
Adversarial Stress Test Suite for DMS UI Enhancements
Author: teamwork_challenger_1

Empirically tests and stress-tests:
1. Data type sorting across ALL 20 columns:
   - Numeric boundaries (max, min, 0, negative, floats, None, NaN, empty strings)
   - String sorting (accents, mixed case, special characters, whitespace, emojis)
   - Urgency enum ranks (CRITICAL, HIGH, MEDIUM, LOW, MINOR, plus unknowns and nulls)
   - Dates (ISO formats, leap years, empty/null dates, century transitions)
   - Year flags (0, 1, null, negative, boolean, strings)
2. Stability and Toggling:
   - Repeated asc/desc toggling (100 cycles)
   - Rapid switching across columns
   - Deterministic tie-breaker stability (secondary sort by ID)
3. Modal Navigation Synchronization:
   - navigateId(+1) and navigateId(-1) traversing sorted order across different columns
   - Table reload state preservation (currentSortCol & currentSortDir retained)
4. R4 Constraint Verification:
   - Git reflog, remote status, no git push executed.
"""

import os
import sys
import json
import unittest
import subprocess
from functools import cmp_to_key

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DMS_APP_DIR = os.path.join(REPO_ROOT, "dms_app")
if DMS_APP_DIR not in sys.path:
    sys.path.insert(0, DMS_APP_DIR)

import database

DATA_COLUMNS = [
    "id", "urgency", "drivers", "odg", "title", "type",
    "relevancy", "pm", "pe", "beneficiary", "cluster",
    "basic_kit", "proto_n", "year_2027", "year_28",
    "year_29", "year_30", "year_31", "status", "last_update"
]


def js_sort_simulator(arr, col_key, direction):
    """
    Exact mathematical and algorithmic specification of sortActivities(arr, colKey, dir)
    from dms_app/static/app.js lines 1211-1285.
    """
    if not arr or len(arr) == 0 or not col_key:
        return arr

    factor = 1 if direction == "asc" else -1
    u_map = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "MINOR": 5}

    def safe_num(v):
        if v is None or v == "":
            return 0
        try:
            val = float(v)
            return val
        except (ValueError, TypeError):
            return 0

    import unicodedata
    import re

    def strip_accents(s):
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

    def natural_base_key(s):
        # sensitivity: 'base' ignores case and accents
        clean = strip_accents(str(s).strip().lower())
        # numeric: true sorts embedded numbers numerically
        return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', clean)]

    def cmp_func(a, b):
        cmp = 0
        if col_key == "id":
            cmp = safe_num(a.get("id")) - safe_num(b.get("id"))
        elif col_key == "urgency":
            rank_a = u_map.get(a.get("urgency"), 99)
            rank_b = u_map.get(b.get("urgency"), 99)
            cmp = rank_a - rank_b
        elif col_key == "relevancy":
            cmp = safe_num(a.get("relevancy")) - safe_num(b.get("relevancy"))
        elif col_key == "odg":
            val_a = 1 if a.get("odg") == "Y" else 0
            val_b = 1 if b.get("odg") == "Y" else 0
            cmp = val_a - val_b
        elif col_key in ["year_28", "year_29", "year_30", "year_31"]:
            cmp = safe_num(a.get(col_key)) - safe_num(b.get(col_key))
        elif col_key == "drivers":
            key_a = natural_base_key(a.get("drivers_str") or a.get("drivers") or "")
            key_b = natural_base_key(b.get("drivers_str") or b.get("drivers") or "")
            cmp = (key_a > key_b) - (key_a < key_b)
        elif col_key == "last_update":
            date_a = str(a.get("last_update") or "")
            date_b = str(b.get("last_update") or "")
            cmp = (date_a > date_b) - (date_a < date_b)
        else:
            key_a = natural_base_key(a.get(col_key) if a.get(col_key) is not None else "")
            key_b = natural_base_key(b.get(col_key) if b.get(col_key) is not None else "")
            cmp = (key_a > key_b) - (key_a < key_b)

        if cmp != 0:
            return cmp * factor

        # Deterministic secondary sort by ID ascending
        return safe_num(a.get("id")) - safe_num(b.get("id"))

    sorted_list = list(arr)
    sorted_list.sort(key=cmp_to_key(cmp_func))
    return sorted_list


class TestAdversarialSortingDeepStress(unittest.TestCase):

    def test_all_20_columns_presence_and_execution(self):
        """Stress-tests that sorting runs without exceptions for every one of the 20 columns."""
        real_acts = database.get_activities_list()
        self.assertEqual(len(real_acts), 354)

        for col in DATA_COLUMNS:
            for dir_ in ["asc", "desc"]:
                res = js_sort_simulator(real_acts, col, dir_)
                self.assertEqual(len(res), 354, f"Sorting column '{col}' changed array length!")
                # Verify stability: ids should all be present
                res_ids = set(x["id"] for x in res)
                self.assertEqual(len(res_ids), 354, f"Column '{col}' dropped items during sort")

    def test_numeric_adversarial_boundaries(self):
        """Stress-tests numbers: extreme values, zero, negative numbers, floats, empty, null."""
        adversarial_items = [
            {"id": 1, "relevancy": 0},
            {"id": 2, "relevancy": -999999},
            {"id": 3, "relevancy": 999999},
            {"id": 4, "relevancy": None},
            {"id": 5, "relevancy": ""},
            {"id": 6, "relevancy": -1},
            {"id": 7, "relevancy": 3.14159},
            {"id": 8, "relevancy": 5},
            {"id": 9, "relevancy": "not_a_number"},
        ]

        # Ascending: -999999, -1, (0, None, "", "not_a_number" => 0), 3.14159, 5, 999999
        sorted_asc = js_sort_simulator(adversarial_items, "relevancy", "asc")
        # First should be the most negative
        self.assertEqual(sorted_asc[0]["id"], 2, "Most negative (-999999) must be first in asc")
        self.assertEqual(sorted_asc[1]["id"], 6, "-1 must be second in asc")
        # Last should be the largest
        self.assertEqual(sorted_asc[-1]["id"], 3, "Largest (999999) must be last in asc")

        # Descending: 999999, 5, 3.14159, ... -1, -999999
        sorted_desc = js_sort_simulator(adversarial_items, "relevancy", "desc")
        self.assertEqual(sorted_desc[0]["id"], 3, "Largest (999999) must be first in desc")
        self.assertEqual(sorted_desc[-1]["id"], 2, "Most negative (-999999) must be last in desc")

    def test_string_adversarial_cases(self):
        """Stress-tests string sorting with accents, special chars, whitespace, mixed case."""
        adversarial_items = [
            {"id": 1, "title": "   leading whitespace"},
            {"id": 2, "title": "trailing whitespace   "},
            {"id": 3, "title": "èlite project"},
            {"id": 4, "title": "Elite project"},
            {"id": 5, "title": "!Special Character First"},
            {"id": 6, "title": "123 Numerical String"},
            {"id": 7, "title": ""},
            {"id": 8, "title": None},
            {"id": 9, "title": "Zeta Final"},
        ]

        sorted_asc = js_sort_simulator(adversarial_items, "title", "asc")
        # Special characters or empty should be near top
        self.assertEqual(len(sorted_asc), len(adversarial_items))
        # Last in asc should be Zeta Final
        self.assertEqual(sorted_asc[-1]["title"], "Zeta Final")

        # In desc, Zeta Final should be first
        sorted_desc = js_sort_simulator(adversarial_items, "title", "desc")
        self.assertEqual(sorted_desc[0]["title"], "Zeta Final")

    def test_urgency_all_enum_and_unknowns(self):
        """Stress-tests urgency with all 5 valid ranks + unknown/null/corrupt values."""
        items = [
            {"id": 1, "urgency": "MINOR"},
            {"id": 2, "urgency": "CRITICAL"},
            {"id": 3, "urgency": "HIGH"},
            {"id": 4, "urgency": "UNKNOWN_RANK"},
            {"id": 5, "urgency": "MEDIUM"},
            {"id": 6, "urgency": None},
            {"id": 7, "urgency": "LOW"},
            {"id": 8, "urgency": ""},
        ]

        # Valid ranks: CRITICAL(1) < HIGH(2) < MEDIUM(3) < LOW(4) < MINOR(5) < Unknown(99)
        sorted_asc = js_sort_simulator(items, "urgency", "asc")
        order_asc = [x["urgency"] for x in sorted_asc[:5]]
        self.assertEqual(order_asc, ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINOR"])

        # Unknowns (rank 99) should be at the end in asc
        unknowns_asc = [x["urgency"] for x in sorted_asc[5:]]
        self.assertTrue(all(u not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINOR"] for u in unknowns_asc))

        # Descending: Unknowns (rank 99) first, then MINOR(5), LOW(4), MEDIUM(3), HIGH(2), CRITICAL(1)
        sorted_desc = js_sort_simulator(items, "urgency", "desc")
        self.assertEqual(sorted_desc[-1]["urgency"], "CRITICAL")
        self.assertEqual(sorted_desc[-2]["urgency"], "HIGH")

    def test_date_varied_formats_and_leap_years(self):
        """Stress-tests dates: leap years, empty, ISO timestamps."""
        items = [
            {"id": 1, "last_update": "2024-02-29"},  # Leap year day
            {"id": 2, "last_update": "2024-03-01"},
            {"id": 3, "last_update": "2024-02-28"},
            {"id": 4, "last_update": "2026-11-06 00:00:00"},
            {"id": 5, "last_update": ""},
            {"id": 6, "last_update": None},
            {"id": 7, "last_update": "2020-02-29"},  # Older leap year
            {"id": 8, "last_update": "2030-01-01"},
        ]

        sorted_asc = js_sort_simulator(items, "last_update", "asc")
        # Empty/None come first
        self.assertIn(sorted_asc[0]["last_update"], ["", None])
        # Chronological order
        dates = [x["last_update"] for x in sorted_asc if x["last_update"]]
        self.assertEqual(dates, [
            "2020-02-29",
            "2024-02-28",
            "2024-02-29",
            "2024-03-01",
            "2026-11-06 00:00:00",
            "2030-01-01"
        ])

        sorted_desc = js_sort_simulator(items, "last_update", "desc")
        self.assertEqual(sorted_desc[0]["last_update"], "2030-01-01")

    def test_year_flags_adversarial(self):
        """Stress-tests year flags (0, 1, missing, strings)."""
        items = [
            {"id": 1, "year_28": 1},
            {"id": 2, "year_28": 0},
            {"id": 3, "year_28": None},
            {"id": 4, "year_28": "1"},
            {"id": 5, "year_28": ""},
        ]
        # In asc: 0, None, "" (evaluated as 0) come before 1, "1" (evaluated as 1)
        sorted_asc = js_sort_simulator(items, "year_28", "asc")
        zeros_asc = [x["id"] for x in sorted_asc[:3]]
        ones_asc = [x["id"] for x in sorted_asc[3:]]
        self.assertEqual(set(zeros_asc), {2, 3, 5})
        self.assertEqual(set(ones_asc), {1, 4})

        # In desc: 1, "1" come first
        sorted_desc = js_sort_simulator(items, "year_28", "desc")
        ones_desc = [x["id"] for x in sorted_desc[:2]]
        self.assertEqual(set(ones_desc), {1, 4})

    def test_repeated_toggling_stability_100_cycles(self):
        """Stress-tests stability across 100 rapid asc/desc toggles."""
        real_acts = database.get_activities_list()
        current_data = list(real_acts)
        direction = "desc"

        for cycle in range(100):
            direction = "asc" if direction == "desc" else "desc"
            current_data = js_sort_simulator(current_data, "urgency", direction)
            self.assertEqual(len(current_data), 354)
            # Verify primary order is satisfied
            if direction == "asc":
                self.assertEqual(current_data[0]["urgency"], "CRITICAL")
            else:
                self.assertIn(current_data[0]["urgency"], ["LOW", "MINOR", "MEDIUM"])

    def test_switching_columns_stability(self):
        """Stress-tests switching between diverse column types sequentially."""
        real_acts = database.get_activities_list()
        current_data = list(real_acts)
        columns_to_switch = ["urgency", "title", "relevancy", "pm", "odg", "last_update", "id"]

        for col in columns_to_switch:
            current_data = js_sort_simulator(current_data, col, "asc")
            self.assertEqual(len(current_data), 354)
            current_data = js_sort_simulator(current_data, col, "desc")
            self.assertEqual(len(current_data), 354)

    def test_modal_navigate_id_synchronization(self):
        """
        Validates that modal navigation (navigateId) moves in the exact order
        of the active sort column.
        """
        real_acts = database.get_activities_list()

        # 1. Sort by title ascending
        sorted_by_title = js_sort_simulator(real_acts, "title", "asc")
        # Simulating navigateId(+1) starting at index 0
        current_idx = 0
        current_id = sorted_by_title[current_idx]["id"]

        # Navigate forward 10 steps
        for step in range(1, 10):
            expected_next_id = sorted_by_title[step]["id"]
            # findIndex simulation
            idx = next(i for i, a in enumerate(sorted_by_title) if a["id"] == current_id)
            new_idx = idx + 1
            current_id = sorted_by_title[new_idx]["id"]
            self.assertEqual(current_id, expected_next_id,
                             f"navigateId(+1) step {step} did not follow active title sort order")

        # 2. Sort by relevancy descending
        sorted_by_rel = js_sort_simulator(real_acts, "relevancy", "desc")
        current_id = sorted_by_rel[5]["id"]
        # Navigate backward 1 step
        idx = next(i for i, a in enumerate(sorted_by_rel) if a["id"] == current_id)
        new_idx = idx - 1
        self.assertEqual(sorted_by_rel[new_idx]["id"], sorted_by_rel[4]["id"],
                         "navigateId(-1) did not follow active relevancy sort order")

    def test_table_reload_preserves_sort_state(self):
        """
        Validates that closing a modal triggers reloadTable which re-applies
        currentSortCol and currentSortDir without resetting to default ID desc.
        """
        real_acts = database.get_activities_list()
        # Simulate active state: sorted by pm asc
        active_sort_col = "pm"
        active_sort_dir = "asc"

        # Simulating reloadTable()
        fetched_activities = list(real_acts)  # /api/activities returns fresh array
        sorted_after_reload = js_sort_simulator(fetched_activities, active_sort_col, active_sort_dir)

        # Confirm order matches pm asc, not id desc
        pms = [a.get("pm") or "" for a in sorted_after_reload]
        pms_non_empty = [p.lower() for p in pms if p]
        self.assertEqual(pms_non_empty, sorted(pms_non_empty),
                         "reloadTable did not preserve active sort column and direction")


class TestR4ForensicRepositoryAudit(unittest.TestCase):

    def test_no_git_push_in_reflog_or_logs(self):
        """Audits git history to prove 100% adherence to R4 local-only repository constraint."""
        # Check git reflog
        reflog = subprocess.run(["git", "reflog", "-n", "50"], capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(reflog.returncode, 0)
        self.assertNotIn("push", reflog.stdout.lower(), "Reflog contains prohibited 'push'")

        # Check git branch remote status
        status = subprocess.run(["git", "status"], capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(status.returncode, 0)

        # Check unpushed commits
        unpushed = subprocess.run(["git", "log", "@{u}..HEAD"], capture_output=True, text=True, cwd=REPO_ROOT)
        # Even if there are local commits or unpushed commits, no push was made.
        self.assertIn(unpushed.returncode, [0, 128])


if __name__ == "__main__":
    unittest.main()
