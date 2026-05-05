"""
BBS Calculation Engine
Follows IS 456:2000 and IS 2502:1963 standards.

Key formulas:
    - Hook length: 9d for 90°, 10d for 135° (IS 2502)
    - Bend deduction per 90° bend: 2d
    - Bend deduction per 135° bend: 3d (approx)
    - Stirrup cutting length: L = 2(a + b) + 2*hook - n_bend * deduction
    - Unit weight: W (kg/m) = d^2 / 162.0
"""

from __future__ import annotations
from typing import Dict, List, Any
import math


# -------- Constants (mm conversions / standards) --------
MM_PER_M = 1000.0
WEIGHT_CONSTANT = 162.0   # for kg/m given dia in mm
STANDARD_ROD_LENGTH_M = 12.0  # standard supplier rod length
WASTAGE_FACTOR = 0.05     # 5% wastage


# ---------------- Helper Calculations ----------------

def hook_length(dia: float, hook_type: int) -> float:
    """Hook length in mm. IS 2502: 90° => 9d, 135° => 10d."""
    if hook_type == 135:
        return 10.0 * dia
    return 9.0 * dia


def bend_deduction(dia: float, hook_type: int) -> float:
    """
    DEPRECATED — kept only for backward import compatibility.

    The exact IS 2502 stirrup formula `L = 2(a+b) + 2(10d) - 4(2d)`
    uses a fixed 2d deduction per bend regardless of hook type.
    Do NOT use this helper inside `calc_stirrup_length()` anymore.
    """
    return 3.0 * dia if hook_type == 135 else 2.0 * dia


def unit_weight(dia: float) -> float:
    """Unit weight in kg/m: d^2 / 162."""
    return (dia * dia) / WEIGHT_CONSTANT


def round_up(x: float, ndigits: int = 2) -> float:
    return float(round(x, ndigits))


# ---------------- Element Calculations ----------------

def calc_main_bar_length(span_mm: float, cover_mm: float,
                         dia: float, hook_type: int,
                         lap_length_mm: float = 0.0) -> float:
    """
    Cutting length of main (longitudinal) bar:
    L = span - 2*cover + 2*hook + lap
    """
    cl = span_mm - (2.0 * cover_mm) + (2.0 * hook_length(dia, hook_type)) + lap_length_mm
    return max(cl, 0.0)


def calc_distribution_bar_length(span_mm: float, cover_mm: float) -> float:
    """
    Slab distribution bar — straight bar, no hooks needed.
    L = span - 2*cover
    Per IS 456: distribution bars do not need hooks like stirrups.
    """
    cl = span_mm - (2.0 * cover_mm)
    return max(cl, 0.0)


def calc_column_main_bar_length(height_mm: float, cover_mm: float,
                                 dia: float, lap_mm: float = 0.0) -> float:
    """
    Column vertical bar cutting length per spec:
        Length = storey_height - 2*cover + lap

    Note: column verticals do NOT use 135° hooks at top/bottom (unlike beam
    longitudinal bars). They are connected to the next storey via lap splice.

    If lap is 0 (not provided), caller is responsible for substituting the
    default value of 50*d. This helper just performs the arithmetic.
    """
    cl = height_mm - (2.0 * cover_mm) + lap_mm
    return max(cl, 0.0)


DEFAULT_COLUMN_LAP_FACTOR = 50   # IS 456 cl. 26.2.5.1 — typical lap = 50·d


def bar_count_along(span_mm: float, spacing_mm: float, cover_mm: float,
                    qty_mode: str = "standard") -> int:
    """No. of bars along the given span at the given spacing (slab main/dist).
       Same three modes as stirrup_quantity().
       (qty_mode constants are defined further below; we use the string name
        directly here to avoid forward-reference ordering issues.)
    """
    if spacing_mm <= 0:
        raise ValueError("Spacing must be > 0")
    if qty_mode not in ("standard", "conservative", "exact"):
        raise ValueError(
            f"qty_mode must be one of (standard, conservative, exact), got {qty_mode!r}")

    effective = span_mm - 2.0 * cover_mm
    ratio = effective / spacing_mm

    if qty_mode == "exact":
        n = math.ceil(ratio) + 1
    elif qty_mode == "conservative":
        n = math.floor(ratio) + 2
    else:
        n = math.floor(ratio) + 1

    return max(n, 1)


