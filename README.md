Preferences vector storage,I would give it a transaction once, and next time I could just say salary credited and it would understand the payment method and amount and all by itself
and other such similar preferences

Also, like
    suppose I added a transaction for coffee via voice in a live day
    and after an hour, I say, nevermind remove the coffee transaction, then it has to remove the last added one, as I drink coffee everyday
    how would we solve this

Also, what if one prompt by user needs 2-3 mcp tool calls together

Also, as the agent will be local in future, we need to have a tool that updates it regarding current day date week month etc details
    so it can perform things like, summarize transactions from day before yesterday, or last wednesday

Cool, now lets start with the app
    For the app my idea is
        basically I want to make it as a widget that will stay on my homescreen page 2
        such that it has two options there, mic and type
            mic one starts the voice agent which listens request, prints it out below in the widget space itself after hearing, and once I press ok/send button, it goes ahead
            and for type, once I type and press the ok/send button, it goes ahead
            and prints the latest success/followup response there it self
        the entire convos/chat will be available when I specifically open the app, not in the widget
        widget is only for recording

        the main app on opening would look like a basic chatbot with all these convos
        and one tab where I can view the raw db in table form

        is this possible

uv run uvicorn api:app --host 0.0.0.0 --port 8000



----------------------------------------------------------- DOCS ------------------------
# Personal Expense AI Agent
## Complete Architecture & Technical Handover

**Project:** Personal Expense Agent  
**Architecture:** Flutter + FastAPI + LangChain + MCP + Groq + Supabase  
**Backend hosting:** Render  
**Database and authentication:** Supabase  
**AI model:** `openai/gpt-oss-20b` through Groq  
**Primary goal:** A personal AI-powered expense manager that accepts natural-language and voice-based expense instructions, manages transactions, and provides conversational financial summaries.

---

# 1. Project Overview

The Personal Expense AI Agent is an AI-powered expense management application.

Instead of manually entering every transaction into a traditional expense tracker, users can interact with an AI assistant using natural language.

Examples:

- "I spent ₹250 on lunch using cash."
- "Add ₹500 for petrol using UPI."
- "Show all my expenses for the last two days."
- "How much did I spend this month?"
- "Compare my expenses this month with last month."
- "Show my latest transactions."

The AI agent understands the request, selects the appropriate tools, executes operations through an MCP server, and returns a natural-language response.

The application supports multiple users. Each user has their own authentication identity, transactions, and conversation history.

## Core architectural idea

The system separates responsibilities into different layers:

1. **Flutter:** User interface and interaction.
2. **FastAPI:** Backend API, authentication, and request orchestration.
3. **LangChain:** AI agent creation and tool orchestration.
4. **Groq:** LLM inference.
5. **MCP:** Standardized interface between the AI agent and backend tools.
6. **Supabase:** Persistent database, authentication, and memory storage.
7. **Render:** Cloud hosting for the FastAPI backend.

---

# 2. High-Level Architecture

```text
                 USER
                  |
                  |
          FLUTTER ANDROID APP
                  |
        +---------+----------+
        |                    |
     Login                Chat UI
        |                    |
        |              Transactions UI
        |                    |
        +---------+----------+
                  |
             HTTPS Requests
                  |
                  v
          RENDER CLOUD SERVER
                  |
               FASTAPI
                  |
        +---------+----------+
        |                    |
   Authentication       Chat API
        |                    |
        |              User-specific
        |              Agent creation
        |                    |
        |                LANGCHAIN
        |                    |
        |              GROQ LLM
        |                    |
        |              Tool selection
        |                    |
        |               MCP CLIENT
        |                    |
        |              STDIO Transport
        |                    |
        |              MCP SERVER
        |                    |
        |       +------------+------------+
        |       |            |            |
        |   Add/List     Update/Delete  Summary
        | Transactions  Transactions   Tools
        |       |            |            |
        +-------+------------+------------+
                             |
                             v
                         SUPABASE
                             |
                 +-----------+-----------+
                 |           |           |
             Profiles   Transactions  Chat Messages
                                         |
                                      Memories
```

**Important:** The diagram represents the logical architecture. Authentication and direct transaction API requests do not need to pass through the LangChain agent or MCP server.

