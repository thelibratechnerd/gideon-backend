from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests

app = FastAPI()

# Allow your iPhone app to call this backend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.environ.get("AIzaSyBYNHU4V8iFnqqgt6ArjM6S33t8GI4WCDY", "").strip()

class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

@app.post("/chat")
def chat(req: ChatRequest):
    if not GEMINI_API_KEY:
        return {
            "assistantText": "Server missing GEMINI_API_KEY.",
            "actions": []
        }

    # Combine user messages (simple)
    user_text = "\n".join([m.text for m in req.messages if m.role == "user"]).strip()

    system_prompt = (
        "You are Gideon, an AI assistant and organizer.\n"
        "You help with calendar events and reminders.\n"
        "Reply concisely.\n\n"
        "Return JSON ONLY in this format:\n"
        "{ \"assistantText\": \"...\", \"actions\": [] }\n"
        "Do not include markdown or extra text.\n"
    )

    # Gemini REST call
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": system_prompt + "\nUser:\n" + user_text}
                ]
            }
        ]
    }

    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()

    raw = (
        data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
    ).strip()

    # If Gemini didn't follow JSON-only rules, fallback safely:
    if not raw.startswith("{"):
        return {"assistantText": raw or "Sorry, I couldn't understand.", "actions": []}

    # Try to return what Gemini gave (already JSON string)
    # But FastAPI needs dict, so parse:
    import json
    try:
        parsed = json.loads(raw)
        # Ensure keys exist
        return {
            "assistantText": parsed.get("assistantText", ""),
            "actions": parsed.get("actions", []) or []
        }
    except Exception:
        return {"assistantText": raw, "actions": []}

