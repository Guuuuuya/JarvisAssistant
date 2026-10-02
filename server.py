import asyncio
import io
import os
import re
import tempfile
import webbrowser

import edge_tts
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import memory

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
VOICE = os.getenv("EDGE_TTS_VOICE", "en-GB-RyanNeural")
USER_NAME = os.getenv("USER_NAME", "Sir")

SYSTEM_PROMPT = f"""You are J.A.R.V.I.S., a witty, dry-humored AI assistant for {USER_NAME}.
Keep responses short (1-3 sentences) since they will be spoken aloud.
If the user asks you to open a website or search, reply with [ACTION:BROWSE <url-or-query>] on its own line.
If the user tells you to remember something, reply with [ACTION:REMEMBER <fact>] on its own line.
If the user asks about calendar/schedule, reply with [ACTION:CALENDAR].
If the user asks about unread emails, reply with [ACTION:EMAIL].
If the user asks about tasks/todo list, reply with [ACTION:TASKS].
If the user asks to add a task, reply with [ACTION:ADD_TASK <task text>].
Otherwise reply naturally."""

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


LAST = {"level": "ok", "msg": ""}


async def ask_llm(user_text: str) -> str:
    global LAST
    LAST = {"level": "ok", "msg": ""}
    memories = memory.get_memories()
    mem_block = "\n".join(f"- {m}" for m in memories) or "(none)"
    prompt = f"{SYSTEM_PROMPT}\n\nKnown facts about the user:\n{mem_block}\n\nUser: {user_text}\nJARVIS:"

    if GEMINI_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                for attempt in range(2):
                    r = await client.post(url, json=payload)
                    if r.status_code == 200:
                        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    await asyncio.sleep(2)
                LAST = {"level": "warn", "msg": f"Gemini returned HTTP {r.status_code} — using backup brain (OpenRouter)."}
        except Exception as e:
            print("Gemini failed:", e)
            LAST = {"level": "warn", "msg": "Gemini failed — using backup brain (OpenRouter)."}

    if OR_KEY:
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": "google/gemma-4-31b-it:free",
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {"Authorization": f"Bearer {OR_KEY}"}
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("OpenRouter failed:", e)
            LAST = {"level": "error", "msg": "Gemini AND OpenRouter both failed!"}

    # last-resort: try OpenRouter free Gemini
    if OR_KEY:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            payload = {"model": "qwen/qwen3.8-27b:free",
                       "messages": [{"role": "user", "content": prompt}]}
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(url, headers={"Authorization": f"Bearer {OR_KEY}"}, json=payload)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("OpenRouter free failed:", e)

    if LAST["level"] != "ok":
        LAST["msg"] += " All providers failed."
        LAST["level"] = "error"
    return "I'm having trouble reaching my brain right now, Sir. Please try again."


async def speak(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, VOICE)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


def _safe(fn) -> str:
    try:
        return fn()
    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        return f"Google API error: {e}"


def handle_actions(text: str) -> str:
    lines = text.splitlines()
    spoken = []
    for line in lines:
        m = re.match(r"\[ACTION:BROWSE (.+)\]", line.strip())
        if m:
            target = m.group(1).strip()
            if not target.startswith("http"):
                target = "https://www.google.com/search?q=" + target.replace(" ", "+")
            webbrowser.open(target)
            spoken.append("Opening that for you now.")
            continue
        m = re.match(r"\[ACTION:REMEMBER (.+)\]", line.strip())
        if m:
            memory.add_memory(m.group(1).strip())
            spoken.append("Noted. I'll remember that.")
            continue
        if line.strip() == "[ACTION:CALENDAR]":
            spoken.append(_safe(lambda: __import__("google_services").calendar_today()))
            continue
        if line.strip() == "[ACTION:EMAIL]":
            spoken.append(_safe(lambda: __import__("google_services").gmail_unread()))
            continue
        if line.strip() == "[ACTION:TASKS]":
            spoken.append(_safe(lambda: __import__("google_services").tasks_list()))
            continue
        m = re.match(r"\[ACTION:ADD_TASK (.+)\]", line.strip())
        if m:
            spoken.append(_safe(lambda: __import__("google_services").tasks_add(m.group(1).strip())))
            continue
        if line.strip() and not line.strip().startswith("[ACTION:"):
            spoken.append(line.strip())
    return " ".join(spoken) if spoken else "Done."


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_text = data.get("text", "").strip()
            if not user_text:
                continue
            await websocket.send_json({"type": "log", "msg": f"> heard: {user_text}"})
            await websocket.send_json({"type": "log", "msg": "> querying LLM..."})
            try:
                raw = await ask_llm(user_text)
                await websocket.send_json({"type": "log", "msg": f"> brain says: {raw[:120]}"})
                spoken = handle_actions(raw)
                await websocket.send_json({"type": "status", "level": LAST["level"], "msg": LAST["msg"]})
                await websocket.send_json({"type": "log", "msg": f"> reply: {spoken[:120]}"})
                await websocket.send_json({"type": "text", "text": spoken})
                await websocket.send_json({"type": "log", "msg": "> generating voice..."})
                audio = await speak(spoken)
                await websocket.send_bytes(audio)
                await websocket.send_json({"type": "log", "msg": "> done"})
            except Exception as e:
                print("Request failed:", e)
                try:
                    await websocket.send_json({"type": "status", "level": "error", "msg": f"Server error: {e}"})
                    await websocket.send_json({"type": "log", "msg": f"ERROR: {e}"})
                    await websocket.send_json({"type": "text", "text": "Something went wrong, Sir. Check the server logs."})
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