---

# 3. Technology Stack

| Component | Technology | Responsibility |
|---|---|---|
| Mobile frontend | Flutter / Dart | UI and user interaction |
| Backend framework | FastAPI | REST APIs |
| Agent framework | LangChain | Agent orchestration |
| LLM provider | Groq | Model inference |
| LLM model | `openai/gpt-oss-20b` | Natural-language understanding and reasoning |
| Tool protocol | MCP | Exposing backend capabilities as tools |
| MCP framework | FastMCP | Building MCP server |
| MCP transport | stdio | Communication between MCP client and server |
| Database | Supabase PostgreSQL | Persistent data |
| Authentication | Supabase Auth | User authentication |
| Vector storage | Supabase with vector search | Semantic memory retrieval |
| Backend hosting | Render | Public cloud API |
| HTTP client | Flutter `http` package | REST communication |
| Secure local storage | `flutter_secure_storage` | Saving authentication tokens |

---

# 4. Backend Architecture

Backend repository:

`personal-expense-agent`

Main responsibilities:

- Authenticate users.
- Receive requests from Flutter.
- Create user-specific AI agents.
- Connect agents to MCP tools.
- Store and retrieve transactions.
- Manage chat history and memories.
- Communicate with Supabase.

## 4.1 FastAPI — API Layer

FastAPI is the entry point for requests from the Flutter application.

The backend exposes REST endpoints.

### Current API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Health check |
| `/docs` | GET | Swagger documentation |
| `/auth/login` | POST | Authenticate username and password |
| `/auth/me` | GET | Validate current authenticated user |
| `/chat` | POST | Send a message to the AI agent |
| `/chat/history` | GET | Retrieve previous conversation |
| `/transactions` | GET | Retrieve transactions |
| `/transactions` | POST | Add a transaction |

The transaction update and delete functionality currently exists as MCP tools. Do not assume that separate REST update/delete endpoints have been implemented.

### Authentication protection

Protected endpoints use:

```python
user_id: str = Depends(get_current_user)
```

This dependency extracts and validates the authenticated user's Supabase access token.

The resulting user ID is passed to the endpoint.

This is important because the backend is using a Supabase service-role key, which bypasses normal Row Level Security restrictions.

Therefore, the backend explicitly scopes database queries:

```python
.eq("user_id", user_id)
```

Without this filtering, one user's request could potentially access another user's data.

---

# 5. Authentication Architecture

The application uses Supabase Auth.

Public signup is disabled. Accounts are created administratively.

## Login flow

```text
USER ENTERS CREDENTIALS
          |
          v
Flutter LoginScreen
          |
          v
AuthService.login()
          |
          v
POST /auth/login
          |
          v
FastAPI
          |
          v
Supabase Auth
          |
          v
Authentication successful
          |
          v
Access Token + Refresh Token
          |
          v
Flutter Secure Storage
          |
          v
AuthGate
          |
          v
HomeScreen
```

### Username-based login

Supabase Auth normally uses email/password.

To provide username-based login, the backend maps usernames to synthetic email addresses:

```text
username@expense-agent.example.com
```

For example:

```text
anujmehta@expense-agent.example.com
```

The user enters their username and password in Flutter. The backend performs the mapping and authenticates against Supabase.

### Flutter authentication files

`lib/data/auth_service.dart`

Responsibilities:

- Login request.
- Save access token.
- Save refresh token.
- Save user ID.
- Read saved tokens.
- Check whether a local session exists.
- Logout and clear stored credentials.

`lib/screens/login_screen.dart`

Responsibilities:

- Username input.
- Password input.
- Login button.
- Password visibility.
- Loading and error states.

`AuthGate` in `main.dart`

Responsibilities:

- Check whether a saved access token exists.
- Show login screen if not authenticated.
- Show HomeScreen if authenticated.

### Logout flow

```text
USER TAPS LOGOUT
       |
       v
Confirmation Dialog
       |
       v
AuthService.logout()
       |
       v
Delete saved tokens
       |
       v
AuthGate state updated
       |
       v
LoginScreen
```