def calc_stirrup_length(width_mm: float, depth_mm: float,
                        cover_mm: float, dia: float,
                        hook_type: int = 135) -> float:
    """
    Rectangular stirrup cutting length — EXACT formula per IS 2502:

        L = 2(a + b) + 2(10d) - 4(2d)

    Where:
        a = width  - 2*cover         (internal width  after cover deduction)
        b = depth  - 2*cover         (internal depth  after cover deduction)
        d = bar diameter
        2(10d) = two 135° hooks @ 10d each
        4(2d)  = bend deduction (2d per bend × 4 bends)

    For a 90° hook the leg is 9d not 10d (IS 2502).
    Bend deduction is applied ONCE per bend (4 bends total).

    Worked example (250×500 beam, cover 25, 8mm stirrup, 135° hook):
        a = 250 - 50 = 200
        b = 500 - 50 = 450
        L = 2(200+450) + 2(10·8) - 4(2·8)
          = 1300 + 160 - 64
          = 1396 mm  ✓
    """
    a = width_mm - (2.0 * cover_mm)
    b = depth_mm - (2.0 * cover_mm)
    if a <= 0 or b <= 0:
        raise ValueError("Cover is too large for the given section dimensions.")

    # Hook leg per IS 2502 — already correct in hook_length()
    hook = hook_length(dia, hook_type)            # 10d for 135°, 9d for 90°
    # Bend deduction — EXACT spec uses 2d per bend, 4 bends total
    bend_ded_per_bend = 2.0 * dia
    n_bends = 4

    L = 2.0 * (a + b) + 2.0 * hook - n_bends * bend_ded_per_bend
    return max(L, 0.0)


# Quantity calculation modes (controls how stirrup/tie/slab-bar count is rounded)
QTY_MODE_STANDARD     = "standard"      # floor(L/s) + 1   ← default per spec
QTY_MODE_CONSERVATIVE = "conservative"  # floor(L/s) + 2   ← +1 extra for safety
QTY_MODE_EXACT        = "exact"         # ceil(L/s)  + 1   ← strict math
ALLOWED_QTY_MODES = (QTY_MODE_STANDARD, QTY_MODE_CONSERVATIVE, QTY_MODE_EXACT)


def stirrup_quantity(span_mm: float, spacing_mm: float, cover_mm: float,
                     qty_mode: str = QTY_MODE_STANDARD) -> int:
    """
    No. of stirrups/ties along the length of beam/column.

    Three modes:
      - "standard"     -> floor(effective / spacing) + 1   (default)
      - "conservative" -> floor(effective / spacing) + 2   (+1 extra for site safety)
      - "exact"        -> ceil(effective / spacing) + 1    (strict mathematical)
    """
    if spacing_mm <= 0:
        raise ValueError("Spacing must be > 0")
    if qty_mode not in ALLOWED_QTY_MODES:
        raise ValueError(f"qty_mode must be one of {ALLOWED_QTY_MODES}, got {qty_mode!r}")

    effective_length = span_mm - 2.0 * cover_mm
    ratio = effective_length / spacing_mm

    if qty_mode == QTY_MODE_EXACT:
        n = math.ceil(ratio) + 1
    elif qty_mode == QTY_MODE_CONSERVATIVE:
        n = math.floor(ratio) + 2
    else:  # standard
        n = math.floor(ratio) + 1

    return max(n, 1)


# ---------------- Helpers for row creation ----------------

def _make_row(bar_mark: str, element_type: str, description: str,
              dia: float, shape: str, cl_mm: float, qty: int) -> Dict[str, Any]:
    """Build one BBS row with all derived fields (DRY helper)."""
    cl_m = cl_mm / MM_PER_M
    total_m = cl_m * qty
    weight = total_m * unit_weight(dia)
    return {
        "bar_mark": bar_mark,
        "element_type": element_type,
        "description": description,
        "dia_mm": dia,
        "shape": shape,
        "cutting_length_mm": round_up(cl_mm, 1),
        "cutting_length_m": round_up(cl_m, 3),
        "quantity": qty,
        "total_length_m": round_up(total_m, 3),
        "unit_weight_kg_m": round_up(unit_weight(dia), 3),
        "total_weight_kg": round_up(weight, 2),
    }


# ---------------- Per-Element Calculators (NO MIXING) ----------------

