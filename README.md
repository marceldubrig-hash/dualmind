# DualMind

Shared, persistent single-owner workspace for connected ChatGPT/Gemini clients and a native Android app. Consumer-client communication and paid model-API orchestration are separate channels. Existing private chats are never scraped or automatically imported.

## What is implemented

- FastAPI + SQLite projects, paginated messages with origin labels, approved structured records (memory, decision, summary, text document, task), source attribution, revision conflicts, record/message/run audit events, export and project deletion.
- Literal project-scoped search, bounded keyword-ranked context selection from approved records only.
- Durable collaboration state with 1–6 provider calls, output-token reservation, deadline checks, cancellation, a global two-job queue and daily call reservations. Failed/interrupted jobs require an explicit new run and are never auto-replayed.
- OAuth-protected Streamable HTTP MCP resource server: issuer/JWKS signature, expiry, audience and owner-subject checks; read/write scopes; protected resource metadata supplied by the official MCP SDK. Login, PKCE and client registration are delegated to your OAuth provider.
- Android Compose client: shared chat, projects, shared memory/tasks, polling/cancellation, explicit provider-transfer consent, system light/dark theme, safe insets, masked tokens, optional Android Keystore encrypted login storage. No provider keys in Android.
- Backend tests and Android build/lint CI with APK artifact upload.

German phone setup guide: [Erste Schritte](docs/ERSTE_SCHRITTE.md).

## Quick start

Requires Python 3.12. From the repository root:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r server/requirements-mcp.txt
cp server/.env.example server/.env
# Edit server/.env; never commit it. Generate token with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
cd server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Configure `DUALMIND_TOKEN` (at least 24 characters), persistent absolute `DUALMIND_DB`, and both provider keys. The database contains private plaintext; restrict file permissions, use encrypted disks/backups. Keep one backend process: startup marks unfinished runs interrupted. Do not horizontally scale this worker design.

Backend docs are at `/docs`. Every data endpoint requires an exact `Authorization: Bearer …` header. `/health` is public. The existing `/rooms/{id}/collaborate` endpoint now returns 410; use `/rooms/{id}/runs` with explicit consent instead.

## Remote MCP and existing apps

See [connector setup](docs/CONNECTORS.md), [deployment](docs/DEPLOYMENT.md), and [verification/limitations](docs/STATUS.md). A public HTTPS hostname and a configured OAuth provider are required before connecting the normal apps. No live consumer app connection is claimed.

## Android

Open `android/` in Android Studio, or install Gradle 8.9, JDK 17, Android SDK 35 and run:

```sh
cd android
gradle --no-daemon assembleDebug lintDebug
```

The GitHub Actions workflow builds and uploads `DualMind-debug-apk` when successful. Enter your own HTTPS backend and owner token, then create/select a project. API collaboration requires explicit transfer/cost consent. No provider calls happen merely by connecting. Tap “Wissen & Aufgaben” to approve shared memory or tasks.

## Tests

```sh
python -m pytest -q server
```

Provider tests use HTTP MockTransport and deterministic model responses; they are not real paid provider calls. MCP tests exercise Streamable HTTP initialization, tool discovery, auth rejection and read-only write rejection; they are not ChatGPT/Gemini application acceptance tests.
