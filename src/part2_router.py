# src/part2_router.py
from __future__ import annotations

def route_query(query: str) -> str:
    q = query.lower()

    csv_signals = ["revenue", "sales volume", "units sold", "units_sold", "region", "category", "december", "2024"]
    text_signals = ["features", "spec", "reviews", "customers say", "ease of cleaning", "clean"]
    both_signals = ["best customer reviews", "best reviews", "selling", "sells well", "highly rated", "recommend", "west region"]

    has_csv = any(s in q for s in csv_signals)
    has_text = any(s in q for s in text_signals)
    has_both = any(s in q for s in both_signals)

    if has_both or (has_csv and has_text):
        return "both"
    if has_csv:
        return "csv"
    if has_text:
        return "text"
    return "text"