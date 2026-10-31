import os
import re
from getpass import getpass

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_PROJECT_URL"),
    os.getenv("SUPABASE_SECRET_KEY")
)

username = "anujmehta"

if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
    raise ValueError("Invalid username")

# Check whether this username already exists
existing = (
    supabase.table("profiles")
    .select("id")
    .eq("username", username)
    .execute()
)

if existing.data:
    raise RuntimeError("This username already exists.")

# Internal email used only by Supabase Auth.
# You will log in using your username, not this email.
internal_email = f"{username}@expense-agent.example.com"

password = getpass("Create password: ")
confirm_password = getpass("Confirm password: ")

if password != confirm_password:
    raise ValueError("Passwords do not match.")

if len(password) < 12:
    raise ValueError("Use a password with at least 12 characters.")

response = supabase.auth.admin.create_user({
    "email": internal_email,
    "password": password,
    "email_confirm": True,
    "user_metadata": {
        "username": username
    }
})

print("\nAccount created successfully!")
print("Username:", username)
print("User ID:", response.user.id)