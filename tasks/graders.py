def grade_action(task_id: str, action: str, signals: dict) -> float:
    """Grade the agent's action and return reward in [0.0, 1.0] range."""
    ideal = signals.get("ideal_action", "approve")

    if action.lower() == ideal.lower():
        return 1.0

    if ideal == "approve":
        if action.lower() == "flag":
            return 0.3
        return 0.0

    if ideal == "reject":
        if action.lower() == "flag":
            return 0.5
        return 0.0

    if ideal == "flag":
        if action.lower() == "reject":
            return 0.7
        if action.lower() == "approve":
            return 0.0
        return 0.5

    return 0.0
