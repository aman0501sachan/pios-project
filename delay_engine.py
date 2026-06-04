from __future__ import annotations

import pandas as pd

from modules.risk_engine import calculate_spi, critical_path_delays, milestones_at_risk


def planned_vs_actual_summary(planning: pd.DataFrame) -> dict[str, float]:
    return {
        "planned_percent": round(float(planning["Planned %"].mean()), 1),
        "actual_percent": round(float(planning["Actual %"].mean()), 1),
        "spi": calculate_spi(planning),
        "variance_percent": round(float(planning["Actual %"].mean() - planning["Planned %"].mean()), 1),
    }


def lookahead_activities(planning: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    df = planning.copy()
    today = pd.Timestamp.today().normalize()
    df["Planned Start"] = pd.to_datetime(df["Planned Start"])
    df["Planned Finish"] = pd.to_datetime(df["Planned Finish"])
    window_end = today + pd.Timedelta(days=days)
    mask = (df["Actual Finish"].isna()) & (df["Planned Finish"] >= today) & (df["Planned Start"] <= window_end)
    cols = ["Activity ID", "Activity Name", "WBS", "Planned Start", "Planned Finish", "Planned %", "Actual %", "Float", "Critical Path Flag"]
    return df.loc[mask, cols].sort_values(["Critical Path Flag", "Planned Finish"], ascending=[False, True]).head(15)


def delay_narrative(planning: pd.DataFrame, milestones: pd.DataFrame, procurement: pd.DataFrame) -> str:
    summary = planned_vs_actual_summary(planning)
    cp = critical_path_delays(planning)
    ms = milestones_at_risk(milestones)
    delayed_proc = procurement[procurement["Status"].str.contains("Delayed", case=False, na=False)]
    reasons = []
    if summary["spi"] < 0.95:
        reasons.append(f"progress efficiency is weak with SPI at {summary['spi']}")
    if not cp.empty:
        top = cp.iloc[0]
        reasons.append(f"critical path activity '{top['Activity Name']}' is {top['Delta %']:.1f}% behind plan")
    if not delayed_proc.empty:
        reasons.append(f"{len(delayed_proc)} procurement items are delayed, including {delayed_proc.iloc[0]['Material']}")
    if not ms.empty:
        reasons.append(f"{len(ms)} milestones are forecast beyond planned dates")
    if not reasons:
        return "The project is broadly tracking to plan; current delays are localized and manageable through normal weekly controls."
    return "The project is delayed because " + "; ".join(reasons) + "."


def critical_path_risks(planning: pd.DataFrame, risks: pd.DataFrame) -> pd.DataFrame:
    cp = critical_path_delays(planning).head(10).copy()
    risk_keywords = ["Access", "ROW", "Material", "Design", "Subcontractor", "Approvals"]
    top_related = risks[risks["Description"].str.contains("|".join(risk_keywords), case=False, na=False)]
    cp["Likely Risk Driver"] = ", ".join(top_related.sort_values("Risk Score", ascending=False).head(3)["Risk ID"].tolist())
    return cp
