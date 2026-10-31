# Vector DB file
import chromadb
from pathlib import Path
import os
from dotenv import load_dotenv

from uuid import UUID
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Supabase environment variables are missing.")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
)

# Persist vector data inside the project directory.
MEMORY_DIR = Path(__file__).resolve().parent / "memory_store"

client = chromadb.PersistentClient(path=str(MEMORY_DIR))

collection = client.get_or_create_collection(
    name="personal_expense_memories",
    metadata={"hnsw:space": "cosine"},
)

def save_memory(
    user_id: str,
    memory_id: str,
    text: str,
    category: str = "general",
) -> None:
    """Save or update a useful fact in long-term memory."""
    text = text.strip()

    if not memory_id.strip():
        raise ValueError("memory_id cannot be empty.")

    if not text:
        raise ValueError("Memory text cannot be empty.")

    user_id = str(UUID(user_id))

    embedding = collection._embedding_function([text])[0].tolist()

    supabase.table("memories").upsert(
        {
            "user_id": user_id,
            "memory_id": memory_id,
            "content": text,
            "category": category,
            "embedding": embedding,
        },
        on_conflict="user_id,memory_id",
    ).execute()

def search_memories(
    user_id: str,
    query: str,
    limit: int = 3,
) -> list[dict]:
    """Find memories that are semantically relevant to a query."""
    query = query.strip()

    if not query:
        return []

    if limit < 1:
        return []

    user_id = str(UUID(user_id))

    query_embedding = collection._embedding_function([query])[0].tolist()

    results = supabase.rpc(
        "search_memories",
        {
            "query_embedding": query_embedding,
            "match_user_id": user_id,
            "match_count": limit,
        },
    ).execute()

    memories = []

    for row in results.data:
        memories.append({
            "text": row["content"],
            "category": row["category"],
            "distance": row["distance"],
        })

    return memories


def extract_memories(user_message: str, assistant_reply: str) -> list[dict]:
    """
    Extract stable, useful user preferences and facts from a conversation.
    Returns an empty list when there is nothing worth remembering.
    """
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, SystemMessage
    import json

    memory_api_key = os.getenv("GROQ_VECTOR_API_KEY")

    if not memory_api_key:
        raise RuntimeError(
            "GROQ_VECTOR_API_KEY is missing from the environment."
        )

    model = ChatGroq(
        api_key=memory_api_key,
        model="openai/gpt-oss-20b",
        temperature=0,
    )

    response = model.invoke([
        SystemMessage(content="""

You extract long-term memories for a personal expense assistant.

Save only useful, reasonably stable information, such as:
- Explicit user preferences for categories or assistant behavior.
- Budgeting preferences and recurring financial workflows.
- Corrections to previously stated preferences.

Do NOT save:
- Ordinary transaction details, amounts, or dates.
- Temporary requests, greetings, or generic questions.
- Guesses about identity, income, habits, or preferences.
- Sensitive financial information that is not necessary.

MEMORY ID RULES:
1. IDs must be deterministic, lowercase snake_case identifiers.
2. The same preference must ALWAYS use the same ID, even when its wording changes.
3. Never create a new ID just because the user rephrased or corrected a preference.
4. For the user's preferred category for restaurant and food expenses,
   ALWAYS use the ID "preference_food_expense_category".
5. For other preferences, use a consistent ID based on the subject,
   such as "preference_response_style".
6. When the user explicitly changes a preference, save the NEW value
   using the SAME ID as the previous preference.
7. If the current message explicitly corrects a preference, treat the
   newly stated value as authoritative. Do not preserve the superseded
   value as a separate memory.
8. Extract only facts supported by the current conversation. Do not
   invent a preference or claim to know an earlier value that is not provided.
9. Return only the current preference value for a preference explicitly
   corrected in the current message.

Return ONLY a valid JSON array. Each item must contain:
- "id": a deterministic, stable identifier
- "text": one concise, standalone factual memory
- "category": "preference", "workflow", or "general"

If nothing is worth remembering, return [].

"""),
        HumanMessage(content=f"""
User message:
{user_message}

Assistant reply:
{assistant_reply}
""")
    ])

    try:
        memories = json.loads(response.content)
        if not isinstance(memories, list):
            return []
    except (json.JSONDecodeError, TypeError):
        return []

    valid_memories = []

    for item in memories:
        if not isinstance(item, dict):
            continue

        memory_id = item.get("id")
        memory_text = item.get("text")
        category = item.get("category", "general")

        if (
            isinstance(memory_id, str)
            and isinstance(memory_text, str)
            and memory_id.strip()
            and memory_text.strip()
            and category in {"preference", "workflow", "general"}
        ):
            valid_memories.append({
                "id": memory_id.strip(),
                "text": memory_text.strip(),
                "category": category,
            })

    return valid_memories