**Known limitation:** The current session restoration checks for the presence of a saved token. It does not necessarily verify that the token is still valid with Supabase.

A proper refresh-token and expired-session flow has not yet been implemented.

---

# 6. Agent Architecture — LangChain + Groq

This is the intelligence layer of the application.

The LLM does not directly access the database.

Instead, it receives a collection of available tools and decides which ones to use based on the user's request.

## 6.1 Agent creation

File:

`agent.py`

The main function:

```python
async def create_expense_agent(user_id: str):
```

This function creates a user-specific MCP client.

Current MCP client configuration:

```python
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
```

### What happens here?

1. FastAPI receives an authenticated user's request.
2. The user ID is passed to `create_expense_agent()`.
3. LangChain starts an MCP server subprocess.
4. The subprocess runs `server.py`.
5. The environment variable `EXPENSE_USER_ID` identifies the user.
6. MCP tools are discovered using:

```python
tools = await client.get_tools()
```

7. Groq is initialized:

```python
model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
)
```

8. The LangChain agent is created:

```python
agent = create_agent(
    model=model,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)
```

The agent now has access to the tools exposed by the MCP server.

### Why use a user-specific agent?

The application is multi-user.

Each user's agent must execute operations using the correct user identity.

The MCP server receives that identity through:

```text
EXPENSE_USER_ID
```

This allows transaction operations to be scoped to the correct account.

---

# 7. MCP Architecture

MCP stands for Model Context Protocol.

It provides a standardized way for AI applications to discover and invoke external tools.

In this project:

- LangChain acts as the MCP client.
- FastMCP implements the MCP server.
- `server.py` exposes expense-management functions as tools.
- Communication uses stdio transport.

## Why MCP?

Without MCP, we could manually define every function and connect it directly to the agent.

MCP separates the tools from the agent implementation.

This makes it easier to:

- Add new tools.
- Modify existing tools.
- Reuse the same server with different clients.
- Keep database operations separate from LLM reasoning.
- Extend the assistant with additional capabilities.

## 7.1 MCP tools

The expense MCP server currently exposes:

| Tool | Purpose |
|---|---|
| `add_transaction` | Add income or expense |
| `list_transactions` | Retrieve transactions |
| `summarize_transactions` | Calculate spending summaries |
| `get_transaction` | Retrieve a particular transaction |
| `update_transaction` | Modify an existing transaction |
| `delete_transaction` | Delete a transaction |
| `get_date_context` | Provide current date context |

### Example: Add expense

User:

"I spent ₹180 on lunch using UPI."

The agent interprets the request and identifies:

```text
Amount: 180
Type: Expense
Category: Food
Payment method: UPI
```

It then invokes:

```text
add_transaction(...)
```

The MCP server receives the arguments and writes the transaction to Supabase.

The result is returned to the agent, which produces a user-friendly confirmation.

### Example: List expenses

User:

"Show all expenses for the last two days."

The agent determines that it needs transaction records and date filtering.

It invokes the appropriate listing tool.

The MCP tool retrieves the relevant records and returns them to the agent.

The agent formats the results into a response, potentially including a Markdown table.

### Important distinction

The LLM decides which tools to invoke.

The MCP server performs the actual operations.

The LLM does not directly insert SQL records into PostgreSQL.

---

# 8. Database Architecture — Supabase

Supabase provides the persistent data layer.

The application uses PostgreSQL rather than relying on a local SQLite database.

The main tables are:

| Table | Purpose |
|---|---|
| `profiles` | User profile information |
| `transactions` | Financial transactions |
| `chat_messages` | Conversation history |
| `memories` | Long-term semantic memory |

## 8.1 Transactions

Stores income and expense records.

Important fields include:

- `id`
- `user_id`
- `amount_paise`
- `transaction_type`
- `payment_method`
- `category`
- `subcategory`
- `note`
- `occurred_on`
- `created_at`

### Why store amounts in paise?

Instead of storing:

```text
₹250.50
```

the database stores:

```text
25050
```

This avoids floating-point precision problems in financial calculations.

Conversion:

```python
amount_rupees = amount_paise / 100
```

### Example record

