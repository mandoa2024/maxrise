import pytest

from server.app.attribution import (
    deepseek_tools,
    deepseek_tool_choice,
    deterministic_report,
    detect_anomaly,
    execute_tool,
    verify_and_enrich_report,
)


COMPARISON = {
    "target_total_samples": 90,
    "baseline_total_samples": 50,
    "function_deltas": [
        {
            "evidence_id": "ev-function-parse",
            "source": "cpu",
            "function": "parse_payload",
            "target_self_percent": 55.556,
            "baseline_self_percent": 20,
            "delta_pp": 35.556,
            "ratio": 2.778,
            "target_samples": 50,
            "baseline_samples": 10,
        }
    ],
    "stack_deltas": [
        {
            "evidence_id": "ev-stack-parse",
            "source": "cpu",
            "frames": ["main", "handle_request", "parse_payload"],
            "target_percent": 55.556,
            "baseline_percent": 20,
            "delta_pp": 35.556,
            "target_samples": 50,
            "baseline_samples": 10,
        }
    ],
    "metric_deltas": [
        {
            "evidence_id": "ev-metric-rss",
            "metric": "rss_kb",
            "target": 200,
            "baseline": 100,
            "delta": 100,
            "ratio": 2,
        }
    ],
}

METADATA = {
    "target_type": "SEGMENT",
    "collector": "perf",
    "pid": 42,
    "baseline_count": 3,
}


def test_detect_anomaly_uses_deterministic_thresholds():
    anomaly = detect_anomaly(COMPARISON)

    assert anomaly["detected"] is True
    assert anomaly["cpu_detected"] is True
    assert anomaly["stack_detected"] is True
    assert anomaly["memory_detected"] is True


def test_detect_anomaly_can_trigger_on_call_path_only():
    comparison = {
        **COMPARISON,
        "function_deltas": [],
        "metric_deltas": [],
    }

    anomaly = detect_anomaly(comparison)
    report = deterministic_report(comparison, anomaly)

    assert anomaly["detected"] is True
    assert anomaly["stack_detected"] is True
    assert report["findings"][0]["category"] == "CALL_PATH_REGRESSION"


def test_attribution_tools_only_expose_scoped_comparison():
    result = execute_tool(
        "compare_profile_summary", {"limit": 1}, METADATA, COMPARISON
    )

    assert result["function_deltas"][0]["function"] == "parse_payload"
    assert result["stack_evidence_candidates"][0][
        "evidence_id"
    ] == "ev-stack-parse"


def test_deepseek_tools_use_chat_completions_shape():
    tools = deepseek_tools()

    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "get_profile_metadata"
    assert "name" not in tools[0]


def test_tool_argument_validation_is_enforced_locally():
    with pytest.raises(ValueError, match="between 1 and 20"):
        execute_tool(
            "compare_profile_summary",
            {"limit": 1000},
            METADATA,
            COMPARISON,
        )


def test_deepseek_thinking_uses_auto_tool_choice(monkeypatch):
    monkeypatch.setattr(
        "server.app.attribution.DEEPSEEK_THINKING", True
    )
    assert deepseek_tool_choice(True) == "auto"


def test_deterministic_report_is_enriched_with_verified_evidence():
    anomaly = detect_anomaly(COMPARISON)
    report = deterministic_report(COMPARISON, anomaly)

    enriched = verify_and_enrich_report(
        report, COMPARISON, METADATA
    )

    assert enriched["verification"]["verified"] is True
    assert enriched["findings"][0]["evidence"][0][
        "function"
    ] == "parse_payload"


def test_verifier_rejects_hallucinated_evidence():
    report = {
        "status": "SUPPORTED",
        "summary": "发现回归。",
        "findings": [
            {
                "category": "CPU_HOTSPOT_REGRESSION",
                "subject": "parse_payload",
                "claim": "CPU 占比上升。",
                "impact": "HIGH",
                "confidence": "HIGH",
                "evidence_ids": ["ev-not-produced-by-tools"],
                "recommendation": "检查实现。",
            }
        ],
        "limitations": [],
    }

    with pytest.raises(ValueError, match="unknown evidence"):
        verify_and_enrich_report(report, COMPARISON, METADATA)
