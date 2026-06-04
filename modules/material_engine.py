from __future__ import annotations

import numpy as np
import pandas as pd


def enrich_inventory(inventory: pd.DataFrame) -> pd.DataFrame:
    df = inventory.copy()
    df["Stock Days"] = np.where(df["Daily Consumption"] > 0, df["Current Stock"] / df["Daily Consumption"], np.inf)
    df["Expiry Date"] = pd.to_datetime(df["Expiry Date"])
    today = pd.Timestamp.today().normalize()
    df["Days To Expiry"] = (df["Expiry Date"] - today).dt.days
    df["Movement Class"] = pd.cut(
        df["Daily Consumption"],
        bins=[-0.1, 0, 8, 999999],
        labels=["Non Moving", "Slow Moving", "Fast Moving"],
    ).astype(str)
    df["Estimated Value"] = (df["Current Stock"] * (25 + (df.index % 17) * 9)).round(0)
    return df


def inventory_kpis(inventory: pd.DataFrame) -> dict[str, float]:
    df = enrich_inventory(inventory)
    return {
        "inventory_value": float(df["Estimated Value"].sum()),
        "stockout_count": int((df["Stock Days"] < 30).sum()),
        "expiry_risk_count": int(df["Days To Expiry"].between(0, 60).sum()),
        "aged_items": int((df["Ageing Days"] > 180).sum()),
    }


def critical_materials(procurement: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    inv = enrich_inventory(inventory)
    stock_risk = inv[inv["Stock Days"] < 45][["Material", "Current Stock", "Stock Days"]]
    delayed = procurement[procurement["Status"].str.contains("Delayed|In Transit|PO Released", case=False, na=False)]
    merged = delayed.merge(stock_risk, on="Material", how="left")
    return merged.sort_values(["Status", "Required On Site Date"]).head(15)


def vendor_performance(procurement: pd.DataFrame) -> pd.DataFrame:
    df = procurement.copy()
    df["PO Date"] = pd.to_datetime(df["PO Date"])
    df["Required On Site Date"] = pd.to_datetime(df["Required On Site Date"])
    df["Delivery Date"] = pd.to_datetime(df["Delivery Date"])
    df["Delay Days"] = (df["Delivery Date"].fillna(pd.Timestamp.today().normalize()) - df["Required On Site Date"]).dt.days.clip(lower=0)
    return (
        df.groupby("Vendor", as_index=False)
        .agg(Items=("Material", "count"), Delayed=("Delay Days", lambda s: int((s > 0).sum())), Avg_Delay_Days=("Delay Days", "mean"))
        .assign(On_Time_Rate=lambda frame: ((frame["Items"] - frame["Delayed"]) / frame["Items"] * 100).round(1))
        .sort_values(["On_Time_Rate", "Avg_Delay_Days"])
    )
