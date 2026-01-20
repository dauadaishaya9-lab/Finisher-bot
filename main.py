from fastapi import FastAPI, Request
import requests
import os

from logic import analyze_query  # 👈 THIS is the connection

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.get("/")
def root():
    return {"status": "alive"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()

    message = data.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # 🚫 no echo
    # 🧠 real logic
    reply = analyze_query(text)

    requests.post(
        f"{TG_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": reply
        }
    )

    return {"ok": True}
