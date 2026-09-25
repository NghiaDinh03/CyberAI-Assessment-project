import json
import time

aid = "42678bba-13b1-4e9b-b869-de7638781e8e"
fpath = f"/data/assessments/{aid}.json"

for _ in range(60):
    with open(fpath, encoding="utf-8") as f:
        d = json.load(f)
    s = d.get("status")
    p = d.get("progress", {})
    pct = p.get("percent")
    msg = p.get("message", "")
    print(f"[{time.strftime('%X')}] {s} ({pct}%) - {msg[:60]}")
    if s in ("completed", "failed"):
        print(f"FINAL STATUS: {s}")
        break
    time.sleep(10)
