from __future__ import annotations

import pandas as pd

from modules.delay_engine import delay_narrative
from modules.risk_engine import (
    alert_rules,
    contract_health,
    cost_health,
    material_health,
    milestones_at_risk,
    overall_health,
    procurement_health,
    quality_health,
    schedule_health,
    top_risks,
)


def health_pack(data: dict[str, pd.DataFrame]) -> list:
    scores = [
        schedule_health(data["planning"], data["milestones"]),
        cost_health(data["contracts"]),
        procurement_health(data["procurement"]),
        material_health(data["inventory"]),
        quality_health(data["quality"]),
        contract_health(data["contracts"]),
    ]
    return [overall_health(scores), *scores]


def recommended_actions(data: dict[str, pd.DataFrame]) -> list[str]:
    ms = milestones_at_risk(data["milestones"]).head(5)
    risks = top_risks(data["risks"], 5)
    delayed_proc = data["procurement"][data["procurement"]["Status"].str.contains("Delayed", case=False, na=False)].head(5)
    actions = [
        "Hold a weekly critical path recovery meeting focused on access, design approvals, rail welding fronts, and commissioning dependencies.",
        "Freeze a 30-day material expediting list and assign vendor-level owners for delayed rail, fastening, pad, and welding consumable deliveries.",
        "Close pending EOT substantiation gaps with daily document sprints covering delay notices, impacted activities, and contemporaneous records.",
        "Prioritize NCR closure for work lots blocking testing and handover; escalate recurring quality failure modes to construction leadership.",
        "Rebaseline only after recovery options are exhausted and board-approved mitigation owners are locked for every Red risk.",
    ]
    if not ms.empty:
        actions.insert(0, f"Protect milestone '{ms.iloc[0]['Milestone']}' through resequencing, double shifts, and constraint removal.")
    if not risks.empty:
        actions.insert(1, f"Treat '{risks.iloc[0]['Description']}' as the top PMO escalation item this week.")
    if not delayed_proc.empty:
        actions.insert(2, f"Expedite {delayed_proc.iloc[0]['Material']} from {delayed_proc.iloc[0]['Vendor']} with daily logistics tracking.")
    return actions[:7]


def pm_brief(data: dict[str, pd.DataFrame]) -> str:
    scores = health_pack(data)
    alerts = alert_rules(data["planning"], data["inventory"], data["contracts"], data["quality"], data["milestones"])
    risks = top_risks(data["risks"], 5)
    milestones = milestones_at_risk(data["milestones"]).head(5)
    actions = recommended_actions(data)[:5]
    top_issues = [alert["Message"] for alert in alerts[:5]]
    if len(top_issues) < 5:
        top_issues.extend([
            "Critical path productivity requires closer daily measurement.",
            "Procurement lead-time exposure remains high for specialist track materials.",
            "Open contractual decisions may affect entitlement protection.",
        ])
    lines = [
        "PROJECT DIRECTOR 60-SECOND PM BRIEF",
        "",
        f"Project Health: {scores[0].status} ({scores[0].score}/100). {scores[0].reason}.",
        "",
        "Top 5 Issues:",
        *[f"- {issue}" for issue in top_issues[:5]],
        "",
        "Top 5 Risks:",
        *[f"- {row['Risk ID']}: {row['Description']} (score {row['Risk Score']})" for _, row in risks.iterrows()],
        "",
        "Milestones At Risk:",
        *[f"- {row['Milestone']} forecast {int(row['Delay Days'])} days late; owner {row['Owner']}" for _, row in milestones.iterrows()],
        "",
        "Management Attention Areas:",
        "- Critical path fronts, specialist material expediting, EOT entitlement closure, NCR ageing, and owner approval cycles.",
        "",
        "Recommended Actions:",
        *[f"- {action}" for action in actions],
        "",
        "Copilot View:",
        f"- {delay_narrative(data['planning'], data['milestones'], data['procurement'])}",
    ]
    return "\n".join(lines)


def answer_copilot(question: str, data: dict[str, pd.DataFrame]) -> str:
    q = question.lower().strip()
    if not q:
        return "Ask about delays, risks, milestones, procurement, inventory, contracts, quality, or this week's management focus."
    if "delay" in q or "delayed" in q or "behind" in q:
        return delay_narrative(data["planning"], data["milestones"], data["procurement"]) + " Recommended response: protect critical path access, expedite specialist materials, and remove approval blockers within the next weekly cycle."
    if "risk" in q:
        risks = top_risks(data["risks"], 5)
        return "Top risks are: " + "; ".join([f"{r['Risk ID']} {r['Description']} (score {r['Risk Score']})" for _, r in risks.iterrows()]) + "."
    if "milestone" in q:
        ms = milestones_at_risk(data["milestones"]).head(5)
        if ms.empty:
            return "No active milestone is forecast beyond its planned date."
        return "Milestones at risk: " + "; ".join([f"{r['Milestone']} by {int(r['Delay Days'])} days, owner {r['Owner']}" for _, r in ms.iterrows()]) + "."
    if "management" in q or "focus" in q or "week" in q or "action" in q:
        return "This week management should focus on: " + "; ".join(recommended_actions(data)[:5])
    if "procurement" in q or "vendor" in q or "delivery" in q:
        delayed = data["procurement"][data["procurement"]["Status"].str.contains("Delayed", case=False, na=False)].head(5)
        return "Procurement attention: " + "; ".join([f"{r['Material']} from {r['Vendor']} required {pd.to_datetime(r['Required On Site Date']).date()}" for _, r in delayed.iterrows()]) + "."
    if "inventory" in q or "stock" in q or "material" in q:
        from modules.risk_engine import stock_out_risk

        stock = stock_out_risk(data["inventory"]).head(5)
        return "Material stock-out risks: " + "; ".join([f"{r['Material']} has {r['Stock Days']:.1f} stock days" for _, r in stock.iterrows()]) + "."
    return pm_brief(data)
