from fastapi import FastAPI, Request
import os

from statsbomb_loader import load_season_finishing
from logic import classify_finisher

app = FastAPI()

BOT_TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

import requests

def send_message(chat_id: int, text: str):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10
    )


# EPL competition id
COMPETITION_ID = 2

# Seasons we *actually* have in StatsBomb open data
SEASONS = {
    "2023/24": 281,
    "2024/25": 317,  # available
    # 2025/26 does NOT exist yet in open data
}

SEASON_CACHE = {}


def load_season(season_label: str):
    if season_label not in SEASON_CACHE:
        SEASON_CACHE[season_label] = load_season_finishing(
            COMPETITION_ID,
            SEASONS[season_label]
        )
    return SEASON_CACHE[season_label]


def get_player_report(player_name: str) -> str:
    total_shots = total_goals = total_psxg = 0.0

    for season in SEASONS:
        df = load_season(season)
        row = df[df["player"].str.lower() == player_name.lower()]

        if row.empty:
            continue

        r = row.iloc[0]
        total_shots += r["shots"]
        total_goals += r["goals"]
        total_psxg += r["psxg"]

    if total_shots == 0:
        return f"No data found for {player_name}"

    sga = (total_goals - total_psxg) / total_shots
    label = classify_finisher(sga, int(total_shots))

    return (
        f"{player_name}\n"
        f"Shots: {int(total_shots)}\n"
        f"Goals: {int(total_goals)}\n"
        f"PSxG: {total_psxg:.2f}\n"
        f"SGA/shot: {sga:.3f}\n"
        f"Verdict: {label}"
    )


@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()

    message = data.get("message")
    if not message or "text" not in message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    player = message["text"].strip()

    # Immediate response so Telegram doesn’t timeout
    send_message(chat_id, "Crunching the numbers…")

    try:
        reply = get_player_report(player)
    except Exception as e:
        reply = f"Error:\n{e}"

    send_message(chat_id, reply)
    return {"ok": True}