```json
{
  "amount_paise": 25000,
  "transaction_type": "expense",
  "payment_method": "cash",
  "category": "Food",
  "subcategory": "Lunch",
  "note": "Lunch",
  "occurred_on": "2026-10-23"
}
```

## 8.2 Chat messages

Stores conversation history.

The backend uses this history to maintain conversational continuity.

Examples:

- User: "Add ₹250 for lunch."
- Assistant: "Added ₹250 under Food."
- User: "Show my expenses today."

The application can retrieve previous messages when the user returns.

## 8.3 Memories

The application also has a semantic memory system.

Memory storage uses Supabase vector capabilities.

The purpose is to retrieve relevant stored context based on semantic similarity rather than relying exclusively on recent chat messages.

The project previously moved away from using ChromaDB as the persistent memory store and toward Supabase vector storage.

The current architecture should be treated as Supabase-backed memory, not a requirement to run a separate ChromaDB server.

---

# 9. Complete Request Lifecycle

This is the most important section to understand when resuming development.

## 9.1 Expense addition

User types:

"I spent ₹250 on lunch using cash."

```text
Flutter ChatScreen
       |
       v
ApiClient.post("/chat")
       |
       v
HTTPS Request
       |
       v
Render FastAPI
       |
       v
Validate Access Token
       |
       v
Extract User ID
       |
       v
Load/Create User Agent
       |
       v
LangChain Agent
       |
       v
Groq LLM
       |
       v
Select add_transaction tool
       |
       v
MCP Client
       |
       v
stdio transport
       |
       v
MCP Server (server.py)
       |
       v
add_transaction()
       |
       v
Supabase PostgreSQL
       |
       v
Transaction Saved
       |
       v
Tool Result Returned
       |
       v
LLM Generates Confirmation
       |
       v
FastAPI Saves Chat Messages
       |
       v
Response Returned to Flutter
       |
       v
Chat Bubble Updated
```

## 9.2 Transaction listing

The user asks:

"Show my latest expenses."

```text
Flutter
  |
  v
POST /chat
  |
  v
FastAPI authentication
  |
  v
LangChain agent
  |
  v
Groq identifies listing intent
  |
  v
list_transactions MCP tool
  |
  v
Supabase query
  |
  v
Records returned
  |
  v
Agent formats results
  |
  v
Flutter displays response
```

## 9.3 Direct transaction retrieval

The Transactions tab does not need to ask the LLM to retrieve records.

Instead:

```text
Flutter TransactionsScreen
       |
       v
TransactionApi.getTransactions()
       |
       v
ApiClient.get("/transactions")
       |
       v
FastAPI authentication
       |
       v
Supabase query scoped by user_id
       |
       v
JSON response
       |
       v
ExpenseTransaction model
       |
       v
Flutter ListView
```

This is more efficient than using an LLM for a simple database retrieval.

---

# 10. Flutter Application Architecture

Flutter project:

`personal_expense_app`

Main responsibilities:

- Display chat interface.
- Authenticate users.
- Send requests to the backend.
- Display transaction records.
- Manage session tokens.
- Display financial information.

## 10.1 Main screens

| Screen | Purpose |
|---|---|
| LoginScreen | User authentication |
| HomeScreen | Main application container |
| ChatScreen | AI assistant interface |
| TransactionsScreen | Transaction history |

HomeScreen uses:

- `IndexedStack`
- `NavigationBar`

The two main tabs are Chat and Transactions.

## 10.2 Important Flutter files

```text
lib/
│
├── main.dart
│
├── data/
│   ├── api_client.dart
│   ├── auth_service.dart
│   ├── transaction_api.dart
│   └── transaction_model.dart
│
└── screens/
    └── login_screen.dart
```

### `main.dart`

Contains:

- ExpenseApp
- AuthGate
- HomeScreen
- ChatScreen
- TransactionsScreen
- AddTransactionScreen

It manages the main navigation and UI.

### `auth_service.dart`

Handles authentication and secure token storage.

### `api_client.dart`

Centralizes authenticated API requests.

It retrieves the saved access token and adds:

```http
Authorization: Bearer <access_token>
```

It also provides shared GET and POST methods.

### `transaction_api.dart`

