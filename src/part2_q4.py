# src/part2_q4.py
from __future__ import annotations

from pathlib import Path
from typing import List

from src.part2_common import load_text_docs, find_best_docs, extract_excerpt


DEFAULT_OUT_FILE = "part2_results.txt"


def answer_q4(data_dir: str = "data", out_file: str | None = DEFAULT_OUT_FILE) -> str:
    """
    Q4: What do customers say about the Air Fryer's ease of cleaning?
    Looks for relevant reviews content in unstructured text.
    """
    docs, files = load_text_docs(data_dir)

    query = "Air Fryer ease of cleaning reviews clean easy to clean"
    best = find_best_docs(docs, query=query, k=2)

    lines: List[str] = []
    lines.append("Part 2 Results\n")
    lines.append('Q4: "What do customers say about the Air Fryer\'s ease of cleaning?"\n')
    lines.append("Answer:\n")

    for d in best[:1]:
        excerpt = extract_excerpt(d.text, query="clean", max_chars=900)
        lines.append(f"From customer feedback in {d.path.name}, comments about cleaning include (excerpt):")
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
    text = answer_q4(data_dir="data", out_file=DEFAULT_OUT_FILE)
    print(f"Wrote Q4 results to: {DEFAULT_OUT_FILE}")
    print(text[:1200])


if __name__ == "__main__":
    main()