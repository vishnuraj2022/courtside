import sys
sys.path.append("src")
from agent import run_agent

answer, trace = run_agent(input("Ask about your results: "))
print("\n" + answer)