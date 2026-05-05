"""
Input validator for BBS API.
Element-aware: required fields differ for beam / column / slab.
Returns hard errors (block calculation) AND soft warnings (recommend review).
"""

from typing import Dict, Any, List, Tuple


# Common required fields for ALL elements
COMMON_REQUIRED = ["element_type", "cover", "main_bar_dia", "hook_type"]

# Element-specific required fields
ELEMENT_REQUIRED = {
    "beam": ["width", "depth", "length",
             "main_bar_qty",
             "stirrup_dia", "stirrup_spacing"],
    "column": ["width", "depth", "length",
               "main_bar_qty",
               "stirrup_dia", "stirrup_spacing"],
    "slab": [
        # Either explicit short_span+long_span OR length+width
        # plus distribution bar fields (with backward-compat fallback)
    ],
}

ALLOWED_ELEMENTS = {"beam", "column", "slab"}
ALLOWED_HOOKS = {90, 135}
ALLOWED_QTY_MODES = {"standard", "conservative", "exact"}

# Sanity ranges (mm) — anything outside is almost certainly a unit error.
RANGES = {
    "width":            (50, 5000),
    "depth":            (50, 5000),
    "length":           (200, 30000),
    "short_span":       (200, 30000),
    "long_span":        (200, 30000),
    "cover":            (10, 100),
    "main_bar_dia":     (6, 50),
    "stirrup_dia":      (6, 25),
    "dist_bar_dia":     (6, 25),
    "stirrup_spacing":  (50, 500),
    "main_bar_spacing": (50, 500),
    "dist_bar_spacing": (50, 500),
    "main_bar_qty":     (1, 100),
    "lap_length":       (0, 2000),
}

# Engineering-judgment warning ranges (NOT errors)
WARNING_RULES = {
    "cover":            {"low": 15, "high": 75,
                          "msg_low":  "Cover < 15 mm is below typical IS 456 minimum for RCC.",
                          "msg_high": "Cover > 75 mm is unusual — please double-check."},
    "stirrup_spacing":  {"low": 75,  "high": 300,
                          "msg_low":  "Stirrup spacing < 75 mm is unusually tight.",
                          "msg_high": "Stirrup spacing > 300 mm exceeds typical IS 456 limits — recheck."},
    "main_bar_spacing": {"low": 75,  "high": 300,
                          "msg_low":  "Main-bar spacing < 75 mm is unusually tight.",
                          "msg_high": "Main-bar spacing > 300 mm — verify against IS 456 cl. 26.3.3."},
    "dist_bar_spacing": {"low": 75,  "high": 450,
                          "msg_low":  "Distribution-bar spacing < 75 mm is unusually tight.",
                          "msg_high": "Distribution-bar spacing > 450 mm — exceeds IS 456 limit (5d or 450mm)."},
}


def _slab_has_required(payload: Dict[str, Any]) -> List[str]:
    """Slab needs (short_span+long_span OR length+width) + main_bar_spacing
    + dist fields. Returns list of missing-field errors."""
    missing: List[str] = []

    has_explicit_spans = ("short_span" in payload and payload["short_span"] not in (None, "")
                           and "long_span" in payload and payload["long_span"] not in (None, ""))
    has_legacy_dims = ("length" in payload and payload["length"] not in (None, "")
                        and "width" in payload and payload["width"] not in (None, ""))

    if not (has_explicit_spans or has_legacy_dims):
        missing.append("Slab requires either (short_span + long_span) "
                       "or (length + width).")

    # Main bar spacing — fallback to stirrup_spacing for back-compat
    if not (payload.get("main_bar_spacing") or payload.get("stirrup_spacing")):
        missing.append("Missing required field: 'main_bar_spacing'")

    # Distribution bar dia/spacing — fallback to stirrup fields for back-compat
    if not (payload.get("dist_bar_dia") or payload.get("stirrup_dia")):
        missing.append("Missing required field: 'dist_bar_dia'")
    if not (payload.get("dist_bar_spacing") or payload.get("stirrup_spacing")):
        missing.append("Missing required field: 'dist_bar_spacing'")

    return missing


