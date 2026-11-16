# Verification status

This branch is a development delivery, not a deployed production service.

| Area | Evidence / status |
|---|---|
| Repository | All two remote branches and commit history inspected; PR #1 read. Existing MVP reused. |
| Backend/database | Automated TestClient tests perform real SQLite writes, reads, literal search, revision conflict detection, export and deletion. |
| Authentication | Exact Bearer syntax checked; owner-token data endpoints reject unauthenticated requests. |
| OAuth | Real RSA-signed JWT tests validate audience, subject and expiry. External IdP login/PKCE/consent not configured or tested. |
| MCP protocol | Official SDK Streamable HTTP initialize, tools/list, 401 rejection and scoped write denial tested with a test verifier. Not a production OAuth end-to-end test. |
| Provider adapters | OpenAI and Gemini HTTP contracts and 429 handling tested using MockTransport. No real credentials/calls. |
| Collaboration | Mock-provider end-to-end persistence, terminal failure and cancellation tested; no paid live dual-model run. |
| Android | Build/lint workflow configured; local build result to be recorded after execution. No Fold7/device/offline instrumentation test. |
| ChatGPT consumer app | Authenticated MCP endpoint prepared; no deployment/account connection executed. Mobile availability not established in this account. |
| Gemini consumer app | Official custom Connected Apps route documented; current US/English restriction blocks the documented route for Germany. |
| AppFunctions | Investigated official API 37 / AGP 9.1 / Connected Console preview requirements. Service and toolchain migration not implemented. |
| TLS | Caddy template supplied; no hostname/host/certificate provisioned. |
| Documents | Approved text documents supported; binary file storage/import is not implemented. |
| Search/context | Literal SQL search with bounded keyword ranking; no vector embeddings or semantic-memory service. |
| Cost controls | Durable daily call reservation, per-run output reservation and max calls. No exact currency accounting; use provider billing caps. |
| Security | Single-owner scopes, fail-closed MCP startup, owner subject allowlist, no client provider keys, Keystore storage and revision audit. No independent security audit or multi-user tenant isolation. |

Run locally: `python -m pytest -q server` (12 tests passed during development). Warnings observed are dependency deprecations and an SDK Pydantic forward-reference warning; no test failures in the final backend run.

Still needed for a real mobile acceptance test: deployed HTTPS host, configured OAuth provider/clients, provider credentials, eligible consumer accounts and a physical device. Do not publish credentials in issues, PRs or chat.
