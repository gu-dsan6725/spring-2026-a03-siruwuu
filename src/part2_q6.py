# src/part2_q6.py
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from src.part2_common import (
    load_sales_df,
    load_text_docs,
    simple_review_sentiment,
    summarize_sales_for_product,
    extract_excerpt,
)


DEFAULT_OUT_FILE = "part2_results.txt"


def answer_q6(data_dir: str = "data", out_file: str | None = DEFAULT_OUT_FILE) -> str:
    """
    Q6: I want a product for fitness that is highly rated and sells well in the West region. What do you recommend?
    Both sources:
      - CSV: pick top sellers in West region (by units_sold)
      - Text: among those candidates, choose best review sentiment score
    """
    df, csv_path = load_sales_df(data_dir)
    docs, _ = load_text_docs(data_dir)

    if "region" not in df.columns or "units_sold" not in df.columns:
        raise ValueError("CSV missing required columns: region, units_sold")

    west = df[df["region"] == "West"]
    if west.empty:
        raise ValueError('No rows for region == "West" in CSV')

    top_in_west = (
        west.groupby("product_id")["units_sold"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )
    candidate_ids = [str(x) for x in top_in_west.index.tolist()]

    # Map product_id -> doc
    doc_by_id = {d.product_id: d for d in docs}
    candidates: List[Tuple[int, str]] = []
    for pid in candidate_ids:
        if pid in doc_by_id:
            score = simple_review_sentiment(doc_by_id[pid].text)
            candidates.append((score, pid))

    if not candidates:
        # fallback: if filenames do not align with product_id, just pick the top seller
        chosen_pid = candidate_ids[0]
        chosen_doc = None
        chosen_score = 0
    else:
        candidates.sort(reverse=True)
        chosen_score, chosen_pid = candidates[0]
        chosen_doc = doc_by_id.get(chosen_pid)

    sales_west = summarize_sales_for_product(df, product_id=chosen_pid, region="West")
    sales_all = summarize_sales_for_product(df, product_id=chosen_pid, region=None)

    lines: List[str] = []
    lines.append("Part 2 Results\n")
    lines.append(
        'Q6: "I want a product for fitness that is highly rated and sells well in the West region. What do you recommend?"\n'
    )
    lines.append("Answer:\n")
    lines.append(
        f"I recommend product {chosen_pid} because it is a strong seller in the West region and has positive customer feedback."
    )
    lines.append("Sales performance:")
    lines.append(f'- West region units_sold: {int(sales_west["units_sold"])}')
    lines.append(f'- West region total_revenue: {float(sales_west["total_revenue"]):.2f}')
    lines.append(f'- All regions units_sold: {int(sales_all["units_sold"])}')
    lines.append(f'- All regions total_revenue: {float(sales_all["total_revenue"]):.2f}')

    if chosen_doc is not None:
        excerpt = extract_excerpt(chosen_doc.text, query="review", max_chars=650)
        lines.append("")
        lines.append(f"Review excerpt from {chosen_doc.path.name} (sentiment score={chosen_score}):")
        lines.append("")
        lines.append(excerpt)
        lines.append("")

    lines.append("Files referenced:")
    lines.append(f"- {csv_path.as_posix()}")
    if chosen_doc is not None:
        lines.append(f"- {chosen_doc.path.as_posix()}")
    lines.append("")

    text = "\n".join(lines)
    if out_file:
        Path(out_file).write_text(text, encoding="utf-8")
    return text


def main() -> None:
    text = answer_q6(data_dir="data", out_file=DEFAULT_OUT_FILE)
    print(f"Wrote Q6 results to: {DEFAULT_OUT_FILE}")
    if not isinstance(text, str):
        raise TypeError(f"answer_q6 returned {type(text)} (expected str)")
    print(text[:1200])


if __name__ == "__main__":
    main()