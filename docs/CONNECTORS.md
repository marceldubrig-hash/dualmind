# Consumer-client connections (checked 2026-11-16)

## What this means

A connected client reads/publishes explicitly selected content in the same project database. It does not import all existing chats, notify another app automatically, or wake Gemini/ChatGPT in the background. Each consumer client must invoke tools during its own conversation. `start_collaboration` is explicitly a separate paid model-API workflow.

## OAuth resource server setup

DualMind does not invent a password login or issue its own OAuth grants. Use an OAuth 2.1-capable identity provider supporting authorization code + S256 PKCE, authorization server metadata/OIDC discovery, resource/audience-bound JWT access tokens, and scopes `workspace:read` and `workspace:write`. Register separate ChatGPT and Gemini clients with the exact callback URLs those products provide. Do not guess callbacks. Disable unnecessary grants. Grant write scope only after consent. Dynamic registration is an IdP feature, not implemented here; use pre-registered client credentials where the product supports them.

Configure in the MCP process environment:

```
DUALMIND_OAUTH_ISSUER=https://your-idp.example/
DUALMIND_OAUTH_JWKS=https://your-idp.example/.well-known/jwks.json
DUALMIND_OAUTH_SUBJECT=your-exact-owner-subject
DUALMIND_MCP_URL=https://your-workspace.example/mcp
DUALMIND_BACKEND_URL=http://127.0.0.1:8000
DUALMIND_TOKEN=the-private-server-to-server-owner-token
```

From `server/`, export these values securely (or use a service EnvironmentFile), then `python -m app.mcp_bridge`. The process binds loopback:8001. Put the supplied Caddy configuration in front. The bridge refuses startup if HTTPS OAuth configuration is missing. Never expose `mcp.streamable_http_app()` directly while bypassing `application()`.

The backend owner token is never the consumer OAuth token. MCP validates incoming tokens before forwarding a limited operation with its separate server credential. Only the configured owner `sub` is accepted: this is intentionally a single-owner deployment, not multi-tenant IAM.

## ChatGPT

Official instructions: https://developers.openai.com/plugins/deploy/connect-chatgpt and https://developers.openai.com/plugins/build/app-quickstart

On an eligible account, enable developer mode as described by OpenAI, create the custom app/plugin with your authenticated HTTPS `/mcp` URL, complete OAuth, and test read-only tool discovery first. Ask for project listing, then publish a harmless approved test message. Confirm write approval in the host UI. Account/plan/workspace/mobile availability must be verified in the actual account; this development session does not prove mobile support. There is no supported automatic access to all old ChatGPT chats.

## Gemini custom Connected App

Official instructions: https://support.google.com/gemini/answer/17209137?hl=en-45

Google's current page requires age 18+, a personal Google account in the US, English, and Keep Activity enabled. Setup is in Gemini web → Settings → Connected Apps → Custom app; paste `/mcp`, optionally provide pre-registered OAuth client credentials, then authorize. Google says a connected app can then be used on web and mobile. For a user in Germany this path is currently region-blocked according to that page; no VPN workaround or unsupported integration is provided.

Developer testing: https://developers.google.com/connected-apps/mcp/dev-mode/usage

## Android AppFunctions

Official guides: https://developer.android.com/ai/appfunctions/add-appfunctions and https://developer.android.com/ai/appfunctions/create-manage-connected-apps

The current guide requires compileSdk 37+, AGP 9.1+, AppFunctions 1.0.0-rc01 and generated service declarations. Gemini distribution requires Connected Apps developer-preview access, a registered developer account, a linked Play app, submitted AAB, privacy policy/terms and console approval/testing. Android 17 alone does not grant access.

This branch does **not** include an unverified AppFunctions service or claim Gemini discoverability. It retains the independently buildable SDK 35 app while the new SDK/AGP migration and console access remain outstanding. Intended initial capabilities: list projects, search approved records, read messages; writes should use the platform's confirmation path plus backend approval and scopes. Do not expose locally decrypted owner credentials to an arbitrary caller.

## Acceptance checklist after deployment

1. Unauthenticated `/mcp` returns 401 and OAuth protected-resource metadata is discoverable.
2. Wrong issuer, audience, expired token and unapproved owner are rejected.
3. Read-only scope can list/search but cannot send messages or create tasks.
4. Approved writes appear in Android with connected-client origin.
5. Gemini can read that same message and publish its approved answer; ChatGPT can read it back.
6. Repeat in each actual mobile app. Record account, region and versions without credentials.

These client acceptance steps remain unexecuted; passing protocol tests is not a substitute.