Provides methods for:

- Fetching transactions.
- Adding transactions.
- Fetching chat history.

### `transaction_model.dart`

Represents a transaction as a Dart model.

It converts API JSON responses into Flutter objects.

---

# 11. Flutter UI Details

## Chat interface

The chat screen:

- Accepts user messages.
- Sends messages to `/chat`.
- Displays user and assistant messages.
- Loads previous chat history.
- Scrolls to recent messages.
- Uses the central authenticated API client.

The Markdown renderer uses `flutter_markdown`.

This is important because the agent can return Markdown tables.

A standard Flutter `Text` widget does not render Markdown tables properly.

The application uses `MarkdownBody` for assistant responses and normal `Text` for user messages.

## Transactions interface

The Transactions screen:

- Loads records from `/transactions`.
- Displays category, date, payment method, and note.
- Provides a refresh button.
- Supports pull-to-refresh.
- Displays income in green.
- Displays expenses in red.
- Displays net balance above the main bottom navigation.

The current net balance calculation is performed locally in Flutter:

```text
Net Balance = Total Income - Total Expenses
```

Amounts are summed using integer paise.

**Note:** A server-side summary response was discussed but was not adopted. The current implementation uses Flutter-side calculations.

## Theme

The app uses a dark theme.

The primary background is:

```text
#101318
```

The card background is:

```text
#1B2029
```

---

# 12. API Communication and Security

Flutter does not connect directly to the Supabase database for privileged operations.

Instead:

```text
Flutter → FastAPI → Supabase
```

This is intentional.

## API request authentication

Every protected request uses the saved access token.

Example:

```http
GET /transactions
Authorization: Bearer ACCESS_TOKEN
```

The backend validates the token and obtains the authenticated user's ID.

## Secrets

The following secrets are stored in the backend environment:

- `GROQ_API_KEY`
- `GROQ_VECTOR_API_KEY`
- `SUPABASE_PWD`
- `SUPABASE_PROJECT_URL`
- `SUPABASE_SECRET_KEY`
- `SUPABASE_ANON_KEY`

These were configured in Render.

They must never be embedded in the Flutter APK or committed to GitHub.

### Important security rule

The Supabase service-role/secret key has elevated privileges.

The backend must always filter user-specific queries using the authenticated user's ID.

Never trust a user ID supplied by Flutter as the authority for data access.

---

# 13. Deployment Architecture

## Backend deployment

The backend is deployed to Render.

Production URL:

`https://personal-exp-agent.onrender.com`

Important URLs:

- API: `https://personal-exp-agent.onrender.com`
- Swagger: `https://personal-exp-agent.onrender.com/docs`
- Health: `https://personal-exp-agent.onrender.com/health`

### Render configuration

Build command:

```bash
pip install uv && uv sync --frozen --no-dev
```

Start command:

```bash
uv run uvicorn api:app --host 0.0.0.0 --port $PORT
```

Python version:

```text
3.11.14
```

The project uses `uv` for dependency management.

The MCP client also launches the MCP server using:

```bash
uv run python server.py
```

This is why `uv` must be available in the Render environment.

### Dependency organization

Voice-specific packages were separated into an optional dependency group:

```toml
[project.optional-dependencies]
voice = [
    "pyaudio>=0.2.14",
    "sounddevice>=0.5.6",
    "speechrecognition>=3.17.0",
]
```

Local voice environment:

```bash
uv sync --extra voice
```

Render environment:

```bash
uv sync --frozen --no-dev
```

This avoids installing unnecessary microphone-device dependencies on the headless server.

## Flutter deployment

The Flutter application is configured to use:

```dart
static const String baseUrl =
    'https://personal-exp-agent.onrender.com';
```

This replaces the previous local-network URL:

```text
http://192.168.29.118:8000
```

The app can now communicate with the cloud backend without requiring the developer's laptop to run FastAPI.

---

# 14. Current Performance and Background Processing

The application currently takes approximately 15 seconds for some operations.

Possible contributors:

1. Render cold starts.
2. Groq model inference.
3. LLM reasoning and tool selection.
4. MCP subprocess communication.
5. Supabase database queries.
6. Multiple tool calls during a single agent interaction.

