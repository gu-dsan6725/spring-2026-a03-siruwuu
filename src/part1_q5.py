import os
import re
import subprocess
from typing import List, Tuple, Optional, Dict
from pathlib import Path

from groq import Groq

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


REPO_DIR = "mcp-gateway-registry"
RESULTS_TXT = "part1_results.txt"

Q5_QUESTION = "What are all the API endpoints available in the registry service and what scopes do they require?"

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build", ".next",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}

# -------------------- utils --------------------
def ensure_env_loaded():
    if load_dotenv is None:
        return
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

def run_cmd(cmd: str, cwd: str) -> str:
    p = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
    if p.returncode != 0:
        # grep/rg can return non-zero on no matches, keep output anyway
        out = (p.stdout or "")
        err = (p.stderr or "")
        if err.strip():
            out += "\n[stderr]\n" + err
        return out
    return p.stdout

def has_rg(cwd: str) -> bool:
    return run_cmd("command -v rg >/dev/null 2>&1; echo $?", cwd=cwd).strip() == "0"

def rg_search(cwd: str, query: str, globs: Optional[List[str]] = None, max_lines: int = 400) -> str:
    globs = globs or []
    if has_rg(cwd):
        glob_flags = " ".join([f"-g '{g}'" for g in globs])
        cmd = f"rg -n --hidden --no-heading --smart-case {glob_flags} \"{query}\" . | head -n {max_lines}"
        return run_cmd(cmd, cwd=cwd)
    cmd = f"grep -RIn \"{query}\" . | head -n {max_lines}"
    return run_cmd(cmd, cwd=cwd)

def parse_hits(output: str, limit: int = 30) -> List[Tuple[str, int, str]]:
    hits = []
    for line in output.splitlines():
        m = re.match(r"^(.+?):(\d+):(.*)$", line)
        if not m:
            continue
        hits.append((m.group(1), int(m.group(2)), m.group(3).strip()))
        if len(hits) >= limit:
            break
    return hits

def snippet_with_lineno(cwd: str, rel_path: str, center_line: int, radius: int = 50) -> str:
    start = max(1, center_line - radius)
    end = center_line + radius
    cmd = f"nl -ba \"{rel_path}\" | sed -n '{start},{end}p'"
    return run_cmd(cmd, cwd=cwd)

def safe_truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED]\n"

# -------------------- retrieval for Q5 --------------------
def retrieve_q5_context(repo_dir: str, max_files_snippets: int = 14) -> str:
    cwd = os.path.abspath(repo_dir)
    globs = ["*.py", "*.md", "*.yaml", "*.yml", "*.toml", "*.json"]

    sections: List[str] = []
    sections.append("## Quick repo listing\n" + run_cmd("ls -la", cwd=cwd).strip() + "\n")

    # Find likely FastAPI service files
    sections.append(
        "## Find likely FastAPI/API files\n"
        + run_cmd(
            "find . \\( -path './.git' -o -path './node_modules' -o -path './.venv' -o -path './venv' \\) -prune -o "
            "-type f \\( -iname '*api*.py' -o -iname '*router*.py' -o -iname '*routes*.py' -o -iname '*endpoint*.py' "
            "-o -iname '*main*.py' -o -iname '*app*.py' \\) -print | head -n 200",
            cwd=cwd,
        ).strip()
        + "\n"
    )

    # Pull route decorators and router wiring
    patterns = [
        ("Route decorators", r"(@router\.(get|post|put|patch|delete|options|head)\b|@app\.(get|post|put|patch|delete|options|head)\b)"),
        ("APIRouter definitions", r"(APIRouter\()"),
        ("include_router wiring", r"(include_router\()"),
        ("Security and scopes keywords", r"(Security\(|OAuth2|HTTPBearer|scopes|scope|Depends\(|require_scopes|permission|role)"),
    ]

    expanded_snips: List[str] = []
    seen_files = set()

    for title, pat in patterns:
        out = rg_search(cwd=cwd, query=pat, globs=globs, max_lines=600)
        sections.append(f"## rg search: {title}\n{out.strip()}\n")

        hits = parse_hits(out, limit=200)
        for path, ln, _ in hits:
            if path in seen_files:
                continue
            seen_files.add(path)
            expanded_snips.append(
                f"### Snippet from {path} around line {ln}\n{snippet_with_lineno(cwd, path, ln, radius=55).strip()}\n"
            )
            if len(expanded_snips) >= max_files_snippets:
                break
        if len(expanded_snips) >= max_files_snippets:
            break

    # Try to grab OpenAPI title if present
    openapi_out = rg_search(cwd=cwd, query=r"(openapi|OpenAPI|swagger|docs_url|redoc_url)", globs=globs, max_lines=200)
    if openapi_out.strip():
        sections.append("## rg search: OpenAPI/docs config\n" + openapi_out.strip() + "\n")

    sections.append("## Expanded snippets (line-numbered)\n" + "\n".join(expanded_snips))

    context = "\n".join(sections)
    return safe_truncate(context, max_chars=24000)

# -------------------- Groq call --------------------
def llm_call_groq(question: str, context: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY. Put it in your .env or environment variables.")

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    system = (
        "You are a codebase analyst. Use only the provided context from the repository. "
        "Extract API endpoints and required scopes. If scopes are enforced indirectly (dependencies/middleware), explain that clearly. "
        "Cite files and line ranges when possible."
    )

    user = f"""Question:
{question}

Context (from bash tools):
{context}

Output format requirements:
1) A table-like bullet list of endpoints:
   - METHOD PATH -> handler (file:line range) -> required scopes/roles (or 'not specified in code found')
2) Then a short explanation of how scope requirements are enforced (Security/Depends, middleware, decorators, etc.)
3) If you cannot confidently list all endpoints, say what might be missing and which files to search next.
"""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

# -------------------- write results --------------------
def append_block(path: str, block: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if f.tell() != 0:
            f.write("\n")
        f.write(block)

def format_q5_block(answer: str) -> str:
    return (
        f"Q5: {Q5_QUESTION}\n\n"
        f"{answer}\n\n"
        f"Context note:\nContext was retrieved via find/rg and expanded with nl+sed line-numbered snippets.\n\n"
        + "=" * 80
        + "\n"
    )

# -------------------- main --------------------
if __name__ == "__main__":
    ensure_env_loaded()

    repo_abs = os.path.abspath(REPO_DIR)
    if not os.path.isdir(repo_abs):
        raise RuntimeError(f"Repo folder not found: {repo_abs}. Did you git clone it into your assignment directory?")

    context = retrieve_q5_context(REPO_DIR, max_files_snippets=16)
    answer = llm_call_groq(Q5_QUESTION, context)

    block = format_q5_block(answer)
    append_block(RESULTS_TXT, block)

    print(f"Saved Q5 answer to {RESULTS_TXT}")