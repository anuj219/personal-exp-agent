
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import calendar

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import sqlite3

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Personal Expense Agent")

DB_PATH = "expenses.db"


EXPENSE_CATEGORIES = [
    "Food",
    "Groceries",
    "Transport",
    "Shopping",
    "Bills & Utilities",
    "Health",
    "Entertainment",
    "Travel",
    "Education",
    "Personal Care",
    "Housing",
    "Other",
]

INCOME_CATEGORIES = [
    "Salary",
    "Freelance",
    "Investments",
    "Gifts",
    "Other Income",
]

PAYMENT_METHODS = [
    "cash",
    "upi",
    "card",
    "bank",
    "other",
]


def validate_category(transaction_type: str, category: str) -> str:
    """Validate and return a category allowed for this transaction type."""

    if transaction_type == "expense":
        allowed_categories = EXPENSE_CATEGORIES
    elif transaction_type == "income":
        allowed_categories = INCOME_CATEGORIES
    else:
        raise ValueError(
            "transaction_type must be 'expense' or 'income'."
        )

    category = category.strip()

    if category not in allowed_categories:
        allowed = ", ".join(allowed_categories)
        raise ValueError(
            f"Invalid category '{category}' for {transaction_type}. "
            f"Allowed categories: {allowed}"
        )

    return category


def get_connection():
    """Open a connection to the local SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """Create the transactions table if it doesn't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
                transaction_type TEXT NOT NULL
                    CHECK (transaction_type IN ('expense', 'income')),
                payment_method TEXT NOT NULL
                    CHECK (payment_method IN ('cash', 'upi', 'card', 'bank', 'other')),
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                occurred_on TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

def initialize_chat_history():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL
                    CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def rupees_to_paise(amount_rupees: float) -> int:
    """Convert rupees into integer paise to avoid floating-point storage."""
    try:
        amount = Decimal(str(amount_rupees))
    except (InvalidOperation, ValueError):
        raise ValueError("Amount must be a valid number.")

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    paise = (amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    if amount != Decimal(str(paise)) / 100:
        raise ValueError("Amount cannot have more than two decimal places.")

    return int(paise)


def validate_date(value: str) -> str:
    """Use today's date when omitted; otherwise require YYYY-MM-DD."""
    if not value:
        return date.today().isoformat()

    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError("Date must use YYYY-MM-DD format.")


def format_transaction(row):
    """Convert a database row into a readable dictionary."""
    return {
        "id": row["id"],
        "amount_rupees": f'{row["amount_paise"] / 100:.2f}',
        "transaction_type": row["transaction_type"],
        "payment_method": row["payment_method"],
        "category": row["category"],
        "subcategory": row["subcategory"],
        "note": row["note"],
        "occurred_on": row["occurred_on"],
    }


@mcp.tool()
def add_transaction(
    amount_rupees: float,
    transaction_type: str,
    payment_method: str,
    category: str,
    subcategory: str = "",
    note: str = "",
    occurred_on: str = "",
) -> dict:
    """Record one expense or income transaction.

    Args:
        amount_rupees: Positive amount in rupees, e.g. 120 or 45.50.
        transaction_type: 'expense' or 'income'.
        payment_method: 'cash', 'upi', 'card', 'bank', or 'other'.
        category: Exact category from the approved expense or income category list.
        subcategory: Optional detail, such as lunch or bus.
        note: Optional description.
        occurred_on: Optional transaction date in YYYY-MM-DD format.
    """
    transaction_type = transaction_type.strip().lower()
    payment_method = payment_method.strip().lower()

    if transaction_type not in {"expense", "income"}:
        raise ValueError("transaction_type must be 'expense' or 'income'.")
    category = validate_category(transaction_type, category)

    if payment_method not in {"cash", "upi", "card", "bank", "other"}:
        raise ValueError("Unsupported payment method.")

    if not category:
        raise ValueError("Category cannot be empty.")

    amount_paise = rupees_to_paise(amount_rupees)
    transaction_date = validate_date(occurred_on)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO transactions (
                amount_paise, transaction_type, payment_method,
                category, subcategory, note, occurred_on
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                amount_paise,
                transaction_type,
                payment_method,
                category,
                subcategory.strip(),
                note.strip(),
                transaction_date,
            ),
        )
        transaction_id = cursor.lastrowid

    return {
        "success": True,
        "message": f"{transaction_type.title()} recorded successfully.",
        "transaction": {
            "id": transaction_id,
            "amount_rupees": f"{amount_paise / 100:.2f}",
            "transaction_type": transaction_type,
            "payment_method": payment_method,
            "category": category,
            "subcategory": subcategory.strip(),
            "note": note.strip(),
            "occurred_on": transaction_date,
        },
    }


