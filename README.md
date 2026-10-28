# Student Finance Manager

A polished, local-first desktop finance tracker for university life. It runs on
Python's standard library: Tkinter provides the desktop interface and SQLite
stores data on your computer. There are no accounts, trackers, bank connections,
or third-party services.

## Run it

1. Install Python 3.10 or newer with **Tcl/Tk** enabled.
2. From this folder, run:

   ```powershell
   python app.py
   ```

The app creates `student_finance.db` beside `app.py` the first time it opens.
Close the app normally to finish any pending database writes.

## What's inside

- **Dashboard:** monthly cash flow, income, spending, remaining balance,
  budget progress, category leaders, recent activity, and quick actions.
- **Transactions:** create, edit, delete, search, filter, sort, and page through
  expenses, income, refunds, and pending recurring payments. Only amount and
  date are required; category and payment method are optional.
- **Budgets:** overall and per-category monthly limits, actual spend, remaining
  amounts, custom budget-cycle start dates, and 75% / 90% / 100% alerts.
- **Insights:** six-month spending trend, category breakdown, income versus
  spending, month-over-month comparison, average daily spend, and a month-end
  spending estimate.
- **Savings goals:** targets, progress, dated goals, and recorded contributions
  or withdrawals.
- **Recurring payments:** weekly, monthly, or yearly expenses, generated as
  pending transactions when due; mark them paid from Transactions.
- **Shared expenses:** groups, equal or custom splits, member balances, and
  recorded repayments. The app never sends money.
- **Notifications, settings, and reports:** budget/payment alerts, light and
  dark themes, INR/USD/EUR/GBP display, custom categories, CSV transaction
  exports, and printable text summaries.

Money is stored as integer paise/cents to avoid floating-point rounding in
splits and totals. The CSV export is UTF-8 encoded and opens in common
spreadsheet applications.

## Run tests

```powershell
python -m unittest discover -s tests -v
```