These are possible contributors, not measured bottlenecks.

### What happens if the user closes the app?

The backend runs independently on Render.

If a request has already reached FastAPI, it will generally continue processing even if the Flutter app closes.

However, the current implementation does not use a durable background-job queue.

Therefore:

- A successfully saved transaction remains saved.
- Closing Flutter does not normally cancel an already-running server operation.
- The user may not receive the confirmation.
- A request that never reached the backend may not execute.
- A backend restart or process failure can interrupt in-flight work.

For the current prototype, the safest practice is to wait for confirmation before closing the app.

A future version should implement background jobs, request IDs, operation status tracking, and retry-safe transaction handling.

---

# 15. Current Project Status

## Implemented

- [x] Flutter Android application.
- [x] Dark theme.
- [x] Login screen.
- [x] Supabase authentication.
- [x] Secure token storage.
- [x] AuthGate session-presence check.
- [x] Logout functionality.
- [x] Centralized authenticated API client.
- [x] FastAPI backend.
- [x] LangChain agent.
- [x] Groq model integration.
- [x] MCP client and FastMCP server.
- [x] Transaction creation.
- [x] Transaction listing.
- [x] Transaction retrieval.
- [x] Transaction update and delete MCP tools.
- [x] Spending summaries.
- [x] Supabase PostgreSQL integration.
- [x] User-specific transaction handling.
- [x] Chat history persistence.
- [x] Supabase-backed semantic memory architecture.
- [x] Render deployment.
- [x] Production HTTPS backend URL.
- [x] Swagger and health endpoint verification.
- [x] Flutter Markdown rendering.
- [x] Income and expense color differentiation.
- [x] Local net-balance calculation.

## Not yet confirmed or not implemented

- [ ] Successful complete Flutter login against the deployed backend after resolving the reported 500 error.
- [ ] Successful end-to-end test of all operations against Render.
- [ ] Release APK successfully built.
- [ ] Friend's separate account created and tested.
- [ ] Access-token refresh flow.
- [ ] Server-side transaction aggregation.
- [ ] Durable background-job processing.
- [ ] Reliable request-status tracking.
- [ ] Duplicate-request protection/idempotency.
- [ ] Production monitoring and structured logging.
- [ ] Automated backend tests against the deployed service.

---

# 16. Known Issues and Things to Remember

### 1. Render cold starts

The free Render service may become idle.

The first request after inactivity can take longer than subsequent requests.

### 2. API 500 error

During the first attempt to connect Flutter to the deployed backend, an Internal Server Error was reported.

The exact cause was not established in the conversation.

Swagger and `/health` were confirmed working.

The next diagnostic step is to inspect Render logs while reproducing the login failure.

Do not assume the login issue is fixed until tested.

### 3. Token refresh

The app currently stores a refresh token but does not have a confirmed refresh implementation.

An expired access token may require the user to log in again.

### 4. MCP subprocess lifecycle

Each user-specific agent uses an MCP server subprocess launched through `uv`.

The lifecycle, cleanup, and resource usage of these subprocesses should be reviewed as the number of concurrent users grows.

### 5. Transaction pagination and balance

The current UI calculates net balance from the transactions loaded into Flutter.

If the API returns only the latest 100 records, the displayed balance may not represent the complete financial history.

A future server-side aggregate query or database RPC would be more reliable.

### 6. Background requests

The current chat endpoint is synchronous from the client's perspective.

There is no durable job queue or guaranteed completion notification after app closure.

---

# 17. Future Improvements and Roadmap

Recommended order of development:

## Phase 1 — Stabilize the prototype

1. Fix the deployed login/API issue.
2. Test every existing feature against Render.
3. Build a release APK.
4. Create a separate account for the friend.
5. Test user-data isolation.
6. Test logout and login.
7. Test the app on another Android device.

## Phase 2 — Improve reliability

1. Implement access-token refresh.
2. Add proper session validation.
3. Add structured backend logging.
4. Add request timeouts and better error handling.
5. Prevent duplicate transaction creation.
6. Implement durable background jobs.
7. Add operation-status polling.

