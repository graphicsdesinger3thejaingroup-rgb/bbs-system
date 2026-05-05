"""
Test suite for BBS Automation.

Run from `backend/` directory:
    python -m unittest tests.py -v

Covers:
  - Beam: main bars + stirrups (NO distribution bars must appear)
  - Column: main bars + ties (NO stirrups labelled 'beam')
  - Slab: main bars + distribution bars (NO stirrups must appear)
  - Validator: missing fields, unit errors, geometric sanity, warnings
  - Double-check engine: weight & length recalculation
  - Final order: 5% wastage + 12 m rods rounding
"""

import unittest
import math
from services.calculator import (
    build_bbs, calculate_beam, calculate_column, calculate_slab,
    hook_length, unit_weight, calc_main_bar_length, calc_stirrup_length,
    bar_count_along, double_check_rows,
)
from services.validator import validate_payload


# ------------------ Sample inputs ------------------

BEAM_INPUT = {
    "element_type": "beam",
    "width": 300, "depth": 450, "length": 6000,
    "cover": 25,
    "main_bar_dia": 16, "main_bar_qty": 4,
    "stirrup_dia": 8, "stirrup_spacing": 150,
    "hook_type": 135, "lap_length": 0,
}

COLUMN_INPUT = {
    "element_type": "column",
    "width": 300, "depth": 300, "length": 3000,
    "cover": 40,
    "main_bar_dia": 20, "main_bar_qty": 6,
    "stirrup_dia": 8, "stirrup_spacing": 200,
    "hook_type": 135, "lap_length": 0,
}

SLAB_INPUT = {
    "element_type": "slab",
    "short_span": 3500, "long_span": 5000,
    "cover": 20,
    "main_bar_dia": 10, "main_bar_spacing": 150,
    "dist_bar_dia": 8, "dist_bar_spacing": 200,
    "hook_type": 135, "lap_length": 0,
}


# ------------------ Helpers ------------------

class HelperTests(unittest.TestCase):
    def test_hook_length_135(self):
        self.assertEqual(hook_length(16, 135), 160)        # 10d
    def test_hook_length_90(self):
        self.assertEqual(hook_length(16, 90), 144)         # 9d
    def test_unit_weight_16mm(self):
        # 16² / 162 = 1.5802...
        self.assertAlmostEqual(unit_weight(16), 256 / 162, places=4)
    def test_main_bar_length(self):
        # 6000 - 2*25 + 2*(10*16) + 0 = 6270
        self.assertEqual(calc_main_bar_length(6000, 25, 16, 135, 0), 6270)
    def test_stirrup_length_135(self):
        # 300×450 beam, cover 25, 8mm stirrup, 135° hook
        # a = 300-50 = 250, b = 450-50 = 400
        # L = 2(250+400) + 2(10·8) - 4(2·8) = 1300 + 160 - 64 = 1396
        self.assertEqual(calc_stirrup_length(300, 450, 25, 8, 135), 1396)

    def test_stirrup_length_spec_example(self):
        """Regression test for the exact IS 2502 formula example.
        Beam 250×500, cover 25, stirrup 8mm, 135° hook → 1396 mm."""
        self.assertEqual(calc_stirrup_length(250, 500, 25, 8, 135), 1396)

    def test_stirrup_no_double_subtraction(self):
        """The dia must NOT be subtracted from a/b a second time.
        Verify by checking the formula components independently."""
        # 300×450 cover=25 dia=10
        # a = 300-50 = 250, b = 450-50 = 400  (NOT minus dia)
        # L = 2(250+400) + 2(10·10) - 4(2·10) = 1300 + 200 - 80 = 1420
        self.assertEqual(calc_stirrup_length(300, 450, 25, 10, 135), 1420)

    def test_stirrup_length_90_hook(self):
        """For 90° hook, leg = 9d but bend deduction is still 2d per bend."""
        # Same beam, 90° hook
        # L = 2(250+400) + 2(9·8) - 4(2·8) = 1300 + 144 - 64 = 1380
        self.assertEqual(calc_stirrup_length(300, 450, 25, 8, 90), 1380)
    def test_bar_count_along(self):
        # DEFAULT mode = "standard" = floor + 1
        # floor((6000 - 50)/150) + 1 = floor(39.67) + 1 = 40
        self.assertEqual(bar_count_along(6000, 150, 25), 40)
        # Exact-fit: floor(6000/150) + 1 = 40 + 1 = 41
        self.assertEqual(bar_count_along(6000, 150, 0), 41)
        # Non-exact: floor(2950/200)+1 = 14+1 = 15
        self.assertEqual(bar_count_along(3000, 200, 25), 15)

    def test_bar_count_along_modes(self):
        """Verify all 3 quantity modes."""
        # 6000mm span, 150mm spacing, 25mm cover
        # effective = 5950, ratio = 39.67
        self.assertEqual(bar_count_along(6000, 150, 25, "standard"),     40)  # floor+1
        self.assertEqual(bar_count_along(6000, 150, 25, "conservative"), 41)  # floor+2
        self.assertEqual(bar_count_along(6000, 150, 25, "exact"),        41)  # ceil+1


