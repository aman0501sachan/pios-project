from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


RAG_ORDER = {"Green": 0, "Amber": 1, "Red": 2}


@dataclass(frozen=True)
class HealthScore:
    area: str
    status: str
    score: float
    reason: str


def rag_from_score(score: float) -> str:
    if score >= 75:
        return "Green"
    if score >= 50:
        return "Amber"
    return "Red"


def worst_rag(*statuses: str) -> str:
    return max(statuses, key=lambda status: RAG_ORDER.get(status, 0))


def calculate_spi(planning: pd.DataFrame) -> float:
    planned = planning["Planned %"].astype(float).clip(lower=0).sum()
    actual = planning["Actual %"].astype(float).clip(lower=0).sum()
    if planned == 0:
        return 1.0
    return round(float(actual / planned), 3)


def schedule_health(planning: pd.DataFrame, milestones: pd.DataFrame) -> HealthScore:
    spi = calculate_spi(planning)
    delayed_cp = critical_path_delays(planning)
    at_risk = milestones_at_risk(milestones)
    score = 100 - max(0, (0.98 - spi) * 180) - len(delayed_cp) * 2.2 - len(at_risk) * 1.5
    status = rag_from_score(max(0, score))
    return HealthScore("Schedule", status, round(max(0, score), 1), f"SPI {spi}; {len(delayed_cp)} delayed critical activities; {len(at_risk)} milestones at risk")


def procurement_health(procurement: pd.DataFrame) -> HealthScore:
    delayed = procurement[procurement["Status"].str.contains("Delayed", case=False, na=False)]
    pending_critical = procurement[
        procurement["Material"].str.contains("Rail|Fastening|Elastic Pad|MSS Pad|Clamp|Welding", case=False, na=False)
        & procurement["Delivery Date"].isna()
    ]
    score = 100 - len(delayed) * 3 - len(pending_critical) * 4
    return HealthScore("Procurement", rag_from_score(max(0, score)), round(max(0, score), 1), f"{len(delayed)} delayed deliveries; {len(pending_critical)} critical items not delivered")


def material_health(inventory: pd.DataFrame) -> HealthScore:
    stockout = stock_out_risk(inventory)
    expiry = expiry_risk(inventory)
    ageing = inventory[inventory["Ageing Days"] > 180]
    score = 100 - len(stockout) * 2.5 - len(expiry) * 1.8 - len(ageing) * 0.4
    return HealthScore("Material", rag_from_score(max(0, score)), round(max(0, score), 1), f"{len(stockout)} stock-out risks; {len(expiry)} expiry risks; {len(ageing)} aged items")


def contract_health(contracts: pd.DataFrame) -> HealthScore:
    eot_pending = int(contracts["EOT Pending"].sum())
    ld_risk = contracts["LD Status"].str.contains("At Risk|Notice", case=False, na=False).sum()
    ns_items = int(contracts["NS Items"].sum())
    score = 100 - eot_pending * 5 - ld_risk * 9 - ns_items * 0.4
    return HealthScore("Contracts", rag_from_score(max(0, score)), round(max(0, score), 1), f"{eot_pending} EOTs pending; {ld_risk} LD risk packages; {ns_items} NS items")


def quality_health(quality: pd.DataFrame) -> HealthScore:
    open_ncr = int(quality["Open NCR"].sum())
    open_rfi = int(quality["Open RFI"].sum())
    score = 100 - open_ncr * 3.5 - open_rfi * 0.7
    return HealthScore("Quality", rag_from_score(max(0, score)), round(max(0, score), 1), f"{open_ncr} open NCRs; {open_rfi} open RFIs")


def cost_health(contracts: pd.DataFrame) -> HealthScore:
    value = contracts["Project Value"].sum()
    changes = contracts["Approved Variations"].sum()
    change_pct = 0 if value == 0 else changes / value
    score = 100 - change_pct * 450 - contracts["PV Items"].sum() * 0.8
    return HealthScore("Cost", rag_from_score(max(0, score)), round(max(0, score), 1), f"Approved variations are {change_pct:.1%} of contract value")


def overall_health(scores: list[HealthScore]) -> HealthScore:
    avg = float(np.mean([score.score for score in scores])) if scores else 100
    status = rag_from_score(avg)
    worst = sorted(scores, key=lambda item: item.score)[0]
    return HealthScore("Overall", status, round(avg, 1), f"Weakest control area: {worst.area} ({worst.status})")


def critical_path_delays(planning: pd.DataFrame) -> pd.DataFrame:
    df = planning.copy()
    df["Delta %"] = df["Planned %"].astype(float) - df["Actual %"].astype(float)
    return df[(df["Critical Path Flag"] == "Yes") & (df["Delta %"] > 5)].sort_values("Delta %", ascending=False)


def milestones_at_risk(milestones: pd.DataFrame) -> pd.DataFrame:
    df = milestones.copy()
    df["Forecast Date"] = pd.to_datetime(df["Forecast Date"])
    df["Planned Date"] = pd.to_datetime(df["Planned Date"])
    df["Delay Days"] = (df["Forecast Date"] - df["Planned Date"]).dt.days
    return df[(df["Delay Days"] > 0) & (df["Status"] != "Completed")].sort_values("Delay Days", ascending=False)


def stock_out_risk(inventory: pd.DataFrame) -> pd.DataFrame:
    df = inventory.copy()
    df["Stock Days"] = np.where(df["Daily Consumption"] > 0, df["Current Stock"] / df["Daily Consumption"], np.inf)
    return df[(df["Stock Days"] < 30) | (df["Current Stock"] <= df["Reorder Level"])].sort_values("Stock Days")


def expiry_risk(inventory: pd.DataFrame) -> pd.DataFrame:
    df = inventory.copy()
    df["Expiry Date"] = pd.to_datetime(df["Expiry Date"])
    today = pd.Timestamp.today().normalize()
    df["Days To Expiry"] = (df["Expiry Date"] - today).dt.days
    return df[df["Days To Expiry"].between(0, 60)].sort_values("Days To Expiry")


def top_risks(risks: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return risks.sort_values(["Risk Score", "Impact", "Probability"], ascending=False).head(n)


def alert_rules(
    planning: pd.DataFrame,
    inventory: pd.DataFrame,
    contracts: pd.DataFrame,
    quality: pd.DataFrame,
    milestones: pd.DataFrame,
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    spi = calculate_spi(planning)
    if spi < 0.95:
        alerts.append({"Type": "Schedule Alert", "Severity": "Red", "Message": f"SPI is {spi}, below the 0.95 threshold."})
    for _, row in stock_out_risk(inventory).head(8).iterrows():
        alerts.append({"Type": "Material Alert", "Severity": "Amber", "Message": f"{row['Material']} has {row['Stock Days']:.1f} stock days remaining."})
    eot_pending = int(contracts["EOT Pending"].sum())
    if eot_pending > 0:
        alerts.append({"Type": "Contract Alert", "Severity": "Amber", "Message": f"{eot_pending} EOT submissions are pending approval."})
    open_ncr = int(quality["Open NCR"].sum())
    if open_ncr > 10:
        alerts.append({"Type": "Quality Alert", "Severity": "Amber", "Message": f"{open_ncr} NCRs remain open across inspection lots."})
    for _, row in milestones_at_risk(milestones).head(8).iterrows():
        alerts.append({"Type": "Milestone Alert", "Severity": "Red" if row["Delay Days"] > 30 else "Amber", "Message": f"{row['Milestone']} forecast slips by {int(row['Delay Days'])} days."})
    return alerts
