"""
Potato Project Topic: Excel
Excel Report Automation with openpyxl

Business question:
    Every month someone manually builds the same sales report in Excel:
    paste data, add a total row, colour the headers, add a chart, freeze the
    top row. That is 20 minutes of repetitive, error-prone clicking. Can
    Python build the exact same formatted workbook in half a second?

openpyxl writes REAL Excel files: live formulas (not just values), cell
colours, borders, column widths, conditional formatting, and native Excel
charts. The file that comes out the other end looks hand-built, not
machine-dumped, and the formulas keep working if someone edits a number.

What this script covers:
    1. Build sample regional sales data
    2. Write a formatted "Raw Data" sheet (styled header, frozen panes, autofit)
    3. Write a "Summary" sheet with LIVE Excel formulas (SUMIF, AVERAGEIFS)
    4. Conditional formatting: colour-scale and highlight rules
    5. A native Excel bar chart built from the summary
    6. Number formatting (currency, percentages) and a few guardrails

Run it with:  python "Excel Report Automation with openpyxl.py"
Requires:     openpyxl (pandas and numpy only to build the sample data)
Output:       Regional_Sales_Report.xlsx (next to this script)
"""

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT_FILE = Path(__file__).parent / "Regional_Sales_Report.xlsx"

# ---------------------------------------------------------------------
# STEP 0: Build sample data (what a CSV export would usually look like)
# ---------------------------------------------------------------------
rng = np.random.default_rng(42)
regions = ["North", "South", "East", "West"]
reps = {"North": ["Asha", "Bikram"], "South": ["Chitra", "Dev"],
       "East": ["Esha", "Farhan"], "West": ["Gita", "Harsh"]}
months = pd.period_range("2026-01", "2026-06", freq="M")

rows = []
for region in regions:
    for rep in reps[region]:
        base = rng.uniform(80000, 160000)
        for month in months:
            sales = round(base * rng.lognormal(0, 0.18), -2)
            target = round(base * 1.05, -2)
            rows.append((month.strftime("%b-%Y"), region, rep, sales, target))

data = pd.DataFrame(rows, columns=["Month", "Region", "Rep", "Sales", "Target"])
print("=" * 60)
print("STEP 0: SAMPLE DATA")
print("=" * 60)
print(data.head())
print(f"\n{len(data)} rows across {len(regions)} regions, "
      f"{sum(len(v) for v in reps.values())} reps, {len(months)} months")

# ---------------------------------------------------------------------
# A reusable style kit, so every sheet looks consistent without repeating
# the same five lines of styling code everywhere (the same instinct as
# Day 6's one-time plt.rcParams setup for matplotlib).
# ---------------------------------------------------------------------
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
TOTAL_FILL = PatternFill("solid", fgColor="D9E1F2")
TOTAL_FONT = Font(bold=True)
THIN = Side(style="thin", color="B7C3CE")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center")

