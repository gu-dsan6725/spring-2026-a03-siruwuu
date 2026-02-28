# src/part2_q1.py
from __future__ import annotations

from pathlib import Path
from typing import List

from src.part2_common import load_sales_df, month_filter


DEFAULT_OUT_FILE = "part2_results.txt"


def answer_q1(data_dir: str = "data", out_file: str | None = DEFAULT_OUT_FILE) -> str:
    """
    Q1: What was the total revenue for Electronics category in December 2024?
    """
    df, csv_path = load_sales_df(data_dir)

    if "category" not in df.columns or "total_revenue" not in df.columns:
        raise ValueError("CSV missing required columns: category, total_revenue")

    mask = (df["category"] == "Electronics") & month_filter(df, 2024, 12)
    total = float(df.loc[mask, "total_revenue"].sum())

    lines: List[str] = []
    lines.append("Part 2 Results\n")
    lines.append('Q1: "What was the total revenue for Electronics category in December 2024?"\n')
    lines.append("Answer:\n")
    lines.append(f"Total revenue for Electronics in Dec 2024 is {total:.2f}.")
    lines.append("")
    lines.append("Files referenced:")
    lines.append(f"- {csv_path.as_posix()}")
    lines.append("")

    text = "\n".join(lines)
    if out_file:
        Path(out_file).write_text(text, encoding="utf-8")
    return text


def main() -> None:
    text = answer_q1(data_dir="data", out_file=DEFAULT_OUT_FILE)
    print(f"Wrote Q1 results to: {DEFAULT_OUT_FILE}")
    print(text[:1200])


if __name__ == "__main__":
    main()