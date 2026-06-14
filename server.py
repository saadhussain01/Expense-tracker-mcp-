from fastmcp import FastMCP
import os
import aiosqlite
import tempfile
import json

# Use temporary directory for the database (writable at runtime)
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")


def init_db():
    """Initialize the SQLite database synchronously at startup."""
    import sqlite3
    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                subcategory TEXT    DEFAULT '',
                note        TEXT    DEFAULT ''
            )
        """)
        # Verify write access
        c.execute("INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')")
        c.execute("DELETE FROM expenses WHERE category = 'test'")
    print("Database initialized successfully.")


# Run once at module load so Horizon picks it up immediately
init_db()


# ── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def add_expense(date: str, amount: float, category: str,
                      subcategory: str = "", note: str = "") -> dict:
    """Add a new expense entry.

    Args:
        date: ISO date string, e.g. '2024-06-14'
        amount: Expense amount (positive number)
        category: Top-level category (e.g. 'Food & Dining')
        subcategory: Optional sub-category
        note: Optional free-text note
    """
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, category, subcategory, note),
            )
            expense_id = cur.lastrowid
            await c.commit()
        return {"status": "success", "id": expense_id, "message": "Expense added successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def list_expenses(start_date: str, end_date: str) -> list:
    """List expenses within an inclusive date range.

    Args:
        start_date: Start of range, e.g. '2024-01-01'
        end_date:   End of range,   e.g. '2024-12-31'
    """
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in await cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def summarize(start_date: str, end_date: str, category: str = "") -> list:
    """Summarize expenses by category within an inclusive date range.

    Args:
        start_date: Start of range, e.g. '2024-01-01'
        end_date:   End of range,   e.g. '2024-12-31'
        category:   Optional — filter to a single category
    """
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) AS count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params: list = [start_date, end_date]
            if category:
                query += " AND category = ?"
                params.append(category)
            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = await c.execute(query, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in await cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Resource ─────────────────────────────────────────────────────────────────

DEFAULT_CATEGORIES = {
    "categories": [
        "Food & Dining",
        "Transportation",
        "Shopping",
        "Entertainment",
        "Bills & Utilities",
        "Healthcare",
        "Travel",
        "Education",
        "Business",
        "Other",
    ]
}

@mcp.resource("expense:///categories", mime_type="application/json")
def categories() -> str:
    """Return available expense categories as JSON."""
    categories_path = os.path.join(os.path.dirname(__file__), "categories.json")
    try:
        with open(categories_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return json.dumps(DEFAULT_CATEGORIES, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
