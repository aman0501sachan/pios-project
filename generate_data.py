from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


np.random.seed(42)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "database" / "pios.db"
TODAY = pd.Timestamp.today().normalize()


def date(days: int) -> pd.Timestamp:
    return TODAY + pd.Timedelta(days=days)


def planning_report() -> pd.DataFrame:
    names = [
        "Topographical Survey", "Utility Mapping", "Setting Out", "Access Road Preparation",
        "Depot Earthwork", "Depot Drainage", "Shuttering for Plinth", "Rebar Fixing",
        "Concreting Track Plinth", "Ballastless Track Survey", "Ballastless Track Bed Preparation",
        "Ballastless Track Concreting", "Fastening System Installation", "Elastic Pad Placement",
        "MSS Pad Placement", "Rail Unloading", "Rail Flash Butt Welding", "Rail Destressing",
        "Track Linking", "Turnout Assembly", "Turnout Welding", "Cable Tray Installation",
        "OHE Mast Foundation", "OHE Mast Erection", "Signalling Cable Pulling", "Axle Counter Installation",
        "Platform Edge Interface", "Depot Track Linking", "Depot Inspection Pit Track",
        "Third Rail Interface Check", "FBW Welding", "Thermit Welding", "Ultrasonic Rail Testing",
        "Track Geometry Measurement", "Walkway Concreting", "Emergency Walkway Handrail",
        "Tunnel Cleaning", "Waterproofing Repairs", "Systems Integration Test", "Power Energisation",
        "Static Testing", "Dynamic Testing", "Trial Run Preparation", "Trial Run",
        "Commissioning Documentation", "Safety Certification Support", "Punch List Closure",
        "As Built Survey", "Depot Commissioning", "Mainline Commissioning",
    ]
    wbs_list = [
        "Survey", "Access", "Depot Work", "Civil Plinth", "Ballastless Track",
        "Track Linking", "FBW Welding", "Systems", "Testing", "Commissioning",
    ]
    rows = []
    for i in range(60):
        start_offset = -160 + i * 5
        duration = int(np.random.choice([14, 18, 21, 28, 35, 42]))
        planned_start = date(start_offset)
        planned_finish = planned_start + pd.Timedelta(days=duration)
        planned_pct = min(100, max(15, 55 + i * 1.2 + np.random.normal(0, 10)))
        delay_factor = np.random.choice([0, 4, 8, 12, 18, 25], p=[0.25, 0.2, 0.2, 0.15, 0.12, 0.08])
        actual_pct = max(0, min(100, planned_pct - delay_factor - np.random.normal(1, 5)))
        actual_start = planned_start + pd.Timedelta(days=int(np.random.choice([0, 0, 2, 5, 8])))
        actual_finish = pd.NaT
        if actual_pct >= 99:
            actual_finish = planned_finish + pd.Timedelta(days=int(np.random.choice([-2, 0, 3, 8, 15])))
        critical = "Yes" if i % 4 == 0 or any(key in names[i % len(names)] for key in ["Track Linking", "FBW", "Testing", "Commissioning"]) else "No"
        float_days = int(np.random.choice([0, 0, 2, 5, 9, 14, 21]) if critical == "Yes" else np.random.randint(8, 36))
        rows.append(
            {
                "Activity ID": f"BLT-{1000 + i}",
                "Activity Name": names[i % len(names)] + (f" Zone {1 + i // 15}" if i >= len(names) else ""),
                "WBS": wbs_list[i % len(wbs_list)],
                "Planned Start": planned_start,
                "Planned Finish": planned_finish,
                "Actual Start": actual_start if actual_pct > 5 else pd.NaT,
                "Actual Finish": actual_finish,
                "Planned %": round(planned_pct, 1),
                "Actual %": round(actual_pct, 1),
                "Float": float_days,
                "Critical Path Flag": critical,
            }
        )
    return pd.DataFrame(rows)


