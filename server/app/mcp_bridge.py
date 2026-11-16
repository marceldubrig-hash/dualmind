"""Local MCP adapter for DualMind. Do not expose directly to the internet.

Run alongside the FastAPI backend. Use a properly authenticated TLS reverse
proxy / OAuth 2.1 gateway before connecting external consumer chat clients.
"""
import os

import httpx
from mcp.server.fastmcp import FastMCP

BACKEND = os.getenv("DUALMIND_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TOKEN = os.getenv("DUALMIND_TOKEN", "")

mcp = FastMCP("DualMind", instructions=(
    "Use these tools to read room-scoped shared notes and chat history. "
    "Never claim an existing consumer chat was synced automatically."
))


def fetch(path: str):
    if not TOKEN or len(TOKEN) < 24:
        raise ValueError("DUALMIND_TOKEN must be configured")
    with httpx.Client(timeout=20) as client:
        response = client.get(
            f"{BACKEND}{path}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
def list_rooms() -> list[dict]:
    """List shared DualMind rooms visible to this server owner."""
    return fetch("/rooms")


@mcp.tool()
def read_room_messages(room_id: str) -> list[dict]:
    """Read saved messages from a specific shared room (UUID)."""
    from uuid import UUID
    room_id = str(UUID(room_id))
    return fetch(f"/rooms/{room_id}/messages")


@mcp.tool()
def read_room_notes(room_id: str) -> dict:
    """Read shared memory notes from a specific room (UUID)."""
    from uuid import UUID
    room_id = str(UUID(room_id))
    return fetch(f"/rooms/{room_id}/notes")


if __name__ == "__main__":
    # The read-only bridge is intentionally loopback-only.
    # External clients need an authenticated HTTPS gateway in front of it.
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8001)
