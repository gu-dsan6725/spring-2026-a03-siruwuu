def route_query(query: str) -> str:
    q = query.lower()

    csv_signals = [
        "total revenue", "revenue", "sales volume", "units_sold",
        "region", "category", "december", "oct", "nov", "2024",
        "highest", "total", "sum", "which region"
    ]
    text_signals = [
        "key features", "features", "spec", "specifications",
        "customers say", "reviews", "ease of cleaning", "clean"
    ]
    both_signals = [
        "best customer reviews", "best reviews", "selling",
        "highly rated", "sells well", "recommend", "west region"
    ]

    has_csv = any(s in q for s in csv_signals)
    has_text = any(s in q for s in text_signals)
    has_both = any(s in q for s in both_signals)

    # Forced both situation
    if has_both and (has_csv or has_text):
        return "both"

    if has_csv and has_text:
        return "both"
    if has_csv:
        return "csv"
    if has_text:
        return "text"

    return "text"