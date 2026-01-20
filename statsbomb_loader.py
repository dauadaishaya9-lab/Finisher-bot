import requests
import pandas as pd
from math import sqrt

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# -----------------------------
# Helpers
# -----------------------------

def load_json(path):
    return requests.get(f"{BASE_URL}/{path}").json()

def distance_from_goal_center(end_location):
    if not end_location or len(end_location) < 3:
        return None

    x, y, z = end_location
    return sqrt((x - 60)**2 + (y - 40)**2 + (z - 1.22)**2)

def estimate_psxg(xg, end_location):
    """
    Proxy for post-shot xG using placement.
    """
    dist = distance_from_goal_center(end_location)
    if dist is None:
        return None

    max_dist = 45
    placement = 1 - min(dist / max_dist, 1)

    return xg * (0.6 + 0.8 * placement)

# -----------------------------
# Classification
# -----------------------------

def classify_finisher(sga_per_shot, shots):
    if shots < 10:
        return "Not enough data"

    if sga_per_shot >= 0.10:
        return "Good finisher"
    elif sga_per_shot <= -0.10:
        return "Wasteful finisher"
    else:
        return "Neutral / Unlucky"

# -----------------------------
# Core
# -----------------------------

def load_season_finishing(competition_id, season_id):
    matches = load_json(f"matches/{competition_id}/{season_id}.json")
    rows = []

    for match in matches:
        events = load_json(f"events/{match['match_id']}.json")

        for e in events:
            if e.get("type", {}).get("name") != "Shot":
                continue

            shot = e.get("shot", {})
            outcome = shot.get("outcome", {}).get("name")

            if outcome not in ["Goal", "Saved", "Saved To Post"]:
                continue

            xg = shot.get("statsbomb_xg", 0)
            psxg = estimate_psxg(xg, shot.get("end_location"))

            if psxg is None:
                continue

            rows.append({
                "player": e["player"]["name"],
                "xG": xg,
                "PSxG": psxg
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    summary = (
        df.groupby("player")
        .agg(
            shots=("xG", "count"),
            xG=("xG", "sum"),
            PSxG=("PSxG", "sum")
        )
        .reset_index()
    )

    summary["SGA"] = summary["PSxG"] - summary["xG"]
    summary["SGA_per_shot"] = summary["SGA"] / summary["shots"]
    summary["classification"] = summary.apply(
        lambda r: classify_finisher(r["SGA_per_shot"], r["shots"]),
        axis=1
    )

    return summary