def style_header_row(ws, row, n_cols):
    for col in range(1, n_cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER

def autofit_columns(ws, df, start_col=1):
    """openpyxl has no built-in autofit, so estimate a sensible width from
    the longest value in each column plus a little padding."""
    for i, col_name in enumerate(df.columns, start=start_col):
        longest = max(df[col_name].astype(str).map(len).max(), len(str(col_name)))
        ws.column_dimensions[get_column_letter(i)].width = min(longest + 3, 28)

# ---------------------------------------------------------------------
# STEP 1: "Raw Data" sheet
# ---------------------------------------------------------------------
wb = Workbook()
ws_data = wb.active
ws_data.title = "Raw Data"

for col_i, col_name in enumerate(data.columns, start=1):
    ws_data.cell(row=1, column=col_i, value=col_name)
style_header_row(ws_data, 1, len(data.columns))

for r_i, row in enumerate(data.itertuples(index=False), start=2):
    for c_i, value in enumerate(row, start=1):
        cell = ws_data.cell(row=r_i, column=c_i, value=value)
        cell.border = BORDER
        if data.columns[c_i - 1] in ("Sales", "Target"):
            cell.number_format = '#,##0'

# Freeze the header row AND the first two columns, so headers and the
# Month/Region labels stay visible while scrolling a long sheet, exactly
# what "Freeze Panes" does when a person does this by hand.
ws_data.freeze_panes = "D2"
autofit_columns(ws_data, data)
print("\n" + "=" * 60)
print("STEP 1: RAW DATA SHEET WRITTEN")
print("=" * 60)
print(f"{ws_data.max_row - 1} data rows, header styled, frozen panes at D2")

# ---------------------------------------------------------------------
# STEP 2: "Summary" sheet with LIVE Excel formulas
# ---------------------------------------------------------------------
# Crucial idea: we write FORMULAS (text starting with "="), not pre-computed
# numbers. If someone edits a number on the Raw Data sheet, every total on
# this sheet recalculates itself automatically, exactly like a real analyst
# workbook, and unlike a static CSV export.
ws_sum = wb.create_sheet("Summary")
headers = ["Region", "Total Sales", "Total Target", "Achievement %", "Avg Monthly Sales"]
for col_i, h in enumerate(headers, start=1):
    ws_sum.cell(row=1, column=col_i, value=h)
style_header_row(ws_sum, 1, len(headers))

last_data_row = ws_data.max_row  # so formulas always cover every row, even if data grows
for i, region in enumerate(regions, start=2):
    ws_sum.cell(row=i, column=1, value=region)
    # SUMIF: total sales for this region, read straight from Raw Data
    ws_sum.cell(row=i, column=2,
                value=f"=SUMIF('Raw Data'!B2:B{last_data_row},A{i},'Raw Data'!D2:D{last_data_row})")
    ws_sum.cell(row=i, column=3,
                value=f"=SUMIF('Raw Data'!B2:B{last_data_row},A{i},'Raw Data'!E2:E{last_data_row})")
    # Achievement % = Total Sales / Total Target, as a formula referencing
    # the two cells on THIS sheet, not recomputed in Python
    ws_sum.cell(row=i, column=4, value=f"=B{i}/C{i}")
    # AVERAGEIFS: average monthly sales for this region
    ws_sum.cell(row=i, column=5,
                value=f"=AVERAGEIFS('Raw Data'!D2:D{last_data_row},'Raw Data'!B2:B{last_data_row},A{i})")
    for c in range(1, 6):
        ws_sum.cell(row=i, column=c).border = BORDER

total_row = len(regions) + 2
ws_sum.cell(row=total_row, column=1, value="Company Total")
ws_sum.cell(row=total_row, column=2, value=f"=SUM(B2:B{total_row - 1})")
ws_sum.cell(row=total_row, column=3, value=f"=SUM(C2:C{total_row - 1})")
ws_sum.cell(row=total_row, column=4, value=f"=B{total_row}/C{total_row}")
ws_sum.cell(row=total_row, column=5, value=f"=AVERAGE(E2:E{total_row - 1})")
for c in range(1, 6):
    cell = ws_sum.cell(row=total_row, column=c)
    cell.fill, cell.font, cell.border = TOTAL_FILL, TOTAL_FONT, BORDER

for col in ("B", "C", "E"):
    for row in range(2, total_row + 1):
        ws_sum[f"{col}{row}"].number_format = '"Rs. "#,##0'
for row in range(2, total_row + 1):
    ws_sum[f"D{row}"].number_format = '0.0%'

summary_df = pd.DataFrame({"Region": headers})  # only used to size columns sensibly
ws_sum.column_dimensions["A"].width = 16
for col, width in zip("BCDE", [15, 15, 15, 18]):
    ws_sum.column_dimensions[col].width = width
ws_sum.freeze_panes = "A2"

print("\n" + "=" * 60)
print("STEP 2: SUMMARY SHEET WRITTEN (with live formulas)")
print("=" * 60)
print("Example formula written to cell B2:", ws_sum["B2"].value)
print("Example formula written to cell D2:", ws_sum["D2"].value)
print("These are live Excel formulas: open the file and edit a Raw Data "
      "number, and the Summary sheet recalculates on its own.")

# ---------------------------------------------------------------------
# STEP 3: Conditional formatting
# ---------------------------------------------------------------------
# Two rules, same idea as Day 6's "make the one important thing impossible
# to miss", applied with Excel's own native formatting instead of a chart.
#   (a) Colour-scale on Achievement % : a quick heat-map of who is behind.
#   (b) Highlight rule on Achievement %: flag anything below 95% in red,
#       so it draws the eye even faster than the colour scale alone.
color_scale = ColorScaleRule(
    start_type="min", start_color="F8696B",     # red  = low achievement
    mid_type="percentile", mid_value=50, mid_color="FFEB84",  # yellow = middle
    end_type="max", end_color="63BE7B",          # green = high achievement
)
ws_sum.conditional_formatting.add(f"D2:D{total_row - 1}", color_scale)

below_target = CellIsRule(
    operator="lessThan", formula=["0.95"],
    fill=PatternFill("solid", fgColor="FFC7CE"),
    font=Font(color="9C0006", bold=True),
)
ws_sum.conditional_formatting.add(f"D2:D{total_row - 1}", below_target)

print("\n" + "=" * 60)
print("STEP 3: CONDITIONAL FORMATTING ADDED")
print("=" * 60)
print("Colour scale on Achievement % (red -> yellow -> green)")
print("Highlight rule: anything below 95% achievement turns red")

# ---------------------------------------------------------------------
# STEP 4: A native Excel bar chart
# ---------------------------------------------------------------------
# This is a REAL Excel chart object (editable, resizable, clickable in
# Excel), not a picture pasted in. Reference() points at live cells, so if
# the summary formulas change, the chart updates with them.
chart = BarChart()
chart.title = "Total Sales by Region"
chart.y_axis.title = "Sales (Rs.)"
chart.x_axis.title = "Region"
chart.style = 10

data_ref = Reference(ws_sum, min_col=2, min_row=1, max_row=len(regions) + 1)
cats_ref = Reference(ws_sum, min_col=1, min_row=2, max_row=len(regions) + 1)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
chart.width, chart.height = 16, 9
ws_sum.add_chart(chart, "G2")

print("\n" + "=" * 60)
print("STEP 4: NATIVE EXCEL CHART ADDED")
print("=" * 60)
print("Bar chart placed at G2 on the Summary sheet, built from live cell references")

# ---------------------------------------------------------------------
# STEP 5: A couple of simple guardrails
# ---------------------------------------------------------------------
# Hide the sheet-selector clutter a real analyst would hide too, and make
# sure the workbook opens on the sheet a reader actually wants to see
# first, not wherever Python happened to finish writing.
wb.active = wb.sheetnames.index("Summary")
ws_sum.sheet_view.showGridLines = False

wb.save(OUT_FILE)
print("\n" + "=" * 60)
print("SAVED WORKBOOK")
print("=" * 60)
print(f"File: {OUT_FILE}")
print(f"Sheets: {wb.sheetnames} | Opens on: Summary")
print(f"Size on disk: {OUT_FILE.stat().st_size / 1024:.1f} KB")
