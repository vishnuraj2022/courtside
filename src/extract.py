from datetime import date
import anthropic
from dotenv import load_dotenv
from config import SPORTS

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-haiku-5-5"

TOOLS = [
    {
        "name": "record_match",
        "description": "Record one completed singles match. If the message describes "
                       "several matches, call this tool once for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sport": {"type": "string", "enum": SPORTS},
                "played_on": {"type": "string",
                              "description": "Date played, as YYYY-MM-DD."},
                "player_a": {"type": "string",
                             "description": "First player as written. Use ME for the user."},
                "player_b": {"type": "string",
                             "description": "Second player as written."},
                "games": {"type": "array",
                          "description": "Every game in order, points from player_a's side.",
                          "items": {"type": "object",
                                    "properties": {"a": {"type": "integer"},
                                                   "b": {"type": "integer"}},
                                    "required": ["a", "b"]}},
                "winner": {"type": "string", "enum": ["player_a", "player_b"]},
            },
            "required": ["sport", "played_on", "player_a", "player_b",
                         "games", "winner"],
        },
    },
    {
        "name": "ask_clarification",
        "description": "Ask the user ONE short question when the sport, a player, "
                       "the date or any game score is missing or ambiguous.",
        "input_schema": {"type": "object",
                         "properties": {"question": {"type": "string"}},
                         "required": ["question"]},
    },
]

def system_prompt(today):
    return f"""You turn messages about racquet-sport matches into records. Today is {today:%A %d %B %Y}. Resolve relative dates against today.
"I" or "me" means the user: write ME as their name. Supported sports: {', '.join(SPORTS)}. 
Badminton games are played to 15 points; squash games to 11.
For any other sport, ask_clarification to say it is not supported yet. 
Always respond by calling exactly one tool.
Never guess a missing sport, player, date or score: ask instead.
Record what the message says even if it looks wrong; the app checks the rules.
A message may describe several matches: call record_match once per match.
If any match is missing a detail, call only ask_clarification and ask about it."""

def start(message):
    return [{"role": "user", "content": message}]

def extract_all(messages, today=None):
    """One model call. Returns (response, results), one result per tool call."""
    today = today or date.today()
    response = client.messages.create(
        model=MODEL, max_tokens=8000, system=system_prompt(today),
        tools=TOOLS, messages=messages)
    results = [{"tool": b.name, "input": b.input, "id": b.id}
               for b in response.content if b.type == "tool_use"]
    if not results:   # plain text instead of a tool call: treat it as a question
        text = "".join(b.text for b in response.content if b.type == "text")
        results = [{"tool": "ask_clarification", "input": {"question": text}, "id": None}]
    return response, results

def extract(messages, today=None):
    """Single-match version, used by the evaluation and test scripts."""
    response, results = extract_all(messages, today)
    return response, results[0]

def continue_after(messages, response, reply):
    """Add the model's last turn, then answer every tool call it made."""
    messages = messages + [{"role": "assistant", "content": response.content}]
    ids = [b.id for b in response.content if b.type == "tool_use"]
    if ids:
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": i, "content": reply} for i in ids]})
    else:
        messages.append({"role": "user", "content": reply})
    return messages