
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import calendar

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from mcp.server.fastmcp import FastMCP

import os
from uuid import UUID
from dotenv import load_dotenv
from supabase import create_client, Client

mcp = FastMCP("Personal Expense Agent")


# ----------- SUPABASE CONFIGS -----------------------
# Load environment variables from .env
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Supabase environment variables are missing.")

# Create one Supabase client for this MCP server process
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)


def get_current_user_id() -> str:
    """
    Get the authenticated user's UUID from the environment.

    This value is injected by our FastAPI backend.
    It is never supplied by the LLM.
    """
    user_id = os.getenv("EXPENSE_USER_ID")

    if not user_id:
        raise RuntimeError(
            "EXPENSE_USER_ID is missing. "
            "The MCP server must be started by the authenticated backend."
        )

    try:
        return str(UUID(user_id))
    except ValueError:
        raise RuntimeError("EXPENSE_USER_ID is not a valid UUID.")
# -----------

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
    occurred_on: str = ""
) -> str:
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

    try:
        # Validate transaction type
        transaction_type = transaction_type.strip().lower()

        if transaction_type not in ["expense", "income"]:
            return "Error: transaction_type must be 'expense' or 'income'."

        # Validate payment method
        payment_method = payment_method.strip().lower()

        if payment_method not in PAYMENT_METHODS:
            return f"Error: Invalid payment method. Allowed: {PAYMENT_METHODS}"

        # Validate category
        category = validate_category(transaction_type, category)

        # Convert rupees into paise
        amount_paise = rupees_to_paise(amount_rupees)

        # Validate date
        occurred_on = validate_date(occurred_on)

        # Get trusted user identity
        user_id = get_current_user_id()

        # Prepare cloud database record
        transaction = {
            "user_id": user_id,
            "amount_paise": amount_paise,
            "transaction_type": transaction_type,
            "payment_method": payment_method,
            "category": category,
            "subcategory": subcategory.strip() or None,
            "note": note.strip() or None,
            "occurred_on": occurred_on,
        }

        # Insert into Supabase
        response = (
            supabase.table("transactions")
            .insert(transaction)
            .execute()
        )

        if not response.data:
            return "Error: Transaction could not be saved."

        saved_transaction = response.data[0]

        return (
            f"Successfully added {transaction_type} of "
            f"₹{amount_rupees:.2f}. "
            f"Transaction ID: {saved_transaction['id']}"
        )

    except Exception as e:
        return f"Error adding transaction: {str(e)}"


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

    if start_date:
        start_date = validate_date(start_date)

    if end_date:
        end_date = validate_date(end_date)

    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    user_id = get_current_user_id()

    query = (
        supabase.table("transactions")
        .select("*")
        .eq("user_id", user_id)
    )

    if start_date:
        query = query.gte("occurred_on", start_date)

    if end_date:
        query = query.lte("occurred_on", end_date)

    if category.strip():
        query = query.ilike("category", category.strip())

    response = (
        query
        .order("occurred_on", desc=True)
        .order("id", desc=True)
        .limit(limit)
        .execute()
    )

    rows = response.data

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
    if start_date:
        start_date = validate_date(start_date)

    if end_date:
        end_date = validate_date(end_date)

    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    user_id = get_current_user_id()

    query = (
        supabase.table("transactions")
        .select("transaction_type, amount_paise")
        .eq("user_id", user_id)
    )

    if start_date:
        query = query.gte("occurred_on", start_date)

    if end_date:
        query = query.lte("occurred_on", end_date)

    rows = query.execute().data

    totals = {
        "expense_paise": 0,
        "income_paise": 0,
        "expense_count": 0,
        "income_count": 0,
    }

    for row in rows:
        if row["transaction_type"] == "expense":
            totals["expense_paise"] += row["amount_paise"]
            totals["expense_count"] += 1
        else:
            totals["income_paise"] += row["amount_paise"]
            totals["income_count"] += 1

    expense = totals["expense_paise"]
    income = totals["income_paise"]

    return {
        "start_date": start_date if start_date else None,
        "end_date": end_date if end_date else None,
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

    user_id = get_current_user_id()

    response = (
        supabase.table("transactions")
        .select("*")
        .eq("id", transaction_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    row = response.data[0] if response.data else None

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

    user_id = get_current_user_id()

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
            existing_response = (
                supabase.table("transactions")
                .select("transaction_type")
                .eq("id", transaction_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )

            existing_type = (
                existing_response.data[0]
                if existing_response.data
                else None
            )

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

    # Verify that the transaction belongs to the current user.
    existing_response = (
        supabase.table("transactions")
        .select("id")
        .eq("id", transaction_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not existing_response.data:
        return {
            "success": False,
            "message": f"Transaction #{transaction_id} was not found.",
        }

    # Update only the supplied fields.
    supabase.table("transactions").update(updates).eq(
        "id", transaction_id
    ).eq(
        "user_id", user_id
    ).execute()

    # Retrieve the updated transaction.
    response = (
        supabase.table("transactions")
        .select("*")
        .eq("id", transaction_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    row = response.data[0]

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

    user_id = get_current_user_id()

    response = (
        supabase.table("transactions")
        .select("*")
        .eq("id", transaction_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    row = response.data[0] if response.data else None

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

    supabase.table("transactions").delete().eq(
        "id", transaction_id
    ).eq(
        "user_id", user_id
    ).execute()

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


if __name__ == "__main__":
    mcp.run(transport="stdio")
