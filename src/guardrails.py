import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"players", "matches", "games", "rankings"}
MAX_ROWS = 500

class UnsafeSQLError(Exception):
    pass

def make_safe(sql):
    """Return a safe version of the SQL, or raise UnsafeSQLError."""
    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except:
        raise UnsafeSQLError(f"Could not parse SQL: {e}")
    
    if len(statements) != 1:
        raise UnsafeSQLError("Exactly one statement is allowed.")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        raise UnsafeSQLError("Only SELECT queries are allowed.") 
    
    cte_names = {cte.alias for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        if table.name not in ALLOWED_TABLES | cte_names:
            raise UnsafeSQLError(f"Table not allowed: {table.sql()}")

    if tree.args.get("limit") is None:
        tree = tree.limit(MAX_ROWS)
    return tree.sql(dialect="duckdb")
