# Deployment and operations

1. Provision a host, persistent volume, DNS hostname, Python 3.12 and Caddy. Keep ports 8000/8001 loopback-only and expose only HTTPS 443. Set restricted permissions on the service user, environment file, SQLite database and backups.
2. Install `server/requirements-mcp.txt`, set the backend environment (see README), start exactly one Uvicorn worker. Start MCP in a separate process with the OAuth variables from CONNECTORS.md. Use a supervisor/systemd for both; do not use reload mode in production.
3. Replace `dualmind.example.com` in `deploy/Caddyfile`. Caddy obtains/renews TLS certificates after DNS is configured. The hostname must exactly match `DUALMIND_MCP_URL`; the MCP Host/Origin checks allow that hostname. Do not disable DNS-rebinding checks.
4. Configure an external IdP and OAuth clients; validate real grants before connecting consumer apps. This repository is an OAuth resource server, not an authorization-server deployment.
5. Test `/health`, authenticated `/rooms`, MCP discovery/authentication and export/restore before storing important information. Set provider-side billing caps as well as `DUALMIND_DAILY_CALL_LIMIT`.

## Limits and costs

Every job reserves `max_calls` against a durable UTC-day counter before submission; default daily ceiling is 30. Each call has a 1,200 output-token ceiling; the run output-token budget bounds the number of calls. Prompt contexts are bounded. This is **not** an exact currency/token-usage accounting system: model input pricing, reasoning, retries at network infrastructure and actual provider billing are not estimated. Use provider billing controls for a monetary ceiling.

The worker checks the deadline between calls and before saving output. Each provider HTTP request has a 60-second network timeout; an already running call cannot be forcibly recalled. Cancellation prevents later rounds and discards returned output after it is observed, but cannot refund an in-flight charge. Do not claim a strict wall-clock kill at the requested deadline.

Two jobs may be active globally. Recent cancelled jobs conservatively consume admission capacity for five minutes to avoid runaway replacement requests. One active run per project is enforced by a unique database index. On restart, queued/running jobs become `interrupted`; manually start a new run to avoid duplicate paid calls. No automatic retry/replay.

The backend enforces a shared authenticated rate limit (default 120 requests/minute). Place additional unauthenticated IP/request protection at the host edge. The SDK enforces OAuth and Host/Origin checks on MCP. An external OAuth deployment and security review remain necessary before broad public use.

## Data management

`GET /rooms/{id}/export` returns project messages, notes, records, runs and audit events. `DELETE /rooms/{id}` deletes project rows, including historical record values in audit. Active jobs must be cancelled first. Deletion does not erase offline backups or already submitted provider data; manage retention separately. SQLite free pages are not a cryptographic erasure guarantee. No binary attachment storage is provided yet; documents are bounded text records with explicit source attribution.

Approved records are eligible for provider transfer only when a run is separately authorized. Legacy notes are retained for compatibility, but the new run worker does not automatically transfer them. Prompt-injection instructions are treated as untrusted data; models have no execution tools and cannot change permissions. This reduces impact, but does not guarantee the truth or instruction-following reliability of model output.
