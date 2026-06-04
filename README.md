# Project Intelligence Operating System (PIOS)

PIOS is a runnable Streamlit PM Copilot for metro rail, EPC, infrastructure, and construction project controls.

It includes realistic dummy data, Excel source reports, a SQLite database, executive health scoring, schedule and material risk engines, contract and quality alerts, and a PM Copilot page that answers management questions from project data.

## Run

```bash
cd PIOS
pip install -r requirements.txt
streamlit run app.py
```

## Included Reports

- `data/planning_report.xlsx` with 60 Primavera-style activities
- `data/milestone_register.xlsx` with 24 milestones
- `data/procurement_report.xlsx` with 48 procurement items
- `data/store_inventory.xlsx` with 120 materials
- `data/contracts_report.xlsx` with metro EPC contract packages
- `data/quality_report.xlsx` with inspection, RFI, and NCR data
- `data/risk_register.xlsx` with 36 project risks
- `database/pios.db` with the same data loaded into SQLite

## Pages

1. Executive Summary
2. Schedule Control
3. Procurement
4. Inventory
5. Contracts
6. Risks
7. PM Copilot

## Alert Rules

- SPI below `0.95` creates a schedule alert
- Stock days below `30` creates a material alert
- Pending EOTs create a contract alert
- Open NCRs above threshold create a quality alert
- Forecast milestone slippage creates milestone alerts

## PM Copilot Examples

Ask:

- Why is project delayed?
- What are top risks?
- Which milestones are at risk?
- What should management focus on this week?
