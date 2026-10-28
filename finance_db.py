"""SQLite-backed data and finance calculations for Student Finance Manager."""

from __future__ import annotations

import calendar
import csv
import json
import re
import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


DEFAULT_CATEGORIES = (
    ("Food & groceries", "🍜", "#F6A85C"),
    ("Mess & hostel", "🏠", "#8B7CF6"),
    ("Rent & utilities", "💡", "#5E9FF2"),
    ("Transport & fuel", "🚌", "#50C4A0"),
    ("College fees & books", "📚", "#E786AB"),
    ("Stationery & supplies", "✏️", "#E3C15A"),
    ("Shopping & entertainment", "🛍", "#E9826E"),
    ("Subscriptions & recharge", "📱", "#63B6D7"),
    ("Health & emergencies", "🩺", "#EB7183"),
    ("Other expenses", "✨", "#92A0B4"),
)


class FinanceDB:
    """Owns the local database and exposes small, testable finance operations."""

    def __init__(self, path: str | Path = "student_finance.db") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                icon TEXT NOT NULL DEFAULT '•',
                color TEXT NOT NULL DEFAULT '#92A0B4'
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL CHECK (kind IN ('expense','income','refund')),
                amount INTEGER NOT NULL CHECK (amount > 0),
                date TEXT NOT NULL,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                payment_method TEXT,
                merchant TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'paid' CHECK (status IN ('paid','pending')),
                recurring_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY,
                month TEXT NOT NULL,
                category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL CHECK (amount > 0)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS budget_month_category
                ON budgets(month, COALESCE(category_id, -1));
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                target INTEGER NOT NULL CHECK (target > 0),
                target_date TEXT,
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','paused'))
            );
            CREATE TABLE IF NOT EXISTS goal_movements (
                id INTEGER PRIMARY KEY,
                goal_id INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL,
                date TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS recurring (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                amount INTEGER NOT NULL CHECK (amount > 0),
                kind TEXT NOT NULL DEFAULT 'expense' CHECK (kind IN ('expense','income')),
                frequency TEXT NOT NULL CHECK (frequency IN ('weekly','monthly','yearly')),
                next_due TEXT NOT NULL,
                anchor_day INTEGER NOT NULL DEFAULT 1,
                anchor_month INTEGER NOT NULL DEFAULT 1,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                payment_method TEXT NOT NULL DEFAULT 'Other',
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS recurring_occurrences (
                id INTEGER PRIMARY KEY,
                recurring_id INTEGER NOT NULL REFERENCES recurring(id) ON DELETE CASCADE,
                due_date TEXT NOT NULL,
                transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
                UNIQUE(recurring_id, due_date)
            );
            CREATE TABLE IF NOT EXISTS groups_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY,
                group_id INTEGER NOT NULL REFERENCES groups_table(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                UNIQUE(group_id, name)
            );
            CREATE TABLE IF NOT EXISTS shared_expenses (
                id INTEGER PRIMARY KEY,
                group_id INTEGER NOT NULL REFERENCES groups_table(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                amount INTEGER NOT NULL CHECK (amount > 0),
                paid_by INTEGER NOT NULL REFERENCES group_members(id),
                date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS expense_splits (
                id INTEGER PRIMARY KEY,
                expense_id INTEGER NOT NULL REFERENCES shared_expenses(id) ON DELETE CASCADE,
                member_id INTEGER NOT NULL REFERENCES group_members(id),
                amount INTEGER NOT NULL CHECK (amount >= 0),
                UNIQUE(expense_id, member_id)
            );
            CREATE TABLE IF NOT EXISTS repayments (
                id INTEGER PRIMARY KEY,
                group_id INTEGER NOT NULL REFERENCES groups_table(id) ON DELETE CASCADE,
                from_member INTEGER NOT NULL REFERENCES group_members(id),
                to_member INTEGER NOT NULL REFERENCES group_members(id),
                amount INTEGER NOT NULL CHECK (amount > 0),
                date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self._migrate_transaction_payment_method()
        recurring_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(recurring)")
        }
        for column, definition in (
            ("kind", "TEXT NOT NULL DEFAULT 'expense' CHECK (kind IN ('expense','income'))"),
            ("anchor_day", "INTEGER NOT NULL DEFAULT 1"),
            ("anchor_month", "INTEGER NOT NULL DEFAULT 1"),
        ):
            if column not in recurring_columns:
                self.connection.execute(f"ALTER TABLE recurring ADD COLUMN {column} {definition}")
        self.connection.executemany(
            "INSERT OR IGNORE INTO categories(name, icon, color) VALUES (?, ?, ?)",
            DEFAULT_CATEGORIES,
        )
        self.connection.executemany(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            (("student_name", "Student"), ("theme", "dark"), ("currency", "INR"), ("budget_start_day", "1")),
        )
        self.connection.commit()

    def _migrate_transaction_payment_method(self) -> None:
        columns = {
            row["name"]: row for row in self.connection.execute("PRAGMA table_info(transactions)")
        }
        if not columns.get("payment_method") or not columns["payment_method"]["notnull"]:
            return
        self.connection.execute("PRAGMA foreign_keys = OFF")
        try:
            self.connection.execute("BEGIN")
            self.connection.execute(
                """CREATE TABLE transactions_new (
                    id INTEGER PRIMARY KEY,
                    kind TEXT NOT NULL CHECK (kind IN ('expense','income','refund')),
                    amount INTEGER NOT NULL CHECK (amount > 0),
                    date TEXT NOT NULL,
                    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                    payment_method TEXT,
                    merchant TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'paid' CHECK (status IN ('paid','pending')),
                    recurring_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            self.connection.execute(
                """INSERT INTO transactions_new
                (id,kind,amount,date,category_id,payment_method,merchant,notes,status,recurring_id,created_at)
                SELECT id,kind,amount,date,category_id,payment_method,merchant,notes,status,recurring_id,created_at
                FROM transactions"""
            )
            self.connection.execute("DROP TABLE transactions")
            self.connection.execute("ALTER TABLE transactions_new RENAME TO transactions")
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
            raise
        finally:
            self.connection.execute("PRAGMA foreign_keys = ON")
        violations = self.connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.IntegrityError(f"Database migration found foreign-key violations: {violations}")

    @staticmethod
    def parse_amount(value: str, allow_zero: bool = False) -> int:
        try:
            amount = Decimal(value.replace(",", "").strip())
            if not amount.is_finite() or amount < 0 or (amount == 0 and not allow_zero):
                raise ValueError("Amount must be greater than zero.")
            cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except InvalidOperation as exc:
            raise ValueError("Enter a valid amount, such as 250.00.") from exc
        if cents < 0 or (cents == 0 and not allow_zero):
            raise ValueError("Amount must be greater than zero.")
        return cents

    @staticmethod
    def month_bounds(month: str) -> tuple[str, str]:
        year, number = (int(part) for part in month.split("-"))
        last_day = calendar.monthrange(year, number)[1]
        return f"{month}-01", f"{month}-{last_day:02d}"

    def budget_bounds(self, month: str) -> tuple[str, str]:
        year, number = (int(part) for part in month.split("-"))
        start_day = min(max(int(self.setting("budget_start_day", "1")), 1),
                        calendar.monthrange(year, number)[1])
        next_month = date(year + (number == 12), number % 12 + 1, 1)
        next_start = min(start_day, calendar.monthrange(next_month.year, next_month.month)[1])
        start = date(year, number, start_day)
        end = date(next_month.year, next_month.month, next_start) - timedelta(days=1)
        return start.isoformat(), end.isoformat()

    def budget_month_for_date(self, day: str) -> str:
        current = date.fromisoformat(day)
        start_day = int(self.setting("budget_start_day", "1"))
        if current.day >= start_day:
            return current.strftime("%Y-%m")
        previous_month = current.replace(day=1) - timedelta(days=1)
        return previous_month.strftime("%Y-%m")

    def categories(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM categories ORDER BY name"))

    def add_category(self, name: str, icon: str, color: str) -> int:
        if not name.strip():
            raise ValueError("Category name cannot be empty.")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ValueError("Choose a valid six-digit hex color.")
        cursor = self.connection.execute(
            "INSERT INTO categories(name, icon, color) VALUES (?, ?, ?)",
            (name.strip(), icon.strip() or "•", color),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def add_transaction(
        self,
        kind: str,
        amount: int,
        day: str,
        category_id: int | None = None,
        payment_method: str | None = None,
        merchant: str = "",
        notes: str = "",
        status: str = "paid",
        recurring_id: int | None = None,
    ) -> int:
        date.fromisoformat(day)
        if kind not in {"expense", "income", "refund"} or amount <= 0:
            raise ValueError("Choose a valid transaction type and positive amount.")
        if payment_method is not None and not payment_method.strip():
            payment_method = None
        cursor = self.connection.execute(
            """INSERT INTO transactions
            (kind, amount, date, category_id, payment_method, merchant, notes, status, recurring_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (kind, amount, day, category_id, payment_method, merchant.strip(), notes.strip(), status, recurring_id),
        )
        self.connection.commit()
        if status == "paid" and kind in {"expense", "refund"}:
            self.refresh_budget_notifications(self.budget_month_for_date(day))
        return int(cursor.lastrowid)

    def update_transaction(self, transaction_id: int, **fields: Any) -> None:
        allowed = {"kind", "amount", "date", "category_id", "payment_method", "merchant", "notes", "status"}
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        if "date" in updates:
            date.fromisoformat(updates["date"])
        if "amount" in updates and updates["amount"] <= 0:
            raise ValueError("Amount must be greater than zero.")
        if "payment_method" in updates and updates["payment_method"] is not None:
            updates["payment_method"] = updates["payment_method"].strip() or None
        assignments = ", ".join(f"{key} = ?" for key in updates)
        self.connection.execute(
            f"UPDATE transactions SET {assignments} WHERE id = ?",
            (*updates.values(), transaction_id),
        )
        self.connection.commit()
        month = self.budget_month_for_date(updates.get("date", self.connection.execute(
            "SELECT date FROM transactions WHERE id = ?", (transaction_id,)
        ).fetchone()["date"]))
        self.refresh_budget_notifications(month)

    def delete_transaction(self, transaction_id: int) -> None:
        self.connection.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        self.connection.commit()

    def restore_transaction(self, record: dict[str, Any]) -> None:
        fields = ("id", "kind", "amount", "date", "category_id", "payment_method",
                  "merchant", "notes", "status", "recurring_id")
        self.connection.execute(
            """INSERT INTO transactions(id,kind,amount,date,category_id,payment_method,merchant,notes,status,recurring_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            tuple(record[field] for field in fields),
        )
        if record["recurring_id"] is not None:
            self.connection.execute(
                """UPDATE recurring_occurrences SET transaction_id=?
                WHERE recurring_id=? AND due_date=?""",
                (record["id"], record["recurring_id"], record["date"]),
            )
        self.connection.commit()
        if record["status"] == "paid" and record["kind"] in {"expense", "refund"}:
            self.refresh_budget_notifications(self.budget_month_for_date(record["date"]))

    def transactions(
        self,
        search: str = "",
        start: str = "",
        end: str = "",
        category_id: int | None = None,
        payment_method: str = "",
        kind: str = "",
        sort: str = "newest",
        limit: int = 200,
        offset: int = 0,
    ) -> list[sqlite3.Row]:
        where = ["(t.merchant LIKE ? OR t.notes LIKE ?)"]
        params: list[Any] = [f"%{search}%", f"%{search}%"]
        if start:
            where.append("t.date >= ?")
            params.append(start)
        if end:
            where.append("t.date <= ?")
            params.append(end)
        if category_id is not None:
            where.append("t.category_id = ?")
            params.append(category_id)
        if payment_method:
            where.append("t.payment_method = ?")
            params.append(payment_method)
        if kind:
            where.append("t.kind = ?")
            params.append(kind)
        ordering = {"newest": "t.date DESC, t.id DESC", "oldest": "t.date ASC, t.id ASC",
                    "amount high": "t.amount DESC", "amount low": "t.amount ASC"}.get(sort, "t.date DESC")
        params.extend((limit, offset))
        return list(self.connection.execute(
            f"""SELECT t.*, c.name AS category, c.icon AS category_icon,
                COUNT(*) OVER (PARTITION BY t.date,t.amount,t.kind,LOWER(TRIM(t.merchant))) AS duplicate_count
                FROM transactions t LEFT JOIN categories c ON c.id = t.category_id
                WHERE {' AND '.join(where)} ORDER BY {ordering} LIMIT ? OFFSET ?""",
            params,
        ))

    def totals(self, start: str, end: str) -> dict[str, int]:
        row = self.connection.execute(
            """SELECT
                COALESCE(SUM(CASE WHEN kind='income' AND status='paid' THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN kind='expense' AND status='paid' THEN amount ELSE 0 END), 0) AS expenses,
                COALESCE(SUM(CASE WHEN kind='refund' AND status='paid' THEN amount ELSE 0 END), 0) AS refunds
                FROM transactions WHERE date BETWEEN ? AND ?""",
            (start, end),
        ).fetchone()
        return dict(row)

    def category_spending(self, start: str, end: str) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            """SELECT c.name, c.icon, c.color,
                SUM(CASE WHEN t.kind='expense' THEN t.amount ELSE -t.amount END) AS amount
                FROM transactions t JOIN categories c ON c.id=t.category_id
                WHERE t.date BETWEEN ? AND ? AND t.status='paid' AND t.kind IN ('expense','refund')
                GROUP BY c.id HAVING amount > 0 ORDER BY amount DESC""",
            (start, end),
        ))

    def daily_spending(self, start: str, end: str) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            """SELECT date, SUM(CASE WHEN kind='expense' THEN amount ELSE -amount END) AS amount
            FROM transactions WHERE date BETWEEN ? AND ? AND status='paid'
            AND kind IN ('expense','refund') GROUP BY date
            HAVING SUM(CASE WHEN kind='expense' THEN amount ELSE -amount END)>0 ORDER BY date""",
            (start, end),
        ))

    def set_budget(self, month: str, amount: int, category_id: int | None = None) -> None:
        self.budget_bounds(month)
        if amount <= 0:
            raise ValueError("Budget must be greater than zero.")
        existing = self.connection.execute(
            "SELECT id FROM budgets WHERE month=? AND COALESCE(category_id, -1)=COALESCE(?, -1)",
            (month, category_id),
        ).fetchone()
        if existing:
            self.connection.execute("UPDATE budgets SET amount=? WHERE id=?", (amount, existing["id"]))
        else:
            self.connection.execute(
                "INSERT INTO budgets(month, category_id, amount) VALUES (?, ?, ?)",
                (month, category_id, amount),
            )
        self.connection.commit()
        self.refresh_budget_notifications(month)

    def copy_budgets(self, source_month: str, target_month: str) -> int:
        self.budget_bounds(source_month)
        self.budget_bounds(target_month)
        source = self.connection.execute(
            "SELECT category_id, amount FROM budgets WHERE month=?", (source_month,)
        ).fetchall()
        copied = 0
        for budget in source:
            exists = self.connection.execute(
                """SELECT 1 FROM budgets WHERE month=?
                AND COALESCE(category_id,-1)=COALESCE(?,-1)""",
                (target_month, budget["category_id"]),
            ).fetchone()
            if not exists:
                self.connection.execute(
                    "INSERT INTO budgets(month,category_id,amount) VALUES (?,?,?)",
                    (target_month, budget["category_id"], budget["amount"]),
                )
                copied += 1
        self.connection.commit()
        self.refresh_budget_notifications(target_month)
        return copied

    def budgets(self, month: str) -> list[sqlite3.Row]:
        start, end = self.budget_bounds(month)
        return list(self.connection.execute(
            """SELECT b.*, c.name AS category,
                COALESCE((SELECT SUM(CASE WHEN t.kind='expense' THEN t.amount ELSE -t.amount END)
                    FROM transactions t
                    WHERE (b.category_id IS NULL OR t.category_id=b.category_id) AND t.date BETWEEN ? AND ?
                    AND t.status='paid' AND t.kind IN ('expense','refund')), 0) AS spent
                FROM budgets b LEFT JOIN categories c ON c.id=b.category_id
                WHERE b.month=? ORDER BY b.category_id IS NOT NULL, c.name""",
            (start, end, month),
        ))

    def refresh_budget_notifications(self, month: str) -> None:
        for budget in self.budgets(month):
            ratio = budget["spent"] / budget["amount"]
            label = budget["category"] or "Overall"
            for threshold in (75, 90, 100):
                if ratio < threshold / 100:
                    continue
                message = f"{label} budget has reached {threshold}% for {month}."
                exists = self.connection.execute(
                    "SELECT 1 FROM notifications WHERE message=? LIMIT 1", (message,)
                ).fetchone()
                if not exists:
                    self.connection.execute("INSERT INTO notifications(message) VALUES (?)", (message,))
        self.connection.commit()

    def create_goal(self, name: str, target: int, target_date: str = "") -> int:
        if not name.strip() or target <= 0:
            raise ValueError("A savings goal needs a name and a positive target.")
        if target_date:
            date.fromisoformat(target_date)
        cursor = self.connection.execute(
            "INSERT INTO goals(name, target, target_date) VALUES (?, ?, ?)",
            (name.strip(), target, target_date or None),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def goals(self) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            """SELECT g.*, COALESCE(SUM(m.amount), 0) AS saved
                FROM goals g LEFT JOIN goal_movements m ON m.goal_id=g.id
                GROUP BY g.id ORDER BY g.id DESC"""
        ))

    def goal_completion_estimate(self, goal_id: int) -> str | None:
        row = self.connection.execute(
            """SELECT COALESCE(SUM(amount),0) AS recent_savings FROM goal_movements
            WHERE goal_id=? AND date>=date('now','-90 days')""",
            (goal_id,),
        ).fetchone()
        goal = next((item for item in self.goals() if item["id"] == goal_id), None)
        if goal is None or row["recent_savings"] <= 0 or goal["saved"] >= goal["target"]:
            return None
        daily_rate = row["recent_savings"] / 90
        remaining_days = (goal["target"] - goal["saved"]) / daily_rate
        return (date.today() + timedelta(days=round(remaining_days))).isoformat()

    def toggle_goal(self, goal_id: int) -> None:
        goal = self.connection.execute("SELECT status FROM goals WHERE id=?", (goal_id,)).fetchone()
        if goal is None:
            raise ValueError("Savings goal not found.")
        if goal["status"] == "completed":
            raise ValueError("A completed goal cannot be paused.")
        status = "active" if goal["status"] == "paused" else "paused"
        self.connection.execute("UPDATE goals SET status=? WHERE id=?", (status, goal_id))
        self.connection.commit()

    def move_goal(self, goal_id: int, amount: int, note: str = "", withdraw: bool = False) -> None:
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        goal = next((item for item in self.goals() if item["id"] == goal_id), None)
        if goal is None:
            raise ValueError("Savings goal not found.")
        if goal["status"] != "active":
            raise ValueError("Only active goals can be updated.")
        movement = -amount if withdraw else amount
        if goal["saved"] + movement < 0:
            raise ValueError("A withdrawal cannot exceed the amount saved.")
        self.connection.execute(
            "INSERT INTO goal_movements(goal_id, amount, date, note) VALUES (?, ?, ?, ?)",
            (goal_id, movement, date.today().isoformat(), note.strip()),
        )
        if goal["saved"] + movement >= goal["target"]:
            self.connection.execute("UPDATE goals SET status='completed' WHERE id=?", (goal_id,))
        self.connection.commit()

    @staticmethod
    def next_date(day: str, frequency: str, anchor_day: int | None = None,
                  anchor_month: int | None = None) -> str:
        current = date.fromisoformat(day)
        if frequency == "weekly":
            result = current.fromordinal(current.toordinal() + 7)
        elif frequency == "monthly":
            month_index = current.month % 12 + 1
            year = current.year + (current.month == 12)
            requested_day = anchor_day or current.day
            result = current.replace(year=year, month=month_index,
                                     day=min(requested_day, calendar.monthrange(year, month_index)[1]))
        elif frequency == "yearly":
            year = current.year + 1
            month = anchor_month or current.month
            requested_day = anchor_day or current.day
            result = current.replace(year=year, month=month,
                                     day=min(requested_day, calendar.monthrange(year, month)[1]))
        else:
            raise ValueError("Frequency must be weekly, monthly or yearly.")
        return result.isoformat()

    def create_recurring(self, name: str, amount: int, frequency: str, next_due: str,
                         category_id: int | None, payment_method: str, kind: str = "expense") -> int:
        due_date = date.fromisoformat(next_due)
        if not name.strip() or amount <= 0 or kind not in {"expense", "income"}:
            raise ValueError("Recurring payments need a name, positive amount, and valid type.")
        if frequency not in {"weekly", "monthly", "yearly"}:
            raise ValueError("Frequency must be weekly, monthly or yearly.")
        cursor = self.connection.execute(
            """INSERT INTO recurring(name, amount, kind, frequency, next_due, anchor_day, anchor_month,
                category_id, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name.strip(), amount, kind, frequency, next_due, due_date.day, due_date.month, category_id, payment_method),
        )
        self.connection.commit()
        self.generate_due_occurrences()
        return int(cursor.lastrowid)

    def generate_due_occurrences(self, today: str | None = None) -> int:
        current_day = today or date.today().isoformat()
        created = 0
        records = self.connection.execute("SELECT * FROM recurring WHERE active=1").fetchall()
        for item in records:
            due = item["next_due"]
            while due <= current_day:
                cursor = self.connection.execute(
                    """INSERT OR IGNORE INTO transactions
                    (kind, amount, date, category_id, payment_method, merchant, notes, status, recurring_id)
                    VALUES (?, ?, ?, ?, ?, ?, 'Recurring payment', 'pending', ?)""",
                    (item["kind"], item["amount"], due, item["category_id"], item["payment_method"],
                     item["name"], item["id"]),
                )
                transaction_id = cursor.lastrowid
                if cursor.rowcount:
                    self.connection.execute(
                        "INSERT OR IGNORE INTO recurring_occurrences(recurring_id, due_date, transaction_id) VALUES (?, ?, ?)",
                        (item["id"], due, transaction_id),
                    )
                    self.connection.execute(
                        "INSERT INTO notifications(message) VALUES (?)",
                        (f"Recurring {'payment' if item['kind'] == 'expense' else 'income'} due: {item['name']} on {due}.",),
                    )
                    created += 1
                due = self.next_date(due, item["frequency"], item["anchor_day"], item["anchor_month"])
            if due != item["next_due"]:
                self.connection.execute("UPDATE recurring SET next_due=? WHERE id=?", (due, item["id"]))
        self.connection.commit()
        return created

    def recurring_items(self) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            """SELECT r.*, c.name AS category FROM recurring r
            LEFT JOIN categories c ON c.id=r.category_id ORDER BY r.active DESC, r.next_due"""
        ))

    def recurring_costs(self) -> tuple[int, int]:
        monthly = 0.0
        for item in self.connection.execute("SELECT amount, frequency FROM recurring WHERE active=1 AND kind='expense'"):
            if item["frequency"] == "weekly":
                monthly += item["amount"] * 52 / 12
            elif item["frequency"] == "monthly":
                monthly += item["amount"]
            else:
                monthly += item["amount"] / 12
        monthly_cents = round(monthly)
        return monthly_cents, round(monthly_cents * 12)

    def toggle_recurring(self, recurring_id: int) -> None:
        self.connection.execute(
            "UPDATE recurring SET active=1-active WHERE id=?", (recurring_id,)
        )
        self.connection.commit()

    def mark_transaction_paid(self, transaction_id: int) -> None:
        row = self.connection.execute(
            "SELECT status, date FROM transactions WHERE id=?", (transaction_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Transaction not found.")
        self.connection.execute("UPDATE transactions SET status='paid' WHERE id=?", (transaction_id,))
        self.connection.commit()
        self.refresh_budget_notifications(self.budget_month_for_date(row["date"]))

    def create_group(self, name: str, members: list[str]) -> int:
        if not name.strip():
            raise ValueError("Enter a group name.")
        unique_members = list(dict.fromkeys(member.strip() for member in members if member.strip()))
        if len(unique_members) < 2:
            raise ValueError("Add at least two different group members.")
        cursor = self.connection.execute("INSERT INTO groups_table(name) VALUES (?)", (name.strip(),))
        group_id = int(cursor.lastrowid)
        self.connection.executemany(
            "INSERT INTO group_members(group_id, name) VALUES (?, ?)",
            ((group_id, member) for member in unique_members),
        )
        self.connection.commit()
        return group_id

    def add_group_member(self, group_id: int, name: str) -> None:
        if not name.strip():
            raise ValueError("Member name cannot be empty.")
        if not self.connection.execute("SELECT 1 FROM groups_table WHERE id=?", (group_id,)).fetchone():
            raise ValueError("Group not found.")
        self.connection.execute(
            "INSERT INTO group_members(group_id,name) VALUES (?,?)", (group_id, name.strip())
        )
        self.connection.commit()

    def groups(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM groups_table ORDER BY name"))

    def group_members(self, group_id: int) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM group_members WHERE group_id=? ORDER BY name", (group_id,)))

    def add_shared_expense(self, group_id: int, title: str, amount: int, paid_by: int,
                           splits: dict[int, int]) -> int:
        members = {member["id"] for member in self.group_members(group_id)}
        if not title.strip() or amount <= 0:
            raise ValueError("A shared expense needs a title and positive amount.")
        if not splits or set(splits) != members or any(value < 0 for value in splits.values()):
            raise ValueError("Every group member needs a valid split amount.")
        if sum(splits.values()) != amount:
            raise ValueError("Split amounts must add up exactly to the expense total.")
        if paid_by not in members:
            raise ValueError("The payer must belong to this group.")
        cursor = self.connection.execute(
            "INSERT INTO shared_expenses(group_id,title,amount,paid_by,date) VALUES (?,?,?,?,?)",
            (group_id, title.strip(), amount, paid_by, date.today().isoformat()),
        )
        expense_id = int(cursor.lastrowid)
        self.connection.executemany(
            "INSERT INTO expense_splits(expense_id,member_id,amount) VALUES (?,?,?)",
            ((expense_id, member_id, share) for member_id, share in splits.items()),
        )
        self.connection.commit()
        return expense_id

    def group_expenses(self, group_id: int) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            """SELECT e.*, m.name AS payer FROM shared_expenses e
            JOIN group_members m ON m.id=e.paid_by WHERE e.group_id=? ORDER BY e.date DESC, e.id DESC""",
            (group_id,),
        ))

    def group_balances(self, group_id: int) -> list[dict[str, Any]]:
        members = self.group_members(group_id)
        balances = {member["id"]: 0 for member in members}
        for expense in self.connection.execute(
            """SELECT e.paid_by, s.member_id, s.amount FROM shared_expenses e
            JOIN expense_splits s ON s.expense_id=e.id WHERE e.group_id=?""", (group_id,)
        ):
            balances[expense["paid_by"]] += expense["amount"]
            balances[expense["member_id"]] -= expense["amount"]
        for payment in self.connection.execute(
            "SELECT from_member,to_member,amount FROM repayments WHERE group_id=?", (group_id,)
        ):
            balances[payment["from_member"]] += payment["amount"]
            balances[payment["to_member"]] -= payment["amount"]
        return [{"member_id": member["id"], "name": member["name"], "balance": balances[member["id"]]}
                for member in members]

    def add_repayment(self, group_id: int, from_member: int, to_member: int, amount: int) -> None:
        if from_member == to_member or amount <= 0:
            raise ValueError("Choose two different members and a positive repayment.")
        members = {member["id"] for member in self.group_members(group_id)}
        if from_member not in members or to_member not in members:
            raise ValueError("Both members must belong to this group.")
        self.connection.execute(
            "INSERT INTO repayments(group_id,from_member,to_member,amount,date) VALUES (?,?,?,?,?)",
            (group_id, from_member, to_member, amount, date.today().isoformat()),
        )
        self.connection.commit()

    def notifications(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 100"))

    def mark_notifications_read(self) -> None:
        self.connection.execute("UPDATE notifications SET is_read=1")
        self.connection.commit()

    def setting(self, key: str, default: str = "") -> str:
        row = self.connection.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.connection.commit()

    def export_csv(self, path: str | Path) -> None:
        records = self.connection.execute(
            """SELECT t.date,t.kind,t.amount/100.0 AS amount,c.name AS category,
            t.payment_method,t.merchant,t.notes,t.status FROM transactions t
            LEFT JOIN categories c ON c.id=t.category_id ORDER BY t.date DESC,t.id DESC"""
        )
        with Path(path).open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(("Date", "Type", "Amount", "Category", "Payment method", "Merchant", "Notes", "Status"))
            writer.writerows(tuple(row) for row in records)

    def export_json(self, path: str | Path) -> None:
        tables = (
            "categories", "transactions", "budgets", "goals", "goal_movements",
            "recurring", "recurring_occurrences", "groups_table", "group_members",
            "shared_expenses", "expense_splits", "repayments", "notifications", "settings",
        )
        backup = {
            "format": "student-finance-manager-backup-v1",
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "data": {
                table: [dict(row) for row in self.connection.execute(f"SELECT * FROM {table}")]
                for table in tables
            },
        }
        with Path(path).open("w", encoding="utf-8") as file:
            json.dump(backup, file, ensure_ascii=False, indent=2)

    def monthly_summary(self, month: str) -> str:
        start, end = self.budget_bounds(month)
        totals = self.totals(start, end)
        spent = totals["expenses"] - totals["refunds"]
        lines = [
            f"STUDENT FINANCE MANAGER — {month}",
            "",
            f"Income received: ₹{totals['income'] / 100:,.2f}",
            f"Expenses:        ₹{totals['expenses'] / 100:,.2f}",
            f"Refunds:         ₹{totals['refunds'] / 100:,.2f}",
            f"Net spending:    ₹{spent / 100:,.2f}",
            f"Net cash flow:   ₹{(totals['income'] - spent) / 100:,.2f}",
            "",
            "SPENDING BY CATEGORY",
        ]
        lines.extend(f"{row['name']}: ₹{row['amount'] / 100:,.2f}" for row in self.category_spending(start, end))
        return "\n".join(lines)
