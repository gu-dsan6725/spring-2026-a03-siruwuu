import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional

from groq import Groq

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


REPO_DIR = "mcp-gateway-registry"
RESULTS_TXT = "part1_results.txt"

Q6_QUESTION = (
    "How would you add support for a new OAuth provider (e.g., Okta) to the authentication system? "
    "What files would need to be modified and what interfaces must be implemented?"
)

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
        out = (p.stdout or "")
        err = (p.stderr or "")
        if err.strip():
            out += "\n[stderr]\n" + err
        return out
    return p.stdout

def has_rg(cwd: str) -> bool:
    return run_cmd("command -v rg >/dev/null 2>&1; echo $?", cwd=cwd).strip() == "0"

def rg_search(cwd: str, query: str, globs: Optional[List[str]] = None, max_lines: int = 500) -> str:
    globs = globs or []
    if has_rg(cwd):
        glob_flags = " ".join([f"-g '{g}'" for g in globs])
        cmd = f"rg -n --hidden --no-heading --smart-case {glob_flags} \"{query}\" . | head -n {max_lines}"
        return run_cmd(cmd, cwd=cwd)
    cmd = f"grep -RIn \"{query}\" . | head -n {max_lines}"
    return run_cmd(cmd, cwd=cwd)

def parse_hits(output: str, limit: int = 40) -> List[Tuple[str, int, str]]:
    hits = []
    for line in output.splitlines():
        m = re.match(r"^(.+?):(\d+):(.*)$", line)
        if not m:
            continue
        hits.append((m.group(1), int(m.group(2)), m.group(3).strip()))
        if len(hits) >= limit:
            break
    return hits

def snippet_with_lineno(cwd: str, rel_path: str, center_line: int, radius: int = 60) -> str:
    start = max(1, center_line - radius)
    end = center_line + radius
    cmd = f"nl -ba \"{rel_path}\" | sed -n '{start},{end}p'"
    return run_cmd(cmd, cwd=cwd)

def safe_truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED]\n"

# -------------------- retrieval for Q6 --------------------
def retrieve_q6_context(repo_dir: str, max_files_snippets: int = 18) -> str:
    cwd = os.path.abspath(repo_dir)
    globs = ["*.py", "*.md", "*.yaml", "*.yml", "*.toml", "*.json", "*.ts", "*.tsx", "*.js"]

    sections: List[str] = []

    # Locate auth provider implementations / registry
    sections.append(
        "## Find likely OAuth/provider/auth integration files\n"
        + run_cmd(
            "find . \\( -path './.git' -o -path './node_modules' -o -path './.venv' -o -path './venv' \\) -prune -o "
            "-type f \\( -iname '*oauth*' -o -iname '*provider*' -o -iname '*auth*' -o -iname '*oidc*' -o -iname '*sso*' "
            "-o -iname '*jwt*' -o -iname '*openid*' -o -iname '*callback*' -o -iname '*login*' \\) -print | head -n 260",
            cwd=cwd,
        ).strip()
        + "\n"
    )

    # Search for patterns indicating a provider interface / enum / factory / registry
    patterns = [
        ("OAuth/OIDC keywords", r"(oauth|oidc|openid|authorization_url|token_url|issuer|jwks|client_id|client_secret)"),
        ("Provider registry/factory", r"(Provider|provider|AUTH_PROVIDER|OAUTH_PROVIDER|SUPPORTED_PROVIDERS|factory|registry|get_provider|create_provider)"),
        ("FastAPI security wiring", r"(fastapi\.security|OAuth2|OAuth2AuthorizationCodeBearer|OAuth2PasswordBearer|HTTPBearer|Security\(|Depends\()"),
        ("Routes for login/callback", r"(@router\.(get|post)\b.*(login|callback|oauth|authorize)|/callback|/authorize|/login)"),
        ("Config/env settings", r"(ENV|os\.environ|pydantic.*BaseSettings|Settings|config|\.env|CLIENT_ID|CLIENT_SECRET|ISSUER|JWKS|DISCOVERY)"),
        ("Docs mentioning providers", r"(Okta|Auth0|Google|GitHub|Azure|Microsoft|Cognito|Keycloak)"),
    ]

    expanded_snips: List[str] = []
    seen_files = set()

    for title, pat in patterns:
        out = rg_search(cwd=cwd, query=pat, globs=globs, max_lines=700)
        sections.append(f"## rg search: {title}\n{out.strip()}\n")

        hits = parse_hits(out, limit=250)
        for path, ln, _ in hits:
            if path in seen_files:
                continue
            seen_files.add(path)
            expanded_snips.append(
                f"### Snippet from {path} around line {ln}\n{snippet_with_lineno(cwd, path, ln, radius=60).strip()}\n"
            )
            if len(expanded_snips) >= max_files_snippets:
                break
        if len(expanded_snips) >= max_files_snippets:
            break

    sections.append("## Expanded snippets (line-numbered)\n" + "\n".join(expanded_snips))
    context = "\n".join(sections)
    return safe_truncate(context, max_chars=26000)

# -------------------- Groq call --------------------
def llm_call_groq(question: str, context: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY. Put it in your .env or environment variables.")

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    system = (
        "You are a senior engineer reading an unfamiliar codebase. "
        "Using only the provided context, explain how to add a new OAuth provider (Okta) to the existing auth system. "
        "Be specific: list files to edit, interfaces/classes to implement, configs to add, and how the new provider is wired into routing and validation. "
        "If the repo uses OIDC discovery, mention it. If you can't confirm details, say what to search next."
    )

    user = f"""Question:
{question}

Context (from bash tools):
{context}

Deliverables:
1) A step-by-step plan to add Okta support
2) A "files to change" list with brief purpose for each
3) The provider interface/contract you must implement (methods, inputs/outputs), inferred from code
4) New config/env variables needed (e.g., issuer, client_id, client_secret, redirect_uri, scopes)
5) How to test locally (unit/integration, endpoint smoke tests)
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

def format_q6_block(answer: str) -> str:
    return (
        f"Q6: {Q6_QUESTION}\n\n"
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

    context = retrieve_q6_context(REPO_DIR, max_files_snippets=20)
    answer = llm_call_groq(Q6_QUESTION, context)

    block = format_q6_block(answer)
    append_block(RESULTS_TXT, block)

    print(f"Saved Q6 answer to {RESULTS_TXT}")