def calculate_beam(p: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    BEAM — main bars + stirrups ONLY.
    Never adds distribution bars.
    """
    width = float(p["width"])
    depth = float(p["depth"])
    span  = float(p["length"])
    cover = float(p["cover"])
    main_dia = float(p["main_bar_dia"])
    main_qty = int(p["main_bar_qty"])
    stir_dia = float(p["stirrup_dia"])
    stir_spc = float(p["stirrup_spacing"])
    hook_type = int(p.get("hook_type", 135))
    lap = float(p.get("lap_length", 0) or 0)
    qty_mode = str(p.get("qty_mode", QTY_MODE_STANDARD)).lower()

    rows: List[Dict[str, Any]] = []

    # Main longitudinal bars
    main_cl = calc_main_bar_length(span, cover, main_dia, hook_type, lap)
    rows.append(_make_row("M1", "beam", "Main Longitudinal Bar",
                          main_dia, "Straight w/ hooks",
                          main_cl, main_qty))

    # Stirrups (rectangular closed)
    stir_cl = calc_stirrup_length(width, depth, cover, stir_dia, hook_type)
    stir_qty = stirrup_quantity(span, stir_spc, cover, qty_mode=qty_mode)
    rows.append(_make_row("S1", "beam", "Stirrup",
                          stir_dia, f"Rect. closed ({hook_type}° hook)",
                          stir_cl, stir_qty))
    return rows


def calculate_column(p: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    COLUMN — main vertical bars + lateral ties ONLY.
    Per spec:
      Main bar length = storey_height - 2*cover + lap
        (NO 135° hooks at ends — column verticals lap to next storey instead)
        If lap not provided -> default = 50 * dia (IS 456 cl. 26.2.5.1)
      Tie length     = 2(a+b) + 2(10d) - 4(2d)   [same as stirrup]
      Tie quantity   = ceil(height / spacing) + 1
    """
    width = float(p["width"])
    depth = float(p["depth"])
    height = float(p["length"])      # for column, "length" = storey height
    cover = float(p["cover"])
    main_dia = float(p["main_bar_dia"])
    main_qty = int(p["main_bar_qty"])
    tie_dia = float(p["stirrup_dia"])     # same field name used for ties
    tie_spc = float(p["stirrup_spacing"])
    hook_type = int(p.get("hook_type", 135))
    qty_mode = str(p.get("qty_mode", QTY_MODE_STANDARD)).lower()

    # Default lap = 50*d if user didn't supply one
    lap_input = p.get("lap_length", 0)
    lap = float(lap_input) if lap_input not in (None, "", 0) else \
          DEFAULT_COLUMN_LAP_FACTOR * main_dia

    rows: List[Dict[str, Any]] = []

    # Main vertical bars — use column-specific formula (no hooks)
    main_cl = calc_column_main_bar_length(height, cover, main_dia, lap)
    rows.append(_make_row("M1", "column", "Main Vertical Bar",
                          main_dia, "Straight w/ lap",
                          main_cl, main_qty))

    # Lateral ties (rectangular closed) — same formula as beam stirrup
    tie_cl = calc_stirrup_length(width, depth, cover, tie_dia, hook_type)
    tie_qty = stirrup_quantity(height, tie_spc, cover, qty_mode=qty_mode)
    rows.append(_make_row("T1", "column", "Lateral Tie",
                          tie_dia, f"Rect. closed ({hook_type}° hook)",
                          tie_cl, tie_qty))
    return rows


def calculate_slab(p: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    SLAB — main bars (along shorter span) + distribution bars (along longer span) ONLY.
    Never adds stirrups.

    Required fields (slab-specific naming):
        short_span, long_span
        main_bar_dia, main_bar_spacing
        dist_bar_dia,  dist_bar_spacing

    Backward compatibility: if only `length`+`width` provided,
    short_span = min(length, width), long_span = max(length, width).
    Same fallback for spacings/diameters from old field names.
    """
    cover = float(p["cover"])
    hook_type = int(p.get("hook_type", 135))
    qty_mode = str(p.get("qty_mode", QTY_MODE_STANDARD)).lower()

    # Slab dimensions: always auto-detect (smaller=short, larger=long)
    # whether values come from explicit short_span/long_span OR legacy length+width.
    if "short_span" in p and "long_span" in p:
        s1 = float(p["short_span"]); s2 = float(p["long_span"])
    else:
        s1 = float(p["length"]); s2 = float(p["width"])
    short_span, long_span = (s1, s2) if s1 <= s2 else (s2, s1)

    main_dia = float(p["main_bar_dia"])
    # Slab main bar SPACING (not quantity). Backward-compat: use stirrup_spacing.
    main_spc = float(p.get("main_bar_spacing", p.get("stirrup_spacing")))

    # Distribution bar fields with backward-compatibility fallbacks
    dist_dia = float(p.get("dist_bar_dia",     p.get("stirrup_dia")))
    dist_spc = float(p.get("dist_bar_spacing", p.get("stirrup_spacing")))

    rows: List[Dict[str, Any]] = []

    # Main bars run ALONG the shorter span (carry primary moment)
    # Their COUNT is determined by spacing across the LONGER span.
    main_cl  = calc_main_bar_length(short_span, cover, main_dia, hook_type, 0)
    main_qty = bar_count_along(long_span, main_spc, cover, qty_mode=qty_mode)
    rows.append(_make_row("M1", "slab", "Main Bar (along shorter span)",
                          main_dia, "Straight w/ hooks",
                          main_cl, main_qty))

    # Distribution bars run ALONG the longer span (no hooks per IS 456).
    # Their COUNT is determined by spacing across the SHORTER span.
    dist_cl  = calc_distribution_bar_length(long_span, cover)
    dist_qty = bar_count_along(short_span, dist_spc, cover, qty_mode=qty_mode)
    rows.append(_make_row("D1", "slab", "Distribution Bar (along longer span)",
                          dist_dia, "Straight",
                          dist_cl, dist_qty))
    return rows


# ---------------- Final Order Engine ----------------

def build_final_order(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group BBS rows by diameter, apply 5% wastage, convert to 12 m rods (round UP)."""
    groups: Dict[float, Dict[str, float]] = {}
    for r in rows:
        d = r["dia_mm"]
        groups.setdefault(d, {"len": 0.0, "wt": 0.0})
        groups[d]["len"] += r["total_length_m"]
        groups[d]["wt"]  += r["total_weight_kg"]

    out: List[Dict[str, Any]] = []
    for dia, vals in sorted(groups.items()):
        net_len, net_wt = vals["len"], vals["wt"]
        order_len = net_len * (1.0 + WASTAGE_FACTOR)
        order_wt  = net_wt  * (1.0 + WASTAGE_FACTOR)
        rods = math.ceil(order_len / STANDARD_ROD_LENGTH_M)   # round UP
        out.append({
            "dia_mm": dia,
            "net_length_m": round_up(net_len, 2),
            "net_weight_kg": round_up(net_wt, 2),
            "wastage_pct": int(WASTAGE_FACTOR * 100),
            "order_length_m": round_up(order_len, 2),
            "order_weight_kg": round_up(order_wt, 2),
            "rods_12m_required": rods,
        })
    return out


# ---------------- Double-Check Engine ----------------

def double_check_rows(rows: List[Dict[str, Any]],
                      tolerance: float = 0.05) -> List[str]:
    """
    Recalculate each row independently from cutting_length × quantity × unit_weight
    and flag anything that drifts by more than `tolerance` kg.
    Returns list of mismatch messages (empty if all good).
    """
    issues: List[str] = []
    for r in rows:
        recomputed_total_m = (r["cutting_length_mm"] / MM_PER_M) * r["quantity"]
        recomputed_weight = recomputed_total_m * unit_weight(r["dia_mm"])

        if abs(recomputed_total_m - r["total_length_m"]) > 0.01:
            issues.append(
                f"[{r['bar_mark']}] total_length mismatch: "
                f"stored={r['total_length_m']} vs recomputed={round_up(recomputed_total_m, 3)}"
            )
        if abs(recomputed_weight - r["total_weight_kg"]) > tolerance:
            issues.append(
                f"[{r['bar_mark']}] weight mismatch: "
                f"stored={r['total_weight_kg']} vs recomputed={round_up(recomputed_weight, 2)}"
            )
    return issues


# ---------------- Master Dispatcher ----------------

# Element type -> calculator function
_DISPATCH = {
    "beam":   calculate_beam,
    "column": calculate_column,
    "slab":   calculate_slab,
}


def build_bbs(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Master entry point. Dispatches to the correct per-element calculator,
    builds the final order, and runs the double-check engine.

    Returns:
    {
      "bbs":         [...rows...],
      "final_order": [...rows...],
      "summary":     {...},
      "verification": {"passed": bool, "issues": [...]},
      "input_echo":  {...}
    }
    """
    et = str(payload["element_type"]).lower()
    if et not in _DISPATCH:
        raise ValueError(f"Unknown element_type: {et}. "
                         f"Must be one of {list(_DISPATCH)}.")

    rows = _DISPATCH[et](payload)
    final_order = build_final_order(rows)

    # Double-check
    issues = double_check_rows(rows)
    verification = {
        "passed": len(issues) == 0,
        "issues": issues,
        "method": "Independent recalculation of total_length & weight per row",
    }

    summary = {
        "element_type": et,
        "total_bars":              sum(r["quantity"] for r in rows),
        "total_length_m":          round_up(sum(r["total_length_m"] for r in rows), 2),
        "total_weight_kg_net":     round_up(sum(r["total_weight_kg"] for r in rows), 2),
        "total_weight_kg_with_wastage": round_up(
            sum(r["order_weight_kg"] for r in final_order), 2),
        "total_order_length_m":    round_up(
            sum(r["order_length_m"] for r in final_order), 2),
    }

    return {
        "bbs": rows,
        "final_order": final_order,
        "summary": summary,
        "verification": verification,
        "input_echo": payload,
    }