def milestone_register() -> pd.DataFrame:
    owners = ["Planning", "Track", "Systems", "Depot", "QA/QC", "Client", "Contracts"]
    milestones = [
        "Depot access handed over", "Viaduct civil front released", "Survey control accepted",
        "First ballastless track plinth complete", "Rail delivery lot 1 on site", "Fastening system lot 1 on site",
        "First FBW weld accepted", "Track linking Ch 0-2 km complete", "Track linking Ch 2-5 km complete",
        "Depot track slab complete", "Turnout 1 commissioned", "OHE interface ready",
        "Signalling cable route clear", "Mainline track geometry approved", "Ultrasonic testing complete",
        "Power energisation permit", "Static testing start", "Dynamic testing start",
        "Trial run start", "Safety certification package submitted", "Punch list below threshold",
        "Depot commissioning complete", "Mainline commissioning complete", "Revenue readiness certificate",
    ]
    rows = []
    for i, name in enumerate(milestones):
        planned = date(-90 + i * 14)
        slip = int(np.random.choice([0, 0, 7, 14, 21, 35, 48], p=[0.22, 0.18, 0.16, 0.17, 0.13, 0.1, 0.04]))
        actual = planned + pd.Timedelta(days=int(np.random.choice([-3, 0, 5, 10]))) if i < 6 else pd.NaT
        status = "Completed" if pd.notna(actual) else ("At Risk" if slip > 0 else "On Track")
        rows.append({"Milestone": name, "Planned Date": planned, "Forecast Date": planned + pd.Timedelta(days=slip), "Actual Date": actual, "Owner": owners[i % len(owners)], "Status": status})
    return pd.DataFrame(rows)


def procurement_report() -> pd.DataFrame:
    materials = [
        "Elastic Pad", "MSS Pad", "Tension Clamp", "UIC 60 Rails", "Fastening System",
        "Welding Consumables", "Base Plate", "Insulated Joint", "Turnout Bearer", "Check Rail",
        "Cable Tray", "OHE Mast", "Signalling Cable", "Axle Counter", "Rail Lubricator", "Grout",
    ]
    vendors = ["RailTech India", "MetroFast Systems", "Global Track GmbH", "Shenzhen Rail Parts", "Nippon Weld", "InfraBuild UAE", "Saini Engineering", "Korea Transit Supply"]
    countries = ["India", "Germany", "China", "Japan", "UAE", "South Korea"]
    rows = []
    for i in range(48):
        material = materials[i % len(materials)]
        lead = int(np.random.choice([35, 45, 60, 75, 90, 120]))
        po = date(-120 + i * 3)
        ros = po + pd.Timedelta(days=lead - int(np.random.choice([5, 0, -10, -20])))
        delay = int(np.random.choice([-8, 0, 5, 14, 28, 42], p=[0.12, 0.28, 0.18, 0.18, 0.16, 0.08]))
        delivery = ros + pd.Timedelta(days=delay) if np.random.rand() > 0.18 else pd.NaT
        status = "Delivered"
        if pd.isna(delivery):
            status = "Delayed - Not Delivered" if ros < TODAY else "PO Released"
        elif delay > 0:
            status = "Delayed - Delivered"
        elif delivery > TODAY:
            status = "In Transit"
        rows.append({"Material": material, "Vendor": vendors[i % len(vendors)], "Country": countries[i % len(countries)], "Lead Time": lead, "PO Date": po, "Required On Site Date": ros, "Delivery Date": delivery, "Status": status})
    return pd.DataFrame(rows)


def store_inventory() -> pd.DataFrame:
    base = ["Elastic Pad", "MSS Pad", "Tension Clamp", "UIC 60 Rails", "Fastening System", "Welding Consumables", "Base Plate", "Grout", "Anchor Bolt", "Cable Lug", "Epoxy", "Primer", "Paint", "Rail Clip", "Washer", "Sleeper Insert", "Drain Cover", "Conduit", "Sealant", "Bearing Plate"]
    rows = []
    for i in range(120):
        material = f"{base[i % len(base)]} {1 + i // len(base)}"
        movement = np.random.choice(["Fast Moving", "Slow Moving", "Non Moving"], p=[0.45, 0.38, 0.17])
        daily = {"Fast Moving": np.random.randint(9, 45), "Slow Moving": np.random.randint(1, 8), "Non Moving": 0}[movement]
        stock = int(np.random.randint(20, 1800) if daily else np.random.randint(50, 900))
        if i % 11 == 0 and daily:
            stock = int(daily * np.random.randint(8, 25))
        reorder = int(max(20, daily * np.random.randint(25, 55)))
        lead = int(np.random.choice([21, 30, 45, 60, 75, 90]))
        ageing = int(np.random.choice([15, 30, 45, 75, 120, 180, 240, 365]))
        expiry = date(int(np.random.choice([20, 35, 55, 90, 180, 365, 540])))
        rows.append({"Material": material, "Current Stock": stock, "Daily Consumption": daily, "Reorder Level": reorder, "Lead Time": lead, "Ageing Days": ageing, "Expiry Date": expiry})
    for idx, exact in enumerate(["Elastic Pad", "MSS Pad", "Tension Clamp", "UIC 60 Rails", "Fastening System", "Welding Consumables"]):
        rows[idx]["Material"] = exact
    return pd.DataFrame(rows)


