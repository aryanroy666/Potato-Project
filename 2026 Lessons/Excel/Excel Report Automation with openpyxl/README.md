# Excel Report Automation with openpyxl

**Tools:** Python, openpyxl (Pandas and NumPy only to build the sample data)
**File:** [`Excel Report Automation with openpyxl.py`](./Excel%20Report%20Automation%20with%20openpyxl.py)
**Output:** [`Regional_Sales_Report.xlsx`](./Regional_Sales_Report.xlsx)

## What I Learned

Every month, someone rebuilds the same sales report by hand: paste data, add a totals row, colour the headers, add a chart, freeze the top row, format the currency. That is 20 minutes of repetitive, error-prone clicking, every single month. **openpyxl writes real Excel files from Python**, not CSV dumps: live formulas, cell colours, conditional formatting, column widths and native Excel charts, all generated in under a second.

The key idea that makes this different from `pandas.to_excel()`: this script writes **formulas**, not pre-computed numbers. If someone opens the file and edits a sales figure on the Raw Data sheet, the Summary sheet, its colour-coding and its chart all recalculate themselves automatically, exactly like a real analyst's workbook, not a static export.

## Workflow

| Step | What happens | Why it matters |
|------|--------------|----------------|
| 0 | Build sample regional sales data (48 rows) | Stand-in for a CSV export from a sales system |
| 1 | Write a styled "Raw Data" sheet, frozen panes, autofit columns | The clean, readable source sheet every workbook needs |
| 2 | Write a "Summary" sheet with **live** `SUMIF` / `AVERAGEIFS` / cell-reference formulas | The sheet keeps working after the data changes |
| 3 | Conditional formatting: a colour scale and a "below target" highlight rule | Turns a table into something scannable at a glance |
| 4 | A native Excel bar chart, built from cell references | Editable and resizable in Excel, not a pasted image |
| 5 | A couple of presentation guardrails (default sheet, gridlines off) | The small details that make a file feel hand-built |

## Verifying the Output

A script that *claims* to write working formulas is not the same as one that does. To check this file is correct, not just "runs without crashing", I opened it with LibreOffice in headless mode to force Excel to actually recalculate every formula, then read the computed values back and compared them against an independent `pandas.groupby().sum()` on the same raw data.

| Region | `SUMIF` result (from the file) | `pandas.groupby().sum()` (independent check) |
|--------|-------------------------------|-----------------------------------------------|
| North | Rs. 1,722,000 | Rs. 1,722,000 |
| South | Rs. 1,358,300 | Rs. 1,358,300 |
| East | Rs. 1,166,300 | Rs. 1,166,300 |
| West | Rs. 1,403,800 | Rs. 1,403,800 |

They match exactly, which confirms the formulas compute the right numbers, not just that the file opens.

## What the Finished Workbook Looks Like

**Summary sheet**, with currency formatting, bold totals row and a red-to-green colour scale on Achievement %:

| Region | Total Sales | Total Target | Achievement % | Avg Monthly Sales |
|--------|-------------|--------------|----------------|---------------------|
| North | Rs. 1,722,000 | Rs. 1,794,000 | 96.0% | Rs. 143,500 |
| South | Rs. 1,358,300 | Rs. 1,410,000 | 96.3% | Rs. 113,192 |
| East | Rs. 1,166,300 | Rs. 1,181,400 | 98.7% | Rs. 97,192 |
| West | Rs. 1,403,800 | Rs. 1,431,000 | 98.1% | Rs. 116,983 |
| **Company Total** | **Rs. 5,650,400** | **Rs. 5,816,400** | **97.1%** | **Rs. 117,717** |

Every one of those numbers is a live formula in the actual file, not a value typed in by Python. The chart sits alongside this table in the real workbook, built from the same cells, so it moves in step with the table.

*The data is simulated, so these numbers describe the exercise, not a real business.*

## Key Concepts and Interview Points

**Formulas, not values, is the whole point.** `ws.cell(value="=SUMIF(...)")` writes a real formula string into the cell. Excel evaluates it the moment the file opens. This is what separates an automated *report* from an automated *export*: a report stays correct when someone edits a number; an export is frozen the moment it is created.

**`SUMIF` and `AVERAGEIFS`, written from Python, read by Excel.** The script builds the formula text as an f-string (`f"=SUMIF('Raw Data'!B2:B{last_data_row},A{i},...)"`), referencing the Raw Data sheet by name. Using `last_data_row` instead of a hard-coded row number means the formulas still cover every row even if next month's data has 60 rows instead of 48.

**A style kit beats repeated styling code.** `HEADER_FILL`, `HEADER_FONT`, `BORDER` and the `style_header_row()` helper are defined once and reused on every sheet, the same instinct as Day 6's one-time `plt.rcParams` setup for matplotlib. Without this, formatting code gets copy-pasted everywhere and drifts out of sync between sheets.

**Conditional formatting is a rule the file remembers, not a one-time paint job.** `ColorScaleRule` and `CellIsRule` are saved inside the workbook itself. If the underlying formulas recalculate to new values, the colours update with them, because the rule, not a fixed colour, is what gets saved.

**A native chart beats a pasted image.** `BarChart()` with `Reference()` objects creates an actual Excel chart object: a user can click it, resize it, change its type, or edit its data range, exactly as if they had built it by hand through Excel's own Insert Chart menu. A pasted matplotlib image could never do any of that.

**No built-in "autofit columns".** Unlike Excel's own double-click-to-autofit, openpyxl has no direct equivalent, since it never actually renders the text to measure it. The `autofit_columns()` helper estimates a column's width from the longest string in it, which is good enough for a clean-looking report without needing a real rendering engine.

**Quote text inside a custom number format.** `'"Rs. "#,##0'` is the correct way to add a currency prefix; the text must sit inside quotes, or some engines parse the letters as date/format codes instead of literal text. This was an easy mistake to make and a quick one to catch by actually rendering the file rather than trusting that the string "looked right".

**Freeze panes, the exact Excel feature.** `ws.freeze_panes = "D2"` keeps the header row and the first three columns (Month, Region, Rep) visible while scrolling through 48+ rows, identical to selecting cell D2 and clicking Freeze Panes in Excel's View ribbon.

**Why this matters for a portfolio.** Interviewers for analyst roles often ask "can you automate a recurring Excel report?" This script is a direct, working answer: it is not a toy, it is a real file an analyst could hand to a manager, backed by a verified formula trail rather than a claim.

## How to Run

```bash
pip install openpyxl pandas numpy
python "Excel Report Automation with openpyxl.py"
```

The script prints each step and saves `Regional_Sales_Report.xlsx` next to it. Open it in Excel (or Google Sheets, or LibreOffice Calc) to see the live formulas, the colour scale, and the chart. The random seed is fixed, so your numbers match those above.

## Next Steps

- Add a pivot table built natively with openpyxl's `PivotTable` support
- Parameterise the script to accept a real CSV export as input instead of simulated data
- Add a macro-free "refresh" workflow: re-run the script monthly and keep the same file name, so a linked PowerPoint or email always points at the latest version
- Package this as a scheduled script (Task Scheduler / cron) that regenerates the report automatically every Monday morning
