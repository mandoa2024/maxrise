import os
import subprocess
import tempfile


def build_perf_command(pid: int, duration: int, sample_rate: int, output: str) -> list[str]:
    if pid <= 0 or duration <= 0 or sample_rate <= 0:
        raise ValueError("pid, duration and sample_rate must be positive")
    return [
        "perf", "record", "-e", "cpu-clock", "-F", str(sample_rate),
        "--call-graph", "fp", "-p", str(pid),
        "-o", output, "--", "sleep", str(duration),
    ]


def demo_collapsed_stacks(pid: int) -> str:
    return "\n".join(
        [
            f"process_{pid};main;handle_request;parse_payload 42",
            f"process_{pid};main;handle_request;query_database 31",
            f"process_{pid};main;handle_request;serialize_response 18",
            f"process_{pid};main;background_worker;flush_metrics 9",
        ]
    )


def demo_memory_metrics(pid: int) -> dict:
    return {
        "pid": pid,
        "source": "demo",
        "rss_kb": 24576,
        "vms_kb": 131072,
        "peak_rss_kb": 32768,
    }


def read_proc_memory_metrics(pid: int) -> dict:
    if pid <= 0:
        raise ValueError("pid must be positive")
    status_path = f"/proc/{pid}/status"
    values = {}
    try:
        with open(status_path, encoding="utf-8") as status:
            for line in status:
                name, separator, value = line.partition(":")
                if not separator:
                    continue
                if name in {"VmRSS", "VmSize", "VmHWM"}:
                    parts = value.strip().split()
                    if parts:
                        values[name] = int(parts[0])
    except FileNotFoundError as exc:
        raise RuntimeError(f"process {pid} not found") from exc
    except PermissionError as exc:
        raise RuntimeError(f"cannot read memory metrics for process {pid}") from exc

    return {
        "pid": pid,
        "source": status_path,
        "rss_kb": values.get("VmRSS"),
        "vms_kb": values.get("VmSize"),
        "peak_rss_kb": values.get("VmHWM"),
    }


def collect_perf(pid: int, duration: int, sample_rate: int, demo_mode: bool) -> str:
    if demo_mode:
        return demo_collapsed_stacks(pid)
    with tempfile.TemporaryDirectory(prefix="minidrop-") as tmpdir:
        perf_data = os.path.join(tmpdir, "perf.data")
        record = subprocess.run(
            build_perf_command(pid, duration, sample_rate, perf_data),
            check=False,
            capture_output=True,
            text=True,
            timeout=duration + 15,
        )
        if record.returncode != 0:
            raise RuntimeError(record.stderr.strip() or "perf record failed")
        script = subprocess.run(
            ["perf", "script", "-i", perf_data, "--no-inline"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if script.returncode != 0:
            raise RuntimeError(script.stderr.strip() or "perf script failed")
        return collapse_perf_script(script.stdout)


def collapse_perf_script(raw: str) -> str:
    stacks = []
    frames = []
    for line in raw.splitlines() + [""]:
        stripped = line.strip()
        if not stripped:
            if frames:
                stacks.append(";".join(reversed(frames)) + " 1")
                frames = []
            continue
        if line[:1].isspace():
            parts = stripped.split()
            if len(parts) >= 2:
                frames.append(parts[1].split("+")[0])
    if not stacks:
        raise RuntimeError("perf produced no stack samples")
    return "\n".join(stacks)


def collect_performance(pid: int, duration: int, sample_rate: int, demo_mode: bool) -> dict:
    collapsed_stacks = collect_perf(pid, duration, sample_rate, demo_mode)
    memory = demo_memory_metrics(pid) if demo_mode else read_proc_memory_metrics(pid)
    return {
        "raw_data": collapsed_stacks,
        "performance_data": {
            "cpu": {
                "collector": "perf",
                "event": "cpu-clock",
                "duration_seconds": duration,
                "sample_rate_hz": sample_rate,
                "collapsed_stack_lines": len(collapsed_stacks.splitlines()),
            },
            "memory": memory,
        },
    }
