from pathlib import Path
import duckdb
from db import add_player
from names import resolve_name

def make_db():
    con = duckdb.connect()   # in memory, gone when the test ends
    con.execute(Path("src/schema.sql").read_text())
    add_player(con, "Sreekumar", aliases=["sree"])
    add_player(con, "Vinit")
    add_player(con, "sam altman")
    add_player(con, "sam son")
    return con

def test_alias_is_found():
    assert resolve_name(make_db(), "sree")["name"] == "Sreekumar"

def test_shared_first_name_is_ambiguous():
    assert resolve_name(make_db(), "Sam")["status"] == "ambiguous"

def test_typo_is_suggested_not_accepted():
    found = resolve_name(make_db(), "srek")
    assert found["status"] == "unknown"
    assert found["suggestions"] == ["Sreekumar"]