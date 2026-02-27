from __future__ import annotations

import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List


DEFAULT_OUT_FILE = "part1_results.txt"

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build", ".next",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}

EXT_TO_LABEL = {
    ".py": "Python",
    ".ipynb": "Jupyter Notebook",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".txt": "Text",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".sh": "Shell Script",
    ".ps1": "PowerShell",
    ".ini": "INI",
    ".cfg": "Config",
    ".conf": "Config",
    ".xml": "XML",
    ".svg": "SVG",
    ".png": "Image (PNG)",
    ".jpg": "Image (JPG)",
    ".jpeg": "Image (JPEG)",
    ".gif": "Image (GIF)",
    ".lock": "Lockfile",
}

SPECIAL_FILES = {
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "compose.yaml": "Docker Compose (YAML)",
    "compose.yml": "Docker Compose (YAML)",
    "docker-compose.yaml": "Docker Compose (YAML)",
    "docker-compose.yml": "Docker Compose (YAML)",
    "requirements.txt": "Python requirements",
    "pyproject.toml": "Python project config (TOML)",
    "package.json": "Node project config (JSON)",
    "tsconfig.json": "TypeScript config (JSON)",
    ".gitignore": "Git config",
    ".dockerignore": "Docker config",
    "kustomization.yaml": "Kubernetes (Kustomize)",
    "chart.yaml": "Helm chart (YAML)",
}

Q3_QUESTION = (
    "What programming languages and file types are used in this repository? "
    "(e.g., Python, TypeScript, YAML, JSON, Dockerfile, etc.)"
)


def _run(cmd: List[str], cwd: str) -> str:
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr}")
    return p.stdout


def _build_find_prune_args(ignore_dirs: set) -> List[str]:
    args: List[str] = ["("]
    first = True
    for d in sorted(ignore_dirs):
        if not first:
            args += ["-o"]
        first = False
        args += ["-path", f"./{d}"]
    args += [")", "-prune", "-o", "-type", "f", "-print"]
    return args


def detect_languages_and_types(repo_path: str, top_k_examples: int = 3) -> Dict[str, object]:
    repo_path = os.path.abspath(repo_path)

    find_args = ["find", "."] + _build_find_prune_args(IGNORE_DIRS)
    out = _run(find_args, cwd=repo_path).splitlines()
    files = [p[2:] if p.startswith("./") else p for p in out if p.strip()]

    ext_counts = Counter()
    label_counts = Counter()
    label_examples = defaultdict(list)

    special_counts = Counter()
    special_examples = defaultdict(list)

    for rel in files:
        p = Path(rel)
        name_lower = p.name.lower()

        if name_lower in SPECIAL_FILES:
            s_label = SPECIAL_FILES[name_lower]
            special_counts[s_label] += 1
            if len(special_examples[s_label]) < top_k_examples:
                special_examples[s_label].append(rel)

        ext = p.suffix.lower()
        if ext:
            ext_counts[ext] += 1
            label = EXT_TO_LABEL.get(ext, f"Other ({ext})")
        else:
            if re.fullmatch(r"dockerfile(\..+)?", name_lower):
                label = "Dockerfile"
            elif name_lower in ("license", "readme"):
                label = "Text/Docs"
            else:
                label = "Other (no extension)"

        label_counts[label] += 1
        if len(label_examples[label]) < top_k_examples:
            label_examples[label].append(rel)

    by_label = [
        {"label": label, "count": count, "examples": label_examples[label]}
        for label, count in label_counts.most_common()
    ]
    by_ext = [
        {"extension": ext, "count": count, "label_guess": EXT_TO_LABEL.get(ext, f"Other ({ext})")}
        for ext, count in ext_counts.most_common()
    ]
    specials = [
        {"label": label, "count": count, "examples": special_examples[label]}
        for label, count in special_counts.most_common()
    ]

    return {
        "repo_path": repo_path,
        "total_files_scanned": len(files),
        "by_language_or_type": by_label,
        "by_extension": by_ext,
        "special_files": specials,
    }


def format_q3_block(result: Dict[str, object], max_each_section: int = 15) -> str:
    lines: List[str] = []
    lines.append("Q3: " + Q3_QUESTION)
    lines.append("")
    lines.append(f"Repo scanned: {result['repo_path']}")
    lines.append(f"Total files scanned: {result['total_files_scanned']}")
    lines.append("")
    lines.append("Languages / file types (top):")

    for item in result["by_language_or_type"][:max_each_section]:
        ex = ", ".join(item["examples"])
        lines.append(f"- {item['label']}: {item['count']} (e.g., {ex})")

    lines.append("")
    lines.append("Special files (infra/config):")
    if result["special_files"]:
        for item in result["special_files"][:max_each_section]:
            ex = ", ".join(item["examples"])
            lines.append(f"- {item['label']}: {item['count']} (e.g., {ex})")
    else:
        lines.append("- (none detected)")

    lines.append("")
    lines.append("Top extensions:")
    for item in result["by_extension"][:max_each_section]:
        lines.append(f"- {item['extension']}: {item['count']} -> {item['label_guess']}")

    lines.append("")
    lines.append("=" * 80)
    lines.append("")
    return "\n".join(lines)


def _append_to_results(file_path: str, block: str) -> None:
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "a", encoding="utf-8") as f:
        if f.tell() != 0:
            f.write("\n")
        f.write(block)


def answer_q3(
    repo_dir: str,
    out_file: str | None = DEFAULT_OUT_FILE,
    top_k_examples: int = 3,
    max_each_section: int = 15,
) -> str:
    """
    Notebook-friendly entry point for Q3.
    Scans repo file tree (excluding common build/venv dirs), summarizes languages/types.

    Args:
        repo_dir: repo root directory
        out_file: append results to this file; None disables writing
        top_k_examples: how many example paths to show per label
        max_each_section: how many labels/extensions to print

    Returns:
        Formatted Q3 block string.
    """
    repo_root = Path(repo_dir)
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo not found: {repo_root}")

    res = detect_languages_and_types(repo_path=str(repo_root), top_k_examples=top_k_examples)
    block = format_q3_block(res, max_each_section=max_each_section)

    if out_file:
        _append_to_results(out_file, block)

    return block


def main() -> None:
    repo = "mcp-gateway-registry"
    text = answer_q3(repo_dir=repo, out_file=DEFAULT_OUT_FILE)
    print(f"Appended Q3 results to: {DEFAULT_OUT_FILE}")
    print(text[:1200])


if __name__ == "__main__":
    main()