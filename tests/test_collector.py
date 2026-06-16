import os
from pathlib import Path

import pytest

from agent.collector import (
    build_perf_command,
    collapse_perf_script,
    collect_performance,
    demo_collapsed_stacks,
    read_proc_memory_metrics,
)


def test_build_perf_command_has_no_shell_interpolation():
    command = build_perf_command(123, 5, 99, "/tmp/perf.data")
    assert command == [
        "perf", "record", "-e", "cpu-clock", "-F", "99",
        "--call-graph", "fp", "-p", "123",
        "-o", "/tmp/perf.data", "--", "sleep", "5",
    ]


def test_build_perf_command_validates_arguments():
    with pytest.raises(ValueError):
        build_perf_command(0, 5, 99, "/tmp/perf.data")


def test_demo_data_is_valid_collapsed_format():
    result = demo_collapsed_stacks(42)
    assert "process_42;main" in result
    assert len(result.splitlines()) == 4


def test_collapse_perf_script():
    raw = "process 1 [000] 1.0: cycles:\n        abc foo+0x1\n        def main+0x2\n\n"
    assert collapse_perf_script(raw) == "main;foo 1"


def test_collect_performance_in_demo_mode_includes_cpu_and_memory():
    result = collect_performance(42, 5, 99, True)

    assert "process_42;main" in result["raw_data"]
    assert result["performance_data"]["cpu"]["collector"] == "perf"
    assert result["performance_data"]["cpu"]["sample_rate_hz"] == 99
    assert result["performance_data"]["memory"]["rss_kb"] > 0


def test_read_proc_memory_metrics_for_current_process():
    if not Path("/proc/self/status").exists():
        pytest.skip("/proc is not available on this platform")

    metrics = read_proc_memory_metrics(os.getpid())
    assert metrics["source"].endswith("/status")
    assert metrics["rss_kb"] is None or metrics["rss_kb"] > 0
