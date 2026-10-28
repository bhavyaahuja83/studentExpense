"""Student Finance Manager — a local-first Tkinter desktop application."""

from __future__ import annotations

import calendar
import sqlite3
import tkinter as tk
from datetime import date, timedelta
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any, Callable

from finance_db import FinanceDB


PAGES = {
    "Dashboard": "⌂",
    "Transactions": "↕",
    "Budgets": "◉",
    "Insights": "⌁",
    "Savings goals": "☆",
    "Recurring": "⟳",
    "Shared expenses": "⇄",
    "Notifications": "♧",
    "Settings": "⚙",
}


class FinanceApp:
    def __init__(self, root: tk.Tk, database: FinanceDB | None = None) -> None:
        self.root = root
        self.db = database or FinanceDB()
        self.page = "Dashboard"
        self.palette: dict[str, str] = {}
        self._set_palette()
        self.root.title("Student Finance Manager")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(1180, max(900, screen_width - 48))
        height = min(780, max(620, screen_height - 72))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(900, screen_width), min(620, screen_height))
        self.root.configure(bg=self.palette["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._style()
        self._shell()
        self.db.generate_due_occurrences()
        self.show_page("Dashboard")

    def close(self) -> None:
        self.db.close()
        self.root.destroy()

    def _set_palette(self) -> None:
        if self.db.setting("theme", "dark") == "light":
            self.palette = {
                "bg": "#F4F6FA", "panel": "#FFFFFF", "panel2": "#EDF1F7",
                "text": "#172033", "muted": "#778198", "line": "#E3E8F0",
                "accent": "#6558E8", "accent2": "#8177FA", "green": "#22A887",
                "red": "#E56872", "orange": "#E9A44F", "nav": "#FFFFFF",
            }
        else:
            self.palette = {
                "bg": "#10131C", "panel": "#191E2A", "panel2": "#222838",
                "text": "#F2F4FA", "muted": "#929CB0", "line": "#2A3142",
                "accent": "#8B7CF6", "accent2": "#A79CFB", "green": "#4BC7A5",
                "red": "#F07883", "orange": "#F2B563", "nav": "#151A25",
            }

    def _style(self) -> None:
        p = self.palette
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=p["bg"], foreground=p["text"])
        style.configure("TFrame", background=p["bg"])
        style.configure("Panel.TFrame", background=p["panel"])
        style.configure("TLabel", background=p["bg"], foreground=p["text"])
        style.configure("Panel.TLabel", background=p["panel"], foreground=p["text"])
        style.configure("Muted.TLabel", background=p["bg"], foreground=p["muted"])
        style.configure("PanelMuted.TLabel", background=p["panel"], foreground=p["muted"])
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 23), background=p["bg"], foreground=p["text"])
        style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 11), background=p["panel"], foreground=p["muted"])
        style.configure("Metric.TLabel", font=("Segoe UI Semibold", 22), background=p["panel"], foreground=p["text"])
        style.configure("Nav.TButton", anchor="w", padding=(15, 11), background=p["nav"],
                        foreground=p["muted"], borderwidth=0, font=("Segoe UI", 10))
        style.map("Nav.TButton", background=[("active", p["panel2"])], foreground=[("active", p["text"])])
        style.configure("Accent.TButton", padding=(13, 9), background=p["accent"], foreground="#FFFFFF",
                        borderwidth=0, font=("Segoe UI Semibold", 10))
        style.map("Accent.TButton", background=[("active", p["accent2"])])
        style.configure("Quiet.TButton", padding=(11, 8), background=p["panel2"], foreground=p["text"], borderwidth=0)
        style.map("Quiet.TButton", background=[("active", p["line"])])
        style.configure("Treeview", background=p["panel"], fieldbackground=p["panel"],
                        foreground=p["text"], rowheight=34, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=p["panel2"], foreground=p["muted"],
                        relief="flat", font=("Segoe UI Semibold", 9), padding=9)
        style.map("Treeview", background=[("selected", p["accent"])], foreground=[("selected", "#FFFFFF")])
        style.configure("TCombobox", fieldbackground=p["panel2"], background=p["panel2"],
                        foreground=p["text"], arrowcolor=p["text"],
                        selectforeground=p["text"], selectbackground=p["accent"], padding=7)
        style.map("TCombobox",
                  fieldbackground=[("readonly", p["panel2"]), ("disabled", p["panel2"]),
                                   ("!disabled", p["panel2"])],
                  foreground=[("readonly", p["text"]), ("disabled", p["muted"]),
                              ("!disabled", p["text"])],
                  selectforeground=[("readonly", p["text"])],
                  selectbackground=[("readonly", p["panel2"])])
        style.configure("TEntry", fieldbackground=p["panel2"], foreground=p["text"],
                        insertcolor=p["text"], bordercolor=p["line"], lightcolor=p["line"],
                        darkcolor=p["line"], padding=7)
        style.configure("TProgressbar", troughcolor=p["panel2"], background=p["accent"], thickness=8)
        style.configure("TNotebook", background=p["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=p["panel2"], foreground=p["muted"], padding=(13, 8))

    def _shell(self) -> None:
        p = self.palette
        self.shell = tk.Frame(self.root, bg=p["bg"])
        self.shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(self.shell, bg=p["nav"], width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="◈  FINMATE", bg=p["nav"], fg=p["text"],
                 font=("Segoe UI Semibold", 17)).pack(anchor="w", padx=23, pady=(27, 4))
        tk.Label(self.sidebar, text="YOUR STUDENT MONEY SPACE", bg=p["nav"], fg=p["muted"],
                 font=("Segoe UI", 8)).pack(anchor="w", padx=24, pady=(0, 26))
        self.nav_buttons: dict[str, ttk.Button] = {}
        for name, icon in PAGES.items():
            button = ttk.Button(self.sidebar, text=f"  {icon}   {name}", style="Nav.TButton",
                                command=lambda selected=name: self.show_page(selected))
            button.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[name] = button
        footer = tk.Frame(self.sidebar, bg=p["nav"])
        footer.pack(side="bottom", fill="x", padx=19, pady=18)
        tk.Label(footer, text="MADE FOR CAMPUS LIFE", bg=p["nav"], fg=p["muted"],
                 font=("Segoe UI", 8)).pack(anchor="w")
        self.main = tk.Frame(self.shell, bg=p["bg"])
        self.main.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(self.main, bg=p["bg"])
        self.header.pack(fill="x", padx=34, pady=(24, 16))
        self.header_title = ttk.Label(self.header, text="", style="Title.TLabel")
        self.header_title.pack(side="left")
        self.header_right = tk.Frame(self.header, bg=p["bg"])
        self.header_right.pack(side="right")
        self.notification_button = ttk.Button(
            self.header_right, text="♧  0", style="Quiet.TButton",
            command=lambda: self.show_page("Notifications"),
        )
        self.notification_button.pack(side="right")
        self.record_expense_button = ttk.Button(
            self.header_right, text="＋  Record expense", style="Accent.TButton",
            command=lambda: self._transaction_form(kind="expense"),
        )
        self.record_expense_button.pack(side="right", padx=(0, 9))
        self.body = tk.Frame(self.main, bg=p["bg"])
        self.body.pack(fill="both", expand=True, padx=34, pady=(0, 26))
        self._notification_count()

    def _notification_count(self) -> None:
        unread = sum(not item["is_read"] for item in self.db.notifications())
        self.notification_button.configure(text=f"♧  {unread}")

    def show_page(self, page: str) -> None:
        self.page = page
        self.header_title.configure(text=page)
        for name, button in self.nav_buttons.items():
            button.configure(style="Nav.TButton" if name != page else "Quiet.TButton")
        for widget in self.body.winfo_children():
            widget.destroy()
        self.header_right.winfo_children()
        for widget in self.header_right.winfo_children():
            if widget not in (self.notification_button, self.record_expense_button):
                widget.destroy()
        self._notification_count()
        builders: dict[str, Callable[[], None]] = {
            "Dashboard": self._dashboard,
            "Transactions": self._transactions_page,
            "Budgets": self._budgets_page,
            "Insights": self._insights_page,
            "Savings goals": self._goals_page,
            "Recurring": self._recurring_page,
            "Shared expenses": self._groups_page,
            "Notifications": self._notifications_page,
            "Settings": self._settings_page,
        }
        builders[page]()

    def _card(self, parent: tk.Widget, padding: int = 18) -> tk.Frame:
        card = tk.Frame(parent, bg=self.palette["panel"], padx=padding, pady=padding,
                        highlightthickness=1, highlightbackground=self.palette["line"])
        return card

    def _section(self, parent: tk.Widget, title: str, action: str | None = None,
                 command: Callable[[], None] | None = None) -> tk.Frame:
        row = tk.Frame(parent, bg=self.palette["panel"])
        tk.Label(row, text=title, bg=self.palette["panel"], fg=self.palette["text"],
                 font=("Segoe UI Semibold", 12)).pack(side="left")
        if action and command:
            ttk.Button(row, text=action, style="Quiet.TButton", command=command).pack(side="right")
        return row

    def _money(self, cents: int) -> str:
        symbol = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(
            self.db.setting("currency", "INR"), "₹"
        )
        return f"{symbol}{cents / 100:,.0f}" if cents % 100 == 0 else f"{symbol}{cents / 100:,.2f}"

    def _month(self) -> str:
        return self.db.budget_month_for_date(date.today().isoformat())

    def _month_range(self, month: str | None = None) -> tuple[str, str]:
        return self.db.budget_bounds(month or self._month())

    def _metric(self, parent: tk.Widget, title: str, value: str, note: str,
                color: str | None = None) -> tk.Frame:
        card = self._card(parent, 17)
        ttk.Label(card, text=title.upper(), style="CardTitle.TLabel").pack(anchor="w")
        tk.Label(card, text=value, bg=self.palette["panel"], fg=color or self.palette["text"],
                 font=("Segoe UI Semibold", 22)).pack(anchor="w", pady=(8, 3))
        ttk.Label(card, text=note, style="PanelMuted.TLabel").pack(anchor="w")
        return card

    def _dashboard(self) -> None:
        p = self.palette
        month_start, month_end = self._month_range()
        totals = self.db.totals(month_start, month_end)
        previous = date.fromisoformat(f"{self._month()}-01") - timedelta(days=1)
        prev_start, prev_end = self._month_range(previous.strftime("%Y-%m"))
        prior = self.db.totals(prev_start, prev_end)
        spending = totals["expenses"] - totals["refunds"]
        prior_spending = prior["expenses"] - prior["refunds"]
        diff = ((spending - prior_spending) / prior_spending * 100) if prior_spending else 0
        comparison = f"{abs(diff):.0f}% {'more' if diff > 0 else 'less'} than last month" if prior_spending else "Your first month starts here"
        current_balance = totals["income"] - spending
        cards = tk.Frame(self.body, bg=p["bg"])
        cards.pack(fill="x", pady=(0, 17))
        for column in range(4):
            cards.grid_columnconfigure(column, weight=1, uniform="metric")
        self._metric(cards, "Spent this month", self._money(spending), comparison, p["orange"]).grid(row=0, column=0, sticky="ew", padx=(0, 9))
        self._metric(cards, "Income received", self._money(totals["income"]), "Allowance, work & more", p["green"]).grid(row=0, column=1, sticky="ew", padx=9)
        self._metric(cards, "Money remaining", self._money(current_balance), "Income minus net spending", p["accent2"]).grid(row=0, column=2, sticky="ew", padx=9)
        budgets = self.db.budgets(self._month())
        overall = next((budget for budget in budgets if budget["category_id"] is None), None)
        budget_note = f"of {self._money(overall['amount'])} monthly limit" if overall else "Set a monthly budget"
        self._metric(cards, "Monthly budget", self._money(overall["amount"] - overall["spent"]) if overall else "Not set",
                     budget_note, p["red"] if overall and overall["spent"] >= overall["amount"] else p["text"]).grid(row=0, column=3, sticky="ew", padx=(9, 0))

        columns = tk.Frame(self.body, bg=p["bg"])
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=3)
        columns.grid_columnconfigure(1, weight=2)
        left = self._card(columns)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        right = self._card(columns)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        self._section(left, "Monthly budget", "Manage", lambda: self.show_page("Budgets")).pack(fill="x")
        if budgets:
            for budget in budgets[:4]:
                spent = budget["spent"]
                ratio = spent / budget["amount"]
                name = budget["category"] or "Overall budget"
                row = tk.Frame(left, bg=p["panel"])
                row.pack(fill="x", pady=(18, 0))
                tk.Label(row, text=name, bg=p["panel"], fg=p["text"], font=("Segoe UI Semibold", 10)).pack(side="left")
                tk.Label(row, text=f"{self._money(spent)} / {self._money(budget['amount'])}",
                         bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9)).pack(side="right")
                bar = ttk.Progressbar(left, maximum=100, value=min(100, ratio * 100))
                bar.pack(fill="x", pady=(7, 0))
                if ratio >= .75:
                    color = p["red"] if ratio >= .9 else p["orange"]
                    tk.Label(left, text=f"{ratio:.0%} used  ·  {self._money(max(0, budget['amount'] - spent))} left",
                             bg=p["panel"], fg=color, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))
        else:
            self._empty(left, "No budgets yet. Set a monthly limit to keep spending on track.")
            ttk.Button(left, text="Create your first budget", style="Accent.TButton",
                       command=self._budget_form).pack(anchor="w", pady=12)
        self._section(right, "Recent activity", "See all", lambda: self.show_page("Transactions")).pack(fill="x", pady=(0, 10))
        self._compact_table(right, [
            ("date", "DATE", 105), ("merchant", "DESCRIPTION", 240), ("category", "CATEGORY", 185),
            ("kind", "TYPE", 100), ("amount", "AMOUNT", 120), ("status", "STATUS", 100),
        ], self.db.transactions(limit=5))

    def _empty(self, parent: tk.Widget, message: str) -> None:
        tk.Label(parent, text=message, bg=self.palette["panel"], fg=self.palette["muted"],
                 justify="left", wraplength=420).pack(anchor="w", pady=(18, 5))

    def _compact_table(self, parent: tk.Widget, columns: list[tuple[str, str, int]],
                       rows: list[Any]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=[item[0] for item in columns], show="headings",
                            height=max(2, min(len(rows), 9)))
        for name, label, width in columns:
            tree.heading(name, text=label)
            tree.column(name, width=width, minwidth=70, anchor="w")
        for row in rows:
            values = []
            for name, _, _ in columns:
                if name == "amount":
                    values.append(self._money(row["amount"]))
                elif name == "kind":
                    values.append(row[name].title())
                elif name == "category":
                    values.append(row[name] or "—")
                elif name == "merchant":
                    values.append(row[name] or row["notes"] or "—")
                else:
                    values.append(row[name] or "—")
            tree.insert("", "end", iid=str(row["id"]), values=values)
        tree.pack(fill="x")
        return tree

    def _transactions_page(self) -> None:
        toolbar = tk.Frame(self.body, bg=self.palette["bg"])
        toolbar.pack(fill="x", pady=(0, 12))
        self.tx_search = tk.StringVar()
        self.tx_start = tk.StringVar()
        self.tx_end = tk.StringVar()
        self.tx_kind = tk.StringVar(value="All types")
        self.tx_category = tk.StringVar(value="All categories")
        self.tx_method = tk.StringVar(value="All methods")
        self.tx_sort = tk.StringVar(value="newest")
        search = ttk.Entry(toolbar, textvariable=self.tx_search, width=22)
        search.pack(side="left", padx=(0, 7))
        self._placeholder(search, "Search merchant or notes")
        self._small_entry(toolbar, self.tx_start, "From YYYY-MM-DD", 14)
        self._small_entry(toolbar, self.tx_end, "To YYYY-MM-DD", 14)
        categories = ["All categories"] + [row["name"] for row in self.db.categories()]
        ttk.Combobox(toolbar, textvariable=self.tx_category, values=categories, state="readonly", width=20).pack(side="left", padx=4)
        ttk.Combobox(toolbar, textvariable=self.tx_method,
                     values=["All methods", "Cash", "UPI", "Card", "Bank transfer", "Other"],
                     state="readonly", width=14).pack(side="left", padx=4)
        ttk.Combobox(toolbar, textvariable=self.tx_kind,
                     values=["All types", "expense", "income", "refund"],
                     state="readonly", width=12).pack(side="left", padx=4)
        ttk.Combobox(toolbar, textvariable=self.tx_sort,
                     values=["newest", "oldest", "amount high", "amount low"],
                     state="readonly", width=13).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Apply", style="Accent.TButton", command=self._apply_transaction_filters).pack(side="left", padx=5)
        action_row = tk.Frame(self.body, bg=self.palette["bg"])
        action_row.pack(fill="x", pady=(0, 10))
        ttk.Button(action_row, text="＋ Expense", style="Accent.TButton",
                   command=lambda: self._transaction_form(kind="expense")).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="＋ Income", style="Quiet.TButton",
                   command=lambda: self._transaction_form(kind="income")).pack(side="left", padx=4)
        ttk.Button(action_row, text="＋ Refund", style="Quiet.TButton",
                   command=lambda: self._transaction_form(kind="refund")).pack(side="left", padx=4)
        ttk.Button(action_row, text="Export CSV", style="Quiet.TButton", command=self._export_csv).pack(side="right")
        bulk_row = tk.Frame(self.body, bg=self.palette["bg"])
        bulk_row.pack(fill="x", pady=(0, 9))
        ttk.Button(bulk_row, text="Edit", style="Quiet.TButton", command=self._edit_transaction).pack(side="left", padx=(0, 5))
        ttk.Button(bulk_row, text="Duplicate", style="Quiet.TButton", command=self._duplicate_transaction).pack(side="left", padx=4)
        ttk.Button(bulk_row, text="Mark paid", style="Quiet.TButton", command=self._mark_paid).pack(side="left", padx=4)
        ttk.Button(bulk_row, text="Categorize", style="Quiet.TButton", command=self._bulk_categorize).pack(side="left", padx=4)
        ttk.Button(bulk_row, text="Delete selected", style="Quiet.TButton", command=self._delete_transaction).pack(side="left", padx=4)
        ttk.Button(bulk_row, text="Undo delete", style="Quiet.TButton", command=self._undo_delete).pack(side="left", padx=4)
        self.tx_tree = ttk.Treeview(self.body, columns=("date", "description", "category", "type", "method", "amount", "status"),
                                    show="headings", height=17)
        specs = (("date", "DATE", 105), ("description", "DESCRIPTION", 240), ("category", "CATEGORY", 175),
                 ("type", "TYPE", 95), ("method", "PAYMENT", 120), ("amount", "AMOUNT", 115), ("status", "STATUS", 155))
        for name, title, width in specs:
            self.tx_tree.heading(name, text=title)
            self.tx_tree.column(name, width=width, anchor="w")
        self.tx_tree.pack(fill="both", expand=True)
        self.tx_page = 0
        pager = tk.Frame(self.body, bg=self.palette["bg"])
        pager.pack(fill="x", pady=(9, 0))
        self.tx_page_label = ttk.Label(pager, text="Page 1", style="Muted.TLabel")
        self.tx_page_label.pack(side="left")
        ttk.Button(pager, text="← Previous", style="Quiet.TButton",
                   command=self._previous_transaction_page).pack(side="right", padx=(6, 0))
        ttk.Button(pager, text="Next →", style="Quiet.TButton",
                   command=self._next_transaction_page).pack(side="right")
        self._refresh_transactions()

    def _placeholder(self, entry: ttk.Entry, text: str) -> None:
        if entry.get():
            return
        entry.insert(0, text)
        entry.bind("<FocusIn>", lambda _event: entry.delete(0, "end") if entry.get() == text else None)
        entry.bind("<FocusOut>", lambda _event: entry.insert(0, text) if not entry.get() else None)
        entry.bind("<Return>", lambda _event: self._apply_transaction_filters())

    def _small_entry(self, parent: tk.Widget, variable: tk.StringVar, placeholder: str, width: int) -> ttk.Entry:
        entry = ttk.Entry(parent, textvariable=variable, width=width)
        entry.pack(side="left", padx=4)
        self._placeholder(entry, placeholder)
        return entry

    def _refresh_transactions(self) -> None:
        if not hasattr(self, "tx_tree") or not self.tx_tree.winfo_exists():
            return
        for item in self.tx_tree.get_children():
            self.tx_tree.delete(item)
        search = self.tx_search.get()
        if search == "Search merchant or notes":
            search = ""
        start = self.tx_start.get() if self.tx_start.get() != "From YYYY-MM-DD" else ""
        end = self.tx_end.get() if self.tx_end.get() != "To YYYY-MM-DD" else ""
        category = self.tx_category.get()
        category_id = next((row["id"] for row in self.db.categories() if row["name"] == category), None)
        method = self.tx_method.get()
        kind = self.tx_kind.get()
        try:
            rows = self.db.transactions(
                search=search, start=start, end=end, category_id=category_id,
                payment_method=method if method != "All methods" else "",
                kind=kind if kind != "All types" else "", sort=self.tx_sort.get(),
                limit=101, offset=self.tx_page * 100,
            )
        except ValueError as exc:
            messagebox.showerror("Invalid date filter", str(exc))
            return
        self.tx_has_next = len(rows) > 100
        for row in rows[:100]:
            merchant = row["merchant"] or row["notes"] or "—"
            status = row["status"].title()
            if row["merchant"] and row["duplicate_count"] > 1:
                status = f"⚠ Possible duplicate · {status}"
            self.tx_tree.insert("", "end", iid=str(row["id"]), values=(
                row["date"], merchant, row["category"] or "—",
                row["kind"].title(), row["payment_method"], self._money(row["amount"]), status,
            ))
        if hasattr(self, "tx_page_label") and self.tx_page_label.winfo_exists():
            self.tx_page_label.configure(text=f"Page {self.tx_page + 1}")

    def _apply_transaction_filters(self) -> None:
        self.tx_page = 0
        self._refresh_transactions()

    def _previous_transaction_page(self) -> None:
        if self.tx_page > 0:
            self.tx_page -= 1
            self._refresh_transactions()

    def _next_transaction_page(self) -> None:
        if getattr(self, "tx_has_next", False):
            self.tx_page += 1
            self._refresh_transactions()

    def _selected_transaction(self) -> int | None:
        selection = self.tx_tree.selection() if hasattr(self, "tx_tree") else ()
        if not selection:
            messagebox.showinfo("Select a transaction", "Choose a transaction first.")
            return None
        return int(selection[0])

    def _transaction_form(self, transaction_id: int | None = None, kind: str = "expense",
                          duplicate: bool = False) -> None:
        existing = None
        if transaction_id is not None:
            existing = next((row for row in self.db.transactions(limit=10000) if row["id"] == transaction_id), None)
            if existing is None:
                messagebox.showerror("Transaction not found", "This transaction is no longer available.")
                return
        title = "Add a copy" if duplicate else "Edit transaction" if existing else {
            "expense": "Record expense", "income": "Record income", "refund": "Record refund",
        }.get(kind, "Add transaction")
        dialog = self._dialog(title, 430, 480)
        categories = self.db.categories()
        names = [row["name"] for row in categories]
        category_names = [""] + names
        default_category = existing["category"] if existing else ""
        variables = {
            "kind": tk.StringVar(value=existing["kind"] if existing else kind),
            "amount": tk.StringVar(value=f"{existing['amount'] / 100:.2f}" if existing else ""),
            "date": tk.StringVar(value=date.today().isoformat() if duplicate else existing["date"] if existing else date.today().isoformat()),
            "category": tk.StringVar(value=default_category or ""),
            "method": tk.StringVar(
                value=existing["payment_method"] if existing and existing["payment_method"] else ""
            ),
            "merchant": tk.StringVar(value=existing["merchant"] if existing else ""),
            "notes": tk.StringVar(value=existing["notes"] if existing else ""),
        }
        content = self._form_content(dialog, "Enter the amount and save.")
        if existing and not duplicate:
            self._form_label(content, "TYPE")
            ttk.Combobox(content, textvariable=variables["kind"], values=["expense", "income", "refund"],
                         state="readonly").pack(fill="x", pady=(4, 5))
        self._form_label(content, "AMOUNT (₹)")
        self._form_entry(content, variables["amount"], "e.g. 250.00")
        self._form_label(content, "DATE")
        self._form_entry(content, variables["date"], "YYYY-MM-DD")
        self._form_label(content, "CATEGORY")
        ttk.Combobox(content, textvariable=variables["category"], values=category_names,
                     state="readonly").pack(fill="x", pady=(4, 7))
        self._form_label(content, "PAYMENT METHOD (OPTIONAL)")
        ttk.Combobox(content, textvariable=variables["method"],
                     values=["", "UPI", "Cash", "Card", "Bank transfer", "Other"],
                     state="readonly").pack(fill="x", pady=(4, 7))
        self._form_label(content, "DESCRIPTION (OPTIONAL)")
        self._form_entry(content, variables["merchant"], "e.g. Campus cafe")

        def save() -> None:
            try:
                cents = self.db.parse_amount(variables["amount"].get())
                category_id = next(
                    (row["id"] for row in categories if row["name"] == variables["category"].get()),
                    None,
                )
                values = {
                    "kind": variables["kind"].get(), "amount": cents, "date": variables["date"].get(),
                    "category_id": category_id, "payment_method": variables["method"].get() or None,
                    "merchant": variables["merchant"].get(), "notes": variables["notes"].get(),
                }
                if existing and not duplicate:
                    self.db.update_transaction(transaction_id, **values)
                else:
                    create_values = dict(values)
                    create_values["day"] = create_values.pop("date")
                    self.db.add_transaction(**create_values)
                dialog.destroy()
                self._after_change()
            except (ValueError, sqlite3.Error) as exc:
                messagebox.showerror("Check your details", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _edit_transaction(self) -> None:
        selected = self._selected_transaction()
        if selected is not None:
            self._transaction_form(selected)

    def _duplicate_transaction(self) -> None:
        selected = self._selected_transaction()
        if selected is not None:
            self._transaction_form(selected, duplicate=True)

    def _delete_transaction(self) -> None:
        selected = self.tx_tree.selection() if hasattr(self, "tx_tree") else ()
        if not selected:
            messagebox.showinfo("Select transactions", "Choose one or more transactions first.")
            return
        if messagebox.askyesno("Delete transactions", f"Delete {len(selected)} selected transaction(s)? You can undo this action."):
            self.last_deleted = []
            for transaction_id in selected:
                record = next((dict(row) for row in self.db.transactions(limit=10000)
                               if row["id"] == int(transaction_id)), None)
                if record:
                    self.last_deleted.append(record)
                    self.db.delete_transaction(int(transaction_id))
            self._after_change()

    def _undo_delete(self) -> None:
        if not getattr(self, "last_deleted", None):
            messagebox.showinfo("Nothing to undo", "Your most recent deletion can be undone here.")
            return
        for record in self.last_deleted:
            self.db.restore_transaction(record)
        self.last_deleted = []
        self._after_change()

    def _bulk_categorize(self) -> None:
        selected = self.tx_tree.selection() if hasattr(self, "tx_tree") else ()
        if not selected:
            messagebox.showinfo("Select transactions", "Choose one or more transactions first.")
            return
        dialog = self._dialog("Categorize selected transactions", 390, 220)
        content = self._form_content(dialog, f"Update {len(selected)} transactions.")
        categories = self.db.categories()
        category = tk.StringVar(value=categories[0]["name"])
        ttk.Combobox(content, textvariable=category, values=[row["name"] for row in categories],
                     state="readonly").pack(fill="x", pady=(5, 15))

        def save() -> None:
            category_id = next(row["id"] for row in categories if row["name"] == category.get())
            for transaction_id in selected:
                self.db.update_transaction(int(transaction_id), category_id=category_id)
            dialog.destroy()
            self._after_change()
        self._form_actions(content, save)

    def _mark_paid(self) -> None:
        selected = self._selected_transaction()
        if selected is not None:
            try:
                self.db.mark_transaction_paid(selected)
                self._after_change()
            except ValueError as exc:
                messagebox.showerror("Could not mark paid", str(exc))

    def _budgets_page(self) -> None:
        top = tk.Frame(self.body, bg=self.palette["bg"])
        top.pack(fill="x", pady=(0, 14))
        self.budget_month = tk.StringVar(value=self._month())
        self._small_entry(top, self.budget_month, "YYYY-MM", 13)
        ttk.Button(top, text="Show month", style="Quiet.TButton", command=self._refresh_budgets).pack(side="left", padx=5)
        ttk.Button(top, text="Carry forward last month", style="Quiet.TButton",
                   command=self._carry_forward_budgets).pack(side="left", padx=5)
        ttk.Button(top, text="＋ Set budget", style="Accent.TButton", command=self._budget_form).pack(side="right")
        self.budget_container = tk.Frame(self.body, bg=self.palette["bg"])
        self.budget_container.pack(fill="both", expand=True)
        self._refresh_budgets()

    def _refresh_budgets(self) -> None:
        if not hasattr(self, "budget_container") or not self.budget_container.winfo_exists():
            return
        for widget in self.budget_container.winfo_children():
            widget.destroy()
        try:
            month = self.budget_month.get()
            self.db.month_bounds(month)
        except ValueError as exc:
            messagebox.showerror("Invalid month", str(exc))
            return
        budgets = self.db.budgets(month)
        if not budgets:
            card = self._card(self.budget_container)
            card.pack(fill="x")
            self._empty(card, f"No limits set for {month}. Add an overall cap and category budgets to spot overspending early.")
            return
        for budget in budgets:
            amount = budget["amount"]
            spent = budget["spent"]
            ratio = spent / amount
            name = budget["category"] or "Overall monthly limit"
            card = self._card(self.budget_container)
            card.pack(fill="x", pady=(0, 10))
            head = tk.Frame(card, bg=self.palette["panel"])
            head.pack(fill="x")
            tk.Label(head, text=name, bg=self.palette["panel"], fg=self.palette["text"],
                     font=("Segoe UI Semibold", 12)).pack(side="left")
            tk.Label(head, text=f"{ratio:.0%} used", bg=self.palette["panel"],
                     fg=self.palette["red"] if ratio >= 1 else self.palette["orange"] if ratio >= .75 else self.palette["green"],
                     font=("Segoe UI Semibold", 10)).pack(side="right")
            ttk.Progressbar(card, maximum=100, value=min(ratio * 100, 100)).pack(fill="x", pady=14)
            bottom = tk.Frame(card, bg=self.palette["panel"])
            bottom.pack(fill="x")
            tk.Label(bottom, text=f"{self._money(spent)} spent", bg=self.palette["panel"], fg=self.palette["text"]).pack(side="left")
            tk.Label(bottom, text=f"{self._money(max(0, amount-spent))} remaining  ·  Limit {self._money(amount)}",
                     bg=self.palette["panel"], fg=self.palette["muted"]).pack(side="right")

    def _carry_forward_budgets(self) -> None:
        try:
            target = self.budget_month.get()
            self.db.budget_bounds(target)
            previous = date.fromisoformat(f"{target}-01") - timedelta(days=1)
            count = self.db.copy_budgets(previous.strftime("%Y-%m"), target)
            messagebox.showinfo("Budgets carried forward", f"Copied {count} budget(s) into {target}.")
            self._after_change()
        except ValueError as exc:
            messagebox.showerror("Could not carry budgets forward", str(exc))

    def _budget_form(self) -> None:
        dialog = self._dialog("Set a monthly budget", 430, 390)
        categories = self.db.categories()
        variables = {"month": tk.StringVar(value=self._month()), "amount": tk.StringVar(),
                     "category": tk.StringVar(value="Overall budget")}
        content = self._form_content(dialog, "Give your money a game plan.")
        self._form_label(content, "MONTH (YYYY-MM)")
        self._form_entry(content, variables["month"], "2026-10")
        self._form_label(content, "LIMIT (₹)")
        self._form_entry(content, variables["amount"], "e.g. 12000")
        self._form_label(content, "APPLIES TO")
        ttk.Combobox(content, textvariable=variables["category"],
                     values=["Overall budget"] + [row["name"] for row in categories],
                     state="readonly").pack(fill="x", pady=(4, 16))

        def save() -> None:
            try:
                self.db.month_bounds(variables["month"].get())
                category = next((row["id"] for row in categories if row["name"] == variables["category"].get()), None)
                self.db.set_budget(variables["month"].get(), self.db.parse_amount(variables["amount"].get()), category)
                dialog.destroy()
                self._after_change()
            except (ValueError, StopIteration) as exc:
                messagebox.showerror("Check your details", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _insights_page(self) -> None:
        p = self.palette
        start, end = self._month_range()
        totals = self.db.totals(start, end)
        expenses = totals["expenses"] - totals["refunds"]
        previous = date.fromisoformat(f"{self._month()}-01") - timedelta(days=1)
        prev_totals = self.db.totals(*self._month_range(previous.strftime("%Y-%m")))
        prev_expenses = prev_totals["expenses"] - prev_totals["refunds"]
        diff = (expenses - prev_expenses) / prev_expenses * 100 if prev_expenses else 0
        month_days = calendar.monthrange(date.today().year, date.today().month)[1]
        elapsed = date.today().day
        daily = expenses / max(elapsed, 1)
        projection = round(daily * month_days)
        categories = self.db.category_spending(start, end)
        top = categories[0] if categories else None
        row = tk.Frame(self.body, bg=p["bg"])
        row.pack(fill="x", pady=(0, 15))
        for i in range(5):
            row.grid_columnconfigure(i, weight=1, uniform="insight")
        self._metric(row, "Average per day", self._money(round(daily)), f"Across {elapsed} days").grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self._metric(row, "Top category", top["name"] if top else "—", self._money(top["amount"]) if top else "No spending yet", p["orange"]).grid(row=0, column=1, sticky="ew", padx=5)
        self._metric(row, "vs. last month", f"{diff:+.0f}%", "Net spending comparison", p["red"] if diff > 0 else p["green"]).grid(row=0, column=2, sticky="ew", padx=5)
        self._metric(row, "Month-end spend", self._money(projection), "Estimated at this pace", p["accent2"]).grid(row=0, column=3, sticky="ew", padx=5)
        self._metric(row, "Est. month-end balance", self._money(totals["income"] - projection),
                     "Income to date less projected spending",
                     p["green"] if totals["income"] >= projection else p["red"]).grid(row=0, column=4, sticky="ew", padx=(5, 0))
        charts = tk.Frame(self.body, bg=p["bg"])
        charts.pack(fill="both", expand=True)
        charts.grid_columnconfigure(0, weight=3)
        charts.grid_columnconfigure(1, weight=2)
        trend_card = self._card(charts)
        trend_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        category_card = self._card(charts)
        category_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._section(trend_card, "Six-month spending trend").pack(fill="x")
        canvas = tk.Canvas(trend_card, height=265, bg=p["panel"], highlightthickness=0)
        canvas.pack(fill="both", expand=True, pady=(12, 0))
        self._draw_trend(canvas)
        self._section(category_card, "Category breakdown").pack(fill="x")
        pie = tk.Canvas(category_card, height=200, bg=p["panel"], highlightthickness=0)
        pie.pack(fill="x", pady=(10, 0))
        self._draw_pie(pie, categories)
        for item in categories[:7]:
            line = tk.Frame(category_card, bg=p["panel"])
            line.pack(fill="x", pady=4)
            tk.Label(line, text=f"●  {item['name']}", bg=p["panel"], fg=item["color"]).pack(side="left")
            tk.Label(line, text=self._money(item["amount"]), bg=p["panel"], fg=p["muted"]).pack(side="right")
        bottom = self._card(self.body)
        bottom.pack(fill="x", pady=(14, 0))
        self._section(bottom, "Cash flow this month").pack(fill="x")
        comparison = tk.Frame(bottom, bg=p["panel"])
        comparison.pack(fill="x", pady=(13, 0))
        for label, amount, color in (("Income received", totals["income"], p["green"]),
                                     ("Net expenses", expenses, p["orange"]),
                                     ("Remaining cash flow", totals["income"] - expenses, p["accent2"])):
            chunk = tk.Frame(comparison, bg=p["panel"])
            chunk.pack(side="left", fill="x", expand=True)
            tk.Label(chunk, text=label, bg=p["panel"], fg=p["muted"]).pack(anchor="w")
            tk.Label(chunk, text=self._money(amount), bg=p["panel"], fg=color,
                     font=("Segoe UI Semibold", 18)).pack(anchor="w", pady=(4, 0))
        essential_categories = {
            "Food & groceries", "Mess & hostel", "Rent & utilities",
            "Transport & fuel", "College fees & books", "Health & emergencies",
        }
        essential = sum(item["amount"] for item in categories if item["name"] in essential_categories)
        nonessential = expenses - essential
        for label, amount, color in (("Essential spending", essential, p["green"]),
                                     ("Flexible spending", nonessential, p["orange"])):
            chunk = tk.Frame(comparison, bg=p["panel"])
            chunk.pack(side="left", fill="x", expand=True)
            tk.Label(chunk, text=label, bg=p["panel"], fg=p["muted"]).pack(anchor="w")
            tk.Label(chunk, text=self._money(amount), bg=p["panel"], fg=color,
                     font=("Segoe UI Semibold", 18)).pack(anchor="w", pady=(4, 0))
        daily_rows = self.db.daily_spending(start, end)
        highest_day = max(daily_rows, key=lambda item: item["amount"], default=None)
        if highest_day:
            tk.Label(bottom, text=f"Highest spending day: {highest_day['date']}  ·  {self._money(highest_day['amount'])}",
                     bg=p["panel"], fg=p["muted"]).pack(anchor="w", pady=(13, 0))
        visual_row = tk.Frame(self.body, bg=p["bg"])
        visual_row.pack(fill="both", expand=True, pady=(14, 0))
        visual_row.grid_columnconfigure(0, weight=1)
        visual_row.grid_columnconfigure(1, weight=1)
        daily_card = self._card(visual_row)
        daily_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        heat_card = self._card(visual_row)
        heat_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._section(daily_card, "Daily spending · last 14 days").pack(fill="x")
        daily_canvas = tk.Canvas(daily_card, height=150, bg=p["panel"], highlightthickness=0)
        daily_canvas.pack(fill="both", expand=True, pady=(10, 0))
        self._draw_daily_spending(daily_canvas)
        self._section(heat_card, "Spending calendar").pack(fill="x")
        calendar_canvas = tk.Canvas(heat_card, height=170, bg=p["panel"], highlightthickness=0)
        calendar_canvas.pack(fill="both", expand=True, pady=(10, 0))
        self._draw_calendar_heatmap(calendar_canvas)

    def _draw_daily_spending(self, canvas: tk.Canvas) -> None:
        p = self.palette
        last_day = date.today()
        first_day = last_day - timedelta(days=13)
        values = {row["date"]: max(0, row["amount"])
                  for row in self.db.daily_spending(first_day.isoformat(), last_day.isoformat())}
        days = [first_day + timedelta(days=index) for index in range(14)]
        maximum = max((values.get(day.isoformat(), 0) for day in days), default=0) or 100

        def draw(_event: Any = None) -> None:
            canvas.delete("all")
            width = max(canvas.winfo_width(), 360)
            height = max(canvas.winfo_height(), 130)
            bar_width = max(8, (width - 30) // 20)
            gap = (width - 30 - bar_width * 14) / 13
            baseline = height - 23
            for index, day in enumerate(days):
                amount = values.get(day.isoformat(), 0)
                bar_height = (height - 46) * amount / maximum
                x = 14 + index * (bar_width + gap)
                color = p["accent"] if amount else p["panel2"]
                canvas.create_rectangle(x, baseline - bar_height, x + bar_width,
                                        baseline, fill=color, outline="")
                canvas.create_text(x + bar_width / 2, baseline + 10, text=day.strftime("%d"),
                                   fill=p["muted"], font=("Segoe UI", 7))
        canvas.bind("<Configure>", draw)
        self.root.after_idle(draw)

    def _draw_calendar_heatmap(self, canvas: tk.Canvas) -> None:
        p = self.palette
        today = date.today()
        amount_by_day = {row["date"]: max(0, row["amount"])
                         for row in self.db.daily_spending(
                             today.replace(day=1).isoformat(),
                             today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat(),
                         )}
        weeks = calendar.monthcalendar(today.year, today.month)
        maximum = max(amount_by_day.values(), default=0) or 1
        labels = ("M", "T", "W", "T", "F", "S", "S")
        colors = (p["panel2"], "#234A48", "#276B60", "#31967C", p["green"])

        def draw(_event: Any = None) -> None:
            canvas.delete("all")
            width = max(canvas.winfo_width(), 310)
            cell_width = min(43, (width - 20) / 7)
            cell_height = 24
            left = (width - cell_width * 7) / 2
            for column, label in enumerate(labels):
                canvas.create_text(left + column * cell_width + cell_width / 2, 9,
                                   text=label, fill=p["muted"], font=("Segoe UI", 8))
            for week_index, week in enumerate(weeks):
                for column, day_number in enumerate(week):
                    if not day_number:
                        continue
                    key = f"{today.year:04d}-{today.month:02d}-{day_number:02d}"
                    amount = amount_by_day.get(key, 0)
                    intensity = min(4, int(amount / maximum * 4) + 1) if amount else 0
                    x = left + column * cell_width
                    y = 21 + week_index * (cell_height + 5)
                    canvas.create_rectangle(x + 2, y, x + cell_width - 2, y + cell_height,
                                           fill=colors[intensity], outline="")
                    canvas.create_text(x + cell_width / 2, y + cell_height / 2,
                                       text=str(day_number), fill=p["text"], font=("Segoe UI", 8))
        canvas.bind("<Configure>", draw)
        self.root.after_idle(draw)

    def _draw_trend(self, canvas: tk.Canvas) -> None:
        p = self.palette
        months: list[tuple[str, int]] = []
        current = date.today().replace(day=1)
        for offset in range(5, -1, -1):
            index = current.year * 12 + current.month - 1 - offset
            year, month = divmod(index, 12)
            month += 1
            month_text = f"{year:04d}-{month:02d}"
            start, end = self.db.month_bounds(month_text)
            totals = self.db.totals(start, end)
            months.append((calendar.month_abbr[month], totals["expenses"] - totals["refunds"]))
        maximum = max((value for _, value in months), default=0) or 100

        def draw(_event: Any = None) -> None:
            canvas.delete("all")
            width = max(canvas.winfo_width(), 360)
            height = max(canvas.winfo_height(), 200)
            left, right, top, bottom = 40, width - 18, 20, height - 33
            for step in range(4):
                y = top + (bottom - top) * step / 3
                canvas.create_line(left, y, right, y, fill=p["line"])
            points = []
            for i, (label, amount) in enumerate(months):
                x = left + (right-left) * i / max(1, len(months)-1)
                y = bottom - (amount / maximum) * (bottom-top)
                points.extend((x, y))
                canvas.create_text(x, bottom + 16, text=label, fill=p["muted"], font=("Segoe UI", 9))
                canvas.create_text(x, y - 14, text=f"₹{amount/100:,.0f}", fill=p["muted"], font=("Segoe UI", 8))
            if len(points) >= 4:
                canvas.create_line(*points, fill=p["accent"], width=3, smooth=True)
                for index in range(0, len(points), 2):
                    canvas.create_oval(points[index]-4, points[index+1]-4, points[index]+4,
                                       points[index+1]+4, fill=p["accent"], outline=p["panel"])
        canvas.bind("<Configure>", draw)
        self.root.after_idle(draw)

    def _draw_pie(self, canvas: tk.Canvas, categories: list[Any]) -> None:
        canvas.delete("all")
        total = sum(row["amount"] for row in categories)
        if not total:
            canvas.create_text(135, 95, text="Nothing to chart yet", fill=self.palette["muted"])
            return
        start = 0
        x1, y1, x2, y2 = 57, 14, 217, 174
        for item in categories:
            extent = 360 * item["amount"] / total
            canvas.create_arc(x1, y1, x2, y2, start=start, extent=extent,
                              fill=item["color"], outline=self.palette["panel"], width=2)
            start += extent

    def _goals_page(self) -> None:
        header = tk.Frame(self.body, bg=self.palette["bg"])
        header.pack(fill="x", pady=(0, 14))
        ttk.Button(header, text="＋ New savings goal", style="Accent.TButton", command=self._goal_form).pack(side="right")
        goals = self.db.goals()
        if not goals:
            card = self._card(self.body)
            card.pack(fill="x")
            self._empty(card, "A laptop upgrade, emergency fund, or next semester's fees—give your savings a purpose.")
            return
        for goal in goals:
            card = self._card(self.body)
            card.pack(fill="x", pady=(0, 10))
            title = tk.Frame(card, bg=self.palette["panel"])
            title.pack(fill="x")
            tk.Label(title, text=f"☆  {goal['name']}", bg=self.palette["panel"], fg=self.palette["text"],
                     font=("Segoe UI Semibold", 13)).pack(side="left")
            status = "Completed" if goal["saved"] >= goal["target"] else goal["status"].title()
            tk.Label(title, text=status, bg=self.palette["panel"],
                     fg=self.palette["green"] if status == "Completed" else self.palette["muted"]).pack(side="right")
            progress = min(100, goal["saved"] / goal["target"] * 100)
            ttk.Progressbar(card, maximum=100, value=progress).pack(fill="x", pady=13)
            footer = tk.Frame(card, bg=self.palette["panel"])
            footer.pack(fill="x")
            tk.Label(footer, text=f"{self._money(goal['saved'])} saved of {self._money(goal['target'])}  ·  {progress:.0f}%",
                     bg=self.palette["panel"], fg=self.palette["muted"]).pack(side="left")
            estimate = self.db.goal_completion_estimate(goal["id"])
            if estimate and goal["status"] == "active":
                tk.Label(footer, text=f"At this pace: {estimate}", bg=self.palette["panel"],
                         fg=self.palette["muted"]).pack(side="right")
            if goal["target_date"]:
                tk.Label(footer, text=f"Target {goal['target_date']}", bg=self.palette["panel"],
                         fg=self.palette["muted"]).pack(side="right", padx=10)
            if goal["status"] != "completed":
                ttk.Button(footer, text="Add / withdraw", style="Quiet.TButton",
                           command=lambda selected=goal: self._goal_movement(selected)).pack(side="right", padx=5)
                ttk.Button(footer, text="Pause" if goal["status"] == "active" else "Resume",
                           style="Quiet.TButton",
                           command=lambda selected=goal: self._toggle_goal(selected["id"])).pack(side="right", padx=5)

    def _toggle_goal(self, goal_id: int) -> None:
        try:
            self.db.toggle_goal(goal_id)
            self._after_change()
        except ValueError as exc:
            messagebox.showerror("Could not update goal", str(exc))

    def _goal_form(self) -> None:
        dialog = self._dialog("Create a savings goal", 430, 360)
        vars = {"name": tk.StringVar(), "target": tk.StringVar(), "date": tk.StringVar()}
        content = self._form_content(dialog, "Little by little adds up.")
        for key, label, hint in (("name", "GOAL NAME", "A new laptop"), ("target", "TARGET AMOUNT (₹)", "45000"),
                                 ("date", "TARGET DATE (OPTIONAL)", "YYYY-MM-DD")):
            self._form_label(content, label)
            self._form_entry(content, vars[key], hint)

        def save() -> None:
            try:
                if not vars["name"].get().strip():
                    raise ValueError("Give your goal a name.")
                self.db.create_goal(vars["name"].get(), self.db.parse_amount(vars["target"].get()), vars["date"].get())
                dialog.destroy()
                self._after_change()
            except ValueError as exc:
                messagebox.showerror("Check your details", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _goal_movement(self, goal: Any) -> None:
        dialog = self._dialog("Update your savings", 400, 310)
        variables = {"amount": tk.StringVar(), "note": tk.StringVar(), "action": tk.StringVar(value="Add")}
        content = self._form_content(dialog, goal["name"])
        tk.Label(content, text=f"Currently saved: {self._money(goal['saved'])}", bg=self.palette["panel"], fg=self.palette["muted"]).pack(anchor="w", pady=(0, 12))
        ttk.Combobox(content, textvariable=variables["action"], values=["Add", "Withdraw"], state="readonly").pack(fill="x", pady=(0, 10))
        self._form_label(content, "AMOUNT (₹)")
        self._form_entry(content, variables["amount"], "e.g. 500")
        self._form_label(content, "NOTE")
        self._form_entry(content, variables["note"], "Optional")

        def save() -> None:
            try:
                self.db.move_goal(goal["id"], self.db.parse_amount(variables["amount"].get()),
                                  variables["note"].get(), variables["action"].get() == "Withdraw")
                dialog.destroy()
                self._after_change()
            except ValueError as exc:
                messagebox.showerror("Could not update goal", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _recurring_page(self) -> None:
        actions = tk.Frame(self.body, bg=self.palette["bg"])
        actions.pack(fill="x", pady=(0, 12))
        ttk.Button(actions, text="＋ Add recurring payment", style="Accent.TButton",
                   command=self._recurring_form).pack(side="left")
        ttk.Button(actions, text="Pause / resume selected", style="Quiet.TButton",
                   command=self._toggle_recurring).pack(side="left", padx=8)
        ttk.Button(actions, text="Mark due as paid", style="Quiet.TButton",
                   command=lambda: self.show_page("Transactions")).pack(side="left")
        card = self._card(self.body)
        card.pack(fill="both", expand=True)
        self._section(card, "Your recurring payments").pack(fill="x", pady=(0, 10))
        items = self.db.recurring_items()
        monthly_cost, yearly_cost = self.db.recurring_costs()
        summary = tk.Frame(card, bg=self.palette["panel"])
        summary.pack(fill="x", pady=(0, 12))
        tk.Label(summary, text=f"Estimated monthly costs  {self._money(monthly_cost)}",
                 bg=self.palette["panel"], fg=self.palette["text"],
                 font=("Segoe UI Semibold", 12)).pack(side="left")
        tk.Label(summary, text=f"About {self._money(yearly_cost)} / year",
                 bg=self.palette["panel"], fg=self.palette["muted"]).pack(side="right")
        self.recurring_tree = self._compact_table(card, [
            ("id", "ID", 45), ("name", "PAYMENT", 190), ("kind", "TYPE", 85),
            ("amount", "AMOUNT", 110), ("frequency", "REPEATS", 100), ("next_due", "NEXT DUE", 120),
            ("category", "CATEGORY", 135), ("status", "STATUS", 90),
        ], [dict(item, amount=item["amount"], status="Active" if item["active"] else "Paused") for item in items])
        self.recurring_tree.column("id", width=55, anchor="center")
        self.recurring_tree.column("amount", width=120)
        upcoming = [row for row in self.db.transactions(limit=100) if row["status"] == "pending"]
        due_card = self._card(self.body)
        due_card.pack(fill="x", pady=(14, 0))
        self._section(due_card, "Due or upcoming payments",
                      "View transactions", lambda: self.show_page("Transactions")).pack(fill="x")
        if upcoming:
            self._compact_table(due_card, [
                ("date", "DUE DATE", 120), ("merchant", "PAYMENT", 250),
                ("category", "CATEGORY", 180), ("amount", "AMOUNT", 130), ("status", "STATUS", 110),
            ], upcoming[:5])
        else:
            self._empty(due_card, "Nothing due right now. Recurring payments are added here when their due date arrives.")

    def _toggle_recurring(self) -> None:
        selected = self.recurring_tree.selection() if hasattr(self, "recurring_tree") else ()
        if not selected:
            messagebox.showinfo("Select a payment", "Choose a recurring payment first.")
            return
        self.db.toggle_recurring(int(selected[0]))
        self._after_change()

    def _recurring_form(self) -> None:
        dialog = self._dialog("Add recurring payment", 440, 510)
        categories = self.db.categories()
        variables = {"name": tk.StringVar(), "amount": tk.StringVar(), "frequency": tk.StringVar(value="monthly"),
                     "due": tk.StringVar(value=date.today().isoformat()), "category": tk.StringVar(value=categories[0]["name"]),
                     "method": tk.StringVar(value="UPI"), "kind": tk.StringVar(value="expense")}
        content = self._form_content(dialog, "Rent, subscriptions, and the regular stuff.")
        for key, label, hint in (("name", "PAYMENT NAME", "Hostel fee / music subscription"),
                                 ("amount", "AMOUNT (₹)", "2500"), ("due", "NEXT DUE DATE", "YYYY-MM-DD")):
            self._form_label(content, label)
            self._form_entry(content, variables[key], hint)
        self._form_label(content, "TYPE")
        ttk.Combobox(content, textvariable=variables["kind"], values=["expense", "income"],
                     state="readonly").pack(fill="x", pady=(4, 10))
        self._form_label(content, "REPEAT")
        ttk.Combobox(content, textvariable=variables["frequency"], values=["weekly", "monthly", "yearly"],
                     state="readonly").pack(fill="x", pady=(4, 10))
        self._form_label(content, "CATEGORY")
        ttk.Combobox(content, textvariable=variables["category"], values=[row["name"] for row in categories],
                     state="readonly").pack(fill="x", pady=(4, 10))
        self._form_label(content, "PAYMENT METHOD")
        ttk.Combobox(content, textvariable=variables["method"], values=["UPI", "Cash", "Card", "Bank transfer", "Other"],
                     state="readonly").pack(fill="x", pady=(4, 10))

        def save() -> None:
            try:
                if not variables["name"].get().strip():
                    raise ValueError("Enter a payment name.")
                category_id = next(row["id"] for row in categories if row["name"] == variables["category"].get())
                self.db.create_recurring(variables["name"].get(), self.db.parse_amount(variables["amount"].get()),
                                         variables["frequency"].get(), variables["due"].get(), category_id,
                                         variables["method"].get(), variables["kind"].get())
                dialog.destroy()
                self._after_change()
            except (ValueError, StopIteration) as exc:
                messagebox.showerror("Check your details", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _groups_page(self) -> None:
        groups = self.db.groups()
        head = tk.Frame(self.body, bg=self.palette["bg"])
        head.pack(fill="x", pady=(0, 13))
        ttk.Button(head, text="＋ New group", style="Accent.TButton", command=self._group_form).pack(side="left")
        if not groups:
            card = self._card(self.body)
            card.pack(fill="x")
            self._empty(card, "Split groceries, bills, and trip costs with your flatmates. Create a group to get started.")
            return
        self.group_var = tk.StringVar(value=groups[0]["name"])
        ttk.Combobox(head, textvariable=self.group_var, values=[group["name"] for group in groups],
                     state="readonly", width=27).pack(side="left", padx=10)
        ttk.Button(head, text="Load group", style="Quiet.TButton", command=self._refresh_group).pack(side="left")
        ttk.Button(head, text="＋ Shared expense", style="Quiet.TButton", command=self._shared_expense_form).pack(side="right")
        ttk.Button(head, text="Record repayment", style="Quiet.TButton", command=self._repayment_form).pack(side="right", padx=7)
        ttk.Button(head, text="＋ Member", style="Quiet.TButton", command=self._add_group_member_form).pack(side="right", padx=7)
        self.group_content = tk.Frame(self.body, bg=self.palette["bg"])
        self.group_content.pack(fill="both", expand=True)
        self._refresh_group()

    def _selected_group(self) -> Any | None:
        name = self.group_var.get() if hasattr(self, "group_var") else ""
        return next((row for row in self.db.groups() if row["name"] == name), None)

    def _refresh_group(self) -> None:
        if not hasattr(self, "group_content") or not self.group_content.winfo_exists():
            return
        for child in self.group_content.winfo_children():
            child.destroy()
        group = self._selected_group()
        if not group:
            return
        members = self.db.group_members(group["id"])
        balance_card = self._card(self.group_content)
        balance_card.pack(fill="x", pady=(0, 12))
        self._section(balance_card, f"{group['name']}  ·  {len(members)} members").pack(fill="x")
        balances = tk.Frame(balance_card, bg=self.palette["panel"])
        balances.pack(fill="x", pady=(12, 0))
        for balance in self.db.group_balances(group["id"]):
            color = self.palette["green"] if balance["balance"] > 0 else self.palette["red"] if balance["balance"] < 0 else self.palette["muted"]
            item = tk.Frame(balances, bg=self.palette["panel"])
            item.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk.Label(item, text=balance["name"], bg=self.palette["panel"], fg=self.palette["muted"]).pack(anchor="w")
            description = "is owed" if balance["balance"] > 0 else "owes" if balance["balance"] < 0 else "settled"
            tk.Label(item, text=f"{self._money(abs(balance['balance']))} {description}" if balance["balance"] else "All settled",
                     bg=self.palette["panel"], fg=color, font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=(4, 0))
        expenses_card = self._card(self.group_content)
        expenses_card.pack(fill="both", expand=True)
        self._section(expenses_card, "Shared expenses").pack(fill="x", pady=(0, 10))
        self._compact_table(expenses_card, [
            ("date", "DATE", 120), ("title", "EXPENSE", 280), ("payer", "PAID BY", 170), ("amount", "TOTAL", 130),
        ], self.db.group_expenses(group["id"]))

    def _group_form(self) -> None:
        dialog = self._dialog("Create a shared group", 430, 380)
        variables = {"name": tk.StringVar(), "members": tk.StringVar(value=self.db.setting("student_name", "Student"))}
        content = self._form_content(dialog, "Better together, down to the last rupee.")
        self._form_label(content, "GROUP NAME")
        self._form_entry(content, variables["name"], "Flat 204 / Goa trip")
        self._form_label(content, "MEMBERS (COMMA SEPARATED)")
        self._form_entry(content, variables["members"], "You, Asha, Kabir")
        tk.Label(content, text="Add yourself and everyone sharing costs.", bg=self.palette["panel"],
                 fg=self.palette["muted"]).pack(anchor="w", pady=(0, 12))

        def save() -> None:
            try:
                if not variables["name"].get().strip():
                    raise ValueError("Enter a group name.")
                self.db.create_group(variables["name"].get(), variables["members"].get().split(","))
                dialog.destroy()
                self._after_change()
            except (ValueError, sqlite3.IntegrityError) as exc:
                messagebox.showerror("Could not create group", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _add_group_member_form(self) -> None:
        group = self._selected_group()
        if not group:
            return
        dialog = self._dialog("Add a group member", 390, 230)
        content = self._form_content(dialog, group["name"])
        name = tk.StringVar()
        self._form_label(content, "MEMBER NAME")
        self._form_entry(content, name, "Name")

        def save() -> None:
            try:
                self.db.add_group_member(group["id"], name.get())
                dialog.destroy()
                self._after_change()
            except (ValueError, sqlite3.IntegrityError) as exc:
                messagebox.showerror("Could not add member", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _shared_expense_form(self) -> None:
        group = self._selected_group()
        if not group:
            messagebox.showinfo("Create a group first", "Add a group before recording a shared expense.")
            return
        members = self.db.group_members(group["id"])
        dialog = self._dialog("Split a shared expense", 480, 560)
        variables = {"title": tk.StringVar(), "amount": tk.StringVar(), "payer": tk.StringVar(value=members[0]["name"]),
                     "mode": tk.StringVar(value="Split equally")}
        shares = {member["id"]: tk.StringVar() for member in members}
        content = self._form_content(dialog, group["name"])
        self._form_label(content, "WHAT WAS IT?")
        self._form_entry(content, variables["title"], "Groceries")
        self._form_label(content, "TOTAL AMOUNT (₹)")
        amount_entry = self._form_entry(content, variables["amount"], "900")
        self._form_label(content, "PAID BY")
        ttk.Combobox(content, textvariable=variables["payer"], values=[member["name"] for member in members],
                     state="readonly").pack(fill="x", pady=(4, 10))
        self._form_label(content, "SPLIT")
        ttk.Combobox(content, textvariable=variables["mode"], values=["Split equally", "Custom amounts"],
                     state="readonly").pack(fill="x", pady=(4, 8))
        share_frame = tk.Frame(content, bg=self.palette["panel"])
        share_frame.pack(fill="x")
        for member in members:
            line = tk.Frame(share_frame, bg=self.palette["panel"])
            line.pack(fill="x", pady=2)
            tk.Label(line, text=member["name"], bg=self.palette["panel"], fg=self.palette["text"]).pack(side="left")
            field = ttk.Entry(line, textvariable=shares[member["id"]], width=12)
            field.pack(side="right")
            field.configure(state="disabled")

        def toggle_custom(*_args: Any) -> None:
            state = "normal" if variables["mode"].get() == "Custom amounts" else "disabled"
            for child in share_frame.winfo_children():
                child.winfo_children()[1].configure(state=state)
        variables["mode"].trace_add("write", toggle_custom)
        tk.Label(content, text="Equal splits distribute remainder cents fairly.",
                 bg=self.palette["panel"], fg=self.palette["muted"]).pack(anchor="w", pady=(8, 0))

        def save() -> None:
            try:
                amount = self.db.parse_amount(variables["amount"].get())
                if variables["mode"].get() == "Split equally":
                    base, remainder = divmod(amount, len(members))
                    split_values = {member["id"]: base + (1 if index < remainder else 0)
                                    for index, member in enumerate(members)}
                else:
                    split_values = {member["id"]: self.db.parse_amount(shares[member["id"]].get() or "0", allow_zero=True)
                                    for member in members}
                payer = next(member["id"] for member in members if member["name"] == variables["payer"].get())
                self.db.add_shared_expense(group["id"], variables["title"].get(), amount, payer, split_values)
                dialog.destroy()
                self._after_change()
            except (ValueError, StopIteration) as exc:
                messagebox.showerror("Check your split", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _repayment_form(self) -> None:
        group = self._selected_group()
        if not group:
            messagebox.showinfo("Create a group first", "Add a group before recording a repayment.")
            return
        members = self.db.group_members(group["id"])
        if len(members) < 2:
            return
        dialog = self._dialog("Record a repayment", 420, 360)
        variables = {"sender": tk.StringVar(value=members[0]["name"]), "receiver": tk.StringVar(value=members[1]["name"]),
                     "amount": tk.StringVar()}
        content = self._form_content(dialog, group["name"])
        self._form_label(content, "PAID BY")
        ttk.Combobox(content, textvariable=variables["sender"], values=[m["name"] for m in members],
                     state="readonly").pack(fill="x", pady=(4, 10))
        self._form_label(content, "PAID TO")
        ttk.Combobox(content, textvariable=variables["receiver"], values=[m["name"] for m in members],
                     state="readonly").pack(fill="x", pady=(4, 10))
        self._form_label(content, "AMOUNT (₹)")
        self._form_entry(content, variables["amount"], "300")

        def save() -> None:
            try:
                sender = next(m["id"] for m in members if m["name"] == variables["sender"].get())
                receiver = next(m["id"] for m in members if m["name"] == variables["receiver"].get())
                self.db.add_repayment(group["id"], sender, receiver, self.db.parse_amount(variables["amount"].get()))
                dialog.destroy()
                self._after_change()
            except (ValueError, StopIteration) as exc:
                messagebox.showerror("Could not record repayment", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _notifications_page(self) -> None:
        top = tk.Frame(self.body, bg=self.palette["bg"])
        top.pack(fill="x", pady=(0, 12))
        ttk.Button(top, text="Mark all as read", style="Quiet.TButton",
                   command=self._mark_all_read).pack(side="right")
        card = self._card(self.body)
        card.pack(fill="both", expand=True)
        notifications = self.db.notifications()
        if not notifications:
            self._empty(card, "You're all caught up. Budget alerts and due-payment reminders will show up here.")
            return
        for item in notifications:
            row = tk.Frame(card, bg=self.palette["panel2"] if not item["is_read"] else self.palette["panel"],
                           padx=14, pady=12)
            row.pack(fill="x", pady=(0, 7))
            tk.Label(row, text="●" if not item["is_read"] else "○",
                     bg=row["bg"], fg=self.palette["accent"]).pack(side="left", padx=(0, 10))
            details = tk.Frame(row, bg=row["bg"])
            details.pack(side="left", fill="x", expand=True)
            tk.Label(details, text=item["message"], bg=row["bg"], fg=self.palette["text"],
                     wraplength=740, justify="left").pack(anchor="w")
            tk.Label(details, text=item["created_at"], bg=row["bg"], fg=self.palette["muted"],
                     font=("Segoe UI", 8)).pack(anchor="w", pady=(5, 0))

    def _mark_all_read(self) -> None:
        self.db.mark_notifications_read()
        self._after_change()

    def _settings_page(self) -> None:
        card = self._card(self.body)
        card.pack(fill="x")
        content = tk.Frame(card, bg=self.palette["panel"])
        content.pack(fill="x")
        name_var = tk.StringVar(value=self.db.setting("student_name", "Student"))
        theme_var = tk.StringVar(value=self.db.setting("theme", "dark"))
        currency_var = tk.StringVar(value=self.db.setting("currency", "INR"))
        start_var = tk.StringVar(value=self.db.setting("budget_start_day", "1"))
        for label, variable, values in (
            ("YOUR NAME", name_var, None), ("APPEARANCE", theme_var, ["dark", "light"]),
            ("CURRENCY", currency_var, ["INR", "USD", "EUR", "GBP"]),
            ("BUDGET CYCLE START DAY", start_var, [str(day) for day in range(1, 29)]),
        ):
            self._form_label(content, label)
            if values:
                ttk.Combobox(content, textvariable=variable, values=values, state="readonly").pack(fill="x", pady=(4, 14))
            else:
                self._form_entry(content, variable, "Student")
        ttk.Button(content, text="Save preferences", style="Accent.TButton",
                   command=lambda: self._save_settings(name_var, theme_var, currency_var, start_var)).pack(anchor="w", pady=(0, 15))
        ttk.Separator(content).pack(fill="x", pady=12)
        self._form_label(content, "YOUR DATA")
        ttk.Button(content, text="Export all transactions as CSV", style="Quiet.TButton",
                   command=self._export_csv).pack(anchor="w", pady=(4, 8))
        ttk.Button(content, text="Export complete personal data backup (JSON)", style="Quiet.TButton",
                   command=self._export_backup).pack(anchor="w", pady=(0, 8))
        ttk.Button(content, text="Save monthly summary", style="Quiet.TButton",
                   command=self._save_report).pack(anchor="w", pady=(0, 12))
        ttk.Separator(content).pack(fill="x", pady=12)
        self._form_label(content, "CUSTOM CATEGORIES")
        ttk.Button(content, text="＋ Create a category", style="Quiet.TButton",
                   command=self._category_form).pack(anchor="w", pady=(4, 8))
        for category in self.db.categories():
            tk.Label(content, text=f"{category['icon']}   {category['name']}", bg=self.palette["panel"],
                     fg=category["color"]).pack(anchor="w", pady=2)

    def _save_settings(self, name: tk.StringVar, theme: tk.StringVar,
                       currency: tk.StringVar, start: tk.StringVar) -> None:
        if not name.get().strip():
            messagebox.showerror("Name required", "Please enter your name.")
            return
        self.db.set_setting("student_name", name.get().strip())
        self.db.set_setting("theme", theme.get())
        self.db.set_setting("currency", currency.get())
        self.db.set_setting("budget_start_day", start.get())
        self._set_palette()
        self._style()
        self.root.configure(bg=self.palette["bg"])
        for widget in self.root.winfo_children():
            widget.destroy()
        self._shell()
        self.show_page("Settings")

    def _category_form(self) -> None:
        dialog = self._dialog("Create a category", 400, 320)
        variables = {"name": tk.StringVar(), "icon": tk.StringVar(value="✨"), "color": tk.StringVar(value="#8B7CF6")}
        content = self._form_content(dialog, "Make it yours.")
        for key, label, hint in (("name", "CATEGORY NAME", "e.g. Printing"), ("icon", "ICON / EMOJI", "✨")):
            self._form_label(content, label)
            self._form_entry(content, variables[key], hint)
        self._form_label(content, "COLOR")
        color_row = tk.Frame(content, bg=self.palette["panel"])
        color_row.pack(fill="x", pady=(4, 14))
        tk.Entry(color_row, textvariable=variables["color"], width=15).pack(side="left")

        def pick() -> None:
            color = colorchooser.askcolor(color=variables["color"].get(), parent=dialog)[1]
            if color:
                variables["color"].set(color)
        ttk.Button(color_row, text="Choose color", style="Quiet.TButton", command=pick).pack(side="left", padx=8)

        def save() -> None:
            try:
                if not variables["name"].get().strip():
                    raise ValueError("Enter a category name.")
                self.db.add_category(variables["name"].get(), variables["icon"].get(), variables["color"].get())
                dialog.destroy()
                self._after_change()
            except (ValueError, sqlite3.IntegrityError) as exc:
                messagebox.showerror("Could not create category", str(exc), parent=dialog)
        self._form_actions(content, save)

    def _save_report(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save monthly finance summary", defaultextension=".txt",
            initialfile=f"finance-summary-{self._month()}.txt",
            filetypes=[("Text summary", "*.txt")],
        )
        if path:
            with open(path, "w", encoding="utf-8") as file:
                file.write(self.db.monthly_summary(self._month()))
            messagebox.showinfo("Report saved", "Your monthly summary is ready to print.")

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export transactions", defaultextension=".csv",
            initialfile="student-finance-transactions.csv", filetypes=[("CSV file", "*.csv")],
        )
        if path:
            try:
                self.db.export_csv(path)
                messagebox.showinfo("Export complete", "Your transactions have been exported.")
            except OSError as exc:
                messagebox.showerror("Export failed", str(exc))

    def _export_backup(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export personal data backup", defaultextension=".json",
            initialfile="student-finance-backup.json", filetypes=[("JSON backup", "*.json")],
        )
        if path:
            try:
                self.db.export_json(path)
                messagebox.showinfo("Backup exported", "Your finance data and preferences have been saved.")
            except OSError as exc:
                messagebox.showerror("Backup failed", str(exc))

    def _after_change(self) -> None:
        self._notification_count()
        self.show_page(self.page)

    def _dialog(self, title: str, width: int, height: int) -> tk.Toplevel:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=self.palette["panel"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = max(self.root.winfo_width(), width)
        parent_height = max(self.root.winfo_height(), height)
        screen_height = self.root.winfo_screenheight()
        height = min(height, screen_height - 60)
        x = max(0, parent_x + (parent_width - width) // 2)
        y = max(0, parent_y + (parent_height - height) // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        return dialog

    def _form_content(self, parent: tk.Widget, heading: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.palette["panel"], padx=25, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=heading, bg=self.palette["panel"], fg=self.palette["text"],
                 font=("Segoe UI Semibold", 16)).pack(anchor="w", pady=(0, 10))
        return frame

    def _form_label(self, parent: tk.Widget, text: str) -> None:
        tk.Label(parent, text=text, bg=self.palette["panel"], fg=self.palette["muted"],
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(3, 0))

    def _form_entry(self, parent: tk.Widget, variable: tk.StringVar, placeholder: str) -> ttk.Entry:
        entry = ttk.Entry(parent, textvariable=variable)
        entry.pack(fill="x", pady=(4, 5))
        return entry

    def _form_actions(self, parent: tk.Widget, save: Callable[[], None]) -> None:
        row = tk.Frame(parent, bg=self.palette["panel"])
        row.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(row, text="Cancel", style="Quiet.TButton",
                   command=parent.winfo_toplevel().destroy).pack(side="right", padx=(8, 0))
        ttk.Button(row, text="Save", style="Accent.TButton", command=save).pack(side="right")


def main() -> None:
    root = tk.Tk()
    FinanceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
