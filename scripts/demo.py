import json
import os
import time
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
PID_FILE = os.getenv("PID_FILE")
DEMO_DURATION_SECONDS = int(os.getenv("DEMO_DURATION_SECONDS", "5"))


def request(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


def main():
    deadline = time.time() + 120
    agents = []
    while time.time() < deadline:
        agents = request("/api/v1/agents")
        if agents:
            break
        time.sleep(2)
    if not agents:
        raise SystemExit("no agent registered after 120 seconds")
    pid = 1
    if PID_FILE:
        while time.time() < deadline:
            try:
                with open(PID_FILE, encoding="ascii") as handle:
                    pid = int(handle.read().strip())
                break
            except (FileNotFoundError, ValueError):
                time.sleep(1)
        else:
            raise SystemExit(f"workload PID not found in {PID_FILE}")
    task = request(
        "/api/v1/tasks",
        method="POST",
        body={
            "agent_id": agents[0]["id"],
            "pid": pid,
            "duration_seconds": DEMO_DURATION_SECONDS,
            "sample_rate": 99,
            "collector": "perf",
        },
    )
    print(f"created real perf task {task['id']} for host PID {pid}", flush=True)
    while time.time() < deadline:
        task = request(f"/api/v1/tasks/{task['id']}")
        print(f"status={task['status']} reason={task['status_reason']}", flush=True)
        if task["status"] == "DONE":
            print("top functions:", task["result"]["top_functions"], flush=True)
            print("open http://localhost:3000", flush=True)
            return
        if task["status"] == "FAILED":
            raise SystemExit(task["status_reason"])
        time.sleep(2)
    raise SystemExit("demo timed out")


if __name__ == "__main__":
    main()
