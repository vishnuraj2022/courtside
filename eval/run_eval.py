import json
import sys
import time
from datetime import date
import pandas as pd

sys.path.append("src")
from config import ME
from db import connect
from extract import extract, start
from names import resolve_name
from rules import validate_match

FIELDS = ["sport", "played_on", "players", "games", "winner"]

def canonical(rec):
    """Same match, same form: players in alphabetical order, scores flipped to match."""
    a, b = rec["player_a"], rec["player_b"]
    games = [(g["a"], g["b"]) if isinstance(g, dict) else tuple(g) for g in rec["games"]]
    winner = a if rec["winner"] == "player_a" else b
    if a.lower() > b.lower():
        a, b = b, a
        games = [(y, x) for x, y in games]
    return {"sport": rec["sport"], "played_on": rec["played_on"],
            "players": (a.lower(), b.lower()), "games": games,
            "winner": winner.lower()}

with open("eval/gold_messages.jsonl", encoding="utf-8") as f:
    cases = [json.loads(line) for line in f if line.strip()]

con = connect()
rows = []
for case in cases:
    exp = case["expected"]
    t0 = time.time()
    _, result = extract(start(case["message"]), today=date.fromisoformat(case["today"]))
    row = {"id": case["id"], "category": case["category"], "expected": exp["action"],
           "seconds": round(time.time() - t0, 1), "output": json.dumps(result["input"])}

    if result["tool"] == "ask_clarification":
        row["action"] = "clarify"
    else:
        got = dict(result["input"])
        found = [resolve_name(con, got["player_a"]), resolve_name(con, got["player_b"])]
        if any(f["status"] == "ambiguous" for f in found):
            row["action"] = "clarify"          # the app would ask "which Sam?"
        elif validate_match(got["sport"], got["games"], got["winner"]):
            row["action"] = "reject"
        else:
            row["action"] = "record"
            for side, f in zip(("player_a", "player_b"), found):
                if f["status"] == "found":
                    got[side] = f["name"]
            if exp["action"] == "record":
                want = dict(exp)
                for side in ("player_a", "player_b"):
                    if want[side] == "ME":
                        want[side] = ME
                g, w = canonical(got), canonical(want)
                for field in FIELDS:
                    row[field] = g[field] == w[field]
                row["all_fields"] = all(row[field] for field in FIELDS)

    row["action_ok"] = row["action"] == row["expected"]
    passed = row["action_ok"] and row.get("all_fields", True)
    print(f"{case['id']}: {'PASS' if passed else 'FAIL'}")
    rows.append(row)
con.close()

results = pd.DataFrame(rows)
results.to_csv("eval/results.csv", index=False)
print("\nAction accuracy by category:")
print(results.groupby("category")["action_ok"].mean().round(2))
records = results.dropna(subset=["all_fields"]) if "all_fields" in results else results.iloc[0:0]
if not records.empty:
    print("\nField accuracy on recorded matches:")
    print(records[FIELDS + ["all_fields"]].astype(bool).mean().round(2))