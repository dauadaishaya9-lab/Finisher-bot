print(">>> RUNNING NEW MAIN.PY <<<")
from fastapi import FastAPI, Request
import requests
import os

from statsbomb_loader import load_season_finishing

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Example: Premier League 2023/24
# StatsBomb IDs
COMPETITION_ID = 2     # Premier League
SEASON_ID = 281        # 2023/24

# Cache season data so we don’t refetch on every message
SEASON_DATA = None


@app.get("/")
def root():
    return {"status": "alive"}


def send_message(chat_id: int, text: str):
    requests.post(
        f"{TG_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )


def get_player_report(player_name: str):
    global SEASON_DATA

    if SEASON_DATA is None:
        SEASON_DATA = load_season_finishing(COMPETITION_ID, SEASON_ID)

    df = SEASON_DATA
    if df.empty:
        return "No data available. StatsBomb giveth, StatsBomb taketh away."

    row = df[df["player"].str.lower() == player_name.lower()]
    if row.empty:
        return f"No shot data found for {player_name}."

    r = row.iloc[0]

    return (
        f"{r['player']} — Premier League 2023/24\n\n"
        f"Shots (on target): {int(r['shots'])}\n"
        f"xG: {r['xG']:.2f}\n"
        f"PSxG (estimated): {r['PSxG']:.2f}\n"
        f"SGA per shot: {r['SGA_per_shot']:+.3f}\n\n"
        f"Verdict: {r['classification']}"
    )


@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()

    message = data.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # Expecting just a player name for now
    if not text:
        send_message(chat_id, "Send a player name. Words help.")
        return {"ok": True}

    reply = get_player_report(text)
    send_message(chat_id, reply)

    return {"ok": True}
