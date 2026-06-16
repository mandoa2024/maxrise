import pytest

from analyzer.parser import collapsed_to_tree, parse_collapsed_line, top_functions
from analyzer.main import analyze, AnalyzeRequest


SAMPLES = "main;api;parse 5\nmain;api;query 3\nmain;worker;flush 2"


def test_collapsed_to_tree_counts_samples():
    tree = collapsed_to_tree(SAMPLES)
    assert tree["value"] == 10
    assert tree["children"][0]["name"] == "main"
    assert tree["children"][0]["value"] == 10


def test_top_functions_uses_leaf_frames():
    assert top_functions(SAMPLES) == [
        {"name": "parse", "samples": 5},
        {"name": "query", "samples": 3},
        {"name": "flush", "samples": 2},
    ]


def test_invalid_collapsed_line():
    with pytest.raises(ValueError):
        parse_collapsed_line("missing-count")


def test_analyze_includes_uploaded_metrics():
    result = analyze(AnalyzeRequest(
        task_id="task-1",
        collapsed_stacks=SAMPLES,
        performance_data={"memory": {"rss_kb": 1234}},
    ))

    assert result["metrics"]["memory"]["rss_kb"] == 1234
