"""
excel_service.py - Generates CoA Excel reports from templates.

Uses a surgical zipfile approach to preserve ALL original XML structure:
- Edits xl/worksheets/sheet2.xml (the CoA form sheet)
- Updates only specific shared string entries by index
- Converts the date cell from numeric to text (mm/dd/yyyy)
- Does NOT touch sheet1.xml (guidelines) or any Wingdings-formatted strings
"""
import io
import re
import zipfile
import calendar
from datetime import date
from pathlib import Path
from html import escape as xml_escape

BASE_DIR    = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates_excel"
REPORTS_DIR   = BASE_DIR / "reports"
UPLOADS_DIR   = BASE_DIR / "uploads" / "signatures"

REPORTS_DIR.mkdir(exist_ok=True)

TEMPLATE_1_15  = TEMPLATES_DIR / "template_1_15.xlsx"
TEMPLATE_16_31 = TEMPLATES_DIR / "template_16_31.xlsx"

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


# ──────────────────────────────────────────────
# Period helpers
# ──────────────────────────────────────────────

def get_period_end_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def get_report_period(trigger_date: date) -> dict:
    """
    16th → report period 1-15 of the SAME month.
    1st  → report period 16-end of the PREVIOUS month.
    """
    if trigger_date.day == 16:
        year, month = trigger_date.year, trigger_date.month
        return {
            "period": "1-15",
            "month": month,
            "year": year,
            "month_name": MONTH_NAMES[month],
            "template": TEMPLATE_1_15,
        }
    else:  # day == 1
        if trigger_date.month == 1:
            year, month = trigger_date.year - 1, 12
        else:
            year, month = trigger_date.year, trigger_date.month - 1
        end_day = get_period_end_day(year, month)
        return {
            "period": f"16-{end_day}",
            "month": month,
            "year": year,
            "month_name": MONTH_NAMES[month],
            "template": TEMPLATE_16_31,
        }


# ──────────────────────────────────────────────
# Surgical XML helpers
# ──────────────────────────────────────────────

def _escape(text: str) -> str:
    return xml_escape(str(text), quote=False)


def _get_cell_ss_index(sheet_xml: str, cell_ref: str) -> int | None:
    """
    Return the shared-string index referenced by a cell (t="s"),
    or None if the cell doesn't exist or isn't a shared-string type.
    """
    pat = r'<c r="' + re.escape(cell_ref) + r'"[^>]*t="s"[^>]*><v>(\d+)</v></c>'
    m = re.search(pat, sheet_xml, re.DOTALL)
    return int(m.group(1)) if m else None


def _update_shared_string(shared_xml: str, index: int, new_value: str) -> str:
    """Replace the text content of shared-string entry at `index`."""
    # Split on <si> boundaries
    parts = re.split(r'(<si>)', shared_xml)
    # parts = [pre_text, '<si>', content+</si>, '<si>', content+</si>, ...]
    si_count = 0
    result = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if part == '<si>':
            # Next part contains content + </si>
            if si_count == index:
                # Replace this entire <si>...</si> block
                result.append('<si>')
                # Skip the old content (parts[i+1])
                i += 1
                # Find the </si> in parts[i+1] and discard everything before it
                old = parts[i]
                result.append('<t>' + _escape(new_value) + '</t></si>')
            else:
                result.append(part)
                if i + 1 < len(parts):
                    i += 1
                    result.append(parts[i])
            si_count += 1
        else:
            result.append(part)
        i += 1
    return ''.join(result)


def _add_shared_string(shared_xml: str, new_value: str) -> tuple:
    """Append a new shared-string entry and return (updated_xml, new_index)."""
    existing = len(re.findall(r'<si>', shared_xml))

    # Bump count and uniqueCount attributes
    updated = re.sub(r'count="(\d+)"', lambda m: 'count="%d"' % (int(m.group(1)) + 1), shared_xml, count=1)
    updated = re.sub(r'uniqueCount="(\d+)"', lambda m: 'uniqueCount="%d"' % (int(m.group(1)) + 1), updated, count=1)

    new_si = '<si><t>' + _escape(new_value) + '</t></si>'
    updated = updated.replace('</sst>', new_si + '</sst>', 1)
    return updated, existing


def _replace_cell_with_shared_string(sheet_xml: str, cell_ref: str, ss_index: int) -> str:
    """
    For a numeric cell that needs to become a shared-string cell.
    Replaces the entire <c ...>...</c> element, keeping the style attribute.
    """
    pat = r'(<c r="' + re.escape(cell_ref) + r'"[^>]*)(>.*?</c>|/>)'

    def replacer(m):
        tag = m.group(1)
        s_match = re.search(r's="(\d+)"', tag)
        s_attr = ' s="%s"' % s_match.group(1) if s_match else ''
        return '<c r="%s"%s t="s"><v>%d</v></c>' % (cell_ref, s_attr, ss_index)

    new_xml, _ = re.subn(pat, replacer, sheet_xml, count=1, flags=re.DOTALL)
    return new_xml


