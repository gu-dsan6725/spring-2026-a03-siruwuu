# src/part2_q3.py
from __future__ import annotations

from pathlib import Path
from typing import List

from src.part2_common import load_text_docs, find_best_docs, extract_excerpt


DEFAULT_OUT_FILE = "part2_results.txt"


def answer_q3(data_dir: str = "data", out_file: str | None = DEFAULT_OUT_FILE) -> str:
    """
    Q3: What are the key features of the Wireless Bluetooth Headphones?
    Retrieves from unstructured product page text.
    """
    docs, files = load_text_docs(data_dir)

    query = "Wireless Bluetooth Headphones key features"
    best = find_best_docs(docs, query=query, k=2)

    lines: List[str] = []
    lines.append("Part 2 Results\n")
    lines.append('Q3: "What are the key features of the Wireless Bluetooth Headphones?"\n')
    lines.append("Answer:\n")

    for d in best[:1]:
        excerpt = extract_excerpt(d.text, query=query, max_chars=900)
        lines.append(f"Based on {d.path.name}, the key features mentioned include (excerpt):")
        lines.append("")
        lines.append(excerpt)
        lines.append("")

    lines.append("Files referenced:")
    for d in best[:1]:
        lines.append(f"- {d.path.as_posix()}")
    lines.append("")

    text = "\n".join(lines)
    if out_file:
        Path(out_file).write_text(text, encoding="utf-8")
    return text


def main() -> None:
    text = answer_q3(data_dir="data", out_file=DEFAULT_OUT_FILE)
    print(f"Wrote Q3 results to: {DEFAULT_OUT_FILE}")
    print(text[:1200])


if __name__ == "__main__":
    main()