@mcp.tool()
def list_transactions(
    start_date: str = "",
    end_date: str = "",
    category: str = "",
    limit: int = 20,
) -> dict:
    """List recent transactions, optionally filtered by date and category.

    Args:
        start_date: Optional inclusive start date in YYYY-MM-DD format.
        end_date: Optional inclusive end date in YYYY-MM-DD format.
        category: Optional category filter.
        limit: Maximum number of results, from 1 to 100.
    """
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100.")

    conditions = []
    params = []

    if start_date:
        conditions.append("occurred_on >= ?")
        params.append(validate_date(start_date))

    if end_date:
        conditions.append("occurred_on <= ?")
        params.append(validate_date(end_date))

    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    if category.strip():
        conditions.append("category = ?")
        params.append(category.strip().lower())

    where_clause = (
        "WHERE " + " AND ".join(conditions) if conditions else ""
    )

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM transactions
            {where_clause}
            ORDER BY occurred_on DESC, id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()

    return {
        "count": len(rows),
        "transactions": [format_transaction(row) for row in rows],
    }


@mcp.tool()
def summarize_transactions(
    start_date: str = "",
    end_date: str = "",
) -> dict:
    """Summarize income, expenses, and net cash flow for a date range.

    Args:
        start_date: Optional inclusive start date in YYYY-MM-DD format.
        end_date: Optional inclusive end date in YYYY-MM-DD format.
    """
    conditions = []
    params = []

    if start_date:
        conditions.append("occurred_on >= ?")
        params.append(validate_date(start_date))

    if end_date:
        conditions.append("occurred_on <= ?")
        params.append(validate_date(end_date))

    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    where_clause = (
        "WHERE " + " AND ".join(conditions) if conditions else ""
    )

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                transaction_type,
                SUM(amount_paise) AS total_paise,
                COUNT(*) AS transaction_count
            FROM transactions
            {where_clause}
            GROUP BY transaction_type
            """,
            params,
        ).fetchall()

    totals = {
        "expense_paise": 0,
        "income_paise": 0,
        "expense_count": 0,
        "income_count": 0,
    }

    for row in rows:
        if row["transaction_type"] == "expense":
            totals["expense_paise"] = row["total_paise"] or 0
            totals["expense_count"] = row["transaction_count"]
        else:
            totals["income_paise"] = row["total_paise"] or 0
            totals["income_count"] = row["transaction_count"]

    expense = totals["expense_paise"]
    income = totals["income_paise"]

    return {
        "start_date": validate_date(start_date) if start_date else None,
        "end_date": validate_date(end_date) if end_date else None,
        "total_expenses_rupees": f"{expense / 100:.2f}",
        "total_income_rupees": f"{income / 100:.2f}",
        "net_rupees": f"{(income - expense) / 100:.2f}",
        "expense_count": totals["expense_count"],
        "income_count": totals["income_count"],
    }



@mcp.tool()
def get_transaction(transaction_id: int) -> dict:
    """Retrieve one transaction using its unique ID."""
    if transaction_id < 1:
        raise ValueError("transaction_id must be a positive integer.")

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()

    if row is None:
        return {
            "success": False,
            "message": f"Transaction #{transaction_id} was not found.",
        }

    return {
        "success": True,
        "transaction": format_transaction(row),
    }


@mcp.tool()
def update_transaction(
    transaction_id: int,
    amount_rupees: float | None = None,
    transaction_type: str | None = None,
    payment_method: str | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    note: str | None = None,
    occurred_on: str | None = None,
) -> dict:
    """Update specified fields of an existing transaction.

    Only supplied fields are changed. Unspecified fields remain unchanged.
    Use get_transaction first if the target transaction is unclear.
    """
    if transaction_id < 1:
        raise ValueError("transaction_id must be a positive integer.")

    updates = {}
    if amount_rupees is not None:
        updates["amount_paise"] = rupees_to_paise(amount_rupees)

    if transaction_type is not None:
        value = transaction_type.strip().lower()
        if value not in {"expense", "income"}:
            raise ValueError("transaction_type must be 'expense' or 'income'.")
        updates["transaction_type"] = value

    if payment_method is not None:
        value = payment_method.strip().lower()
        if value not in {"cash", "upi", "card", "bank", "other"}:
            raise ValueError("Unsupported payment method.")
        updates["payment_method"] = value

    if category is not None:
        # Use the new transaction type if supplied;
        # otherwise, retrieve the existing type from the database.
        if transaction_type is not None:
            effective_type = transaction_type.strip().lower()
        else:
            with get_connection() as conn:
                existing_type = conn.execute(
                    "SELECT transaction_type FROM transactions WHERE id = ?",
                    (transaction_id,),
                ).fetchone()

            if existing_type is None:
                return {
                    "success": False,
                    "message": f"Transaction #{transaction_id} was not found.",
                }

            effective_type = existing_type["transaction_type"]

        value = validate_category(effective_type, category)
        updates["category"] = value

    if subcategory is not None:
        updates["subcategory"] = subcategory.strip()

    if note is not None:
        updates["note"] = note.strip()

    if occurred_on is not None:
        updates["occurred_on"] = validate_date(occurred_on)

    if not updates:
        raise ValueError("Provide at least one field to update.")

    # Column names come only from the fixed dictionary above.
    assignments = ", ".join(
        f"{column} = ?" for column in updates
    )
    values = list(updates.values()) + [transaction_id]

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()

        if existing is None:
            return {
                "success": False,
                "message": f"Transaction #{transaction_id} was not found.",
            }

        conn.execute(
            f"UPDATE transactions SET {assignments} WHERE id = ?",
            values,
        )

        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()

    return {
        "success": True,
        "message": f"Transaction #{transaction_id} updated successfully.",
        "transaction": format_transaction(row),
    }


@mcp.tool()
def delete_transaction(
    transaction_id: int,
    confirm: bool = False,
) -> dict:
    """Delete a transaction by ID.

    First call with confirm=False to preview the transaction.
    Delete only after the user explicitly confirms that exact transaction,
    by calling again with confirm=True.
    """
    if transaction_id < 1:
        raise ValueError("transaction_id must be a positive integer.")

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()

        if row is None:
            return {
                "success": False,
                "message": f"Transaction #{transaction_id} was not found.",
            }

        transaction = format_transaction(row)

        if not confirm:
            return {
                "success": False,
                "confirmation_required": True,
                "message": (
                    f"Confirm deletion of transaction #{transaction_id}. "
                    "No changes have been made."
                ),
                "transaction": transaction,
            }

        conn.execute(
            "DELETE FROM transactions WHERE id = ?",
            (transaction_id,),
        )

    return {
        "success": True,
        "message": f"Transaction #{transaction_id} deleted.",
        "deleted_transaction": transaction,
    }



@mcp.tool()
def get_date_context() -> dict:
    """Get the current date, weekday, and calendar boundaries in India.
    Use this tool whenever interpreting relative dates such as yesterday,
    last Wednesday, this week, last month, or today."""

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    # Monday is the first day of the week.
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(days=1)

    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    return {
        "current_date": today.isoformat(),
        "current_weekday": today.strftime("%A"),
        "timezone": "Asia/Kolkata",
        "yesterday": (today - timedelta(days=1)).isoformat(),
        "day_before_yesterday": (
            today - timedelta(days=2)
        ).isoformat(),
        "this_week_start": this_week_start.isoformat(),
        "this_week_end": (
            this_week_start + timedelta(days=6)
        ).isoformat(),
        "last_week_start": last_week_start.isoformat(),
        "last_week_end": last_week_end.isoformat(),
        "this_month_start": this_month_start.isoformat(),
        "this_month_end": (
            today.replace(
                day=calendar.monthrange(today.year, today.month)[1]
            )
        ).isoformat(),
        "last_month_start": last_month_start.isoformat(),
        "last_month_end": last_month_end.isoformat(),
        "current_year": today.year,
    }


initialize_database()
initialize_chat_history()

if __name__ == "__main__":
    mcp.run(transport="stdio")
