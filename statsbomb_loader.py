import requests
import pandas as pd

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


def load_json(path: str):
    url = f"{BASE_URL}/{path}"
    r = requests.get(url, timeout=20)

    if r.status_code != 200:
        raise RuntimeError(f"StatsBomb HTTP {r.status_code} → {url}")

    try:
        return r.json()
    except Exception:
        raise RuntimeError(
            f"StatsBomb returned non-JSON for {url}\n"
            f"First 200 chars:\n{r.text[:200]}"
        )


def load_season_finishing(competition_id: int, season_id: int) -> pd.DataFrame:
    matches = load_json(f"matches/{competition_id}/{season_id}.json")

    rows = []

    for match in matches:
        match_id = match["match_id"]
        events = load_json(f"events/{match_id}.json")

        for e in events:
            if e.get("type", {}).get("name") != "Shot":
                continue

            shot = e.get("shot", {})
            outcome = shot.get("outcome", {}).get("name", "")

            rows.append({
                "player": e["player"]["name"],
                "goals": 1 if outcome == "Goal" else 0,
                "psxg": shot.get("post_shot_xg", 0.0)
            })

    if not rows:
        return pd.DataFrame(columns=["player", "shots", "goals", "psxg"])

    df = pd.DataFrame(rows)

    return (
        df.groupby("player", as_index=False)
          .agg(
              shots=("player", "count"),
              goals=("goals", "sum"),
              psxg=("psxg", "sum")
          )
      )
