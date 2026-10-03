# Pandas Data Cleaning & Exploratory Data Analysis (EDA)

**Tools:** Python, Pandas, NumPy

**File:** [`Pandas Data Cleaning & EDA.py`](./Pandas%20Data%20Cleaning%20&%20EDA.py)

## What I Learned

Real-world data is almost never clean, and analysts spend a large share of their time fixing it before any analysis can start. Think of it like cooking: **cleaning is washing and chopping the vegetables, EDA is tasting as you go.** Skip the washing and everything downstream is unreliable.

The script builds a small, deliberately messy retail dataset (so no download is needed), cleans it step by step, and then answers business questions from it.

## The Workflow: Inspect → Clean → Explore

Always **look before you clean**, the way a doctor examines a patient before prescribing medicine.

### 1. Inspect

| Check | Code | What it tells you |
|-------|------|-------------------|
| Size | `df.shape` | How many rows and columns |
| Types | `df.dtypes` | Are dates stored as text? Numbers as strings? |
| Missing values | `df.isna().sum()` | Which columns have gaps |
| Duplicates | `df.duplicated().sum()` | Repeated rows that inflate totals |

### 2. Clean

| Problem | Fix | Why it matters |
|---------|-----|----------------|
| Duplicate rows | `drop_duplicates()` | Duplicates double-count revenue |
| `"kolkata "` vs `"Kolkata"` | `str.strip().str.title()` | Otherwise one city is counted as two |
| Dates stored as text | `pd.to_datetime(..., format=...)` | Needed for sorting and monthly grouping |
| `"Rs. 1500"` in a number column | `str.replace()` then `pd.to_numeric(errors="coerce")` | Text blocks any maths on the column |
| Extreme outlier (typo) | IQR rule, per category | One huge value ruins averages |
| Missing numbers | Fill with the **median** of the same category | Median is not pulled by extremes |
| Missing city | Fill with `"Unknown"` | More honest than guessing |

### 3. Explore (EDA)

- Summary statistics with `describe()`
- Revenue by category and by city using `groupby().agg()`
- Monthly revenue and month-over-month growth using `pct_change()`
- Top customers using `nlargest()`
- Correlation between quantity, price and revenue using `corr()`

## Key Concepts and Interview Points

**Mean vs median for filling gaps.** If most people in a room earn Rs. 50k and one earns Rs. 9 crore, the average is meaningless. The median stays sensible. This is a very common interview question: *"How do you handle missing values?"* A strong answer explains that the method depends on the column and the reason the data is missing, not one fixed rule.

**Imputing vs dropping.** Dropping rows loses information and can bias results; filling invents information. Filling with a group-level median (here, per category) is usually more accurate than a global value. Always be ready to justify the choice.

**Outliers depend on context.** A Rs. 15,000 laptop is normal, but a Rs. 15,000 T-shirt is not. My first version of the IQR check ran on the whole column and wrongly flagged valid laptop prices, so I changed it to run **per category**. Being able to say *"I tested it, found a flaw, and fixed it"* is a great interview story.

**The IQR rule.** Values above `Q3 + 1.5 × IQR` (or below `Q1 − 1.5 × IQR`) are flagged. IQR is the range of the middle 50% of the data, so the rule is robust to extreme values, unlike a rule based on the mean and standard deviation.

**`errors="coerce"`.** Turns unconvertible values into `NaN` instead of crashing, so you can deal with them deliberately afterwards.

**Never edit the raw data.** The script works on `df = raw.copy()`, so the original is always available to compare against or restart from. In real projects this is the difference between a reproducible analysis and a mess.

**Correlation is not causation.** A high correlation between price and revenue is expected here (revenue is calculated from price), which is a reminder to check whether a relationship is meaningful or just built into the formula.

**Document every cleaning decision.** In a real job, someone will ask why a number changed. Comments in the script (and this README) are the paper trail.

## How to Run

```bash
pip install pandas numpy
python Pandas-Data-Cleaning-EDA.py
```

The script prints the inspection, the cleaning results and the EDA tables, then saves `cleaned_retail_orders.csv` in the same folder. The dataset is generated with a fixed random seed, so your output matches mine every time.

## Next Steps

- Add visualizations with Matplotlib or Seaborn (monthly trend line, revenue by category bar chart)
- Try the same cleaning workflow on a real Kaggle dataset
- Practice the same revenue questions in SQL and compare with the Pandas version
