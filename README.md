# DualMind

A self-hosted shared workspace connecting OpenAI and Google Gemini with an Android client.

## Status
First MVP implementation. **Not deployed, APK not built, and external APIs not yet integration-tested.** The normal ChatGPT/Gemini consumer apps are **not** automatically connected. Their chat histories and memories do not transfer without an explicit supported integration/import.

## Architecture
- FastAPI backend, SQLite persistence, room-scoped conversation history and notes
- OpenAI Responses API and Gemini generateContent REST adapters
- Bounded collaborative conversation: OpenAI -> Gemini -> OpenAI, persisted in shared room
- Single-user Bearer authentication; LLM API keys remain on the server
- Android Kotlin/Compose client for rooms, messages, notes and collaborative rounds

## Server setup
```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set a long random DUALMIND_TOKEN and both provider keys in .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
For local development only, use http://127.0.0.1:8000. To reach it from a real phone, deploy behind HTTPS with access controls; **do not expose the local development server directly to the public internet**. Variables in .env are loaded by python-dotenv.

## Android
Open `android/` in Android Studio with JDK 17, sync Gradle, and run on a device. Enter an HTTPS server URL and your DUALMIND_TOKEN in the connection screen. The token is held in memory only (re-enter on app restart). No API provider keys belong in Android.

## API
All endpoints except `/health` require `Authorization: Bearer <DUALMIND_TOKEN>`.
- `POST /rooms` — body `{"name":"My room"}`
- `GET /rooms`
- `GET /rooms/{id}/messages`
- `POST /rooms/{id}/messages` — body `{"role":"user","content":"..."}`
- `GET /rooms/{id}/notes`
- `PUT /rooms/{id}/notes/{key}` — body `{"value":"..."}`
- `POST /rooms/{id}/collaborate` — body `{"prompt":"..."}`

The collaborative endpoint adds a user prompt, asks OpenAI for a proposal, Gemini for a critique, and OpenAI for a synthesis; all stages are saved. It is a bounded workflow, not an autonomous agent. Server HTTP requests have timeouts; provider failures surface as error responses. Calls may incur API charges.

## Security and next steps
This MVP targets a single trusted user. The server bearer token is not multi-user IAM. Add encrypted secure token storage, rate limiting, deployment TLS, migration framework, tests with mocked providers, and account-based access controls before a wider release. Provider API formats/models can evolve; verify them during integration testing.

Consumer-chat integration requires an explicitly available MCP/connectors integration in each chat client; this server alone does not magically grant access to those clients.
