import pytest

from server.app.state import validate_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("PENDING", "RUNNING"),
        ("PENDING", "FAILED"),
        ("RUNNING", "UPLOADING"),
        ("RUNNING", "FAILED"),
        ("UPLOADING", "DONE"),
        ("UPLOADING", "FAILED"),
    ],
)
def test_valid_transitions(current, target):
    validate_transition(current, target, "test reason")


def test_rejects_empty_reason():
    with pytest.raises(ValueError, match="reason"):
        validate_transition("PENDING", "RUNNING", " ")


def test_rejects_invalid_transition():
    with pytest.raises(ValueError, match="invalid"):
        validate_transition("PENDING", "DONE", "skip states")

