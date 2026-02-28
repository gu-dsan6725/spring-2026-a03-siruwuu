# src/part2_q5.py
from __future__ import annotations

from pathlib import Path
from typing import List

from src.part2_common import (
    load_sales_df,
    load_text_docs,
    simple_review_sentiment,
    summarize_sales_for_product,
    extract_excerpt,
)


DEFAULT_OUT_FILE = "part2_results.txt"


def answer_q5(data_dir: str = "data", out_file: str | None = DEFAULT_OUT_FILE) -> str:
    """
    Q5: Which product has the best customer reviews and how well is it selling?
    Both sources:
      - Text: heuristic sentiment score for each product page
      - CSV: total units_sold and total_revenue for that product_id
    """
    df, csv_path = load_sales_df(data_dir)
    docs, _ = load_text_docs(data_dir)

    # Pick "best reviewed" by simple heuristic score
    scored = [(simple_review_sentiment(d.text), d) for d in docs]
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_doc = scored[0]

    pid = best_doc.product_id
    sales = summarize_sales_for_product(df, product_id=pid, region=None)

    excerpt = extract_excerpt(best_doc.text, query="review", max_chars=700)

    lines: List[str] = []
    lines.append("Part 2 Results\n")
    lines.append('Q5: "Which product has the best customer reviews and how well is it selling?"\n')
    lines.append("Answer:\n")
    lines.append(
        f"Based on a simple review sentiment heuristic over the product pages, the top product is {pid} "
        f"(score={best_score})."
    )
    lines.append(f"Sales performance for {pid} in the CSV:")
    lines.append(f"- Total units_sold: {int(sales['units_sold'])}")
    lines.append(f"- Total total_revenue: {float(sales['total_revenue']):.2f}")
    lines.append("")
    lines.append(f"Review excerpt from {best_doc.path.name}:")
    lines.append("")
    lines.append(excerpt)
    lines.append("")

    lines.append("Files referenced:")
    lines.append(f"- {csv_path.as_posix()}")
    lines.append(f"- {best_doc.path.as_posix()}")
    lines.append("")

    text = "\n".join(lines)
    if out_file:
        Path(out_file).write_text(text, encoding="utf-8")
    return text


def main() -> None:
    text = answer_q5(data_dir="data", out_file=DEFAULT_OUT_FILE)
    print(f"Wrote Q5 results to: {DEFAULT_OUT_FILE}")
    print(text[:1200])


if __name__ == "__main__":
    main()