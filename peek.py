import duckdb

# con = duckdb.connect("uk_data.duckdb", read_only=True)
con = duckdb.connect("courtside.duckdb")

while True:
    query = input("\nSQL> ")
    if query.strip().lower() in ("exit", "quit"):
        break
    try:
        print(con.sql(query))
    except Exception as error:
        print("Error:", error)

con.close()
