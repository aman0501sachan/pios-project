from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.delay_engine import critical_path_risks, lookahead_activities, planned_vs_actual_summary
from modules.executive_summary import answer_copilot, health_pack, pm_brief, recommended_actions
from modules.material_engine import critical_materials, enrich_inventory, inventory_kpis, vendor_performance
from modules.risk_engine import alert_rules, critical_path_delays, milestones_at_risk, top_risks


RAG_COLORS = {"Green": "#16a34a", "Amber": "#d97706", "Red": "#dc2626"}


def load_data(db_path: Path) -> dict[str, pd.DataFrame]:
    with sqlite3.connect(db_path) as conn:
        return {
            "planning": pd.read_sql("select * from planning_report", conn, parse_dates=["Planned Start", "Planned Finish", "Actual Start", "Actual Finish"]),
            "procurement": pd.read_sql("select * from procurement_report", conn, parse_dates=["PO Date", "Required On Site Date", "Delivery Date"]),
            "inventory": pd.read_sql("select * from store_inventory", conn, parse_dates=["Expiry Date"]),
            "contracts": pd.read_sql("select * from contracts_report", conn),
            "quality": pd.read_sql("select * from quality_report", conn),
            "risks": pd.read_sql("select * from risk_register", conn),
            "milestones": pd.read_sql("select * from milestone_register", conn, parse_dates=["Planned Date", "Forecast Date", "Actual Date"]),
        }


