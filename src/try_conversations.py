from extract import extract, start, continue_after

messages = start(input("Match: "))
while True:
    response, result = extract(messages)
    if result["tool"] == "record_match":
        print("Record:", result["input"])
        break
    reply = input(f"{result['input']['question']}\n> ")
    messages = continue_after(messages, response, result["id"], reply)