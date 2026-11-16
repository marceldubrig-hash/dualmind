# Direct consumer-app connection plan

## Current working scope
DualMind's core FastAPI backend remains the source of truth. A read-only MCP
bridge is implemented in `server/app/mcp_bridge.py`, exposing three tools:
`list_rooms`, `read_room_messages`, and `read_room_notes`.

This is a first stage only. It is **not** an activated ChatGPT or Gemini
connection. It does not automatically ingest existing chats or memories.

## Run for local development
From `server/`, with `.env` configured, install:
```sh
pip install -r requirements-mcp.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
# In a second terminal, with DUALMIND_TOKEN exported from your .env:
python -m app.mcp_bridge
```
The MCP endpoint is at `http://127.0.0.1:8001/mcp`, on the
same development machine only.

**Security warning:** The initial bridge has no inbound MCP client authentication.
Do not expose or tunnel it publicly as is. Put it behind a standards-compliant
OAuth 2.1 auth gateway with TLS, user-level authorization, origin validation,
rate limiting, access logs and least-privilege scopes. The backend token is a
server-to-server credential and must never appear in Gemini/ChatGPT tools or apps.

## ChatGPT
ChatGPT's supported Plugins workflow can connect a remote MCP server via
Plugins > Add custom MCP server, subject to account/plan permissions.
See https://developers.openai.com/api/docs/guides/custom-mcp-server
Use the **authenticated HTTPS gateway URL** ending in `/mcp`, not localhost.

## Gemini
Google's custom Connected Apps integration supports MCP servers in the standard
Gemini web/mobile apps only for eligible personal accounts in the US, in English,
at the time this document was written (November 2026).
See https://support.google.com/gemini/answer/17209137

If consumer custom connected apps aren't available in your region, use Gemini
through our existing server API; alternatively investigate Android AppFunctions
and the Google Connected Apps developer platform for supported distributions.
See https://developers.google.com/connected-apps/

## Planned extensions
1. Add OAuth 2.1 / identity-aware access layer for remote MCP.
2. Add user-confirmed write tools: `post_message`, `save_note`, `submit_task`.
3. Add Android AppFunctions for on-device discoverability if compatible with
   target Android/Gemini versions.
4. Add event polling/notifications, conflict handling and explicit imports.
5. Test against both providers' actual client applications before claiming support.

The shared store is a collaboration channel, not automatic cross-provider
transcript or memory synchronization.
