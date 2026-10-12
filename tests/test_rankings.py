from pathlib import Path
import duckdb
from pytest import approx
from db import add_player, save_match, void_match
from rankings import elo_update, rebuild_rankings

def test_equal_players_exchange_16():
    assert elo_update(1000, 1000) == approx((1016, 984))

def test_favourite_gains_little():
    winner, _ = elo_update(1100, 900)
    assert winner - 1100 == approx(7.69, abs=0.01)

def test_upset_gains_a_lot():
    winner, _ = elo_update(900, 1100)
    assert winner - 900 == approx(24.31, abs=0.01)

def test_voided_match_does_not_count():
    con = duckdb.connect()
    con.execute(Path("src/schema.sql").read_text())
    a, b = add_player(con, "Ann"), add_player(con, "Ben")
    rec = {"sport": "badminton", "played_on": "2026-10-01", "winner": "player_a",
           "games": [{"a": 15, "b": 10}, {"a": 15, "b": 12}]}
    void_match(con, save_match(con, rec, a, b, "test"))
    rebuild_rankings(con)
    assert con.execute("SELECT COUNT(*) FROM rankings").fetchone()[0] == 0