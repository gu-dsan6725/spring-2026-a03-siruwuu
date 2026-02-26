from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import tomllib
import re

REPO_ROOT = Path("mcp-gateway-registry")
OUT_FILE = Path("part1_results.txt")


@dataclass
class PyProjectDeps:
    rel_path: str
    project_name: str | None
    dependencies: List[str]
    optional_dependencies: Dict[str, List[str]]


def parse_pyproject(pyproject_path: Path) -> PyProjectDeps:
    # Most compatible approach: use tomllib.load on a binary file object
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    proj = data.get("project", {}) or {}
    name = proj.get("name")

    deps = proj.get("dependencies", []) or []
    if not isinstance(deps, list):
        deps = [str(deps)]

    opt = proj.get("optional-dependencies", {}) or {}
    optional_deps: Dict[str, List[str]] = {}
    if isinstance(opt, dict):
        for k, v in opt.items():
            if isinstance(v, list):
                optional_deps[k] = [str(x) for x in v]
            else:
                optional_deps[k] = [str(v)]
    else:
        optional_deps = {}

    return PyProjectDeps(
        rel_path=str(pyproject_path.relative_to(REPO_ROOT)),
        project_name=str(name) if name is not None else None,
        dependencies=[str(d) for d in deps],
        optional_dependencies=optional_deps,
    )


def collect_all_pyprojects() -> List[Path]:
    return sorted(REPO_ROOT.rglob("pyproject.toml"))


def is_core_service(rel_path: str) -> bool:
    return rel_path in {
        "pyproject.toml",
        "auth_server/pyproject.toml",
        "metrics-service/pyproject.toml",
    }


def normalize_pkg_name(dep: str) -> str:
    dep = dep.strip()
    dep = dep.split("@", 1)[0].strip()
    dep = dep.split("[", 1)[0].strip()
    dep = re.split(r"(<=|>=|==|~=|!=|<|>)", dep, maxsplit=1)[0].strip()
    return dep.lower()


def build_summary(core: List[PyProjectDeps]) -> str:
    core_pkgs = []
    for p in core:
        for d in p.dependencies:
            core_pkgs.append(normalize_pkg_name(d))
    core_pkg_set = sorted({x for x in core_pkgs if x})

    keywords = [
        "fastapi", "uvicorn", "pydantic", "httpx", "aiohttp",
        "pymongo", "motor", "pyjwt", "python-jose", "cryptography",
        "sentence-transformers", "faiss-cpu", "prometheus-client",
        "opentelemetry-api", "opentelemetry-sdk",
    ]
    present = [k for k in keywords if k in core_pkg_set]

    lines: List[str] = []
    lines.append("Summary:")
    lines.append(
        "This repository contains multiple Python services. The core services use FastAPI for API serving, "
        "plus libraries for authentication (JWT/Cognito-related), database access (MongoDB drivers), and HTTP clients."
    )
    if present:
        lines.append("Notable dependencies in core services include: " + ", ".join(present) + ".")
    return "\n".join(lines)


def format_q1_answer(core: List[PyProjectDeps], all_projects: List[PyProjectDeps]) -> str:
    lines: List[str] = []
    lines.append("Part 1 Results\n")
    lines.append("Q1: What Python dependencies does this project use?\n")
    lines.append("Answer:\n")

    lines.append("Core services (most relevant):")
    for p in core:
        title = f"- {p.rel_path}"
        if p.project_name:
            title += f" (project.name={p.project_name})"
        lines.append(title)

        if not p.dependencies:
            lines.append("  - (no dependencies listed)")
        else:
            for d in p.dependencies:
                lines.append(f"  - {d}")

        if p.optional_dependencies:
            keys = ", ".join(sorted(p.optional_dependencies.keys()))
            lines.append(f"  - optional-dependencies groups: {keys}")

        lines.append("")

    lines.append("All discovered Python subprojects (pyproject.toml):")
    for p in all_projects:
        title = f"- {p.rel_path}"
        if p.project_name:
            title += f" (project.name={p.project_name})"
        lines.append(title)

    lines.append("")
    lines.append(build_summary(core))
    lines.append("")
    lines.append("Files referenced:")
    for p in core:
        lines.append(f"- {p.rel_path}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if not REPO_ROOT.exists():
        raise FileNotFoundError(f"Repo not found: {REPO_ROOT}")

    pyproject_paths = collect_all_pyprojects()
    parsed: List[PyProjectDeps] = []
    parse_errors: List[Tuple[str, str]] = []

    for p in pyproject_paths:
        rel = str(p.relative_to(REPO_ROOT))
        try:
            parsed.append(parse_pyproject(p))
        except Exception as e:
            parse_errors.append((rel, str(e)))

    core = [p for p in parsed if is_core_service(p.rel_path)]
    if not core:
        # fallback: at least include root pyproject.toml if present
        for p in parsed:
            if p.rel_path == "pyproject.toml":
                core = [p]
                break

    text = format_q1_answer(core, parsed)
    OUT_FILE.write_text(text, encoding="utf-8")

    print(f"Wrote Q1 results to: {OUT_FILE}")
    if parse_errors:
        print("Some pyproject.toml files failed to parse (showing up to 10):")
        for rel, err in parse_errors[:10]:
            print(f"- {rel}: {err}")
        if len(parse_errors) > 10:
            print(f"... and {len(parse_errors) - 10} more")


if __name__ == "__main__":
    main()
