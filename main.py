import requests
import os
import re
print("DEBUG BOT_TOKEN:", os.getenv("BOT_TOKEN"))
from statsbomb_loader import load_season_finishing

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

COMPETITION_ID = 2  # Premier League

SEASONS = {
    "2023/24": 281,
    "2024/25": 317,
    "2025/26": 345
}

SEASON_CACHE = {}


@app.get("/")
def root():
    return {"status": "alive"}


def send_message(chat_id: int, text: str):
    requests.post(
        f"{TG_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )


def classify_finisher(sga, shots):
    if shots < 10:
        return "Not enough data (early season)"

    if sga >= 0.15:
        return "Good finisher"
    if sga <= -0.15:
        return "Wasteful"

    return "Neutral / Unlucky"


def load_season(season_label):
    if season_label not in SEASONS:
        return None

    if season_label not in SEASON_CACHE:
        SEASON_CACHE[season_label] = load_season_finishing(
            COMPETITION_ID,
            SEASONS[season_label]
        )

    return SEASON_CACHE[season_label]


def latest_available_season():
    # Try newest → oldest
    for season in reversed(SEASONS.keys()):
        df = load_season(season)
        if df is not None and not df.empty:
            return season, df
    return None, None


def parse_message(text):
    match = re.search(r"(.*?)(20\d{2}/\d{2})$", text)
    if match:
        return match.group(1).strip(), match.group(2)
    return text.strip(), None


def get_player_report(player_name, season_label=None):
    if season_label:
        df = load_season(season_label)
        if df is None or df.empty:
            return f"No data available for {season_label}."
    else:
        season_label, df = latest_available_season()
        if df is None:
            return "No season data available yet."

    row = df[df["player"].str.lower() == player_name.lower()]
    if row.empty:
        return f"No shot data found for {player_name} in {season_label}."

    r = row.iloc[0]

    sga = r["post_shot_xG"] - r["xG"]
    sga_per_shot = sga / r["shots"]
    verdict = classify_finisher(sga_per_shot, r["shots"])

    return (
        f"{r['player']} — Premier League {season_label}\n\n"
        f"Shots (on target): {int(r['shots'])}\n"
        f"xG: {r['xG']:.2f}\n"
        f"PSxG (estimated): {r['post_shot_xG']:.2f}\n"
        f"SGA per shot: {sga_per_shot:+.3f}\n\n"
        f"Verdict: {verdict}"
    )


@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()

    message = data.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if not text:
        send_message(chat_id, "Send a player name.")
        return {"ok": True}

    player, season = parse_message(text)
    reply = get_player_report(player, season)

    send_message(chat_id, reply)
    return {"ok": True}
