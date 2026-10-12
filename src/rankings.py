START, K, MIN_MATCHES = 1000, 32, 3

def elo_update(r_winner, r_loser, k=K):
    """Return the new ratings after one match."""
    expected = 1 / (1 + 10 ** ((r_loser - r_winner) / 400))   # winner's chance
    change = k * (1 - expected)
    return r_winner + change, r_loser - change

def rebuild_rankings(con):
    """Recompute every rating from scratch by replaying active matches in order."""
    rows = con.execute("""
        SELECT sport, winner_id,
               CASE WHEN winner_id = player_a_id THEN player_b_id
                    ELSE player_a_id END AS loser_id
        FROM matches
        WHERE status = 'active'
        ORDER BY played_on, match_id""").fetchall()

    table = {}   # (sport, player_id) -> [rating, played, won, lost]
    for sport, winner, loser in rows:
        w = table.setdefault((sport, winner), [START, 0, 0, 0])
        l = table.setdefault((sport, loser), [START, 0, 0, 0])
        w[0], l[0] = elo_update(w[0], l[0])
        w[1] += 1
        w[2] += 1
        l[1] += 1
        l[3] += 1

    con.begin()
    try:
        con.execute("DELETE FROM rankings")
        if table:
            con.executemany(
                """INSERT INTO rankings
                       (sport, player_id, rating, matches_played, wins, losses)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [[sport, pid, round(rating, 1), played, won, lost]
                 for (sport, pid), (rating, played, won, lost) in table.items()])
            con.execute("""
                UPDATE rankings SET rank = ranked.pos
                FROM (SELECT sport, player_id,
                             RANK() OVER (PARTITION BY sport ORDER BY rating DESC) AS pos
                      FROM rankings WHERE matches_played >= ?) AS ranked
                WHERE rankings.sport = ranked.sport
                  AND rankings.player_id = ranked.player_id""", [MIN_MATCHES])
        con.commit()
    except Exception:
        con.rollback()
        raise