def rag_card(label: str, status: str, detail: str, score: float | None = None) -> None:
    color = RAG_COLORS.get(status, "#64748b")
    score_text = "" if score is None else f"<strong>{score}/100</strong><br/>"
    st.markdown(
        f"""
        <div class="rag-card" style="border-left: 6px solid {color}">
          <div class="rag-title">{label}</div>
          <div class="rag-status" style="color:{color}">{status}</div>
          <div class="rag-detail">{score_text}{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_shell() -> None:
    st.set_page_config(page_title="PIOS", page_icon="P", layout="wide")
    st.markdown(
        """
        <style>
        :root { --border:#d7dde8; --ink:#172033; --muted:#637083; --band:#f7f9fc; }
        .main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1440px; }
        h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
        .rag-card { background:#fff; border:1px solid var(--border); border-radius:8px; padding:14px 16px; min-height:132px; box-shadow:0 1px 2px rgba(16,24,40,.04); }
        .rag-title { color:var(--muted); font-size:13px; text-transform:uppercase; font-weight:700; }
        .rag-status { font-size:26px; font-weight:800; margin:4px 0; }
        .rag-detail { color:#334155; font-size:14px; line-height:1.35; }
        .brief { white-space:pre-wrap; background:#0f172a; color:#e2e8f0; padding:18px; border-radius:8px; line-height:1.45; }
        .alert { padding:10px 12px; border:1px solid var(--border); border-radius:8px; margin-bottom:8px; background:#fff; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Project Intelligence Operating System")
    st.caption("Metro Rail / EPC PM Copilot for schedule, cost, procurement, materials, contracts, quality, risks, and executive actions.")


def page_executive(data: dict[str, pd.DataFrame]) -> None:
    st.header("Executive Summary")
    scores = health_pack(data)
    cols = st.columns(4)
    for idx, score in enumerate(scores):
        with cols[idx % 4]:
            rag_card(score.area, score.status, score.reason, score.score)

    st.subheader("Active Alerts")
    alerts = alert_rules(data["planning"], data["inventory"], data["contracts"], data["quality"], data["milestones"])
    for alert in alerts[:12]:
        st.markdown(f"<div class='alert'><strong>{alert['Type']}</strong> · {alert['Severity']}<br>{alert['Message']}</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.subheader("One-Page PM Brief")
        st.markdown(f"<div class='brief'>{pm_brief(data)}</div>", unsafe_allow_html=True)
    with c2:
        st.subheader("Recommended Management Actions")
        for action in recommended_actions(data):
            st.write(f"- {action}")


def page_schedule(data: dict[str, pd.DataFrame]) -> None:
    st.header("Schedule Control")
    summary = planned_vs_actual_summary(data["planning"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planned %", f"{summary['planned_percent']}%")
    c2.metric("Actual %", f"{summary['actual_percent']}%", f"{summary['variance_percent']}%")
    c3.metric("SPI", summary["spi"])
    c4.metric("Critical Delays", len(critical_path_delays(data["planning"])))

    wbs = data["planning"].groupby("WBS", as_index=False)[["Planned %", "Actual %"]].mean()
    st.plotly_chart(px.bar(wbs, x="WBS", y=["Planned %", "Actual %"], barmode="group", title="Planned vs Actual Progress by WBS"), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Critical Activities")
        st.dataframe(data["planning"][data["planning"]["Critical Path Flag"] == "Yes"].sort_values("Float").head(15), use_container_width=True)
    with c2:
        st.subheader("Critical Path Delays")
        st.dataframe(critical_path_risks(data["planning"], data["risks"]), use_container_width=True)

    st.subheader("Milestones At Risk")
    st.dataframe(milestones_at_risk(data["milestones"]), use_container_width=True)
    st.subheader("30-Day Look Ahead Activities")
    st.dataframe(lookahead_activities(data["planning"]), use_container_width=True)


def page_procurement(data: dict[str, pd.DataFrame]) -> None:
    st.header("Procurement")
    proc = data["procurement"].copy()
    proc["Delay Days"] = (proc["Delivery Date"].fillna(pd.Timestamp.today().normalize()) - proc["Required On Site Date"]).dt.days.clip(lower=0)
    c1, c2, c3 = st.columns(3)
    c1.metric("Procurement Items", len(proc))
    c2.metric("Delayed Deliveries", int((proc["Delay Days"] > 0).sum()))
    c3.metric("Avg Lead Time", f"{proc['Lead Time'].mean():.0f} days")
    st.plotly_chart(px.bar(proc, x="Vendor", y="Lead Time", color="Status", title="Lead Time by Vendor and Status"), use_container_width=True)
    st.subheader("Delayed Deliveries")
    st.dataframe(proc[proc["Delay Days"] > 0].sort_values("Delay Days", ascending=False), use_container_width=True)
    st.subheader("Critical Materials")
    st.dataframe(critical_materials(proc, data["inventory"]), use_container_width=True)
    st.subheader("Vendor Performance")
    st.dataframe(vendor_performance(proc), use_container_width=True)


def page_inventory(data: dict[str, pd.DataFrame]) -> None:
    st.header("Inventory")
    inv = enrich_inventory(data["inventory"])
    kpis = inventory_kpis(inv)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Inventory Value", f"{kpis['inventory_value']:,.0f}")
    c2.metric("Stock-Out Risks", kpis["stockout_count"])
    c3.metric("Expiry Risks", kpis["expiry_risk_count"])
    c4.metric("Aged Items", kpis["aged_items"])
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.histogram(inv, x="Ageing Days", nbins=18, color="Movement Class", title="Ageing Analysis"), use_container_width=True)
    with c2:
        st.plotly_chart(px.scatter(inv, x="Stock Days", y="Days To Expiry", size="Current Stock", color="Movement Class", hover_name="Material", title="Stock-Out vs Expiry Risk"), use_container_width=True)
    st.subheader("Expiry Risk")
    st.dataframe(inv[inv["Days To Expiry"].between(0, 60)].sort_values("Days To Expiry"), use_container_width=True)
    st.subheader("Stock-Out Risk")
    st.dataframe(inv[inv["Stock Days"] < 30].sort_values("Stock Days"), use_container_width=True)


def page_contracts(data: dict[str, pd.DataFrame]) -> None:
    st.header("Contracts")
    contracts = data["contracts"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contract Value", f"{contracts['Project Value'].sum():,.0f}")
    c2.metric("NS Items", int(contracts["NS Items"].sum()))
    c3.metric("PV Items", int(contracts["PV Items"].sum()))
    c4.metric("EOT Pending", int(contracts["EOT Pending"].sum()))
    st.plotly_chart(px.bar(contracts, x="Contract Type", y=["Project Value", "Approved Variations"], barmode="group", title="Contract Value and Approved Variations"), use_container_width=True)
    st.dataframe(contracts, use_container_width=True)


def page_risks(data: dict[str, pd.DataFrame]) -> None:
    st.header("Risks")
    risks = data["risks"]
    st.subheader("Top 10 Risks")
    st.dataframe(top_risks(risks, 10), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.scatter(risks, x="Probability", y="Impact", size="Risk Score", color="Owner", hover_name="Risk ID", hover_data=["Description"], title="Risk Matrix")
        fig.update_layout(xaxis_range=[0, 6], yaxis_range=[0, 6])
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        trend = risks.groupby("Owner", as_index=False)["Risk Score"].sum().sort_values("Risk Score", ascending=False)
        st.plotly_chart(px.line(trend, x="Owner", y="Risk Score", markers=True, title="Risk Trend by Owner Portfolio"), use_container_width=True)


def page_copilot(data: dict[str, pd.DataFrame]) -> None:
    st.header("PM Copilot")
    question = st.text_input("Ask PIOS", value="What should management focus on this week?")
    st.info(answer_copilot(question, data))
    st.subheader("Suggested Questions")
    st.write("- Why is project delayed?")
    st.write("- What are top risks?")
    st.write("- Which milestones are at risk?")
    st.write("- What should management focus on this week?")
    st.download_button("Download PM Brief", data=pm_brief(data), file_name="pios_pm_brief.txt", mime="text/plain")


def render_app(db_path: Path) -> None:
    render_shell()
    data = load_data(db_path)
    pages = {
        "Executive Summary": page_executive,
        "Schedule Control": page_schedule,
        "Procurement": page_procurement,
        "Inventory": page_inventory,
        "Contracts": page_contracts,
        "Risks": page_risks,
        "PM Copilot": page_copilot,
    }
    page = st.sidebar.radio("PIOS Navigation", list(pages.keys()))
    st.sidebar.divider()
    st.sidebar.metric("Activities", len(data["planning"]))
    st.sidebar.metric("Procurement Items", len(data["procurement"]))
    st.sidebar.metric("Inventory Materials", len(data["inventory"]))
    pages[page](data)
