"""
PDF report generator using ReportLab.
Produces a clean, construction-ready BBS report.
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak)
from datetime import datetime
import os
from typing import Dict, Any


def _styled_table(data, col_widths=None, header_bg=colors.HexColor("#1F4E78")):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.whitesmoke, colors.HexColor("#EAF1F8")]),
        ("GRID",         (0, 0), (-1, -1), 0.4, colors.grey),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 8),
        ("TOPPADDING",   (0, 0), (-1, 0), 8),
    ]))
    return t


def generate_pdf(result: Dict[str, Any], out_dir: str, project_name: str = "BBS_Report") -> str:
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{project_name}_{timestamp}.pdf"
    path = os.path.join(out_dir, filename)

    doc = SimpleDocTemplate(
        path, pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title="Bar Bending Schedule"
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"],
                        fontSize=18, textColor=colors.HexColor("#1F4E78"),
                        spaceAfter=4)
    sub = ParagraphStyle("sub", parent=styles["Normal"],
                         fontSize=9, textColor=colors.grey, spaceAfter=10)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"],
                        fontSize=13, textColor=colors.HexColor("#1F4E78"),
                        spaceBefore=10, spaceAfter=6)
    body = styles["BodyText"]

    elements = []

    # --- Header ---
    elements.append(Paragraph("Bar Bending Schedule (BBS) Report", h1))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d-%b-%Y %H:%M')} &nbsp;|&nbsp; "
        f"Element: <b>{result['summary']['element_type'].title()}</b> &nbsp;|&nbsp; "
        f"Standards: IS 456:2000, IS 2502:1963", sub))

    # --- Input echo (element-aware) ---
    inp = result["input_echo"]
    et = inp.get("element_type", "").lower()
    elements.append(Paragraph("1. Input Parameters", h2))
    inp_data = [["Parameter", "Value", "Parameter", "Value"]]

    if et == "slab":
        items = [
            ("Element", "Slab"),
            ("Cover (mm)", inp.get("cover", "-")),
            ("Shorter Span (mm)", inp.get("short_span", inp.get("width", "-"))),
            ("Longer Span (mm)",  inp.get("long_span",  inp.get("length", "-"))),
            ("Main Bar Dia (mm)",       inp.get("main_bar_dia", "-")),
            ("Main Bar Spacing (mm)",   inp.get("main_bar_spacing",
                                                inp.get("stirrup_spacing", "-"))),
            ("Dist. Bar Dia (mm)",      inp.get("dist_bar_dia",
                                                inp.get("stirrup_dia", "-"))),
            ("Dist. Bar Spacing (mm)",  inp.get("dist_bar_spacing",
                                                inp.get("stirrup_spacing", "-"))),
            ("Hook Type", f"{inp.get('hook_type', '-')}°"),
            ("Lap Length (mm)", inp.get("lap_length", 0) or 0),
        ]
    else:  # beam or column
        bar_label = "Lateral Tie" if et == "column" else "Stirrup"
        len_label = "Height (mm)" if et == "column" else "Length / Span (mm)"
        items = [
            ("Element", et.title()),
            ("Width (mm)",  inp.get("width",  "-")),
            ("Depth (mm)",  inp.get("depth",  "-")),
            (len_label,     inp.get("length", "-")),
            ("Cover (mm)",  inp.get("cover",  "-")),
            ("Main Bar Dia (mm)", inp.get("main_bar_dia", "-")),
            ("Main Bar Qty",      inp.get("main_bar_qty", "-")),
            (f"{bar_label} Dia (mm)",     inp.get("stirrup_dia", "-")),
            (f"{bar_label} Spacing (mm)", inp.get("stirrup_spacing", "-")),
            ("Hook Type", f"{inp.get('hook_type', '-')}°"),
            ("Lap Length (mm)", inp.get("lap_length", 0) or 0),
        ]
    # arrange two-column
    for i in range(0, len(items), 2):
        left = items[i]
        right = items[i + 1] if i + 1 < len(items) else ("", "")
        inp_data.append([left[0], str(left[1]), right[0], str(right[1])])
    elements.append(_styled_table(inp_data, col_widths=[55*mm, 55*mm, 55*mm, 55*mm]))
    elements.append(Spacer(1, 8))

    # --- BBS Table ---
    elements.append(Paragraph("2. Bar Bending Schedule", h2))
    bbs_headers = ["Bar Mark", "Element", "Description", "Dia (mm)", "Shape",
                   "Cutting Len (mm)", "Qty",
                   "Total Len (m)", "Unit Wt (kg/m)", "Total Wt (kg)"]
    bbs_rows = [bbs_headers]
    for r in result["bbs"]:
        bbs_rows.append([
            r["bar_mark"], r.get("element_type", "-").title(), r["description"],
            r["dia_mm"], r["shape"],
            r["cutting_length_mm"], r["quantity"],
            r["total_length_m"], r["unit_weight_kg_m"], r["total_weight_kg"],
        ])
    # totals row
    bbs_rows.append([
        "TOTAL", "", "", "", "", "", "",
        result["summary"]["total_length_m"], "",
        result["summary"]["total_weight_kg_net"]
    ])
    elements.append(_styled_table(bbs_rows))
    elements.append(Spacer(1, 8))

    # --- Final order ---
    elements.append(Paragraph("3. Final Steel Order (with 5% wastage, 12 m rods)", h2))
    fo_headers = ["Dia (mm)", "Net Length (m)", "Net Weight (kg)",
                  "Wastage %", "Order Length (m)",
                  "Order Weight (kg)", "12 m Rods"]
    fo_rows = [fo_headers]
    for r in result["final_order"]:
        fo_rows.append([
            r["dia_mm"], r["net_length_m"], r["net_weight_kg"],
            f'{r["wastage_pct"]}%', r["order_length_m"],
            r["order_weight_kg"], r["rods_12m_required"],
        ])
    fo_rows.append([
        "GRAND TOTAL", "", "", "",
        result["summary"]["total_order_length_m"],
        result["summary"]["total_weight_kg_with_wastage"], ""
    ])
    elements.append(_styled_table(fo_rows))
    elements.append(Spacer(1, 10))

    # --- Verification stamp ---
    if "verification" in result:
        v = result["verification"]
        if v["passed"]:
            stamp_color = colors.HexColor("#2E7D32")
            stamp_text = (f"<b>✓ Engineering Verified</b> — "
                          f"{v.get('method', 'Independent recalculation')} passed.")
        else:
            stamp_color = colors.HexColor("#C62828")
            stamp_text = ("<b>✗ Verification FAILED</b> — issues: "
                          + "; ".join(v.get("issues", [])))
        stamp_style = ParagraphStyle("stamp", parent=body,
                                     textColor=stamp_color, fontSize=10,
                                     spaceBefore=6, spaceAfter=6)
        elements.append(Paragraph(stamp_text, stamp_style))

    # --- Footer note ---
    elements.append(Paragraph(
        "<i>This report is auto-generated. Verify against site drawings before fabrication. "
        "Hook lengths and bend deductions follow IS 2502.</i>", body))

    doc.build(elements)
    return path
