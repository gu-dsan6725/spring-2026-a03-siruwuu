from pathlib import Path
import pandas as pd

DATA_CSV = Path("data/structured/daily_sales.csv")

def load_sales_df() -> pd.DataFrame:
    df = pd.read_csv(DATA_CSV)
    df["date"] = pd.to_datetime(df["date"])
    return df

def total_revenue_for_category_in_month(df: pd.DataFrame, category: str, year: int, month: int) -> float:
    mask = (df["category"] == category) & (df["date"].dt.year == year) & (df["date"].dt.month == month)
    return float(df.loc[mask, "total_revenue"].sum())

def top_region_by_units(df: pd.DataFrame) -> tuple[str, int]:
    g = df.groupby("region")["units_sold"].sum().sort_values(ascending=False)
    return str(g.index[0]), int(g.iloc[0])

def product_sales_summary(df: pd.DataFrame, product_id: str, region: str | None = None) -> dict:
    sub = df[df["product_id"] == product_id]
    if region:
        sub = sub[sub["region"] == region]

    return {
        "product_id": product_id,
        "region": region or "ALL",
        "units_sold": int(sub["units_sold"].sum()),
        "total_revenue": float(sub["total_revenue"].sum()),
    }