"""Shared Sage hours interpretation for tracking and portfolio totals."""
import json
import math


def sage_hours(raw):
    try:
        payload = json.loads(raw or "{}")
        for key, value in payload.items():
            if "heure" in key.casefold():
                number = float(str(value or 0).replace(" ", "").replace(",", "."))
                if math.isfinite(number) and number >= 0 and number:
                    return number
    except (ValueError, TypeError, AttributeError):
        pass
    return 0.0


def summarize(initial, consumed, reestimated=None):
    remaining = reestimated if reestimated is not None else max(0, initial - consumed)
    return {"initial_hours": round(initial, 2), "consumed_hours": round(consumed, 2),
            "raf": round(remaining, 2), "remaining_mode": "reestimated" if reestimated is not None else "budget_balance",
            "overrun_hours": round(max(0, consumed - initial), 2)}


def project_hours(project, cdc_hours, consumed):
    """Common operational budget precedence for portfolio, planning and cockpit."""
    return summarize(cdc_hours or project.tdao_budget_h or 0, consumed, project.remaining_hours)
