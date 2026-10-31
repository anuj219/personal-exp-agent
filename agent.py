
import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient


load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError(
        "GROQ_API_KEY is missing. Add it to your .env file."
    )


SYSTEM_PROMPT = """
You are a personal expense tracking assistant.

Use the available MCP tools to manage and query transactions.

Rules:
- Never claim an operation succeeded unless the tool confirms success.
- Never invent transaction amounts, dates, IDs, or tool results.
- Use summarize_transactions for financial totals.
- When editing a transaction, identify the correct record first
  using get_transaction or list_transactions.
- Use update_transaction to correct existing records. Do not
  create a replacement transaction when an existing one needs editing.
- Change only the fields the user asked to change.
- If the target transaction is ambiguous, ask which one they mean.
- For deletion, first call delete_transaction with confirm=False
  to retrieve the record and preview the deletion.
- Show the user the exact transaction that would be deleted.
- Do not delete until the user explicitly confirms that transaction.
  Only then call delete_transaction with confirm=True.
- Never treat an ambiguous reply as deletion confirmation.
- Ask for missing details rather than guessing.
- Distinguish hypothetical spending from actual transactions.

For requests to compare this month with last month:
1. Determine the current date.
2. Calculate the first and last dates of the current month.
3. Calculate the first and last dates of the previous month.
4. Call summarize_transactions separately for each date range.
5. Compare total expenses, total income, and net balance.
6. Calculate absolute and percentage changes.
7. If the previous month's value is zero, do not calculate a percentage change; explain why.
8. Clearly label both date ranges in the response.


TRANSACTION CATEGORY RULES:

Expense categories (use exact spelling):
- Food
- Groceries
- Transport
- Shopping
- Bills & Utilities
- Health
- Entertainment
- Travel
- Education
- Personal Care
- Housing
- Other

Income categories (use exact spelling):
- Salary
- Freelance
- Investments
- Gifts
- Other Income

Rules:
1. Every new or updated transaction must use a category
   from the appropriate list above.
2. Match the category to the transaction type:
   expenses use expense categories; income uses income categories.
3. Map natural-language descriptions to the closest appropriate
   approved category. For example, restaurant meals use
   "Food & Dining", bus fares use "Transport", and salary
   payments use "Salary".
4. Never invent new categories or use abbreviations or alternate
   spellings for category names.
5. If the category cannot be determined confidently, ask the user
   rather than guessing.
6. When updating a transaction's category, preserve its existing
   transaction type unless the user explicitly requests a change.
    

DATE AND CALENDAR RULES:
1. Use get_date_context whenever a request depends on the current date
  or a relative calendar expression.
2. Never guess today's date from model knowledge or conversation history.
"""


async def create_expense_agent(user_id: str):
    """Create a user-specific MCP client and LangChain agent."""

    client = MultiServerMCPClient(
        {
            "expenses": {
                "transport": "stdio",
                "command": "uv",
                "args": ["run", "python", "server.py"],
                "env": {
                    **os.environ,
                    "EXPENSE_USER_ID": user_id,
                },
            }
        }
    )

    tools = await client.get_tools()

    print(f"Tools discovered for user: {user_id}")
    for tool in tools:
        print(f"- {tool.name}")

    model = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0,
    )

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    return agent


async def process_message(agent, messages, user_message):
    """Send one text message to the existing agent."""

    messages.append(
        {"role": "user", "content": user_message}
    )

    result = await agent.ainvoke({"messages": messages})
    updated_messages = result["messages"]

    # Find the latest non-empty assistant response.
    for message in reversed(updated_messages):
        if message.type == "ai" and message.content:
            print(f"\nAgent: {message.content}\n")
            break

    return updated_messages


async def main():
    agent = await create_expense_agent()
    messages = []

    print("\nExpense Agent ready!")
    print("Examples:")
    print("  I spent 180 rupees on lunch using UPI")
    print("  Show my latest transactions")
    print("  How much did I spend?")
    print("Type 'exit' to quit.\n")

    while True:
        user_message = input("You: ").strip()

        if user_message.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        if not user_message:
            continue

        try:
            messages = await process_message(
                agent, messages, user_message
            )
        except Exception as exc:
            print(f"\nRequest failed: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())