# ------------------ BEAM ------------------

class BeamTests(unittest.TestCase):
    def test_beam_only_main_and_stirrups(self):
        rows = calculate_beam(BEAM_INPUT)
        self.assertEqual(len(rows), 2)
        bar_marks = sorted(r["bar_mark"] for r in rows)
        self.assertEqual(bar_marks, ["M1", "S1"])
        # No distribution bars in a beam
        self.assertNotIn("D1", bar_marks)

    def test_beam_full_pipeline(self):
        out = build_bbs(BEAM_INPUT)
        self.assertTrue(out["verification"]["passed"])
        self.assertEqual(len(out["bbs"]), 2)
        # Element type stamped in every row
        for r in out["bbs"]:
            self.assertEqual(r["element_type"], "beam")

    def test_beam_main_bar_known_value(self):
        out = build_bbs(BEAM_INPUT)
        m1 = next(r for r in out["bbs"] if r["bar_mark"] == "M1")
        self.assertEqual(m1["cutting_length_mm"], 6270)
        self.assertEqual(m1["quantity"], 4)
        # 25.08 m × 1.580 ≈ 39.63 kg
        self.assertAlmostEqual(m1["total_weight_kg"], 39.63, places=1)

    def test_beam_stirrup_known_value(self):
        out = build_bbs(BEAM_INPUT)
        s1 = next(r for r in out["bbs"] if r["bar_mark"] == "S1")
        # 300×450 beam, cover 25, 8mm stirrup, 135° hook
        # = 2(250+400) + 2(80) - 4(16) = 1396 mm  (per IS 2502 exact formula)
        self.assertEqual(s1["cutting_length_mm"], 1396)
        # Default mode = standard = floor((6000 - 50)/150) + 1 = 40
        self.assertEqual(s1["quantity"], 40)

    def test_beam_stirrup_qty_modes(self):
        """Verify mode toggle works through the full beam pipeline."""
        for mode, expected in [("standard", 40), ("conservative", 41), ("exact", 41)]:
            payload = {**BEAM_INPUT, "qty_mode": mode}
            out = build_bbs(payload)
            s1 = next(r for r in out["bbs"] if r["bar_mark"] == "S1")
            self.assertEqual(s1["quantity"], expected,
                msg=f"qty_mode={mode!r} expected {expected}, got {s1['quantity']}")


# ------------------ COLUMN ------------------

