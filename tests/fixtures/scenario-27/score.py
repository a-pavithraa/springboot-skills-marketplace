#!/usr/bin/env python3
"""Score one scenario 27 session: compare its last JSON line with the answers. Prints one line."""

import json
import re
import sys
from pathlib import Path

answers = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
name, result_path = sys.argv[2], Path(sys.argv[3])
try:
    result = json.loads(result_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    sys.exit(print(f"{name}: no result"))
found = re.findall(r"\{[^{}]*\"catalog\"[^{}]*\}", result.get("result", "") or "")
verdicts = json.loads(found[-1]) if found else {}
bugs = [key for key, value in answers.items() if value == "FAIL"]
caught = [key for key in bugs if verdicts.get(key) == "FAIL"]
false_alarms = [key for key, value in answers.items() if value == "PASS" and verdicts.get(key) == "FAIL"]
print(f"{name}: caught {len(caught)}/{len(bugs)} {caught} false_alarms={false_alarms} "
      f"verdict={'yes' if verdicts else 'NONE'} turns={result.get('num_turns')} "
      f"cost=${result.get('total_cost_usd', 0):.2f} stop={result.get('subtype')}")