## Phase 3 — Improve performance

1. Measure LLM inference time.
2. Measure MCP tool execution time.
3. Measure Supabase query time.
4. Reuse agent/client resources where safe.
5. Optimize unnecessary LLM calls.
6. Reduce the number of tool iterations.
7. Consider a faster model for straightforward transaction operations.

## Phase 4 — Improve expense intelligence

1. Monthly and yearly spending reports.
2. Category-wise spending breakdown.
3. Budget creation and tracking.
4. Spending trends.
5. Recurring expense detection.
6. Financial insights and anomaly detection.
7. Search and filter transactions.

## Phase 5 — Improve input methods

1. Voice expense recording.
2. Google Pay transaction notifications or SMS parsing, with explicit user permissions.
3. Credit/debit transaction recognition.
4. Automatic transaction categorization.
5. Manual correction and confirmation workflow.

---

# 18. Important Architectural Decisions

| Decision | Reason |
|---|---|
| Flutter frontend | Android application with room for future cross-platform support |
| FastAPI backend | Centralized API and business logic |
| Groq | Hosted LLM inference |
| LangChain | Agent and tool orchestration |
| MCP | Standardized tool integration |
| Supabase | Persistent PostgreSQL database and authentication |
| Integer paise | Financial precision |
| User-specific MCP environment | Isolate transaction operations by user |
| Secure token storage | Protect authentication credentials on the device |
| Render hosting | Deploy backend independently of the developer's laptop |
| Direct transaction REST API | Avoid unnecessary LLM calls for simple record retrieval |

---

# 19. How to Resume This Project Later

When returning to this project, follow this order:

### Step 1 — Understand the backend

Open:

- `api.py`
- `agent.py`
- `server.py`
- `memory.py`

Understand the request flow before modifying anything.

### Step 2 — Understand the Flutter app

Open:

- `main.dart`
- `auth_service.dart`
- `api_client.dart`
- `transaction_api.dart`
- `transaction_model.dart`
- `login_screen.dart`

### Step 3 — Verify infrastructure

Check:

- GitHub repository and latest commit.
- Render service and deployment logs.
- Supabase tables and authentication users.
- Environment variables.
- Production API health.

### Step 4 — Run locally

Backend:

```bash
uv sync --extra voice
uv run uvicorn api:app --reload
```

Flutter:

```bash
flutter pub get
flutter run
```

Remember to use the appropriate backend URL for your environment. For an Android emulator, the host-machine address differs from the address used by a physical phone.

### Step 5 — Test the complete flow

1. Login.
2. Add a transaction.
3. Retrieve transactions.
4. Update a transaction.
5. Delete a transaction.
6. Request a spending summary.
7. Retrieve chat history.
8. Logout.
9. Login again.
10. Verify that another user's data remains isolated.

---

# 20. Final Mental Model

The most important thing to remember about this project is the separation of responsibilities.

**Flutter is the interface.**

It collects user input and displays results.

**FastAPI is the gateway.**

It authenticates users and manages requests.

**LangChain is the agent orchestrator.**

It connects the LLM with available tools.

**Groq provides the intelligence.**

It interprets natural-language requests and determines what to do.

**MCP exposes capabilities.**

It allows the agent to interact with transaction-management functions through a standardized tool interface.

**Supabase is the source of truth.**

It stores the users, transactions, chat history, and memories.

**Render keeps the backend online.**

It allows the Android application to access the system without depending on the developer's laptop.

The complete architecture can be remembered as:

```text
USER
 |
 v
FLUTTER
 |
 v
FASTAPI
 |
 v
LANGCHAIN AGENT
 |
 +------ GROQ (REASONING)
 |
 v
MCP CLIENT
 |
 v
MCP SERVER
 |
 v
TOOLS
 |
 v
SUPABASE
 |
 v
RESULT
 |
 v
GROQ FORMATS RESPONSE
 |
 v
FASTAPI
 |
 v
FLUTTER
 |
 v
USER
```

**The central design principle:** The LLM decides what operation should happen, the MCP tools perform the operation, and Supabase stores the actual data.

That separation is what makes the project extensible. You can add new capabilities without rebuilding the entire application.