class ColumnTests(unittest.TestCase):
    def test_column_only_main_and_ties(self):
        rows = calculate_column(COLUMN_INPUT)
        bar_marks = sorted(r["bar_mark"] for r in rows)
        self.assertEqual(bar_marks, ["M1", "T1"])  # T1, not S1
        self.assertNotIn("D1", bar_marks)

    def test_column_descriptions(self):
        rows = calculate_column(COLUMN_INPUT)
        descs = {r["bar_mark"]: r["description"] for r in rows}
        self.assertIn("Vertical", descs["M1"])
        self.assertIn("Tie", descs["T1"])

    def test_column_full_pipeline(self):
        out = build_bbs(COLUMN_INPUT)
        self.assertTrue(out["verification"]["passed"])
        for r in out["bbs"]:
            self.assertEqual(r["element_type"], "column")

    # ----- New spec-driven tests -----

    def test_column_main_bar_no_hooks_default_lap(self):
        """Column main bar = height - 2*cover + lap. Default lap = 50*d.
        For 3000mm height, 40mm cover, 20mm dia, no lap input:
            lap = 50*20 = 1000
            CL  = 3000 - 80 + 1000 = 3920 mm
        """
        p = {**COLUMN_INPUT}
        p.pop("lap_length", None)   # ensure default kicks in
        rows = calculate_column(p)
        m1 = next(r for r in rows if r["bar_mark"] == "M1")
        self.assertEqual(m1["cutting_length_mm"], 3920)
        # Shape says "lap", not "hooks"
        self.assertIn("lap", m1["shape"].lower())
        self.assertNotIn("hook", m1["shape"].lower())

    def test_column_main_bar_explicit_lap(self):
        """When lap is explicitly given, use it (don't substitute default)."""
        p = {**COLUMN_INPUT, "lap_length": 800}
        rows = calculate_column(p)
        m1 = next(r for r in rows if r["bar_mark"] == "M1")
        # 3000 - 80 + 800 = 3720
        self.assertEqual(m1["cutting_length_mm"], 3720)

    def test_column_tie_qty_default_standard(self):
        """Default qty mode = standard = floor + 1.
        For height=3000, spacing=200, cover=40:
          floor((3000 - 80)/200) + 1 = floor(14.6) + 1 = 15
        """
        rows = calculate_column(COLUMN_INPUT)
        t1 = next(r for r in rows if r["bar_mark"] == "T1")
        self.assertEqual(t1["quantity"], 15)

    def test_column_tie_qty_modes(self):
        """Mode toggle through the full column pipeline."""
        for mode, expected in [("standard", 15), ("conservative", 16), ("exact", 16)]:
            payload = {**COLUMN_INPUT, "qty_mode": mode}
            rows = calculate_column(payload)
            t1 = next(r for r in rows if r["bar_mark"] == "T1")
            self.assertEqual(t1["quantity"], expected,
                msg=f"qty_mode={mode!r} expected {expected}, got {t1['quantity']}")

    def test_column_tie_cutting_length(self):
        """Tie uses exact stirrup formula 2(a+b)+2(10d)-4(2d)."""
        rows = calculate_column(COLUMN_INPUT)
        t1 = next(r for r in rows if r["bar_mark"] == "T1")
        # 300×300, cover 40, 8mm tie, 135°
        # a=b=300-80=220 → 2(440)+160-64 = 880+160-64 = 976
        self.assertEqual(t1["cutting_length_mm"], 976)


# ------------------ SLAB ------------------

class SlabTests(unittest.TestCase):
    def test_slab_only_main_and_distribution(self):
        rows = calculate_slab(SLAB_INPUT)
        bar_marks = sorted(r["bar_mark"] for r in rows)
        self.assertEqual(bar_marks, ["D1", "M1"])
        # No stirrups/ties in a slab
        self.assertNotIn("S1", bar_marks)
        self.assertNotIn("T1", bar_marks)

    def test_slab_distribution_has_no_hook(self):
        rows = calculate_slab(SLAB_INPUT)
        d1 = next(r for r in rows if r["bar_mark"] == "D1")
        # dist bar = long_span - 2*cover = 5000 - 40 = 4960
        self.assertEqual(d1["cutting_length_mm"], 4960)
        self.assertEqual(d1["shape"], "Straight")

    def test_slab_main_bar_uses_short_span(self):
        rows = calculate_slab(SLAB_INPUT)
        m1 = next(r for r in rows if r["bar_mark"] == "M1")
        # main bar = 3500 - 2*20 + 2*100 = 3660 mm
        self.assertEqual(m1["cutting_length_mm"], 3660)

    def test_slab_quantities(self):
        rows = calculate_slab(SLAB_INPUT)
        m1 = next(r for r in rows if r["bar_mark"] == "M1")
        d1 = next(r for r in rows if r["bar_mark"] == "D1")
        # Default mode = standard = floor + 1
        # main bars: floor((5000 - 40)/150) + 1 = floor(33.07) + 1 = 34
        self.assertEqual(m1["quantity"], 34)
        # dist bars: floor((3500 - 40)/200) + 1 = floor(17.3) + 1 = 18
        self.assertEqual(d1["quantity"], 18)

    def test_slab_qty_modes(self):
        """All 3 modes through the slab pipeline."""
        # main: ratio=33.07  → standard=34, conservative=35, exact=35
        # dist: ratio=17.30  → standard=18, conservative=19, exact=19
        cases = [
            ("standard",     34, 18),
            ("conservative", 35, 19),
            ("exact",        35, 19),
        ]
        for mode, m_exp, d_exp in cases:
            payload = {**SLAB_INPUT, "qty_mode": mode}
            rows = calculate_slab(payload)
            m1 = next(r for r in rows if r["bar_mark"] == "M1")
            d1 = next(r for r in rows if r["bar_mark"] == "D1")
            self.assertEqual(m1["quantity"], m_exp,
                msg=f"slab main mode={mode}: expected {m_exp}, got {m1['quantity']}")
            self.assertEqual(d1["quantity"], d_exp,
                msg=f"slab dist mode={mode}: expected {d_exp}, got {d1['quantity']}")

    def test_slab_full_pipeline(self):
        out = build_bbs(SLAB_INPUT)
        self.assertTrue(out["verification"]["passed"])
        for r in out["bbs"]:
            self.assertEqual(r["element_type"], "slab")

    def test_slab_backward_compat_legacy_dims(self):
        """Old payload using length+width should still work."""
        legacy = {
            "element_type": "slab",
            "length": 5000, "width": 3500,
            "cover": 20,
            "main_bar_dia": 10, "main_bar_spacing": 150,
            "dist_bar_dia": 8, "dist_bar_spacing": 200,
            "hook_type": 135,
        }
        out = build_bbs(legacy)
        self.assertEqual(len(out["bbs"]), 2)
        m1 = next(r for r in out["bbs"] if r["bar_mark"] == "M1")
        self.assertEqual(m1["cutting_length_mm"], 3660)  # short_span = 3500

    def test_slab_auto_swaps_short_long(self):
        """If user accidentally labels short_span > long_span, system should
        auto-swap so main bars use the actually-shorter dimension."""
        wrong_order = {
            **SLAB_INPUT,
            "short_span": 5000,    # user mistakenly put bigger here
            "long_span":  3500,    # and smaller here
        }
        rows = calculate_slab(wrong_order)
        m1 = next(r for r in rows if r["bar_mark"] == "M1")
        d1 = next(r for r in rows if r["bar_mark"] == "D1")
        # Main bar runs along TRUE shorter span = 3500
        # CL = 3500 - 40 + 200 = 3660
        self.assertEqual(m1["cutting_length_mm"], 3660)
        # Distribution bar runs along TRUE longer span = 5000
        # CL = 5000 - 40 = 4960
        self.assertEqual(d1["cutting_length_mm"], 4960)


