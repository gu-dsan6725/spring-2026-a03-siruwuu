# src/part2_q2.py
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from src.part2_common import load_sales_df


DEFAULT_OUT_FILE = "part2_results.txt"


def answer_q2(data_dir: str = "data", out_file: str | None = DEFAULT_OUT_FILE) -> str:
    """
    Q2: Which region had the highest sales volume?
    Interprets "sales volume" as total units_sold.
    """
    df, csv_path = load_sales_df(data_dir)

    if "region" not in df.columns or "units_sold" not in df.columns:
        raise ValueError("CSV missing required columns: region, units_sold")

    g = df.groupby("region")["units_sold"].sum().sort_values(ascending=False)
    top_region: str = str(g.index[0])
    top_units: int = int(g.iloc[0])

    lines: List[str] = []
    lines.append("Part 2 Results\n")
    lines.append('Q2: "Which region had the highest sales volume?"\n')
    lines.append("Answer:\n")
    lines.append(f'The region with the highest total units sold is "{top_region}" with {top_units} units.')
    lines.append("")
    lines.append("Files referenced:")
    lines.append(f"- {csv_path.as_posix()}")
    lines.append("")

    text = "\n".join(lines)
    if out_file:
        Path(out_file).write_text(text, encoding="utf-8")
    return text


def main() -> None:
    text = answer_q2(data_dir="data", out_file=DEFAULT_OUT_FILE)
    print(f"Wrote Q2 results to: {DEFAULT_OUT_FILE}")
    print(text[:1200])


if __name__ == "__main__":
    main()