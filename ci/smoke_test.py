"""End-to-end smoke test of a running CiteMap container.

Runs inside the container (python - < ci/smoke_test.py), uses only the standard
library and the bundled demo dataset, so it needs no network access. Exits with
a non-zero status if any check fails.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def call(method: str, path: str, body: dict | None = None) -> tuple[int, bytes]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.read()


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"{'PASS' if condition else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not condition:
        sys.exit(1)


status, raw = call("GET", "/api/health")
health = json.loads(raw)
check("health endpoint", status == 200 and health["status"] == "ok", f"version {health['version']}")

status, raw = call("GET", "/")
check("frontend is served", status == 200 and b'id="root"' in raw)

status, raw = call("POST", "/api/graphs", {"source": "demo", "seed_id": "D042"})
job = json.loads(raw)
check("graph job accepted", status == 202, f"job {job['id']} {job['status']}")
deadline = time.time() + 60
while job["status"] in ("queued", "running") and time.time() < deadline:
    time.sleep(0.5)
    job = json.loads(call("GET", f"/api/jobs/{job['id']}")[1])
check("graph job finished", job["status"] == "done", job.get("error") or "")

status, raw = call("GET", "/api/graphs/demo/D042?limit=20")
view = json.loads(raw)
check(
    "graph view",
    status == 200 and view["shown_nodes"] == 20 and len(view["clusters"]) >= 2,
    f"{view['total_nodes']} papers, {len(view['links'])} links shown, {len(view['clusters'])} clusters",
)

status, raw = call("GET", "/api/graphs/demo/D042/export.csv?limit=5")
rows = raw.decode().strip().splitlines()
check("CSV export", status == 200 and len(rows) == 6 and rows[0].startswith("rank,id,title"))
print("Smoke test passed")
