VALID_TRANSITIONS = {
    "PENDING": {"RUNNING", "FAILED"},
    "RUNNING": {"UPLOADING", "FAILED"},
    "UPLOADING": {"DONE", "FAILED"},
    "DONE": set(),
    "FAILED": set(),
}


def validate_transition(current: str, target: str, reason: str) -> None:
    if not reason or not reason.strip():
        raise ValueError("status transition reason must not be empty")
    if target not in VALID_TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid status transition: {current} -> {target}")

