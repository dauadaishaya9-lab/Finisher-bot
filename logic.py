def classify_finisher(sga, shots):
    if shots < 10:
        return "Not enough data"

    if sga >= 0.15:
        return "Good finisher"
    if sga <= -0.15:
        return "Wasteful"

    return "Neutral / Unlucky"
