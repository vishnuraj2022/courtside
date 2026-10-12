CREATE SEQUENCE IF NOT EXISTS player_seq;
CREATE SEQUENCE IF NOT EXISTS match_seq;

CREATE TABLE IF NOT EXISTS players(
    player_id       INTEGER PRIMARY KEY DEFAULT nextval('player_seq'),
    display_name    VARCHAR NOT NULL UNIQUE,
    created_at      TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS player_aliases (
    alias     VARCHAR PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players (player_id)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id    INTEGER PRIMARY KEY DEFAULT nextval('match_seq'),
    sport       VARCHAR NOT NULL CHECK (sport IN ('badminton', 'squash')),
    played_on   DATE NOT NULL,
    player_a_id INTEGER NOT NULL REFERENCES players (player_id),
    player_b_id INTEGER NOT NULL REFERENCES players (player_id),
    winner_id   INTEGER NOT NULL REFERENCES players (player_id),
    status      VARCHAR NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'voided')),
    raw_text    VARCHAR NOT NULL,
    recorded_at TIMESTAMP DEFAULT current_timestamp,
    CHECK (player_a_id <> player_b_id),
    CHECK (winner_id IN (player_a_id, player_b_id))
);

CREATE TABLE IF NOT EXISTS games (
    match_id INTEGER NOT NULL, 
    game_no  INTEGER NOT NULL CHECK (game_no >= 1),
    score_a  INTEGER NOT NULL CHECK (score_a >= 0),
    score_b  INTEGER NOT NULL CHECK (score_b >= 0),
    PRIMARY KEY (match_id, game_no)
);

CREATE TABLE IF NOT EXISTS rankings (
    sport          VARCHAR NOT NULL,
    player_id      INTEGER NOT NULL REFERENCES players (player_id),
    rating         DOUBLE NOT NULL,
    matches_played INTEGER NOT NULL,
    wins           INTEGER NOT NULL,
    losses         INTEGER NOT NULL,
    rank           INTEGER,
    updated_at     TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (sport, player_id)
);