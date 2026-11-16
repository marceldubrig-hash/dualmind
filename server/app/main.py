"""DualMind single-user API. Provider keys never leave the backend."""
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from uuid import uuid4
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app = FastAPI(title="DualMind", version="0.1.0")
DB_PATH = os.getenv("DUALMIND_DB", str(Path(__file__).resolve().parents[1] / "dualmind.sqlite3"))
room_locks: dict[str, Lock] = {}
locks_guard = Lock()


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS rooms (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, room_id TEXT NOT NULL REFERENCES rooms(id),
            role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        if 'origin' not in [r['name'] for r in c.execute('PRAGMA table_info(messages)')]:
            c.execute("ALTER TABLE messages ADD COLUMN origin TEXT NOT NULL DEFAULT 'legacy'")
        c.execute("""CREATE TABLE IF NOT EXISTS notes (
            room_id TEXT NOT NULL REFERENCES rooms(id), key TEXT NOT NULL,
            value TEXT NOT NULL, PRIMARY KEY(room_id,key))""")


init_db()


def auth(authorization: str | None = Header(default=None)):
    token = os.getenv("DUALMIND_TOKEN", "")
    if not token or len(token) < 24:
        raise HTTPException(503, "Server authentication not configured")
    offered = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if not secrets.compare_digest(token, offered):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})
    import time
    minute = int(time.time() // 60)
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS rate_limits (minute INTEGER PRIMARY KEY, count INTEGER NOT NULL)")
        c.execute("DELETE FROM rate_limits WHERE minute < ?", (minute-1,))
        c.execute("INSERT INTO rate_limits VALUES (?,1) ON CONFLICT(minute) DO UPDATE SET count=count+1", (minute,))
        count = c.execute("SELECT count FROM rate_limits WHERE minute=?", (minute,)).fetchone()[0]
    if count > int(os.getenv("DUALMIND_REQUESTS_PER_MINUTE", "120")):
        raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": "60"})


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class MessageIn(BaseModel):
    origin: Literal['user', 'connected_client'] = 'user'
    role: str = Field(pattern="^user$")
    content: str = Field(min_length=1, max_length=12000)


class NoteIn(BaseModel):
    value: str = Field(max_length=30000)


class PromptIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/rooms", dependencies=[Depends(auth)])
def create_room(data: RoomIn):
    rid = str(uuid4())
    with db() as c:
        c.execute("INSERT INTO rooms(id,name) VALUES (?,?)", (rid, data.name))
    return {"id": rid, "name": data.name}


@app.get("/rooms", dependencies=[Depends(auth)])
def rooms():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT id,name FROM rooms ORDER BY rowid DESC")]


def ensure_room(c, rid: str):
    if not c.execute("SELECT 1 FROM rooms WHERE id=?", (rid,)).fetchone():
        raise HTTPException(404, "Room not found")


def save_message(rid: str, role: str, content: str, origin: str = 'model_apis'):
    mid = str(uuid4())
    with db() as c:
        ensure_room(c, rid)
        c.execute("INSERT INTO messages(id,room_id,role,content,origin) VALUES (?,?,?,?,?)",
                  (mid, rid, role, content, origin))
        c.execute("INSERT INTO audit(room_id,action,object_id,detail) VALUES (?,'message.append',?,?)", (rid,mid,origin))
    return {"id": mid, "room_id": rid, "role": role, "content": content}


@app.get("/rooms/{rid}/messages", dependencies=[Depends(auth)])
def messages(rid: str, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0), latest: bool = False):
    with db() as c:
        ensure_room(c, rid)
        order = 'DESC' if latest else 'ASC'
        rows = [dict(r) for r in c.execute(
            f"SELECT id,room_id,role,content,created_at,origin FROM messages WHERE room_id=? ORDER BY rowid {order} LIMIT ? OFFSET ?", (rid, limit, offset))]
        return list(reversed(rows)) if latest else rows


@app.post("/rooms/{rid}/messages", dependencies=[Depends(auth)])
def add_message(rid: str, data: MessageIn):
    return save_message(rid, data.role, data.content, data.origin)


@app.get("/rooms/{rid}/notes", dependencies=[Depends(auth)])
def get_notes(rid: str):
    with db() as c:
        ensure_room(c, rid)
        return {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM notes WHERE room_id=?", (rid,))}


@app.put("/rooms/{rid}/notes/{key}", dependencies=[Depends(auth)])
def put_note(rid: str, key: str, data: NoteIn):
    if not key or len(key) > 100:
        raise HTTPException(422, "Invalid note key")
    with db() as c:
        ensure_room(c, rid)
        c.execute("INSERT INTO notes(room_id,key,value) VALUES (?,?,?) ON CONFLICT(room_id,key) DO UPDATE SET value=excluded.value", (rid,key,data.value))
    return {"key": key, "value": data.value}


def openai_reply(prompt: str) -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(503, "OPENAI_API_KEY missing")
    try:
        with httpx.Client(timeout=60) as client:
            r = client.post("https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                      "input": prompt, "max_output_tokens": 1200})
            r.raise_for_status()
            data = r.json()
        pieces = [part.get("text", "") for item in data.get("output", [])
                  if item.get("type") == "message"
                  for part in item.get("content", []) if part.get("type") == "output_text"]
        answer = "\n".join(pieces).strip()
        if not answer:
            raise ValueError("OpenAI returned no text")
        return answer
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(502, f"OpenAI request failed: {type(exc).__name__}") from exc


def gemini_reply(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise HTTPException(503, "GEMINI_API_KEY missing")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    try:
        with httpx.Client(timeout=60) as client:
            r = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key},
                json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 1200}})
            r.raise_for_status()
            data = r.json()
        answer = "\n".join(p["text"] for p in data["candidates"][0]["content"]["parts"] if "text" in p).strip()
        if not answer:
            raise ValueError("Gemini returned no text")
        return answer
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        raise HTTPException(502, f"Gemini request failed: {type(exc).__name__}") from exc


def get_room_lock(rid: str) -> Lock:
    with locks_guard:
        return room_locks.setdefault(rid, Lock())


@app.post("/rooms/{rid}/collaborate", dependencies=[Depends(auth)])
def collaborate(rid: str, data: PromptIn):
    raise HTTPException(410, "Use POST /rooms/{id}/runs with explicit provider-transfer consent and limits")


# Structured workspace and durable collaboration jobs share this database.
from .workspace import install
install(app)
