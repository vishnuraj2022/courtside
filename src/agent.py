import json
import duckdb
import yaml
import anthropic
from dotenv import load_dotenv
from guardrails import make_safe
from config import DB_PATH

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-haiku-5-5"
MAX_STEPS = 8

with open("courtside_dictionary.yaml") as f:
    DICTIONARY = yaml.safe_load(f)["tables"]

def connect():
    return duckdb.connect(DB_PATH, read_only=True,
                          config={"enable_external_access": False})

def list_tables():
    return {name: info["description"] for name, info in DICTIONARY.items()}

def describe_table(table_name):
    if table_name not in DICTIONARY:   # also protects the f-string below
        return {"error": f"Unknown table: {table_name}"}
    con = connect()
    try:
        sample = con.execute(f"SELECT * FROM {table_name} LIMIT 3").df()
    finally:
        con.close()
    return {**DICTIONARY[table_name], "sample_rows": sample.to_csv(index=False)}

def run_sql(query):
    try:
        safe_sql = make_safe(query)
        con = connect()
        try:
            df = con.execute(safe_sql).df()
        finally:
            con.close()
        return {"sql_executed": safe_sql, "row_count": len(df),
                "rows_csv": df.head(50).to_csv(index=False)}
    except Exception as error:
        return {"error": str(error)}   # the model reads this and can fix its query

#  how the model sees the tools 

TOOLS = [
    {"name": "list_tables",
     "description": "List available tables and what each contains.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "describe_table",
     "description": "Get column definitions, units, caveats and 3 recent "
                    "sample rows for one table. Use before querying it.",
     "input_schema": {"type": "object",
                      "properties": {"table_name": {"type": "string"}},
                      "required": ["table_name"]}},
    {"name": "run_sql",
     "description": "Run one read-only DuckDB SELECT query. Returns up to "
                    "200 rows as CSV, or an error message to fix.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
]
FUNCTIONS = {"list_tables": list_tables,
             "describe_table": describe_table,
             "run_sql": run_sql}

SYSTEM = """You are an analyst of racquet-sport match results.
Answer using ONLY data returned by your tools.
- Check a table's definitions before writing SQL against it.
- Never state a number that did not come from a tool result.
- If the data cannot answer the question, say so plainly.
- Explore first if you need to, but make your LAST run_sql call return exactly the rows and columns that answer the question.
- Finish with a 2-4 sentence answer that states the period covered."""


# agent loop

def run_agent(question, verbose=True):
    messages = [{"role": "user", "content": question}]
    trace = []
    for step in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL, max_tokens=2048, system=SYSTEM, 
            tools=TOOLS, messages=messages
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            answer = "".join(b.text for b in response.content if b.type == "text")
            return answer, trace
        
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = FUNCTIONS[block.name](**block.input)
                trace.append({"tool": block.name, "input": block.input,
                              "output": output})
                if verbose:
                    print(f"step {step + 1}: {block.name}({block.input})")
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(output, default=str)})
        messages.append({"role": "user", "content": results})

    return "Stopped: too many steps without an answer.", trace

if __name__ == "__main__":
    answer, trace = run_agent(input("Ask a question: "))
    print("\n" + answer)