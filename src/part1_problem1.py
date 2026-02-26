from pathlib import Path
import tomllib

ROOT = Path("mcp-gateway-registry")

def load_deps(pyproject_path: Path):
    data = tomllib.loads(pyproject_path.read_text())
    proj = data.get("project", {})
    deps = proj.get("dependencies", [])
    return deps

def main():
    pyprojects = sorted(ROOT.rglob("pyproject.toml"))
    results = []
    for p in pyprojects:
        try:
            deps = load_deps(p)
        except Exception as e:
            deps = [f"[parse error: {e}]"]
        results.append((str(p.relative_to(ROOT)), deps))

    for path, deps in results:
        print(f"\n## {path}")
        for d in deps:
            print(f"- {d}")

if __name__ == "__main__":
    main()