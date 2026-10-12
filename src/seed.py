from config import ME
from db import connect, init_db, add_player

init_db()
con = connect()
if con.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 0:
    add_player(con, ME)
    add_player(con, "Peter", aliases=["pete"])
    add_player(con, "Elon")
    add_player(con, "Sam A")
    add_player(con, "Tim")
    add_player(con, "Mark")
print(con.execute("SELECT * FROM players").df())
con.close()