# ------------------ Validator ------------------

class ValidatorTests(unittest.TestCase):
    def test_valid_beam(self):
        ok, errs, warns = validate_payload(BEAM_INPUT)
        self.assertTrue(ok)
        self.assertEqual(errs, [])

    def test_missing_field(self):
        bad = {**BEAM_INPUT}
        del bad["main_bar_dia"]
        ok, errs, _ = validate_payload(bad)
        self.assertFalse(ok)
        self.assertTrue(any("main_bar_dia" in e for e in errs))

    def test_unit_error(self):
        # All sizes given in cm — should be detected
        cm = {**BEAM_INPUT, "width": 30, "depth": 45, "length": 600,
              "cover": 2.5, "main_bar_dia": 1.6, "stirrup_dia": 0.8,
              "stirrup_spacing": 15}
        ok, errs, _ = validate_payload(cm)
        self.assertFalse(ok)
        self.assertTrue(any("cm/m" in e for e in errs))

    def test_negative_length(self):
        bad = {**BEAM_INPUT, "length": -100}
        ok, errs, _ = validate_payload(bad)
        self.assertFalse(ok)

    def test_zero_main_bar(self):
        bad = {**BEAM_INPUT, "main_bar_dia": 0}
        ok, errs, _ = validate_payload(bad)
        self.assertFalse(ok)

    def test_cover_too_large(self):
        bad = {**BEAM_INPUT, "cover": 200, "width": 300}
        ok, errs, _ = validate_payload(bad)
        self.assertFalse(ok)
        self.assertTrue(any("Cover is too large" in e for e in errs))

    def test_warning_low_cover(self):
        edge = {**BEAM_INPUT, "cover": 12}
        ok, errs, warns = validate_payload(edge)
        self.assertTrue(ok)   # 12 is in valid range [10,100], just a warning
        self.assertTrue(any("Cover" in w for w in warns))

    def test_warning_high_stirrup_spacing(self):
        edge = {**BEAM_INPUT, "stirrup_spacing": 400}
        ok, errs, warns = validate_payload(edge)
        self.assertTrue(ok)
        self.assertTrue(any("Stirrup spacing" in w for w in warns))

    def test_slab_requires_dimensions(self):
        bad = {"element_type": "slab", "cover": 20,
               "main_bar_dia": 10, "main_bar_spacing": 150,
               "dist_bar_dia": 8, "dist_bar_spacing": 200, "hook_type": 135}
        ok, errs, _ = validate_payload(bad)
        self.assertFalse(ok)
        self.assertTrue(any("short_span" in e or "length" in e for e in errs))

    # ----- Spec-driven column tests -----

    def test_column_minimum_4_bars(self):
        """IS 456 cl. 26.5.3.1.a — column needs >=4 main bars."""
        bad = {**COLUMN_INPUT, "main_bar_qty": 3}
        ok, errs, _ = validate_payload(bad)
        self.assertFalse(ok)
        self.assertTrue(any("4 main bars" in e for e in errs))

    def test_column_4_bars_passes(self):
        """Boundary — exactly 4 should be allowed."""
        good = {**COLUMN_INPUT, "main_bar_qty": 4}
        ok, errs, _ = validate_payload(good)
        self.assertTrue(ok, msg=f"errors: {errs}")

    def test_column_lap_default_warning(self):
        """If lap not provided, validator should warn about default."""
        no_lap = {k: v for k, v in COLUMN_INPUT.items() if k != "lap_length"}
        ok, errs, warns = validate_payload(no_lap)
        self.assertTrue(ok)
        self.assertTrue(any("Lap length not provided" in w for w in warns))

    def test_column_high_tie_spacing_warning(self):
        """Spec rule: warn if tie spacing > 300 mm."""
        edge = {**COLUMN_INPUT, "stirrup_spacing": 350}
        ok, errs, warns = validate_payload(edge)
        self.assertTrue(ok)
        self.assertTrue(any("Stirrup spacing" in w for w in warns))

    # ----- qty_mode tests -----

    def test_qty_mode_valid_values(self):
        for mode in ("standard", "conservative", "exact"):
            payload = {**BEAM_INPUT, "qty_mode": mode}
            ok, errs, _ = validate_payload(payload)
            self.assertTrue(ok, msg=f"mode={mode} failed: {errs}")

    def test_qty_mode_invalid_rejected(self):
        bad = {**BEAM_INPUT, "qty_mode": "aggressive"}
        ok, errs, _ = validate_payload(bad)
        self.assertFalse(ok)
        self.assertTrue(any("qty_mode" in e for e in errs))

    def test_qty_mode_conservative_emits_info_warning(self):
        good = {**BEAM_INPUT, "qty_mode": "conservative"}
        ok, errs, warns = validate_payload(good)
        self.assertTrue(ok)
        self.assertTrue(any("Conservative" in w for w in warns))

    def test_qty_mode_omitted_uses_default(self):
        """No qty_mode field = no error, defaults applied silently."""
        payload = {k: v for k, v in BEAM_INPUT.items() if k != "qty_mode"}
        ok, errs, warns = validate_payload(payload)
        self.assertTrue(ok)
        # No conservative-mode warning when mode is absent
        self.assertFalse(any("Conservative" in w for w in warns))


