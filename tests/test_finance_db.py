import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from finance_db import FinanceDB


class FinanceDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = FinanceDB(Path(self.temp_dir.name) / "test.sqlite3")

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def category_id(self, name: str = "Food & groceries") -> int:
        return next(row["id"] for row in self.db.categories() if row["name"] == name)

    def test_seed_categories_and_transaction_totals(self) -> None:
        self.assertGreaterEqual(len(self.db.categories()), 10)
        category = self.category_id()
        self.db.add_transaction("income", 150_000, "2026-10-05")
        self.db.add_transaction("expense", 23_500, "2026-10-06", category, merchant="Lunch")
        self.db.add_transaction("refund", 3_500, "2026-10-07", category)
        self.db.add_transaction("expense", 50_000, "2026-10-08", category, status="pending")
        totals = self.db.totals("2026-10-01", "2026-10-31")
        self.assertEqual(totals, {"income": 150_000, "expenses": 23_500, "refunds": 3_500})
        self.assertEqual(self.db.category_spending("2026-10-01", "2026-10-31")[0]["amount"], 20_000)

    def test_transaction_category_and_payment_method_are_optional(self) -> None:
        transaction_id = self.db.add_transaction("expense", 1200, "2026-10-28")
        row = self.db.connection.execute(
            "SELECT category_id,payment_method FROM transactions WHERE id=?", (transaction_id,)
        ).fetchone()
        self.assertIsNone(row["category_id"])
        self.assertIsNone(row["payment_method"])

        self.db.update_transaction(transaction_id, category_id=self.category_id(), payment_method="UPI")
        row = self.db.connection.execute(
            "SELECT category_id,payment_method FROM transactions WHERE id=?", (transaction_id,)
        ).fetchone()
        self.assertEqual(row["category_id"], self.category_id())
        self.assertEqual(row["payment_method"], "UPI")

    def test_old_database_migrates_nullable_payment_method_without_losing_data(self) -> None:
        self.db.close()
        connection = sqlite3.connect(self.db.path)
        try:
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("DROP TABLE recurring_occurrences")
            connection.execute("DROP TABLE transactions")
            connection.execute(
                """CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY,
                    kind TEXT NOT NULL CHECK (kind IN ('expense','income','refund')),
                    amount INTEGER NOT NULL CHECK (amount > 0),
                    date TEXT NOT NULL,
                    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                    payment_method TEXT NOT NULL DEFAULT 'Other',
                    merchant TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'paid' CHECK (status IN ('paid','pending')),
                    recurring_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            category_id = connection.execute("SELECT id FROM categories LIMIT 1").fetchone()[0]
            connection.execute(
                """INSERT INTO transactions(kind,amount,date,category_id,payment_method,merchant)
                VALUES ('expense',2500,'2026-10-28',?,'UPI','Campus cafe')""",
                (category_id,),
            )
            connection.execute(
                """CREATE TABLE recurring_occurrences (
                    id INTEGER PRIMARY KEY,
                    recurring_id INTEGER NOT NULL REFERENCES recurring(id) ON DELETE CASCADE,
                    due_date TEXT NOT NULL,
                    transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
                    UNIQUE(recurring_id,due_date)
                )"""
            )
            connection.commit()
        finally:
            connection.close()

        self.db = FinanceDB(self.db.path)
        row = self.db.connection.execute(
            "SELECT kind,amount,payment_method,merchant FROM transactions"
        ).fetchone()
        self.assertEqual(tuple(row), ("expense", 2500, "UPI", "Campus cafe"))
        payment_column = next(
            item for item in self.db.connection.execute("PRAGMA table_info(transactions)")
            if item["name"] == "payment_method"
        )
        self.assertEqual(payment_column["notnull"], 0)
        self.assertFalse(self.db.connection.execute("PRAGMA foreign_key_check").fetchall())

    def test_budget_totals_for_overall_and_category(self) -> None:
        food = self.category_id()
        travel = self.category_id("Transport & fuel")
        self.db.add_transaction("expense", 60_000, "2026-10-04", food)
        self.db.add_transaction("expense", 20_000, "2026-10-05", travel)
        self.db.set_budget("2026-10", 100_000)
        self.db.set_budget("2026-10", 70_000, food)
        budgets = self.db.budgets("2026-10")
        overall = next(row for row in budgets if row["category_id"] is None)
        food_budget = next(row for row in budgets if row["category_id"] == food)
        self.assertEqual(overall["spent"], 80_000)
        self.assertEqual(food_budget["spent"], 60_000)
        self.assertEqual(self.db.budgets("2026-10"), budgets)

    def test_budget_carry_forward_does_not_replace_existing_limits(self) -> None:
        food = self.category_id()
        travel = self.category_id("Transport & fuel")
        self.db.set_budget("2026-09", 100_000)
        self.db.set_budget("2026-09", 35_000, food)
        self.db.set_budget("2026-10", 50_000, food)
        copied = self.db.copy_budgets("2026-09", "2026-10")
        budgets = self.db.budgets("2026-10")
        self.assertEqual(copied, 1)
        self.assertEqual(next(row["amount"] for row in budgets if row["category_id"] is None), 100_000)
        self.assertEqual(next(row["amount"] for row in budgets if row["category_id"] == food), 50_000)
        self.assertFalse(any(row["category_id"] == travel for row in budgets))

    def test_custom_budget_cycle_and_notification_threshold(self) -> None:
        food = self.category_id()
        self.db.set_setting("budget_start_day", "10")
        self.assertEqual(self.db.budget_bounds("2026-02"), ("2026-02-10", "2026-03-09"))
        self.assertEqual(self.db.budget_month_for_date("2026-03-09"), "2026-02")
        self.db.set_budget("2026-02", 10_000, food)
        self.db.add_transaction("expense", 10_000, "2026-03-01", food)
        messages = [item["message"] for item in self.db.notifications()]
        self.assertTrue(any("75%" in message for message in messages))
        self.assertTrue(any("90%" in message for message in messages))
        self.assertTrue(any("100%" in message for message in messages))

    def test_goal_withdrawal_cannot_make_savings_negative(self) -> None:
        goal_id = self.db.create_goal("Laptop", 100_000)
        self.db.move_goal(goal_id, 30_000)
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            self.db.move_goal(goal_id, 30_001, withdraw=True)
        self.db.move_goal(goal_id, 10_000, withdraw=True)
        self.assertEqual(self.db.goals()[0]["saved"], 20_000)

    def test_recurring_payments_generate_pending_transactions(self) -> None:
        food = self.category_id()
        recurring_id = self.db.create_recurring("Hostel", 25_000, "monthly", "2099-10-01", food, "UPI")
        created = self.db.generate_due_occurrences("2099-11-02")
        self.assertEqual(created, 2)
        pending = self.db.transactions(start="2099-10-01", end="2099-11-02")
        self.assertEqual([row["status"] for row in pending], ["pending", "pending"])
        self.db.mark_transaction_paid(pending[0]["id"])
        self.assertEqual(self.db.totals("2099-10-01", "2099-11-02")["expenses"], 25_000)
        self.assertGreaterEqual(self.db.recurring_items()[0]["id"], recurring_id)

    def test_month_end_recurring_dates_do_not_drift(self) -> None:
        february = FinanceDB.next_date("2024-01-31", "monthly", 31, 1)
        march = FinanceDB.next_date(february, "monthly", 31, 1)
        self.assertEqual((february, march), ("2024-02-29", "2024-03-31"))

    def test_recurring_income_is_generated_as_pending_income(self) -> None:
        self.db.create_recurring("Allowance", 80_000, "monthly", "2099-10-01", None, "Bank transfer", "income")
        self.db.generate_due_occurrences("2099-10-01")
        row = self.db.transactions(start="2099-10-01", end="2099-10-01")[0]
        self.assertEqual((row["kind"], row["status"]), ("income", "pending"))
        self.assertEqual(self.db.recurring_costs(), (0, 0))

    def test_shared_expense_settlement_balances(self) -> None:
        group_id = self.db.create_group("Flat 204", ["You", "Asha", "Kabir"])
        members = {row["name"]: row["id"] for row in self.db.group_members(group_id)}
        self.db.add_shared_expense(group_id, "Groceries", 900, members["You"],
                                   {member_id: 300 for member_id in members.values()})
        balances = {row["name"]: row["balance"] for row in self.db.group_balances(group_id)}
        self.assertEqual(balances, {"Asha": -300, "Kabir": -300, "You": 600})
        with self.assertRaisesRegex(ValueError, "add up exactly"):
            self.db.add_shared_expense(group_id, "Bad split", 900, members["You"],
                                       {members["You"]: 200, members["Asha"]: 300, members["Kabir"]: 300})
        self.db.add_repayment(group_id, members["Asha"], members["You"], 300)
        balances = {row["name"]: row["balance"] for row in self.db.group_balances(group_id)}
        self.assertEqual(balances["Asha"], 0)
        self.assertEqual(sum(balances.values()), 0)

    def test_csv_export_contains_transactions(self) -> None:
        self.db.add_transaction("income", 123_450, "2026-10-28", merchant="Scholarship")
        export = Path(self.temp_dir.name) / "transactions.csv"
        self.db.export_csv(export)
        with export.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.reader(file))
        self.assertEqual(rows[1][1], "income")
        self.assertEqual(rows[1][2], "1234.5")
        self.assertEqual(rows[1][5], "Scholarship")

    def test_amount_parsing_rounds_decimal_currency_safely(self) -> None:
        self.assertEqual(FinanceDB.parse_amount("1.005"), 101)
        with self.assertRaisesRegex(ValueError, "valid amount"):
            FinanceDB.parse_amount("not money")
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            FinanceDB.parse_amount("0")

    def test_transaction_search_flags_duplicates_and_restores_deletions(self) -> None:
        category = self.category_id()
        original_id = self.db.add_transaction("expense", 1200, "2026-10-28", category, merchant="Campus Cafe")
        self.db.add_transaction("expense", 1200, "2026-10-28", category, merchant="campus cafe")
        rows = self.db.transactions(search="cafe")
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["duplicate_count"] for row in rows], [2, 2])
        deleted = next(dict(row) for row in rows if row["id"] == original_id)
        self.db.delete_transaction(deleted["id"])
        self.db.restore_transaction(deleted)
        self.assertTrue(any(row["id"] == original_id for row in self.db.transactions()))

    def test_json_backup_includes_financial_records(self) -> None:
        self.db.add_transaction("income", 20_000, "2026-10-28", merchant="Allowance")
        self.db.set_setting("student_name", "Student A")
        export = Path(self.temp_dir.name) / "backup.json"
        self.db.export_json(export)
        data = json.loads(export.read_text(encoding="utf-8"))
        self.assertEqual(data["format"], "student-finance-manager-backup-v1")
        self.assertEqual(data["data"]["transactions"][0]["merchant"], "Allowance")
        self.assertEqual(data["data"]["settings"][0]["value"], "Student A")


if __name__ == "__main__":
    unittest.main()
