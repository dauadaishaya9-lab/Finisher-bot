import requests
import pandas as pd
import numpy as np
from math import sqrt

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# -----------------------------
# Helpers
# -----------------------------

def load_json(path):
    url = f"{BASE_URL}/{path}"
    return requests.get(url).json()

def distance_from_goal_center(end_location):
    # StatsBomb goal mouth center ≈ (60, 40, 1.22)
    goal_x, goal_y, goal_z = 60, 40, 1.22

    if end_location is None or len(end_location) < 3:
        return None

    x, y, z = end_location
    return sqrt((x - goal_x)**2 + (y - goal_y)**2 + (z - goal_z)**2)

def post_shot_xg(xg, end_location):
    dist = distance_from_goal_center(end_location)
    if dist is None:
        return None

    max_dist = 45  # roughly worst plausible placement
    placement = 1 - min(dist / max_dist, 1)

    multiplier = 0.6 + 0.8 * placement
    return xg * multiplier

# -----------------------------
# Core loader
# -----------------------------

def load_season_finishing(competition_id, season_id):
    matches = load_json(f"matches/{competition_id}/{season_id}.json")

    rows = []

    for match in matches:
        match_id = match["match_id"]
        events = load_json(f"events/{match_id}.json")

        for e in events:
            if e.get("type", {}).get("name") != "Shot":
                continue

            shot = e.get("shot", {})
            outcome = shot.get("outcome", {}).get("name")

            if outcome not in ["Goal", "Saved", "Saved To Post"]:
                continue  # on-target only

            xg = shot.get("statsbomb_xg", 0)
            end_loc = shot.get("end_location")

            psxg = post_shot_xg(xg, end_loc)
            if psxg is None:
                continue

            rows.append({
                "player": e["player"]["name"],
                "xG": xg,
                "post_shot_xG": psxg
            })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    summary = (
        df.groupby("player")
        .agg(
            xG=("xG", "sum"),
            post_shot_xG=("post_shot_xG", "sum"),
            shots=("xG", "count")
        )
        .reset_index()
    )

    summary["SGA"] = summary["post_shot_xG"] - summary["xG"]

    return summary
