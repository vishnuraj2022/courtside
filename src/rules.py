RULES = {
    "badminton": {"target": 15, "cap": 21,   "best_of": {1, 3}},   # 15-point scoring
    "squash":    {"target": 11, "cap": None, "best_of": {1, 3, 5}},
}

def valid_game(winner_pts, loser_pts, target, cap):
    """Is winner_pts-loser_pts a legal finished game?"""
    if loser_pts < 0:
        return False
    if winner_pts == target and loser_pts <= target - 2:
        return True                                    # 15-13, 11-4
    if winner_pts > target and winner_pts - loser_pts == 2:
        return cap is None or winner_pts <= cap        # 16-14, 12-10
    return cap is not None and winner_pts == cap and loser_pts == cap - 1  # 21-20

def validate_match(sport, games, winner):
    """Return a list of problems. An empty list means the match is valid."""
    rules = RULES.get(sport)
    if rules is None:
        return [f"{sport} is not supported yet"]
    if not games:
        return ["No game scores given"]
    problems, wins = [], {"player_a": 0, "player_b": 0}
    for i, g in enumerate(games, start=1):
        a, b = g["a"], g["b"]
        if a == b:
            problems.append(f"Game {i}: {a}-{b} has no winner")
            continue
        if not valid_game(max(a, b), min(a, b), rules["target"], rules["cap"]):
            problems.append(f"Game {i}: {a}-{b} is not a valid {sport} score")
        wins["player_a" if a > b else "player_b"] += 1

    loser = "player_b" if winner == "player_a" else "player_a"
    w, l = wins[winner], wins[loser]
    last = "player_a" if games[-1]["a"] > games[-1]["b"] else "player_b"
    finished = any(w == n // 2 + 1 and l < w for n in rules["best_of"])
    if not finished or last != winner:
        problems.append(f"Games {wins['player_a']}-{wins['player_b']} are not a "
                        "finished match won by the stated winner")
    return problems