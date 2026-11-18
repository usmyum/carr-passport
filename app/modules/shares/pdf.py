"""Render the public history as a PDF a buyer can download or print."""

from fpdf import FPDF
from fpdf.fonts import FontFace

from app.modules.shares.schemas import PublicHistory

# The built-in PDF fonts only cover Latin-1. Map the usual typographic
# characters, and anything else becomes "?" rather than failing the render.
# (Full Unicode would mean bundling a TTF font — worth it once non-Latin
# descriptions show up.)
_REPLACEMENTS = str.maketrans({
    "—": "-",
    "–": "-",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "€": "EUR ",
})


def _text(value: object) -> str:
    if value is None:
        return ""

    return (
        str(value)
        .translate(_REPLACEMENTS)
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def _km(value: int | None) -> str:
    return f"{value:,} km" if value is not None else "-"


def render_history_pdf(history: PublicHistory) -> bytes:

    vehicle = history.vehicle

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _text(f"Vehicle history: {vehicle.name}"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)

    for label, value in (
        ("VIN", vehicle.vin),
        ("Registration", vehicle.registration_number or "-"),
        ("Current mileage", _km(vehicle.current_mileage)),
        ("Owners", vehicle.owner_count),
        ("Service records", len(history.service_records)),
        ("Total spent on recorded work", f"{history.total_spend:,.2f}"),
        ("Generated", history.generated_at.strftime("%Y-%m-%d %H:%M UTC")),
    ):
        pdf.cell(55, 6, _text(label))
        pdf.cell(0, 6, _text(value), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Service history", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)

    if history.service_records:
        with pdf.table(
            col_widths=(22, 22, 25, 63, 33, 20),
            headings_style=FontFace(emphasis="BOLD"),
            text_align=("LEFT", "RIGHT", "LEFT", "LEFT", "LEFT", "RIGHT"),
        ) as table:
            table.row(["Date", "Odometer", "Type", "Work done", "Garage", "Cost"])

            for record in history.service_records:
                work = record.description

                if record.receipt_count:
                    plural = "s" if record.receipt_count > 1 else ""
                    work += f" ({record.receipt_count} receipt{plural} on file)"

                table.row([
                    record.service_date.isoformat(),
                    _km(record.odometer_reading),
                    _text(record.service_type or "-"),
                    _text(work),
                    _text(record.garage or "-"),
                    f"{record.cost:,.2f}" if record.cost is not None else "-",
                ])
    else:
        pdf.cell(0, 6, "No service records yet.", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Odometer readings", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)

    if history.mileage:
        with pdf.table(
            col_widths=(40, 40),
            width=80,
            align="LEFT",
            headings_style=FontFace(emphasis="BOLD"),
            text_align=("LEFT", "RIGHT"),
        ) as table:
            table.row(["Date", "Odometer"])

            for reading in history.mileage:
                table.row([reading.recorded_on.isoformat(), _km(reading.odometer)])
    else:
        pdf.cell(0, 6, "No readings yet.", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, _text(history.disclaimer))

    return bytes(pdf.output())