def contracts_report() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Contract Type": "Main Civil and Track EPC", "Project Value": 18500000000, "Approved Variations": 740000000, "NS Items": 18, "PV Items": 12, "EOT Submitted": 4, "EOT Approved": 1, "EOT Pending": 3, "LD Status": "At Risk"},
            {"Contract Type": "Systems Interface Package", "Project Value": 4200000000, "Approved Variations": 115000000, "NS Items": 7, "PV Items": 5, "EOT Submitted": 2, "EOT Approved": 1, "EOT Pending": 1, "LD Status": "Watch"},
            {"Contract Type": "Depot Works", "Project Value": 3100000000, "Approved Variations": 210000000, "NS Items": 11, "PV Items": 9, "EOT Submitted": 3, "EOT Approved": 2, "EOT Pending": 1, "LD Status": "Notice Issued"},
            {"Contract Type": "OHE and Power", "Project Value": 2800000000, "Approved Variations": 95000000, "NS Items": 5, "PV Items": 4, "EOT Submitted": 1, "EOT Approved": 1, "EOT Pending": 0, "LD Status": "No LD"},
            {"Contract Type": "Signalling and Telecom", "Project Value": 3600000000, "Approved Variations": 175000000, "NS Items": 9, "PV Items": 6, "EOT Submitted": 2, "EOT Approved": 0, "EOT Pending": 2, "LD Status": "At Risk"},
        ]
    )


def quality_report() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Open RFI": 14, "Closed RFI": 126, "Open NCR": 5, "Closed NCR": 42, "Inspection Status": "Track plinth inspections ongoing; welding NCR ageing visible"},
            {"Open RFI": 9, "Closed RFI": 88, "Open NCR": 3, "Closed NCR": 31, "Inspection Status": "Depot works inspections acceptable with minor shuttering observations"},
            {"Open RFI": 11, "Closed RFI": 74, "Open NCR": 4, "Closed NCR": 28, "Inspection Status": "Material inspection reports pending for fastening lot 3"},
            {"Open RFI": 6, "Closed RFI": 63, "Open NCR": 2, "Closed NCR": 19, "Inspection Status": "Systems installation quality stable"},
        ]
    )


def risk_register() -> pd.DataFrame:
    topics = [
        "Access Delay at depot interface", "ROW Delay near station approach", "Material Delay for fastening system", "Design Delay on plinth interface",
        "Subcontractor Performance below baseline", "Weather disruption to concreting", "Client approvals cycle exceeds SLA", "Utility diversion obstruction",
        "Rail delivery customs hold", "FBW machine availability", "NCR recurrence in welding", "Testing slot conflict with systems contractor",
    ]
    owners = ["Project Manager", "Planning Engineer", "Contracts Engineer", "Procurement Lead", "QA/QC Manager", "Construction Manager", "Client Interface"]
    mitigations = [
        "Daily constraint log and escalation to corridor director",
        "Expedite approval package with decision due dates",
        "Alternative vendor and buffer stock review",
        "Recovery schedule with resequenced work fronts",
        "Dedicated task force with weekly PMO review",
    ]
    rows = []
    for i in range(36):
        prob = int(np.random.choice([2, 3, 4, 5], p=[0.12, 0.34, 0.34, 0.2]))
        impact = int(np.random.choice([2, 3, 4, 5], p=[0.1, 0.28, 0.37, 0.25]))
        rows.append({"Risk ID": f"R-{i + 1:03d}", "Description": topics[i % len(topics)], "Probability": prob, "Impact": impact, "Risk Score": prob * impact, "Owner": owners[i % len(owners)], "Mitigation": mitigations[i % len(mitigations)]})
    return pd.DataFrame(rows)


def write_all() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    frames = {
        "planning_report": planning_report(),
        "procurement_report": procurement_report(),
        "store_inventory": store_inventory(),
        "contracts_report": contracts_report(),
        "quality_report": quality_report(),
        "risk_register": risk_register(),
        "milestone_register": milestone_register(),
    }
    for name, frame in frames.items():
        frame.to_excel(DATA_DIR / f"{name}.xlsx", index=False)
    with sqlite3.connect(DB_PATH) as conn:
        for name, frame in frames.items():
            frame.to_sql(name, conn, index=False, if_exists="replace")


if __name__ == "__main__":
    write_all()
