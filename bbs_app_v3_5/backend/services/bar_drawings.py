"""
Bar shape drawings.

Produces ReportLab Drawing objects (vector graphics — sharp at any zoom level)
for the three bar shapes used by the BBS:

    1. straight_with_hooks  → main longitudinal bar with 90°/135° hooks at ends
    2. straight             → distribution bar (no hooks)
    3. rectangular_stirrup  → closed rectangular stirrup/tie

All dimensions are auto-scaled to fit the requested canvas size while
preserving aspect ratio. Labels (a, b, hook length, dia) are drawn alongside
so the user can see exactly what each input value represents.
"""

from reportlab.graphics.shapes import (Drawing, Line, Polygon, String, Rect, Path)
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.graphics.shapes import PolyLine
from typing import Optional


STEEL_COLOR = colors.HexColor("#1F4E78")
LABEL_COLOR = colors.HexColor("#374151")
DIM_COLOR   = colors.HexColor("#6B7280")
BAR_THICKNESS = 3.0  # visual thickness of bar line, points


def _label(x, y, text, size=8, color=LABEL_COLOR, anchor="middle"):
    """Helper to make a sharp text label."""
    s = String(x, y, str(text), fontName="Helvetica", fontSize=size, fillColor=color)
    s.textAnchor = anchor
    return s


def _dim_arrow(x1, y1, x2, y2):
    """Tiny dimension line with tick marks at both ends — used for arrows."""
    return [Line(x1, y1, x2, y2, strokeColor=DIM_COLOR, strokeWidth=0.6)]