def validate_payload(payload: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Returns (ok, errors, warnings).
        ok=True  iff errors is empty.
        warnings are advisory (do NOT block calculation).
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(payload, dict):
        return False, ["Payload must be a JSON object."], []

    # 1) Common required fields
    for f in COMMON_REQUIRED:
        if f not in payload or payload[f] in (None, ""):
            errors.append(f"Missing required field: '{f}'")

    # 2) Element-type validity (must succeed before element-specific checks)
    et = str(payload.get("element_type", "")).lower()
    if et not in ALLOWED_ELEMENTS:
        errors.append(f"element_type must be one of {sorted(ALLOWED_ELEMENTS)}")
        return False, errors, warnings

    # 3) Element-specific required fields
    if et == "slab":
        errors.extend(_slab_has_required(payload))
    else:
        for f in ELEMENT_REQUIRED[et]:
            if f not in payload or payload[f] in (None, ""):
                errors.append(f"Missing required field: '{f}'")

    if errors:
        return False, errors, warnings

    # 4) Hook type
    try:
        hook = int(payload["hook_type"])
        if hook not in ALLOWED_HOOKS:
            errors.append("hook_type must be 90 or 135")
    except (ValueError, TypeError):
        errors.append("hook_type must be an integer (90 or 135)")

    # 4b) Quantity mode (optional; defaults to "standard" if absent)
    if "qty_mode" in payload and payload["qty_mode"] not in (None, ""):
        mode = str(payload["qty_mode"]).lower()
        if mode not in ALLOWED_QTY_MODES:
            errors.append(
                f"qty_mode must be one of {sorted(ALLOWED_QTY_MODES)}; got {mode!r}.")
        elif mode == "conservative":
            warnings.append(
                "Conservative mode active — adding +1 extra stirrup/tie/bar "
                "as site-safety margin.")

    # 5) Numeric range checks (catches unit errors — e.g. dia=0.012 means metres)
    OPTIONAL_ZERO_OK = {"lap_length"}
    for field, (lo, hi) in RANGES.items():
        if field not in payload or payload[field] in (None, ""):
            continue
        try:
            v = float(payload[field])
        except (ValueError, TypeError):
            errors.append(f"'{field}' must be numeric (mm).")
            continue
        if v == 0 and field in OPTIONAL_ZERO_OK:
            continue
        if v < 0:
            errors.append(f"'{field}' must be ≥ 0 mm. Negative values not allowed.")
            continue
        if v == 0 and field not in OPTIONAL_ZERO_OK:
            errors.append(f"'{field}' must be > 0 mm.")
            continue
        if v < lo or v > hi:
            errors.append(
                f"'{field}' = {v} is outside valid mm range "
                f"[{lo}, {hi}]. Did you submit in cm/m instead of mm?"
            )

    # 6) Geometric sanity (only meaningful for beam/column with width+depth)
    if et in ("beam", "column"):
        try:
            cover = float(payload["cover"])
            width = float(payload["width"])
            depth = float(payload["depth"])
            if 2 * cover >= min(width, depth):
                errors.append(
                    "Cover is too large for the section "
                    "(2*cover ≥ min(width, depth))."
                )
        except Exception:
            pass

    # 6b) COLUMN-specific structural rules (per IS 456 cl. 26.5.3)
    if et == "column":
        try:
            qty = int(payload["main_bar_qty"])
            # Minimum 4 bars in a rectangular column (IS 456 cl. 26.5.3.1.a)
            if qty < 4:
                errors.append(
                    f"Column must have a minimum of 4 main bars "
                    f"(IS 456 cl. 26.5.3.1.a). Got {qty}."
                )
        except (KeyError, ValueError, TypeError):
            pass

        # Warn if lap not provided — system will auto-default to 50d
        if not payload.get("lap_length"):
            try:
                d = float(payload["main_bar_dia"])
                warnings.append(
                    f"Lap length not provided — using default 50·d = "
                    f"{int(50 * d)} mm (IS 456 cl. 26.2.5.1)."
                )
            except (KeyError, ValueError, TypeError):
                pass

    # 7) Slab span sanity (no-op now — auto-swap handles it silently)
    # Kept block for backward compat; only emits info-level note.
    if et == "slab":
        try:
            if "short_span" in payload and "long_span" in payload:
                ss = float(payload["short_span"])
                ls = float(payload["long_span"])
                if ss > ls:
                    warnings.append(
                        f"Inputs labeled short_span ({ss}) > long_span ({ls}) — "
                        "auto-detected & swapped. Please verify your input."
                    )
        except Exception:
            pass

    # 8) Engineering-judgment warnings (advisory, not errors)
    for field, rule in WARNING_RULES.items():
        if field in payload and payload[field] not in (None, ""):
            try:
                v = float(payload[field])
                if v < rule["low"]:
                    warnings.append(rule["msg_low"])
                elif v > rule["high"]:
                    warnings.append(rule["msg_high"])
            except (ValueError, TypeError):
                pass

    return (len(errors) == 0), errors, warnings
