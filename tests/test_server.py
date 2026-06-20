from datetime import datetime, timedelta, timezone

from server.app.main import build_window_performance_data


def test_build_window_performance_data_aggregates_segment_metrics():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session = {
        "collector": "perf",
        "pid": 6424,
        "sample_rate": 49,
        "ebpf_probes": ["vfs_read"],
    }
    rows = [
        {
            "start_at": start,
            "end_at": start + timedelta(seconds=30),
            "performance_data": {
                "cpu": {
                    "collector": "perf",
                    "event": "cpu-clock",
                    "duration_seconds": 30,
                    "sample_rate_hz": 49,
                    "collapsed_stack_lines": 10,
                },
                "memory": {
                    "rss_kb": 1000,
                    "vms_kb": 3000,
                    "peak_rss_kb": 1200,
                },
            }
        },
        {
            "start_at": start + timedelta(seconds=32),
            "end_at": start + timedelta(seconds=60),
            "performance_data": {
                "cpu": {
                    "collector": "perf",
                    "event": "cpu-clock",
                    "duration_seconds": 30,
                    "sample_rate_hz": 49,
                    "collapsed_stack_lines": 12,
                },
                "memory": {
                    "rss_kb": 1100,
                    "vms_kb": 3100,
                    "peak_rss_kb": 1400,
                },
            }
        },
    ]

    result = build_window_performance_data(
        session, rows, start, start + timedelta(minutes=1)
    )

    assert result["cpu"] == {
        "collector": "perf",
        "event": "cpu-clock",
        "duration_seconds": 60,
        "sampled_duration_seconds": 58,
        "coverage_percent": 96.7,
        "sample_rate_hz": 49,
        "collapsed_stack_lines": 22,
    }
    assert result["memory"] == {
        "rss_kb": 1100,
        "vms_kb": 3100,
        "peak_rss_kb": 1400,
    }
    assert result["window"]["segments"] == 2
    assert result["window"]["duration_seconds"] == 60
    assert result["window"]["sampled_duration_seconds"] == 58


def test_build_window_performance_data_keeps_ebpf_probe_metadata():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session = {
        "collector": "ebpf",
        "pid": 6725,
        "sample_rate": 49,
        "ebpf_probes": ["vfs_read", "tcp_sendmsg"],
    }
    rows = [
        {
            "start_at": start,
            "end_at": start + timedelta(seconds=30),
            "performance_data": {
                "cpu": {
                    "collector": "ebpf",
                    "event": "profile:hz",
                    "duration_seconds": 30,
                    "sample_rate_hz": 49,
                    "ebpf_probes": ["vfs_read", "tcp_sendmsg"],
                    "probes": [
                        {"source": "kprobe", "event": "vfs_read"},
                        {"source": "kprobe", "event": "tcp_sendmsg"},
                    ],
                }
            }
        }
    ]

    result = build_window_performance_data(
        session, rows, start, start + timedelta(seconds=30)
    )

    assert result["cpu"]["event"] == "profile:hz"
    assert result["cpu"]["ebpf_probes"] == ["vfs_read", "tcp_sendmsg"]
    assert result["cpu"]["probes"][0]["event"] == "vfs_read"
