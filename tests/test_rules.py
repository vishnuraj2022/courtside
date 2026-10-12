import pytest
from rules import valid_game, validate_match

# ---------- single games ----------
@pytest.mark.parametrize("w, l, ok", [ 
    (21, 19, True), (21, 20, False), (22, 20, True), (23, 20, False),
    (30, 28, True), (30, 29, True), (31, 29, False), (21, -1, False),
])
def test_badminton_game_scores(w, l, ok):
    assert valid_game(w, l, target=21, cap=30) == ok

@pytest.mark.parametrize("w, l, ok", [
    (11, 9, True), (11, 10, False), (12, 10, True), (15, 13, True), (13, 10, False),
])
def test_squash_game_scores(w, l, ok):
    assert valid_game(w, l, target=11, cap=None) == ok

# ---------- whole matches ----------
def g(*scores):
    """Turn (21, 15), (18, 21) into the record format."""
    return [{"a": a, "b": b} for a, b in scores]

def test_valid_badminton_matches():
    assert validate_match("badminton", g((21, 15), (21, 18)), "player_a") == []
    assert validate_match("badminton", g((21, 15), (18, 21), (21, 19)), "player_a") == []

def test_valid_squash_matches():
    assert validate_match("squash", g((11, 5), (11, 7), (11, 9)), "player_a") == []
    assert validate_match("squash", g((11, 8), (9, 11), (8, 11), (11, 7), (7, 11)),
                          "player_b") == []

def test_invalid_game_score_is_reported():
    problems = validate_match("badminton", g((21, 20), (21, 18)), "player_a")
    assert any("21-20" in p for p in problems)

def test_extra_game_after_match_decided():
    assert validate_match("badminton", g((21, 10), (21, 12), (15, 21)), "player_a")

def test_winner_contradicts_scores():
    assert validate_match("badminton", g((21, 15), (21, 18)), "player_b")

def test_unfinished_match():
    assert validate_match("badminton", g((21, 15)), "player_a")

def test_unsupported_sport():
    assert validate_match("tennis", g((6, 4), (6, 3)), "player_a")