# ------------------ Final Order ------------------

class FinalOrderTests(unittest.TestCase):
    def test_final_order_groups_by_dia(self):
        out = build_bbs(BEAM_INPUT)
        diameters = sorted(r["dia_mm"] for r in out["final_order"])
        self.assertEqual(diameters, [8, 16])

    def test_final_order_wastage(self):
        out = build_bbs(BEAM_INPUT)
        for r in out["final_order"]:
            self.assertEqual(r["wastage_pct"], 5)
            self.assertAlmostEqual(r["order_length_m"],
                                   r["net_length_m"] * 1.05, places=1)

    def test_rods_rounded_up(self):
        out = build_bbs(BEAM_INPUT)
        for r in out["final_order"]:
            self.assertEqual(r["rods_12m_required"],
                             math.ceil(r["order_length_m"] / 12.0))


# ------------------ Double-Check ------------------

class DoubleCheckTests(unittest.TestCase):
    def test_clean_rows_pass(self):
        out = build_bbs(BEAM_INPUT)
        self.assertEqual(double_check_rows(out["bbs"]), [])

    def test_corrupted_row_detected(self):
        out = build_bbs(BEAM_INPUT)
        # Tamper with stored weight
        out["bbs"][0]["total_weight_kg"] += 100
        issues = double_check_rows(out["bbs"])
        self.assertTrue(len(issues) >= 1)
        self.assertTrue(any("weight mismatch" in i for i in issues))


if __name__ == "__main__":
    unittest.main(verbosity=2)
