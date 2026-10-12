import sys
from datetime import date
import streamlit as st

sys.path.append("src")
from db import connect, init_db, add_player, save_match, void_match
from extract import extract_all, start, continue_after
from names import resolve_name
from rules import validate_match
from rankings import rebuild_rankings
from config import SPORTS


st.set_page_config(page_title="Courtside")
st.title("Courtside")
st.caption("Log a badminton or squash result in plain English.")

init_db()
con = connect()
state = st.session_state
KEYS = ("messages", "response", "question", "pending", "problems")
for key in KEYS:
    state.setdefault(key, None)
state.setdefault("raw_text", "")
state.setdefault("flash", None)

if state.flash:
    st.success(state.flash)
    state.flash = None

def reset():
    for key in KEYS:
        state[key] = None
    state.raw_text = ""

def ask_model():
    state.response, results = extract_all(state.messages)
    questions = [r["input"]["question"] for r in results if r["tool"] == "ask_clarification"]
    records = [r["input"] for r in results if r["tool"] == "record_match"]
    if questions:
        state.question, state.pending = " ".join(questions), None
    else:
        state.question, state.pending = None, records
    
def pick_player(side, typed):
    """Return (player_id or None, name), asking when the name isn't clear."""
    found = resolve_name(con, typed)
    if found["status"] == "found":
        return found["player_id"], found["name"]
    options = found.get("options") or found.get("suggestions") or []
    choice = st.selectbox(f'Who is "{typed}"?', options + [f"New player: {typed}"],
                          key=f"pick-{side}-{typed}")
    if choice.startswith("New player: "):
        return None, typed            # created only when Save is pressed
    return resolve_name(con, choice)["player_id"], choice

def check_record(rec, a_name, b_name):
    """All the problems with one record."""
    problems = validate_match(rec["sport"], rec["games"], rec["winner"])
    if a_name.lower() == b_name.lower():
        problems.append("Both players are the same person")
    try:
        if date.fromisoformat(rec["played_on"]) > date.today():
            problems.append("The date is in the future")
    except ValueError:
        problems.append(f"'{rec['played_on']}' is not a valid date")
    return problems

def ensure_player(player_id, name):
    """Existing ID, or the player just added earlier in this batch, or a new player."""
    return player_id or resolve_name(con, name).get("player_id") or add_player(con, name)

# ---------- the message box ----------
text = st.chat_input("e.g. Beat Tom 15-11, 13-15, 15-12 at badminton last night")
if text:
    if state.messages and (state.question or state.pending):   # answer or correction
        reply = text
        if state.pending and state.problems:
            reply = (f"The app rejected that record: {'; '.join(state.problems)}. "
                     f"The user says: {text}")
        state.messages = continue_after(state.messages, state.response, reply)
        state.raw_text += f" | {text}"
    else:                                                      # a new match
        state.messages, state.raw_text = start(text), text
    with st.spinner("Reading your message..."):
        ask_model()

if state.question:
    st.info(state.question)

# ---------- the confirmation card ----------
if state.pending:
    batch, all_problems = [], []
    for i, rec in enumerate(state.pending, start=1):
        a_id, a_name = pick_player(f"a{i}", rec["player_a"])
        b_id, b_name = pick_player(f"b{i}", rec["player_b"])
        problems = check_record(rec, a_name, b_name)
        winner, loser = (a_name, b_name) if rec["winner"] == "player_a" else (b_name, a_name)
        scores = ", ".join(f"{g['a']}-{g['b']}" for g in rec["games"])
        with st.container(border=True):
            st.markdown(f"**{i}. {rec['sport'].title()}** · {rec['played_on']}")
            st.markdown(f"**{winner}** beat {loser}")
            st.caption(f"Scores, {a_name} first: {scores}")
            for problem in problems:
                st.error(problem)
        all_problems += [f"Match {i}: {p}" for p in problems]
        batch.append((rec, a_id, a_name, b_id, b_name))
    state.problems = all_problems

    if all_problems:
        st.caption("Type a correction below, e.g. 'in match 2 the first game was 16-14'.")

    save_col, discard_col = st.columns(2)
    label = f"Save {len(batch)} matches" if len(batch) > 1 else "Save match"
    if save_col.button(label, type="primary", disabled=bool(all_problems)):
        for rec, a_id, a_name, b_id, b_name in batch:
            save_match(con, rec, ensure_player(a_id, a_name),
                       ensure_player(b_id, b_name), state.raw_text)
        rebuild_rankings(con)
        state.flash = f"Saved {len(batch)} match(es)."
        reset()
        con.close()
        st.rerun()
    if discard_col.button("Discard"):
        reset()
        con.close()
        st.rerun()

# ---------- recent matches, with void ----------
with st.expander("Recent matches"):
    recent = con.execute("""
        SELECT m.match_id AS id, m.played_on AS date, m.sport,
               pa.display_name AS player_a, pb.display_name AS player_b,
               pw.display_name AS winner,
               string_agg(concat(g.score_a, '-', g.score_b), ', '
                          ORDER BY g.game_no) AS scores
        FROM matches m
        JOIN players pa ON m.player_a_id = pa.player_id
        JOIN players pb ON m.player_b_id = pb.player_id
        JOIN players pw ON m.winner_id = pw.player_id
        LEFT JOIN games g ON g.match_id = m.match_id
        WHERE m.status = 'active'
        GROUP BY ALL
        ORDER BY m.played_on DESC, m.match_id DESC
        LIMIT 10""").df()

    if recent.empty:
        st.caption("No matches yet.")
    else:
        st.dataframe(recent, hide_index=True)
        to_void = st.selectbox("Match to void", recent["id"].tolist())
        sure = st.checkbox("Yes, void this match")
        if st.button("Void match", disabled=not sure):
            void_match(con, int(to_void))
            rebuild_rankings(con)          # remove this line until you've done Phase 5
            state.flash = f"Match {to_void} voided."
            con.close()
            st.rerun()

with st.sidebar:
    st.header("Rankings")
    for sport in SPORTS:
        st.subheader(sport.title())
        df = con.execute("""
            SELECT COALESCE(CAST(r.rank AS VARCHAR), '–') AS "#", p.display_name AS player,
                r.rating, r.wins AS won, r.losses AS lost
            FROM rankings r JOIN players p ON r.player_id = p.player_id
            WHERE r.sport = ?
            ORDER BY r.rank NULLS LAST, r.rating DESC""", [sport]).df()
        if df.empty:
            st.caption("No matches yet.")
        else:
            st.dataframe(df, hide_index=True)

con.close()