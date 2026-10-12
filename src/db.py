from datetime import date
from pathlib import Path
import duckdb
from config import DB_PATH

def connect():
    return duckdb.connect(DB_PATH)

def init_db():
    con = connect()
    con.execute(Path("src/schema.sql").read_text())
    con.close()

def add_player(con, name, aliases=()):
    player_id = con.execute(
        "INSERT INTO players (display_name) VALUES (?) RETURNING player_id",
        [name]).fetchone()[0]
    for alias in {name.lower(), *(a.lower() for a in aliases)}:
        con.execute("INSERT INTO player_aliases (alias, player_id) VALUES (?, ?)",
                    [alias, player_id])
    return player_id

def add_player(con, name, aliases=()):
    player_id = con.execute(
        "INSERT INTO players (display_name) VALUES (?) RETURNING player_id",
        [name]).fetchone()[0]
    for alias in {name.lower(), *(a.lower() for a in aliases)}:
        con.execute("INSERT INTO player_aliases (alias, player_id) VALUES (?, ?)",
                    [alias, player_id])
    return player_id

def save_match(con, rec, a_id, b_id, raw_text):
    """Save a match and its games together, or not at all."""
    winner_id = a_id if rec["winner"] == "player_a" else b_id
    con.begin()
    try:
        match_id = con.execute(
            """INSERT INTO matches (sport, played_on, player_a_id, player_b_id, winner_id, raw_text) VALUES (?, ?, ?, ?, ?, ?) RETURNING match_id""",
            [rec["sport"], date.fromisoformat(rec["played_on"]),
             a_id, b_id, winner_id, raw_text]).fetchone()[0]
        con.executemany(
            "INSERT INTO games (match_id, game_no, score_a, score_b) VALUES (?, ?, ?, ?)",
            [[match_id, i, g["a"], g["b"]] for i, g in enumerate(rec["games"], start=1)])
        con.commit()
    except Exception:
        con.rollback()
        raise
    return match_id

def void_match(con, match_id):
    con.execute("UPDATE matches SET status = 'voided' WHERE match_id = ?", [match_id])