def _update_numeric_cell(sheet_xml: str, cell_ref: str, value) -> str:
    """Update the <v> value inside a numeric cell, keeping everything else."""
    pat = r'(<c r="' + re.escape(cell_ref) + r'"[^>]*>)<v>[^<]*</v>(</c>)'

    def replacer(m):
        return m.group(1) + '<v>%s</v>' % str(value) + m.group(2)

    new_xml, n = re.subn(pat, replacer, sheet_xml, count=1, flags=re.DOTALL)
    if n == 0:
        # Cell not found – insert it into the row
        row_num = int(re.search(r'\d+', cell_ref).group())
        row_pat = r'(<row[^>]*r="%d"[^>]*>)(.*?)(</row>)' % row_num
        def row_replacer(rm):
            new_cell = '<c r="%s"><v>%s</v></c>' % (cell_ref, str(value))
            return rm.group(1) + rm.group(2) + new_cell + rm.group(3)
        new_xml, _ = re.subn(row_pat, row_replacer, sheet_xml, count=1, flags=re.DOTALL)
    return new_xml


def _build_empty_drawing_xml() -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        b'<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"'
        b' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"></xdr:wsDr>'
    )


# ──────────────────────────────────────────────
# Main generation function
# ──────────────────────────────────────────────

def generate_coa_report(user, trigger_date: date = None):
    """
    Generates a CoA Excel report by surgically editing the template xlsx.

    All changes are made to xl/worksheets/sheet2.xml (the CoA form).
    xl/worksheets/sheet1.xml (the guidelines) is left completely untouched.
    Only the specific shared-string entries for our 8 fields are updated;
    all other shared strings (including Wingdings-formatted checkbox text)
    remain byte-for-byte identical.

    Returns: (output_path: Path, period_info: dict)
    """
    if trigger_date is None:
        trigger_date = date.today()

    period_info   = get_report_period(trigger_date)
    template_path = period_info["template"]

    # ── Load entire template into memory ──────────────────────
    with zipfile.ZipFile(str(template_path), 'r') as zin:
        all_files = {item.filename: (item, zin.read(item.filename))
                     for item in zin.infolist()}

    sheet2_xml = all_files['xl/worksheets/sheet2.xml'][1].decode('utf-8')
    shared_xml = all_files['xl/sharedStrings.xml'][1].decode('utf-8')

    # ── Build the 8 field values ───────────────────────────────
    date_str  = trigger_date.strftime("%m/%d/%Y")
    load_str  = str(user.total_teaching_load)

    # Map: (cell_ref, new_value, is_uppercase)
    # For shared-string cells: detect index in sheet2, update that shared string
    # For J5 (date): convert numeric cell to shared string
    # For I37 (load): update numeric value in place
    shared_string_cells = {
        "B5":  user.full_name,
        "B6":  user.department,
        "B7":  user.college,
        "G8":  period_info["month_name"],
        "J6":  user.term_school_year,
        "A31": user.full_name.upper(),
    }

    for cell_ref, new_value in shared_string_cells.items():
        ss_idx = _get_cell_ss_index(sheet2_xml, cell_ref)
        if ss_idx is not None:
            # Update the existing shared string in place
            shared_xml = _update_shared_string(shared_xml, ss_idx, new_value)
        else:
            # Cell doesn't exist as a shared string – add a new one and point cell to it
            shared_xml, ss_idx = _add_shared_string(shared_xml, new_value)
            sheet2_xml = _replace_cell_with_shared_string(sheet2_xml, cell_ref, ss_idx)

    # J5 – Date Accomplished: stored as numeric (Excel date serial) → convert to text
    shared_xml, date_ss_idx = _add_shared_string(shared_xml, date_str)
    sheet2_xml = _replace_cell_with_shared_string(sheet2_xml, "J5", date_ss_idx)

    # I37 – Teaching Load: numeric cell, just update the value
    sheet2_xml = _update_numeric_cell(sheet2_xml, "I37", load_str)

    # ── Handle e-signature image ───────────────────────────────
    if user.signature_filename:
        sig_path = UPLOADS_DIR / user.signature_filename
        if sig_path.exists():
            sig_bytes = sig_path.read_bytes()
            ext = Path(user.signature_filename).suffix.lower()
            media_key = 'xl/media/image1' + ext
            if media_key in all_files:
                info, _ = all_files[media_key]
                all_files[media_key] = (info, sig_bytes)
            else:
                import zipfile as zf
                new_info = zf.ZipInfo(media_key)
                new_info.compress_type = zipfile.ZIP_DEFLATED
                all_files[media_key] = (new_info, sig_bytes)
        else:
            # Signature file missing → clear drawing so placeholder image is removed
            if 'xl/drawings/drawing1.xml' in all_files:
                info, _ = all_files['xl/drawings/drawing1.xml']
                all_files['xl/drawings/drawing1.xml'] = (info, _build_empty_drawing_xml())
    else:
        if 'xl/drawings/drawing1.xml' in all_files:
            info, _ = all_files['xl/drawings/drawing1.xml']
            all_files['xl/drawings/drawing1.xml'] = (info, _build_empty_drawing_xml())

    # ── Write output xlsx ──────────────────────────────────────
    safe_name  = user.full_name.replace(" ", "_").replace(".", "")
    period_label = period_info["period"]
    month_name   = period_info["month_name"]
    report_year  = period_info["year"]
    filename = "CoA_%s_%s%d_%s.xlsx" % (
        safe_name, month_name, report_year, period_label.replace('-', '_'))

    output_path = REPORTS_DIR / str(user.id) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for fname, (info, data) in all_files.items():
            if fname == 'xl/worksheets/sheet2.xml':
                zout.writestr(info, sheet2_xml.encode('utf-8'))
            elif fname == 'xl/sharedStrings.xml':
                zout.writestr(info, shared_xml.encode('utf-8'))
            else:
                zout.writestr(info, data)

    with open(str(output_path), 'wb') as f:
        f.write(buf.getvalue())

    return output_path, period_info
