from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re


DEFAULT_OUT_FILE = "part1_results.txt"

# Q2: "What is the main entry point file for the registry service?"
# Heuristic:
# 1) Prefer files under registry/ that define a FastAPI app (app = FastAPI(...) or FastAPI(...))
# 2) Extra points if the file also includes routers or mentions uvicorn / __main__
PATTERNS: List[Tuple[str, int]] = [
    (r"\bapp\s*=\s*FastAPI\s*\(", 8),
    (r"\bFastAPI\s*\(", 4),
    (r"\binclude_router\s*\(", 3),
    (r"\bAPIRouter\s*\(", 2),
    (r"\buvicorn\b", 2),
    (r"if\s+__name__\s*==\s*[\"']__main__[\"']\s*:", 3),
]

CANDIDATE_DIRS = ["registry", "api"]  # registry is primary; api is fallback


@dataclass
class FileScore:
    rel_path: str
    score: int
    hits: Dict[str, int]
    first_hit_line: Optional[int]


def count_hits_and_first_line(text: str) -> Tuple[int, Dict[str, int], Optional[int]]:
    score = 0
    hits: Dict[str, int] = {}
    first_line: Optional[int] = None

    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        for pat, weight in PATTERNS:
            if re.search(pat, line):
                score += weight
                hits[pat] = hits.get(pat, 0) + 1
                if first_line is None:
                    first_line = i

    return score, hits, first_line


def gather_py_files(base: Path) -> List[Path]:
    if not base.exists():
        return []
    return [p for p in base.rglob("*.py") if p.is_file()]


def extract_snippet(path: Path, center_line: int, radius: int = 20) -> str:
    lines = path.read_text(errors="replace").splitlines()
    start = max(1, center_line - radius)
    end = min(len(lines), center_line + radius)

    out: List[str] = []
    for ln in range(start, end + 1):
        out.append(f"{ln:>4} | {lines[ln - 1]}")
    return "\n".join(out)


def find_best_entrypoint(repo_root: Path) -> Tuple[Optional[FileScore], List[FileScore]]:
    candidates: List[Path] = []

    for d in CANDIDATE_DIRS:
        candidates.extend(gather_py_files(repo_root / d))

    # fallback: if nothing found in registry/api, scan entire repo
    if not candidates:
        candidates = [p for p in repo_root.rglob("*.py") if p.is_file()]

    scored: List[FileScore] = []
    for p in candidates:
        rel = str(p.relative_to(repo_root))
        try:
            text = p.read_text(errors="replace")
        except Exception:
            continue

        score, hits, first_line = count_hits_and_first_line(text)
        if score > 0:
            scored.append(
                FileScore(rel_path=rel, score=score, hits=hits, first_hit_line=first_line)
            )

    scored.sort(key=lambda x: (x.score, -len(x.hits)), reverse=True)
    best = scored[0] if scored else None
    return best, scored


def format_q2(best: FileScore, snippet: str) -> str:
    lines: List[str] = []
    lines.append("")
    lines.append("Q2: What is the main entry point file for the registry service?")
    lines.append("")
    lines.append("Answer:")
    lines.append(f"The registry service entry point is most likely: {best.rel_path}")
    lines.append("")
    lines.append("Evidence (snippet):")
    lines.append("```")
    lines.append(snippet)
    lines.append("```")
    lines.append("")
    lines.append("Why this file:")
    lines.append(
        "It contains the FastAPI application definition and related routing/setup code, "
        "which typically indicates the service entry point."
    )
    lines.append("")
    lines.append("Files referenced:")
    lines.append(f"- {best.rel_path}")
    lines.append("")
    return "\n".join(lines)


def answer_q2(repo_dir: str, out_file: str | None = DEFAULT_OUT_FILE) -> str:
    """
    Notebook-friendly entry point for Q2.

    Args:
        repo_dir: path to the cloned repository root (e.g. "mcp-gateway-registry")
        out_file: where to append results; set None to disable writing

    Returns:
        The formatted Q2 answer text.
    """
    repo_root = Path(repo_dir)
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo not found: {repo_root}")

    best, scored = find_best_entrypoint(repo_root)

    if best is None:
        text = (
            "\nQ2: What is the main entry point file for the registry service?\n\n"
            "Answer:\n"
            "Could not automatically locate a FastAPI entry point under registry/ or api/. "
            "Try searching manually for 'FastAPI(' under the repo.\n\n"
        )
        if out_file:
            with open(out_file, "a", encoding="utf-8") as f:
                f.write(text)
        return text

    center = best.first_hit_line or 1
    snippet = extract_snippet(repo_root / best.rel_path, center_line=center, radius=20)
    text = format_q2(best, snippet)

    # Append top candidates for transparency/debugging
    if scored:
        text += "Top candidates (debug):\n"
        for s in scored[:5]:
            text += f"- {s.rel_path} (score={s.score})\n"
        text += "\n"

    if out_file:
        with open(out_file, "a", encoding="utf-8") as f:
            f.write(text)

    return text


def main() -> None:
    repo_dir = "mcp-gateway-registry"
    text = answer_q2(repo_dir=repo_dir, out_file=DEFAULT_OUT_FILE)
    print(f"Appended Q2 result to: {DEFAULT_OUT_FILE}")
    print(text[:1200])


if __name__ == "__main__":
    main()