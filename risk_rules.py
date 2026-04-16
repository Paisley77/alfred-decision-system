"""Deterministic risk scoring - no LLM involved"""

ACTION_RISK = {
    "send_email": "low",
    "read_file": "low",
    "search_web": "low",
    "create_calendar_event": "low",
    "send_slack": "medium",
    "create_file": "medium",
    "post_tweet": "medium",
    "delete_file": "high",
    "read_screen": "high",
    "execute_command": "critical",
    "delete_everything": "critical"
}

SILENT_EXECUTION_THRESHOLD = "low"  # Only low-risk actions can be silent
CONFIRM_THRESHOLD = "medium"  # Medium+ risk requires confirmation

def get_risk(action_type):
    """Return risk level for an action"""
    return ACTION_RISK.get(action_type, "medium")

def requires_confirmation(risk_level, llm_verdict):
    """Override LLM decisions for high-risk actions"""
    if risk_level == "critical":
        return True, "refuse", "Action is critical and cannot be automated"
    if risk_level == "high" and llm_verdict in ["execute_silently", "execute_and_tell"]:
        return True, "confirm_before_execute", "High-risk action requires confirmation"
    if risk_level == "medium" and llm_verdict == "execute_silently":
        return True, "execute_and_tell", "Medium-risk action: telling user after execution"
    return False, llm_verdict, None