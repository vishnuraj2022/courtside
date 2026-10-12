import difflib
from config import ME

def resolve_name(con, name):
    """Match a typed name to a player. Never guesses silently."""
    key = name.strip().lower()
    if key in ("me", "i", "myself"):
        key = ME.lower()

    # 1. Exact name or known alias
    row = con.execute(
        """SELECT p.player_id, p.display_name 
            FROM player_aliases a JOIN players p ON a.player_id = p.player_id
            WHERE a.alias = ?""", [key]).fetchone()

    if row:
            return {"status": "found", "player_id": row[0], "name": row[1]}
        
    # 2. First name only: fine if exactly one player has it
    players = con.execute("SELECT player_id, display_name FROM players").fetchall()
    first = [p for p in players if p[1].lower().split()[0] == key]
    if len(first) == 1:
        return {"status": "found", "player_id": first[0][0], "name": first[0][1]}
    if len(first) > 1:
        return {"status": "ambiguous", "options": [p[1] for p in first]}

    # 3. Close spellings are suggestions only
    by_lower = {p[1].lower(): p[1] for p in players}
    close = difflib.get_close_matches(key, list(by_lower), n=3, cutoff=0.75)
    return {"status": "unknown", "suggestions": [by_lower[c] for c in close]}