def draw_straight_with_hooks(canvas_w: float, canvas_h: float,
                              cutting_length_mm: float,
                              hook_length_mm: float,
                              dia_mm: float,
                              hook_angle: int = 135,
                              title: str = "Main Bar") -> Drawing:
    r"""
    A horizontal main bar with hooks at both ends.

         +--------------------------------------+
       _/                                        \_
        ^                                         ^
      hook                                      hook

    The visual is purely schematic; numbers below the bar give the real values.
    """
    d = Drawing(canvas_w, canvas_h)

    # Inner-padding on the canvas (gives space for labels)
    pad_x = 10
    pad_top = 18
    pad_bot = 38

    bar_y = pad_bot + (canvas_h - pad_bot - pad_top) * 0.55
    body_left = pad_x + 14
    body_right = canvas_w - pad_x - 14
    body_len = body_right - body_left

    # Hook visual size (scaled). 135° hooks are drawn slightly longer to feel right.
    hook_visual = 10 if hook_angle == 90 else 14

    # ---- Bar body (horizontal) ----
    d.add(Line(body_left, bar_y, body_right, bar_y,
               strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
               strokeLineCap=1))

    # ---- Left hook (goes down) ----
    if hook_angle == 90:
        d.add(Line(body_left, bar_y, body_left, bar_y - hook_visual,
                   strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
                   strokeLineCap=1))
    else:  # 135°
        d.add(Line(body_left, bar_y, body_left - 6, bar_y - hook_visual,
                   strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
                   strokeLineCap=1))

    # ---- Right hook (goes down) ----
    if hook_angle == 90:
        d.add(Line(body_right, bar_y, body_right, bar_y - hook_visual,
                   strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
                   strokeLineCap=1))
    else:  # 135°
        d.add(Line(body_right, bar_y, body_right + 6, bar_y - hook_visual,
                   strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
                   strokeLineCap=1))

    # ---- Length dimension (below the bar) ----
    dim_y = bar_y - hook_visual - 12
    d.add(Line(body_left, dim_y, body_right, dim_y,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(Line(body_left, dim_y - 3, body_left, dim_y + 3,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(Line(body_right, dim_y - 3, body_right, dim_y + 3,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(_label((body_left + body_right) / 2, dim_y - 11,
                 f"L = {int(cutting_length_mm)} mm", size=8, color=LABEL_COLOR))

    # ---- Hook length labels ----
    if hook_length_mm > 0:
        d.add(_label(body_left + 2, bar_y - hook_visual - 2,
                     f"{int(hook_length_mm)}",
                     size=7, color=DIM_COLOR, anchor="start"))
        d.add(_label(body_right - 2, bar_y - hook_visual - 2,
                     f"{int(hook_length_mm)}",
                     size=7, color=DIM_COLOR, anchor="end"))

    # ---- Title at top ----
    d.add(_label(canvas_w / 2, canvas_h - 8, title, size=9, color=STEEL_COLOR))
    # Dia + hook info
    d.add(_label(canvas_w / 2, canvas_h - 20,
                 f"⌀{int(dia_mm)} mm   hook: {hook_angle}° ({int(hook_length_mm)} mm = 10·d)",
                 size=7, color=DIM_COLOR))

    return d


def draw_straight(canvas_w: float, canvas_h: float,
                  cutting_length_mm: float,
                  dia_mm: float,
                  title: str = "Distribution Bar",
                  subtitle: Optional[str] = None) -> Drawing:
    """A plain straight bar — no hooks. Used for slab distribution bars
       and column vertical bars (which are spliced via lap, not hooked)."""
    d = Drawing(canvas_w, canvas_h)

    pad_x = 12
    pad_top = 18
    pad_bot = 30

    bar_y = pad_bot + (canvas_h - pad_bot - pad_top) * 0.5
    body_left = pad_x + 6
    body_right = canvas_w - pad_x - 6

    d.add(Line(body_left, bar_y, body_right, bar_y,
               strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
               strokeLineCap=1))

    # Length dimension
    dim_y = bar_y - 14
    d.add(Line(body_left, dim_y, body_right, dim_y,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(Line(body_left, dim_y - 3, body_left, dim_y + 3,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(Line(body_right, dim_y - 3, body_right, dim_y + 3,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(_label((body_left + body_right) / 2, dim_y - 11,
                 f"L = {int(cutting_length_mm)} mm", size=8, color=LABEL_COLOR))

    # Title
    d.add(_label(canvas_w / 2, canvas_h - 8, title, size=9, color=STEEL_COLOR))
    sub = subtitle or f"⌀{int(dia_mm)} mm   straight (no hooks)"
    d.add(_label(canvas_w / 2, canvas_h - 20, sub,
                 size=7, color=DIM_COLOR))

    return d


def draw_rectangular_stirrup(canvas_w: float, canvas_h: float,
                              width_mm: float, depth_mm: float,
                              cover_mm: float, dia_mm: float,
                              cutting_length_mm: float,
                              hook_angle: int = 135,
                              title: str = "Stirrup") -> Drawing:
    """
    A rectangular closed stirrup with hooks at one corner.
    Section dimensions a (horizontal) and b (vertical) labelled.

      a = section_width  - 2·cover
      b = section_depth  - 2·cover
    """
    d = Drawing(canvas_w, canvas_h)
    a = width_mm - 2 * cover_mm
    b = depth_mm - 2 * cover_mm

    # Reserve space for labels
    pad_x = 20
    pad_top = 22
    pad_bot = 42

    avail_w = canvas_w - 2 * pad_x
    avail_h = canvas_h - pad_top - pad_bot

    # Maintain aspect ratio of a×b inside the available area
    asp = a / b if b > 0 else 1.0
    if asp >= avail_w / avail_h:
        rect_w = avail_w
        rect_h = rect_w / asp
    else:
        rect_h = avail_h
        rect_w = rect_h * asp

    rect_x = (canvas_w - rect_w) / 2
    rect_y = pad_bot + (avail_h - rect_h) / 2

    # ---- Stirrup rectangle ----
    d.add(Rect(rect_x, rect_y, rect_w, rect_h,
               strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
               fillColor=None))

    # ---- Hook visualisation at top-left corner ----
    hook_size = 8
    if hook_angle == 90:
        # 90° hook: small horizontal line going inward from top-left
        d.add(Line(rect_x, rect_y + rect_h, rect_x + hook_size, rect_y + rect_h,
                   strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
                   strokeLineCap=1))
    else:
        # 135° hook: diagonal coming inward
        d.add(Line(rect_x, rect_y + rect_h,
                   rect_x + hook_size, rect_y + rect_h - hook_size,
                   strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
                   strokeLineCap=1))

    # Mirror hook on top-right (the two free ends overlap there)
    if hook_angle == 90:
        d.add(Line(rect_x + rect_w, rect_y + rect_h,
                   rect_x + rect_w - hook_size, rect_y + rect_h,
                   strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
                   strokeLineCap=1))
    else:
        d.add(Line(rect_x + rect_w, rect_y + rect_h,
                   rect_x + rect_w - hook_size, rect_y + rect_h - hook_size,
                   strokeColor=STEEL_COLOR, strokeWidth=BAR_THICKNESS,
                   strokeLineCap=1))

    # ---- 'a' dimension at bottom ----
    dim_y = rect_y - 14
    d.add(Line(rect_x, dim_y, rect_x + rect_w, dim_y,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(Line(rect_x, dim_y - 3, rect_x, dim_y + 3,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(Line(rect_x + rect_w, dim_y - 3, rect_x + rect_w, dim_y + 3,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(_label(rect_x + rect_w / 2, dim_y - 10,
                 f"a = {int(a)} mm", size=8, color=LABEL_COLOR))

    # ---- 'b' dimension at right ----
    dim_x = rect_x + rect_w + 14
    d.add(Line(dim_x, rect_y, dim_x, rect_y + rect_h,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(Line(dim_x - 3, rect_y, dim_x + 3, rect_y,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    d.add(Line(dim_x - 3, rect_y + rect_h, dim_x + 3, rect_y + rect_h,
               strokeColor=DIM_COLOR, strokeWidth=0.6))
    # rotated label for b
    b_label = String(dim_x + 8, rect_y + rect_h / 2,
                     f"b = {int(b)} mm",
                     fontName="Helvetica", fontSize=8, fillColor=LABEL_COLOR)
    b_label.textAnchor = "start"
    d.add(b_label)

    # ---- Title + cutting length ----
    d.add(_label(canvas_w / 2, canvas_h - 8, title, size=9, color=STEEL_COLOR))
    d.add(_label(canvas_w / 2, canvas_h - 20,
                 f"⌀{int(dia_mm)} mm   {hook_angle}° hooks   "
                 f"L = {int(cutting_length_mm)} mm",
                 size=7, color=DIM_COLOR))

    return d


def make_drawing_for_row(row: dict, input_echo: dict,
                          canvas_w: float, canvas_h: float) -> Drawing:
    """Choose the right drawing function based on the bar's shape/description."""
    shape  = (row.get("shape") or "").lower()
    desc   = (row.get("description") or "").lower()
    dia    = float(row["dia_mm"])
    cl     = float(row["cutting_length_mm"])
    hook   = int(input_echo.get("hook_type", 135))

    # Stirrups / ties: rectangular closed shape
    if "rect" in shape or "stirrup" in desc or "tie" in desc:
        width = float(input_echo.get("width", 300))
        depth = float(input_echo.get("depth", 450))
        cover = float(input_echo.get("cover", 25))
        title = row.get("description", "Stirrup")
        return draw_rectangular_stirrup(canvas_w, canvas_h,
                                         width, depth, cover, dia, cl,
                                         hook_angle=hook, title=title)

    # Bars with hooks at both ends: beam main bar, slab main bar
    if "hook" in shape:
        hook_len = (10 if hook == 135 else 9) * dia
        return draw_straight_with_hooks(canvas_w, canvas_h, cl, hook_len,
                                         dia, hook_angle=hook,
                                         title=row.get("description", "Main Bar"))

    # Straight bars with NO hooks: column verticals (with lap), slab dist bars
    # ("Straight w/ lap" or "Straight" both end up here.)
    if "lap" in shape:
        subtitle = f"⌀{int(dia)} mm   straight + lap splice (no hooks)"
    else:
        subtitle = f"⌀{int(dia)} mm   straight (no hooks)"
    return draw_straight(canvas_w, canvas_h, cl, dia,
                          title=row.get("description", "Bar"),
                          subtitle=subtitle)
