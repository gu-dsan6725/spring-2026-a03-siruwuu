from __future__ import annotations

import os
import re
import subprocess
from typing import List, Tuple, Optional

from groq import Groq

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


DEFAULT_OUT_FILE = "part1_results.txt"
Q4_QUESTION = "How does the authentication flow work, from token validation to user authorization?"

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build", ".next",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}


# ---------- bash runner ----------
def run_cmd(cmd: str, cwd: str) -> str:
    p = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
    if p.returncode != 0:
        return (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
    return p.stdout


def has_rg(cwd: str) -> bool:
    out = run_cmd("command -v rg >/dev/null 2>&1; echo $?", cwd=cwd).strip()
    return out == "0"


def rg_search(cwd: str, query: str, globs: Optional[List[str]] = None, max_lines: int = 300) -> str:
    globs = globs or []
    if has_rg(cwd):
        glob_flags = " ".join([f"-g '{g}'" for g in globs])
        cmd = f"rg -n --hidden --no-heading --smart-case {glob_flags} \"{query}\" . | head -n {max_lines}"
        return run_cmd(cmd, cwd=cwd)
    cmd = f"grep -RIn \"{query}\" . | head -n {max_lines}"
    return run_cmd(cmd, cwd=cwd)


def snippet_with_lineno(cwd: str, rel_path: str, center_line: int, radius: int = 35) -> str:
    start = max(1, center_line - radius)
    end = center_line + radius
    cmd = f"nl -ba \"{rel_path}\" | sed -n '{start},{end}p'"
    return run_cmd(cmd, cwd=cwd)


def parse_rg_hits(rg_output: str, limit: int = 12) -> List[Tuple[str, int, str]]:
    hits: List[Tuple[str, int, str]] = []
    for line in rg_output.splitlines():
        m = re.match(r"^(.+?):(\d+):(.*)$", line)
        if not m:
            continue
        path, ln, rest = m.group(1), int(m.group(2)), m.group(3).strip()
        hits.append((path, ln, rest))
        if len(hits) >= limit:
            break
    return hits


def safe_truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED]\n"


# ---------- retrieval for Q4 ----------
def retrieve_q4_context(repo_dir: str, max_snippets: int = 10) -> str:
    cwd = os.path.abspath(repo_dir)
    globs = ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.md", "*.yaml", "*.yml", "*.toml", "*.json"]

    sections: List[str] = []
    sections.append("## Repo listing\n" + run_cmd("ls -la", cwd=cwd).strip() + "\n")

    sections.append(
        "## Find likely auth/security files\n"
        + run_cmd(
            "find . "
            "\\( -path './.git' -o -path './node_modules' -o -path './.venv' -o -path './venv' \\) -prune -o "
            "-type f \\( "
            "-iname '*auth*' -o -iname '*oauth*' -o -iname '*token*' -o -iname '*jwt*' -o -iname '*security*' "
            "-o -iname '*middleware*' -o -iname '*permission*' -o -iname '*scope*' -o -iname '*role*' "
            "\\) -print | head -n 200",
            cwd=cwd,
        ).strip()
        + "\n"
    )

    searches = [
        (
            "FastAPI security wiring",
            r"(OAuth2|HTTPBearer|Bearer|Security\(|Depends\(|fastapi\.security|Authorization:|X-API-Key)",
        ),
        (
            "Token/JWT validation",
            r"(jwt|JWKS|JWK|decode\(|verify|signature|bearer|token_url|tokenUrl|issuer|audience|kid)",
        ),
        (
            "Authorization / scopes / roles",
            r"(scope|scopes|role|roles|permission|permissions|authorize|authorized|RBAC|ACL)",
        ),
    ]

    expanded_snippets: List[str] = []
    seen_files: set[str] = set()

    for title, pattern in searches:
        out = rg_search(cwd=cwd, query=pattern, globs=globs, max_lines=400)
        sections.append(f"## rg search: {title}\n{out.strip()}\n")

        hits = parse_rg_hits(out, limit=max_snippets)
        for path, ln, _ in hits:
            if path in seen_files:
                continue
            seen_files.add(path)
            snippet = snippet_with_lineno(cwd=cwd, rel_path=path, center_line=ln, radius=35)
            expanded_snippets.append(f"### Snippet from {path} around line {ln}\n{snippet.strip()}\n")
            if len(expanded_snippets) >= max_snippets:
                break
        if len(expanded_snippets) >= max_snippets:
            break

    sections.append("## Expanded snippets (line-numbered)\n" + "\n".join(expanded_snippets))
    context = "\n".join(sections)

    return safe_truncate(context, max_chars=22000)


# ---------- Groq LLM call ----------
def llm_call_groq(question: str, context: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY. Put it in your .env or environment variables.")

    client = Groq(api_key=api_key)

    system = (
        "You are a codebase analyst. Use the provided repo context to explain the authentication flow. "
        "Be concrete and reference specific files and line ranges when possible. "
        "If context is insufficient, state what is missing and suggest what to search next."
    )

    user = f"""Question:
{question}

Context (from bash tools):
{context}

Write an answer that:
1) Describes the end-to-end auth flow (token extraction -> validation -> identity -> authorization/scopes)
2) Lists key files involved (with short reasons)
3) Mentions any relevant middleware/dependencies and how they are wired
"""

    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


# ---------- write results ----------
def append_block(path: str, block: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if f.tell() != 0:
            f.write("\n")
        f.write(block)


def format_q4_block(answer: str, context_note: str) -> str:
    return (
        f"Q4: {Q4_QUESTION}\n\n"
        f"{answer}\n\n"
        f"Context note:\n{context_note}\n\n"
        + "=" * 80
        + "\n"
    )


def answer_q4(
    repo_dir: str,
    out_file: str | None = DEFAULT_OUT_FILE,
    max_snippets: int = 12,
) -> str:
    """
    Notebook-friendly entry point for Q4.

    Args:
        repo_dir: repo root directory (e.g. "mcp-gateway-registry")
        out_file: append results to this file; None disables writing
        max_snippets: how many file snippets to expand in context

    Returns:
        Formatted Q4 block string (ready to print).
    """
    repo_abs = os.path.abspath(repo_dir)
    if not os.path.isdir(repo_abs):
        raise RuntimeError(f"Repo folder not found: {repo_abs}. Did you git clone it into your assignment directory?")

    context = retrieve_q4_context(repo_dir, max_snippets=max_snippets)
    answer = llm_call_groq(Q4_QUESTION, context)

    block = format_q4_block(
        answer=answer,
        context_note="Context was retrieved via find/rg and expanded with nl+sed line-numbered snippets.",
    )

    if out_file:
        append_block(out_file, block)

    return block


def main() -> None:
    repo = "mcp-gateway-registry"
    block = answer_q4(repo_dir=repo, out_file=DEFAULT_OUT_FILE, max_snippets=12)
    print(f"Saved Q4 answer to {DEFAULT_OUT_FILE}")
    print(block[:1200])


if __name__ == "__main__":
    main()