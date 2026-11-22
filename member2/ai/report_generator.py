"""Generate a readable report from Member 2's computed JSON results."""

import json
import os
from dotenv import load_dotenv
load_dotenv()
from typing import Any

from ai.prompts import SYSTEM_INSTRUCTIONS


def _number(value: Any, digits: int = 6) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}g}"
    return "not supplied"


def _local_report(result: dict) -> str:
    """Deterministic report used when no API key is configured or API is unavailable."""
    risk = result.get("risk_assessment", {})
    plan = result.get("manoeuvre_plan", {})
    anomalies = result.get("anomaly_details", [])

    conjunction = result.get("conjunction_input", {})
    cid = risk.get("conjunction_id") or conjunction.get("conjunction_id") or "Not supplied"
    level = risk.get("risk_level", "Not supplied")
    pc = risk.get("pc", risk.get("collision_probability", risk.get("Pc")))
    miss = conjunction.get("miss_distance_km", risk.get("miss_distance_km"))
    tca = conjunction.get("tca", risk.get("tca", "Not supplied"))
    relative_speed = conjunction.get("relative_speed_kms", risk.get("relative_speed_kms"))

    lines = [
        f"ORBI-SYNC RISK REPORT — {cid}",
        "=" * 52,
        "SITUATION",
        f"The current risk engine classified this encounter as {str(level).upper()}.",
        f"Predicted miss distance: {_number(miss)} km.",
        f"Calculated collision probability (Pc): {_number(pc)}.",
        f"Time of closest approach: {tca}.",
        f"Relative speed: {_number(relative_speed)} km/s.",
        "",
        "WHY IT MATTERS",
        "The risk label is based on the thresholds configured in this prototype. "
        "It is a screening result, not by itself an instruction to perform a burn.",
        "",
        "DATA-QUALITY NOTES",
    ]
    if anomalies:
        lines.extend([f"- {item}" for item in anomalies])
    else:
        lines.append("No anomaly flags were returned by the current checks.")

    lines.extend(["", "MANOEUVRE ASSESSMENT"])
    if plan:
        lines.append(f"Plan status: {plan.get('status', 'not supplied')}.")
        if plan.get("strategy"):
            lines.append(f"Selected strategy: {plan['strategy']}.")
        if plan.get("total_dv_ms") is not None:
            lines.append(f"Total delta-v: {_number(plan['total_dv_ms'])} m/s.")
        if plan.get("new_pc_after") is not None:
            lines.append(f"Predicted post-manoeuvre Pc: {_number(plan['new_pc_after'])}.")
        if plan.get("actions"):
            for action in plan["actions"]:
                lines.append(
                    f"Proposed action: {action.get('object_id', 'object not supplied')} "
                    f"with {action.get('dv_ms', 'unknown')} m/s {action.get('direction', 'unspecified')} burn."
                )
        if plan.get("reason"):
            lines.append(f"Planner note: {plan['reason']}")
    else:
        lines.append("No manoeuvre plan was supplied.")

    if result.get("evaluation_mode") == "synthetic_demo":
        lines.extend([
            "",
            "DEMO VALIDITY WARNING",
            "The manoeuvre evaluator used for this run is synthetic test data. "
            "The proposed burn and post-manoeuvre Pc are demonstrations of software "
            "wiring only, not physically valid orbital predictions.",
        ])

    lines.extend([
        "",
        "RECOMMENDED NEXT STEP",
        "Review the data quality and have the real orbital propagation and "
        "secondary-conjunction checks evaluate any candidate before considering execution.",
        "",
        "IMPORTANT LIMITATIONS",
        "This report summarizes software output; it does not independently validate "
        "the orbital physics. Any unvalidated evaluator output must not be treated as "
        "a real manoeuvre prediction. Human review and approval are required.",
    ])
    return "\n".join(lines)


def generate_ai_report(result: dict) -> dict:
    """Return {report, mode, model}. Uses a real LLM only when configured."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "report": _local_report(result),
            "mode": "local_fallback_no_api_key",
            "model": None,
        }

    try:
        from openai import OpenAI

        model = os.getenv("OPENAI_MODEL", "gpt-5.5")
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            instructions=SYSTEM_INSTRUCTIONS,
            input=(
                "Write a clear report from this Member 2 result. Preserve every "
                "numerical value exactly as supplied and clearly disclose limitations.\n\n"
                + json.dumps(result, indent=2, default=str)
            ),
        )
        text = (response.output_text or "").strip()
        if not text:
            raise RuntimeError("The AI model returned an empty report.")
        return {"report": text, "mode": "openai_api", "model": model}
    except Exception as exc:
        # Do not lose the engineering result if the external service is unavailable.
        return {
            "report": _local_report(result),
            "mode": "local_fallback_api_error",
            "model": os.getenv("OPENAI_MODEL", "gpt-5.5"),
            "error": f"{type(exc).__name__}: {exc}",
        }
